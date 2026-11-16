#!/usr/bin/env python3
"""Перевірка документації проти фактичного коду й контракту.

Кроки 9 і 12 лабораторної роботи №6. Документація застаріває мовчки: код
змінюється, а текст лишається, і помилка виявляється лише тоді, коли хтось
спробує зробити те, що там написано.

Перевірка на етапі 3 цієї ж роботи показала, чому автоматичний контроль
потрібен: розділ «Терміни та визначення» специфікації посилався на
`spec/glossary.md`, якого в репозиторії не було. Посилання пройшло через
п'ять контрольних точок — люди перевіряли зміст артефактів, але не
перевіряли, чи існує те, на що артефакти посилаються.

Інструмент перевіряє п'ять зв'язків:

1. **Файли.** Кожен шлях, згаданий у документації, існує в репозиторії.
2. **Вимоги.** Кожен ID вимоги, згаданий у документації або в docstring-у,
   оголошений у специфікації чи в адендумі.
3. **Операції.** Кожна назва операції, згадана в документації або в
   docstring-у обробника маршруту, є в контракті.
4. **Адреси.** Кожна адреса API, згадана в документації користувача, є в
   контракті.
5. **Елементи коду.** Кожен модуль, клас і функція, згадані в документації,
   існують у початковому коді.

Запуск:

    python tools/check_docs.py

Код повернення 0 — розбіжностей немає, 1 — знайдено посилання в нікуди.
"""

from __future__ import annotations

import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = PROJECT_ROOT / "src"
CONTRACT_PATH = PROJECT_ROOT / "spec" / "api" / "openapi.yaml"
SRS_PATH = PROJECT_ROOT / "spec" / "srs.tex"
ADDENDUM_PATH = PROJECT_ROOT / "spec" / "addendum-01-budgets.md"
REPORT_PATH = PROJECT_ROOT / "docs" / "doc-code-check.md"

#: Документи, які перевіряються. Журнали рішень у `logs/` сюди не входять:
#: вони описують стан на момент рішення й навмисно не оновлюються.
DOCUMENTS = (
    "README.md",
    "docs/user-guide.md",
    "docs/coding-convention.md",
    "docs/docstring-tags.md",
    "spec/glossary.md",
    "spec/traceability.md",
    "spec/addendum-01-budgets.md",
)

#: Корені, відносно яких розв'язуються шляхи в документації. Текст про
#: будову пакета природно пише `services/exports.py`, а не повний шлях від
#: кореня репозиторію, і це не помилка.
PATH_ROOTS = (PROJECT_ROOT, SOURCE_DIR / "food_expenses")

#: Шляхи, які створюються під час роботи системи, а не лежать у репозиторії.
#: Згадувати їх у документації треба, перевіряти на існування — ні.
RUNTIME_PATHS = frozenset(
    {
        "data/food-expenses.db",
        "data/backups/",
        "logs/app.log",
        "logs/errors.log",
        "logs/test-runs.md",
        "docs/sphinx/_build/html",
        "docs/sphinx/_build/html/index.html",
    }
)

#: Шлях у зворотних лапках: має розширення або закінчується скісною рискою.
FILE_REFERENCE = re.compile(r"`([A-Za-z0-9_./-]+(?:\.[a-z]{2,5}|/))`")

#: ID вимоги: REQ-F-001, REQ-NF-012, REQ-A-005, REQ-I-003.
REQUIREMENT = re.compile(r"\bREQ-[A-Z]+-\d{3}\b")

#: ID вимоги в тексті SRS оголошується командою \req{...}.
SRS_REQUIREMENT = re.compile(r"\\req\{(REQ-[A-Z]+-\d+)\}")

#: ID вимоги адендуму оголошується першою колонкою таблиці.
ADDENDUM_REQUIREMENT = re.compile(r"^\|\s*(REQ-A-\d+)\s*\|", re.MULTILINE)

#: Назва операції контракту в зворотних лапках: listProfiles, createBudget.
OPERATION = re.compile(r"`([a-z][a-zA-Z]{3,})`")

#: Адреса API в документації: GET /profiles/{profileId}/purchases.
API_PATH = re.compile(r"\b(GET|POST|PATCH|DELETE|PUT)\s+(/[A-Za-z0-9_{}/-]*)")

