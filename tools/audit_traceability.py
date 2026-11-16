#!/usr/bin/env python3
"""Аудит матриці простежуваності.

Крок 12 лабораторної роботи №6. Матриця — це таблиця посилань, і вона
старіє так само, як будь-яка документація: вимогу додали, рядок забули;
модуль перейменували, у матриці лишилася стара назва. Прочитати це
неможливо — 64 рядки по вісім колонок читаються як суцільна стіна.

Інструмент перевіряє сім видів розривів:

1. **Вимога без рядка.** ID оголошений у SRS чи адендумі, але в матриці
   його немає.
2. **Рядок без вимоги.** У матриці є ID, якого немає в специфікації.
3. **Порожній зв'язок.** Вимога в обсязі роботи, але без тесту або без коду.
4. **Посилання на неіснуючий тест.** Названий файл тестів не існує.
5. **Посилання на неіснуючий модуль.** Названий модуль коду не існує.
6. **Посилання на неіснуючу операцію.** Адреса API не оголошена в контракті.
7. **Тест без вимоги.** Тест без позначки `@pytest.mark.requirement`.

Запуск:

    python tools/audit_traceability.py

Код повернення 0 — розривів немає, 1 — знайдено розрив.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = PROJECT_ROOT / "spec" / "traceability.md"
SRS_PATH = PROJECT_ROOT / "spec" / "srs.tex"
ADDENDUM_PATH = PROJECT_ROOT / "spec" / "addendum-01-budgets.md"
CONTRACT_PATH = PROJECT_ROOT / "spec" / "api" / "openapi.yaml"
SOURCE_DIR = PROJECT_ROOT / "src" / "food_expenses"
TESTS_DIR = PROJECT_ROOT / "tests"
REPORT_PATH = PROJECT_ROOT / "docs" / "traceability-audit.md"

SRS_REQUIREMENT = re.compile(r"\\req\{(REQ-[A-Z]+-\d+)\}")
ADDENDUM_REQUIREMENT = re.compile(r"^\|\s*(REQ-A-\d+)\s*\|", re.MULTILINE)
MATRIX_ROW = re.compile(r"^\|\s*(REQ-[A-Z]+-\d+)\s*\|(.+)$", re.MULTILINE)
RANGE_ROW = re.compile(r"^\|\s*(REQ-[A-Z]+-\d+)\.\.(REQ-[A-Z]+-\d+)\s*\|", re.MULTILINE)
BACKTICKED = re.compile(r"`([^`]+)`")
API_ROUTE = re.compile(r"\b(GET|POST|PATCH|DELETE|PUT)\s+(/[A-Za-z0-9_{}/-]*)")
TEST_FUNCTION = re.compile(r"^def (test_\w+)", re.MULTILINE)
REQUIREMENT_MARK = re.compile(r'@pytest\.mark\.requirement\("(REQ-[A-Z]+-\d+)"\)')

#: Вимоги, які свідомо винесені за межі роботи. Порожній зв'язок для них —
#: не розрив, а зафіксоване рішення (розділ «Вимоги поза обсягом» матриці).
OUT_OF_SCOPE = frozenset({"REQ-I-001", "REQ-I-002", "REQ-I-004", "REQ-NF-012", "REQ-NF-014"})

#: Вимоги, для яких автоматизований тест не є доказом, із причиною для
#: кожної. Перелік короткий і явний навмисно: без нього достатньо було б
#: оголосити «тест не потрібен» будь-де, і перевірка перестала б щось
#: означати. Причини друкуються у звіті, тому виняток лишається на видноті.
NO_TEST_EXPECTED = {
    "REQ-NF-001": "доводиться порядком комітів в історії Git і журналом logs/test-gate.md",
    "REQ-NF-002": "доводиться інструментом tools/requirement_coverage.py, а не тестом",
    "REQ-NF-003": "доводиться тим, що прогін тестів завершується без помилок",
    "REQ-NF-004": "доводиться історією Git: коміт test: передує коміту feat:",
    "REQ-NF-006": "доводиться журналом сесії агента logs/agent-session-03.md",
    "REQ-NF-007": "доводиться позначкою [agent] у повідомленнях комітів",
    "REQ-NF-011": "доводиться будовою коду: запис у межах транзакції",
    "REQ-NF-013": "доводиться складом залежностей: FastAPI і SQLite в requirements.txt",
    "REQ-NF-015": "доводиться структурою каталогів репозиторію",
}

#: Тести, у яких немає позначки вимоги, із причиною для кожного.
#: Єдиний запис — наслідок справжнього розриву, описаного як відкрите
#: питання ВП-07: журналювання всіх дій системи вимагає завдання практикуму,
#: але жодна вимога затвердженої SRS його не описує.
TESTS_WITHOUT_REQUIREMENT = {
    "test_application_start_is_written_to_action_log": (
        "перевіряє журнал дій системи; відповідної вимоги в SRS немає — ВП-07"
    ),
}


@dataclass(frozen=True)
class Gap:
    """Один розрив у матриці.

    Attributes:
        kind: Вид розриву.
        subject: ID вимоги або ім'я тесту, якого він стосується.
        detail: Пояснення.
    """

    kind: str
    subject: str
    detail: str


def declared_requirements() -> list[str]:
    """ID вимог, оголошені в специфікації та адендумі.

    Returns:
        ID у порядку появи, без повторів.
    """
    seen: list[str] = []
    for text, pattern in (
        (SRS_PATH.read_text(encoding="utf-8"), SRS_REQUIREMENT),
        (ADDENDUM_PATH.read_text(encoding="utf-8"), ADDENDUM_REQUIREMENT),
    ):
        for found in pattern.findall(text):
            if found not in seen:
                seen.append(found)
    return seen


def matrix_rows() -> dict[str, str]:
    """Рядки матриці за ID вимоги.

    Рядки з діапазоном (`REQ-A-001..REQ-A-009`) до основних таблиць не
    належать — це таблиця документації, і вона розбирається окремо.

    Returns:
        Відображення «ID вимоги -> решта рядка».
    """
    text = MATRIX_PATH.read_text(encoding="utf-8")
    rows: dict[str, str] = {}
    for identifier, rest in MATRIX_ROW.findall(text):
        rows.setdefault(identifier, rest)
    return rows


def documented_requirements() -> set[str]:
    """ID вимог, для яких у матриці вказано розділ документації.

    Діапазон `REQ-F-001..REQ-F-004` розгортається в усі ID між межами за
    умови, що префікс у них однаковий.

    Returns:
        Множина ID.
    """
    text = MATRIX_PATH.read_text(encoding="utf-8")
    covered: set[str] = set()
    section = text.partition("## Зв'язок вимог із документацією")[2].partition("\n## ")[0]
    for identifier, rest in MATRIX_ROW.findall(section):
        covered.add(identifier)
        del rest
    for first, last in RANGE_ROW.findall(section):
        prefix, _, start = first.rpartition("-")
        other_prefix, _, end = last.rpartition("-")
        if prefix != other_prefix:
            continue
        for number in range(int(start), int(end) + 1):
            covered.add(f"{prefix}-{number:03d}")
    return covered


def contract_routes() -> set[tuple[str, str]]:
    """Пари «метод, шлях» із затвердженого контракту.

    Returns:
        Множина пар; шлях — без префікса `/api/v1`.
    """
    document = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
    return {
        (method.upper(), path)
        for path, operations in document.get("paths", {}).items()
        for method, operation in operations.items()
        if isinstance(operation, dict) and "operationId" in operation
    }


def tests_by_requirement() -> dict[str, list[str]]:
    """Тести з позначкою вимоги.

    Returns:
        Відображення «ID вимоги -> імена тестів».
    """
    coverage: dict[str, list[str]] = {}
    for path in sorted(TESTS_DIR.glob("test_*.py")):
        text = path.read_text(encoding="utf-8")
        for block in text.split("@pytest.mark.requirement")[1:]:
            identifier = REQUIREMENT_MARK.search("@pytest.mark.requirement" + block)
            name = TEST_FUNCTION.search(block)
            if identifier and name:
                coverage.setdefault(identifier.group(1), []).append(name.group(1))
    return coverage


def unmarked_tests() -> list[tuple[str, str]]:
    """Тести без позначки вимоги.

    Returns:
        Пари «файл, ім'я тесту».
    """
    found: list[tuple[str, str]] = []
    for path in sorted(TESTS_DIR.glob("test_*.py")):
        text = path.read_text(encoding="utf-8")
        marked = set()
        for block in text.split("@pytest.mark.requirement")[1:]:
            name = TEST_FUNCTION.search(block)
            if name:
                marked.add(name.group(1))
        for name in TEST_FUNCTION.findall(text):
            if name not in marked:
                found.append((path.name, name))
    return found


def check_references(identifier: str, row: str, routes: set[tuple[str, str]]) -> list[Gap]:
    """Перевіряє, що все, на що посилається рядок матриці, існує.

    Args:
        identifier: ID вимоги.
        row: Решта рядка матриці.
        routes: Адреси з контракту.

    Returns:
        Перелік розривів у цьому рядку.
    """
    gaps: list[Gap] = []
    for reference in BACKTICKED.findall(row):
        reference = reference.strip()
        if reference.startswith("test_") and reference.endswith(".py"):
            if not (TESTS_DIR / reference).exists():
                gaps.append(Gap("неіснуючий тест", identifier, reference))
        elif reference.endswith(".py") and not any(
            (root / reference).exists() for root in (SOURCE_DIR, PROJECT_ROOT)
        ):
            gaps.append(Gap("неіснуючий модуль", identifier, reference))
    for method, route in API_ROUTE.findall(row):
        if (method, route) not in routes:
            gaps.append(Gap("неіснуюча операція", identifier, f"{method} {route}"))
    return gaps


def main() -> int:
    """Перевіряє матрицю на розриви й пише звіт."""
    declared = declared_requirements()
    rows = matrix_rows()
    documented = documented_requirements()
    routes = contract_routes()
    coverage = tests_by_requirement()

    gaps: list[Gap] = []

    for identifier in declared:
        if identifier not in rows:
            gaps.append(Gap("вимога без рядка", identifier, "немає в матриці"))

    for identifier in rows:
        if identifier not in declared:
            gaps.append(Gap("рядок без вимоги", identifier, "немає в специфікації"))

    for identifier, row in rows.items():
        if identifier not in declared:
            continue
        gaps.extend(check_references(identifier, row, routes))
        if identifier in OUT_OF_SCOPE:
            continue
        if identifier not in coverage and identifier not in NO_TEST_EXPECTED:
            gaps.append(Gap("порожній зв'язок", identifier, "немає тесту з позначкою вимоги"))
        if identifier not in documented and identifier not in OUT_OF_SCOPE:
            gaps.append(Gap("порожній зв'язок", identifier, "немає розділу документації"))

    without_requirement = [
        (file_name, name)
        for file_name, name in unmarked_tests()
        if name not in TESTS_WITHOUT_REQUIREMENT
    ]
    gaps.extend(
        Gap("тест без вимоги", f"{file_name}::{name}", "немає @pytest.mark.requirement")
        for file_name, name in without_requirement
    )

    by_kind: dict[str, int] = {}
    for gap in gaps:
        by_kind[gap.kind] = by_kind.get(gap.kind, 0) + 1

    lines = [
        "# Аудит матриці простежуваності",
        "",
        "Звіт складається інструментом `tools/audit_traceability.py`",
        "(крок 12 лабораторної роботи №6).",
        "",
        "| Показник | Значення |",
        "|---|---|",
        f"| Вимог оголошено | {len(declared)} |",
        f"| Рядків у матриці | {len(rows)} |",
        f"| Вимог із розділом документації | {len(documented & set(declared))} |",
        f"| Вимог поза обсягом роботи | {len(OUT_OF_SCOPE)} |",
        f"| Вимог, що доводяться не тестом | {len(NO_TEST_EXPECTED)} |",
        f"| Тестів із позначкою вимоги | {sum(len(v) for v in coverage.values())} |",
        f"| Тестів без позначки | {len(without_requirement)} |",
        f"| Розривів | {len(gaps)} |",
        "",
    ]
    if gaps:
        lines += ["## Розриви", "", "| Вид | Вимога або тест | Деталі |", "|---|---|---|"]
        lines += [f"| {g.kind} | `{g.subject}` | {g.detail} |" for g in gaps]
    else:
        lines += [
            "Розривів немає. Кожна оголошена вимога має рядок у матриці; кожен",
            "рядок матриці посилається на вимогу, що існує; кожен названий тест,",
            "модуль і операція існують; кожен тест прив'язаний до вимоги.",
        ]
    lines += [
        "",
        "## Вимоги, для яких тест не є доказом",
        "",
        "| ID | Чим доводиться |",
        "|---|---|",
        *(f"| {key} | {value} |" for key, value in sorted(NO_TEST_EXPECTED.items())),
        "",
        "## Тести без позначки вимоги",
        "",
        "| Тест | Чому |",
        "|---|---|",
        *(f"| `{key}` | {value} |" for key, value in sorted(TESTS_WITHOUT_REQUIREMENT.items())),
    ]
    lines.append("")
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print(f"Вимог оголошено: {len(declared)}")
    print(f"Рядків у матриці: {len(rows)}")
    print(f"Тестів із позначкою вимоги: {sum(len(v) for v in coverage.values())}")
    print(f"Розривів: {len(gaps)}")
    for kind, count in sorted(by_kind.items(), key=lambda item: -item[1]):
        print(f"  {kind}: {count}")
    for gap in gaps[:30]:
        print(f"    {gap.kind}: {gap.subject} — {gap.detail}")
    if len(gaps) > 30:
        print(f"    ... ще {len(gaps) - 30}")
    print(f"Звіт: {REPORT_PATH.relative_to(PROJECT_ROOT).as_posix()}")
    return 1 if gaps else 0


if __name__ == "__main__":
    sys.exit(main())
