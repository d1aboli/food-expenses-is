#!/usr/bin/env python3
"""Перевірка повноти docstring-ів за правилами docs/docstring-tags.md.

`ruff` із набором правил `D` перевіряє, що docstring є і що він правильно
оформлений. Він не перевіряє, чи описані параметри й результат: docstring з
одного рядка над функцією з п'ятьма аргументами правила `D` проходить.

Цей інструмент перевіряє саме зміст:

* функція з параметрами (крім `self` і `cls`) має секцію `Args`, і в ній
  згадані всі параметри;
* функція, що повертає не `None`, має секцію `Returns`, а генератор —
  `Yields`;
* у секції `Args` немає імен, яких немає в сигнатурі.

Конструктор, тіло якого складається з одного виклику `super().__init__`,
перевірці не підлягає: він нічого не додає до батьківського, і docstring над
ним переказував би код. Так оголошені підкласи помилок у `errors.py`, кожен з
яких лише задає типове повідомлення; саме повідомлення наведене в docstring-у
класу.

Обробники маршрутів у `api/routers/` — виняток, і виняток зі своєю, сильнішою
вимогою. Їхні параметри та відповіді задані затвердженим контрактом
`spec/api/openapi.yaml`; переписати їх у `Args` означало б завести друге
джерело правди, яке розійдеться з контрактом при першій же правці. Натомість
від docstring-а обробника вимагається назвати операцію контракту, яку він
реалізує, і ця назва перевіряється проти самого контракту: якщо операцію
перейменують або приберуть, перевірка впаде.

Звіт записується в `docs/docstring-coverage.md`.

Запуск:

    python tools/check_docstrings.py

Код повернення 0 — зауважень немає, 1 — знайдено неповні docstring-и.
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = PROJECT_ROOT / "src"
CONTRACT_PATH = PROJECT_ROOT / "spec" / "api" / "openapi.yaml"
REPORT_PATH = PROJECT_ROOT / "docs" / "docstring-coverage.md"

#: Каталог обробників маршрутів. Для них діє окреме правило: замість
#: `Args` і `Returns` docstring має назвати операцію контракту.
ROUTERS_PREFIX = "src/food_expenses/api/routers/"

#: Параметри, які не є параметрами виклику і в `Args` не описуються.
IMPLICIT_PARAMETERS = {"self", "cls"}

#: Назви секцій Google-style, які розпізнає інструмент.
SECTIONS = ("Args", "Returns", "Yields", "Raises", "Attributes", "Note", "Example")


@dataclass(frozen=True)
class Finding:
    """Одне зауваження до docstring-а.

    Attributes:
        location: Шлях файла й номер рядка.
        name: Повне ім'я елемента, наприклад `PurchaseService.create`.
        issue: Чого саме бракує.
    """

    location: str
    name: str
    issue: str


def sections_of(docstring: str) -> dict[str, list[str]]:
    """Розбирає docstring на секції Google-style.

    Args:
        docstring: Текст docstring-а без лапок.

    Returns:
        Відображення «назва секції -> її рядки». Текст до першої секції
        не повертається: він не перевіряється.
    """
    result: dict[str, list[str]] = {}
    current: str | None = None
    for raw in docstring.splitlines():
        stripped = raw.strip()
        heading = stripped[:-1] if stripped.endswith(":") else ""
        if heading in SECTIONS:
            current = heading
            result[current] = []
        elif current is not None:
            result[current].append(raw)
    return result


def documented_parameters(lines: list[str]) -> set[str]:
    """Імена параметрів, згадані в секції `Args`.

    Опис параметра може займати кілька рядків, тому ім'ям вважається лише
    те, що стоїть на початку рядка з найменшим відступом у секції.

    Args:
        lines: Рядки секції `Args`.

    Returns:
        Множина імен параметрів.
    """
    indents = [len(line) - len(line.lstrip()) for line in lines if line.strip()]
    if not indents:
        return set()
    base = min(indents)
    names: set[str] = set()
    for line in lines:
        if not line.strip() or (len(line) - len(line.lstrip())) != base:
            continue
        head, separator, _ = line.strip().partition(":")
        if separator and head and " " not in head:
            names.add(head.strip("*"))
    return names


def only_delegates(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Чи складається тіло функції з одного виклику `super().__init__`.

    Args:
        node: Вузол оголошення функції або методу.

    Returns:
        `True`, якщо тіло — рівно один такий виклик і нічого більше.
    """
    if len(node.body) != 1:
        return False
    statement = node.body[0]
    if not (isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call)):
        return False
    function = statement.value.func
    return (
        isinstance(function, ast.Attribute)
        and function.attr == "__init__"
        and isinstance(function.value, ast.Call)
        and isinstance(function.value.func, ast.Name)
        and function.value.func.id == "super"
    )