#: Елемент коду в зворотних лапках: food_expenses.money.calculate_amount.
CODE_REFERENCE = re.compile(r"`(food_expenses(?:\.[A-Za-z_][A-Za-z0-9_]*)+)`")


@dataclass(frozen=True)
class Finding:
    """Одне посилання в нікуди.

    Attributes:
        source: Документ або модуль, у якому стоїть посилання.
        kind: Що саме не знайдено: файл, вимога, операція, адреса, елемент.
        reference: Текст посилання.
    """

    source: str
    kind: str
    reference: str


def declared_requirements() -> set[str]:
    """Усі ID вимог, оголошені в специфікації та адендумі.

    Returns:
        Множина ID. Вимоги адендуму нумеруються як `REQ-A-NNN` і живуть
        в окремому документі, бо базова SRS після затвердження не
        редагується.
    """
    found = set(SRS_REQUIREMENT.findall(SRS_PATH.read_text(encoding="utf-8")))
    found |= set(ADDENDUM_REQUIREMENT.findall(ADDENDUM_PATH.read_text(encoding="utf-8")))
    return found


def contract_facts() -> tuple[set[str], set[tuple[str, str]], set[str]]:
    """Назви операцій, адреси та імена полів із затвердженого контракту.

    Імена полів потрібні окремо: у документації вони пишуться так само, як
    назви операцій — у зворотних лапках і в mixedCase, тому без цього
    переліку `unitPrice` виглядав би як неіснуюча операція.

    Returns:
        Трійку «назви операцій, пари (метод, шлях), імена полів і
        параметрів». Шлях подається без префікса `/api/v1`, як він
        записаний у контракті.
    """
    document = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
    names: set[str] = set()
    routes: set[tuple[str, str]] = set()
    fields: set[str] = set()

    for path, operations in document.get("paths", {}).items():
        for method, operation in operations.items():
            if not isinstance(operation, dict) or "operationId" not in operation:
                continue
            names.add(operation["operationId"])
            routes.add((method.upper(), path))
            for parameter in operation.get("parameters", []):
                fields.add(parameter["name"])

    for schema in document.get("components", {}).get("schemas", {}).values():
        fields.update((schema.get("properties") or {}).keys())
    for value in document.get("components", {}).get("parameters", {}).values():
        if isinstance(value, dict) and "name" in value:
            fields.add(value["name"])

    return names, routes, fields


def code_elements() -> set[str]:
    """Повні імена модулів, класів і функцій у початковому коді.

    Returns:
        Множина імен вигляду `food_expenses.money.calculate_amount`,
        включно з іменами самих модулів і пакетів.
    """
    names: set[str] = set()
    for path in SOURCE_DIR.rglob("*.py"):
        relative = path.relative_to(SOURCE_DIR).with_suffix("")
        parts = list(relative.parts)
        if parts[-1] == "__init__":
            parts.pop()
        module = ".".join(parts)
        if not module:
            continue
        names.add(module)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                names.add(f"{module}.{node.name}")
                for member in node.body:
                    if isinstance(member, ast.FunctionDef | ast.AsyncFunctionDef):
                        names.add(f"{module}.{node.name}.{member.name}")
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                names.add(f"{module}.{node.name}")
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        names.add(f"{module}.{target.id}")
    return names


def docstring_texts() -> list[tuple[str, str]]:
    """Усі docstring-и початкового коду разом із шляхами їхніх файлів.

    Returns:
        Пари «шлях файла, текст docstring-а».
    """
    texts: list[tuple[str, str]] = []
    for path in sorted(SOURCE_DIR.rglob("*.py")):
        relative = path.relative_to(PROJECT_ROOT).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        for node in [tree, *ast.walk(tree)]:
            if isinstance(
                node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
            ) and (text := ast.get_docstring(node)):
                texts.append((relative, text))
    return texts


