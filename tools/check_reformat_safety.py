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

    python tools/check_reformat_safety.py

Код повернення 0 — переформатування безпечне, 1 — знайдено розбіжність або
файл перестав розбиратися.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TARGETS = ("src", "tests", "tools")


def python_files() -> list[Path]:
    """Усі файли з розширенням `.py`, на які поширюється конвенція.

    Returns:
        Відсортований перелік шляхів відносно кореня проєкту, включно з
        файлами в корені (`run_server.py`).
    """
    found: list[Path] = sorted(PROJECT_ROOT.glob("*.py"))
    for name in TARGETS:
        found.extend(sorted((PROJECT_ROOT / name).rglob("*.py")))
    return found


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
    файл на диску не змінюється й перевірку можна робити до застосування
    форматування.

    Args:
        source: Початковий текст програми.
        name: Шлях файла — ruff використовує його, щоб знайти конфігурацію.

    Returns:
        Переформатований текст.
    """
    result = subprocess.run(
        ["ruff", "format", "--stdin-filename", name, "-"],
        input=source,
        capture_output=True,
        text=True,
        check=True,
        cwd=PROJECT_ROOT,
    )
    return result.stdout


def main() -> int:
    """Порівнює дерева розбору до й після форматування для кожного файла."""
    changed: list[str] = []
    broken: list[str] = []
    checked = 0

    for path in python_files():
        relative = path.relative_to(PROJECT_ROOT).as_posix()
        original = path.read_text(encoding="utf-8")
        formatted = format_source(original, relative)
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

    print(f"Перевірено файлів: {checked}")
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
