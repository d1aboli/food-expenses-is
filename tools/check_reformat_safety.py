#!/usr/bin/env python3
"""Перевірка, що автоматичне переформатування не змінює поведінки програми.

Крок 2 лабораторної роботи №6 дозволяє автоматичне переформатування лише за
умови, що воно не змінює зовнішню поведінку. Прогін тестів після
переформатування цю умову підтверджує, але не доводить: тест перевіряє те, що
перевіряє, і може не зачепити змінений рядок.

Цей інструмент дає сильніше твердження. Він розбирає кожен файл двічі — до й
після форматування — і порівнює абстрактні синтаксичні дерева з відкинутими
номерами рядків і стовпців. Якщо дерева збігаються, форматувальник змінив
лише пробіли, переноси й лапки: виконуваний код той самий, і зміни поведінки
не може бути за побудовою.

Запуск:

    python tools/check_reformat_safety.py            # поточний стан файлів
    python tools/check_reformat_safety.py --rev HEAD~1   # стан із історії Git

Другий варіант потрібен, коли форматування вже застосовано: він бере вміст
файлів із указаного коміту, форматує його в пам'яті й порівнює дерева. Так
доказ лишається відтворюваним і після того, як зміни потрапили в репозиторій.

Код повернення 0 — переформатування безпечне, 1 — знайдено розбіжність або
файл перестав розбиратися.
"""

from __future__ import annotations

import argparse
import ast
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TARGETS = ("src", "tests", "tools")


class ToolError(RuntimeError):
    """Зовнішня програма завершилася помилкою."""


def run(command: list[str], stdin: str | None = None) -> str:
    """Запускає зовнішню програму й повертає її вивід.

    Кодування задається явно. Без цього Python на Windows бере кодування
    локалі (cp1251), і український текст у початковому коді не передається
    ні на вхід програми, ні назад — саме на цьому інструмент уперше впав
    під час перевірки на цільовій платформі.

    Args:
        command: Програма та її аргументи.
        stdin: Текст, що подається на стандартний вхід.

    Returns:
        Стандартний вивід програми.

    Raises:
        ToolError: Програма завершилася ненульовим кодом або її не знайдено.
    """
    try:
        result = subprocess.run(
            command,
            input=stdin,
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=PROJECT_ROOT,
            check=False,
        )
    except FileNotFoundError as error:
        raise ToolError(f"не знайдено програму {command[0]}: {error}") from error
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "").strip()
        raise ToolError(f"{' '.join(command)} -> код {result.returncode}: {message}")
    return result.stdout


def python_files() -> list[Path]:
    """Усі файли з розширенням `.py`, на які поширюється конвенція.

    Returns:
        Відсортований перелік шляхів, включно з файлами в корені проєкту
        (`run_server.py`).
    """
    found: list[Path] = sorted(PROJECT_ROOT.glob("*.py"))
    for name in TARGETS:
        found.extend(sorted((PROJECT_ROOT / name).rglob("*.py")))
    return found


def source_at_revision(revision: str, relative: str) -> str | None:
    """Вміст файла в заданому коміті.

    Args:
        revision: Будь-яка назва коміту, яку розуміє Git.
        relative: Шлях файла відносно кореня репозиторію.

    Returns:
        Текст файла або `None`, якщо в тому коміті файла ще не було.
    """
    try:
        return run(["git", "show", f"{revision}:{relative}"])
    except ToolError:
        return None


def tree_of(source: str, name: str) -> str:
    """Текстове подання дерева розбору без номерів рядків.

    Args:
        source: Текст програми на Python.
        name: Ім'я файла — потрібне лише для повідомлення про помилку.

    Returns:
        Рядок, у якому однакові програми дають однаковий результат незалежно
        від розташування пробілів і переносів.

    Raises:
        SyntaxError: Якщо текст не розбирається як Python.
    """
    return ast.dump(ast.parse(source, filename=name), include_attributes=False)


def format_source(source: str, name: str) -> str:
    """Повертає текст, переформатований `ruff format`.

    Форматувальник викликається в режимі читання зі стандартного входу, тому
    файл на диску не змінюється й перевірку можна робити як до застосування
    форматування, так і після нього.

    Args:
        source: Початковий текст програми.
        name: Шлях файла — `ruff` використовує його, щоб знайти конфігурацію.

    Returns:
        Переформатований текст.

    Raises:
        ToolError: `ruff` недоступний або завершився помилкою.
    """
    return run([sys.executable, "-m", "ruff", "format", "--stdin-filename", name, "-"], source)


def main() -> int:
    """Порівнює дерева розбору до й після форматування для кожного файла."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rev",
        help="брати вміст файлів із цього коміту замість поточного стану",
    )
    arguments = parser.parse_args()

    changed: list[str] = []
    broken: list[str] = []
    checked = 0
    skipped = 0

    for path in python_files():
        relative = path.relative_to(PROJECT_ROOT).as_posix()
        if arguments.rev:
            original = source_at_revision(arguments.rev, relative)
            if original is None:
                skipped += 1
                continue
        else:
            original = path.read_text(encoding="utf-8")

        try:
            formatted = format_source(original, relative)
        except ToolError as error:
            broken.append(f"{relative}: {error}")
            continue
        checked += 1
        if formatted == original:
            continue
        try:
            same = tree_of(original, relative) == tree_of(formatted, relative)
        except SyntaxError as error:
            broken.append(f"{relative}: {error}")
            continue
        if same:
            changed.append(relative)
        else:
            broken.append(f"{relative}: дерево розбору змінилося")

    source = f"коміт {arguments.rev}" if arguments.rev else "поточний стан файлів"
    print(f"Джерело: {source}")
    print(f"Перевірено файлів: {checked}")
    if skipped:
        print(f"Пропущено (у тому коміті ще не було): {skipped}")
    print(f"Форматування змінило б: {len(changed)}")
    for name in changed:
        print(f"  {name}")
    if broken:
        print()
        print("РОЗБІЖНОСТІ:")
        for item in broken:
            print(f"  {item}")
        print()
        print("Переформатування НЕ є безпечним.")
        return 1

    print()
    print("Дерева розбору збігаються в усіх файлах: переформатування змінює")
    print("лише пробіли, переноси й лапки.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