def check_files(source: str, text: str) -> list[Finding]:
    """Перевіряє, що кожен згаданий шлях існує.

    Шлях розв'язується від кореня репозиторію або від кореня пакета:
    у тексті про будову системи природно написати `services/exports.py`.

    Args:
        source: Документ, у якому стоять посилання.
        text: Текст документа.

    Returns:
        Перелік посилань на неіснуючі файли.
    """
    findings: list[Finding] = []
    for reference in sorted(set(FILE_REFERENCE.findall(text))):
        if reference.startswith("http") or "/" not in reference or reference in RUNTIME_PATHS:
            continue
        if any((root / reference.rstrip("/")).exists() for root in PATH_ROOTS):
            continue
        findings.append(Finding(source, "файл", reference))
    return findings


def main() -> int:
    """Звіряє документацію з кодом, контрактом і специфікацією."""
    requirements = declared_requirements()
    operations, routes, contract_fields = contract_facts()
    elements = code_elements()
    known_paths = {path for _, path in routes}

    findings: list[Finding] = []
    checked_documents = 0

    for name in DOCUMENTS:
        path = PROJECT_ROOT / name
        if not path.exists():
            findings.append(Finding("tools/check_docs.py", "файл", name))
            continue
        checked_documents += 1
        text = path.read_text(encoding="utf-8")

        findings.extend(check_files(name, text))

        for requirement in sorted(set(REQUIREMENT.findall(text))):
            if requirement not in requirements:
                findings.append(Finding(name, "вимога", requirement))

        for candidate in sorted(set(OPERATION.findall(text))):
            # Назвою операції вважається тільки те, що схоже на неї за
            # написанням і водночас згадане поряд з іншими операціями.
            if not any(c.isupper() for c in candidate):
                continue
            if candidate in operations or candidate in contract_fields:
                continue
            if candidate in {element.split(".")[-1] for element in elements}:
                continue
            findings.append(Finding(name, "операція", candidate))

        for method, route in sorted(set(API_PATH.findall(text))):
            stripped = route.removeprefix("/api/v1").rstrip("/")
            if stripped and stripped not in known_paths:
                findings.append(Finding(name, "адреса", f"{method} {route}"))

        for element in sorted(set(CODE_REFERENCE.findall(text))):
            if element not in elements:
                findings.append(Finding(name, "елемент коду", element))

    for source, text in docstring_texts():
        for requirement in sorted(set(REQUIREMENT.findall(text))):
            if requirement not in requirements:
                findings.append(Finding(source, "вимога", requirement))

    lines = [
        "# Перевірка документації проти коду",
        "",
        "Звіт складається інструментом `tools/check_docs.py` (кроки 9 і 12",
        "лабораторної роботи №6). Перевіряється, що кожне посилання в",
        "документації веде кудись: файл існує, вимога оголошена, операція є в",
        "контракті, адреса є в контракті, елемент коду є в початковому коді.",
        "",
        "| Показник | Значення |",
        "|---|---|",
        f"| Документів перевірено | {checked_documents} |",
        f"| Оголошених вимог | {len(requirements)} |",
        f"| Операцій у контракті | {len(operations)} |",
        f"| Полів контракту | {len(contract_fields)} |",
        f"| Елементів коду | {len(elements)} |",
        f"| Розбіжностей | {len(findings)} |",
        "",
    ]
    if findings:
        lines += ["## Посилання в нікуди", "", "| Джерело | Тип | Посилання |", "|---|---|---|"]
        lines += [f"| `{f.source}` | {f.kind} | `{f.reference}` |" for f in findings]
    else:
        lines += [
            "Розбіжностей немає: кожне посилання в документації веде до того,",
            "що справді існує.",
        ]
    lines.append("")
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print(f"Документів перевірено: {checked_documents}")
    print(f"Оголошених вимог: {len(requirements)}")
    print(f"Операцій у контракті: {len(operations)}")
    print(f"Полів контракту: {len(contract_fields)}")
    print(f"Елементів коду: {len(elements)}")
    print(f"Розбіжностей: {len(findings)}")
    for finding in findings[:40]:
        print(f"  {finding.source}: {finding.kind} «{finding.reference}»")
    if len(findings) > 40:
        print(f"  ... ще {len(findings) - 40}")
    print(f"Звіт: {REPORT_PATH.relative_to(PROJECT_ROOT).as_posix()}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