def declared_parameters(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """Імена параметрів функції, які належить описати в `Args`.

    Args:
        node: Вузол оголошення функції або методу.

    Returns:
        Імена параметрів без `self`, `cls` і без `**kwargs`-подібних, які
        описуються текстом, а не окремим рядком.
    """
    arguments = node.args
    names = [a.arg for a in (*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs)]
    return [name for name in names if name not in IMPLICIT_PARAMETERS]


def returns_value(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Чи оголошено, що функція повертає значення.

    Args:
        node: Вузол оголошення функції або методу.

    Returns:
        `True`, якщо анотація результату є і це не `None`.
    """
    annotation = node.returns
    if annotation is None:
        return False
    return not (isinstance(annotation, ast.Constant) and annotation.value is None)


def is_generator(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Чи є функція генератором.

    Args:
        node: Вузол оголошення функції або методу.

    Returns:
        `True`, якщо в тілі є `yield`, не рахуючи вкладених функцій.
    """
    for child in ast.walk(node):
        if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef) and child is not node:
            continue
        if isinstance(child, ast.Yield | ast.YieldFrom):
            return True
    return False


def contract_operations() -> set[str]:
    """Назви операцій (`operationId`) із затвердженого контракту.

    Returns:
        Множина назв операцій, наприклад `listProfiles`, `createBudget`.
    """
    document = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
    names: set[str] = set()
    for operations in document.get("paths", {}).values():
        for operation in operations.values():
            if isinstance(operation, dict) and "operationId" in operation:
                names.add(operation["operationId"])
    return names


def check_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    qualified: str,
    relative: str,
    operations: set[str],
) -> list[Finding]:
    """Перевіряє повноту docstring-а однієї функції чи методу.

    Args:
        node: Вузол оголошення.
        qualified: Повне ім'я для звіту.
        relative: Шлях файла відносно кореня проєкту.
        operations: Назви операцій контракту — для обробників маршрутів.

    Returns:
        Перелік зауважень; порожній, якщо docstring повний.
    """
    docstring = ast.get_docstring(node)
    location = f"{relative}:{node.lineno}"
    if node.name == "__init__" and only_delegates(node):
        return []
    if docstring is None:
        return [Finding(location, qualified, "немає docstring-а")]

    if relative.startswith(ROUTERS_PREFIX):
        named = {name for name in operations if f"`{name}`" in docstring}
        if not named:
            return [
                Finding(
                    location,
                    qualified,
                    "docstring не називає жодної операції контракту",
                )
            ]
        return []

    findings: list[Finding] = []
    sections = sections_of(docstring)
    expected = declared_parameters(node)

    if expected and "Args" not in sections:
        findings.append(Finding(location, qualified, "немає секції Args"))
    elif expected:
        described = documented_parameters(sections["Args"])
        allowed = set(expected)
        for extra_argument in (node.args.vararg, node.args.kwarg):
            if extra_argument is not None:
                allowed.add(extra_argument.arg)
        missing = [name for name in expected if name not in described]
        extra = [name for name in sorted(described) if name not in allowed]
        if missing:
            findings.append(Finding(location, qualified, f"в Args немає: {', '.join(missing)}"))
        if extra:
            findings.append(
                Finding(location, qualified, f"в Args зайве: {', '.join(extra)}"),
            )

    if returns_value(node):
        needed = "Yields" if is_generator(node) else "Returns"
        if needed not in sections:
            findings.append(Finding(location, qualified, f"немає секції {needed}"))

    return findings


def walk_module(path: Path, operations: set[str]) -> tuple[list[Finding], int]:
    """Перевіряє всі публічні елементи одного модуля.

    Args:
        path: Шлях до файла з початковим кодом.
        operations: Назви операцій контракту — для обробників маршрутів.

    Returns:
        Пара «зауваження, кількість перевірених елементів».
    """
    relative = path.relative_to(PROJECT_ROOT).as_posix()
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
    findings: list[Finding] = []
    checked = 0

    def visit(node: ast.AST, prefix: str) -> None:
        nonlocal checked
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                if child.name.startswith("_"):
                    continue
                visit(child, f"{prefix}{child.name}.")
            elif isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                if child.name.startswith("_") and not child.name.startswith("__"):
                    continue
                checked += 1
                findings.extend(
                    check_function(child, f"{prefix}{child.name}", relative, operations)
                )

    visit(tree, "")
    return findings, checked


def main() -> int:
    """Перевіряє повноту docstring-ів у `src/` і пише звіт."""
    findings: list[Finding] = []
    checked = 0
    operations = contract_operations()
    modules = sorted(SOURCE_DIR.rglob("*.py"))
    for path in modules:
        module_findings, module_checked = walk_module(path, operations)
        findings.extend(module_findings)
        checked += module_checked

    lines = [
        "# Повнота docstring-ів",
        "",
        "Звіт складається інструментом `tools/check_docstrings.py` за правилами",
        "`docs/docstring-tags.md`. Перевіряється не наявність docstring-а —",
        "це робить `ruff` із набором `D` — а наявність секцій `Args`, `Returns`",
        "і `Yields` там, де вони потрібні за сигнатурою.",
        "",
        "| Показник | Значення |",
        "|---|---|",
        f"| Модулів перевірено | {len(modules)} |",
        f"| Публічних функцій, методів і класів | {checked} |",
        f"| Зауважень | {len(findings)} |",
        "",
    ]
    if findings:
        lines += ["## Зауваження", "", "| Місце | Елемент | Чого бракує |", "|---|---|---|"]
        lines += [f"| `{f.location}` | `{f.name}` | {f.issue} |" for f in findings]
    else:
        lines += [
            "Зауважень немає: кожна публічна функція й метод із параметрами має",
            "секцію `Args` з повним переліком, а кожна, що повертає значення, —",
            "секцію `Returns` або `Yields`.",
        ]
    lines.append("")
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print(f"Модулів перевірено: {len(modules)}")
    print(f"Публічних елементів: {checked}")
    print(f"Зауважень: {len(findings)}")
    for finding in findings[:40]:
        print(f"  {finding.location} {finding.name}: {finding.issue}")
    if len(findings) > 40:
        print(f"  ... ще {len(findings) - 40}")
    print(f"Звіт: {REPORT_PATH.relative_to(PROJECT_ROOT).as_posix()}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
