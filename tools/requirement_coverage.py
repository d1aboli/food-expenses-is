#!/usr/bin/env python3
"""Покриття вимог автоматизованими тестами (REQ-NF-002).

    python tools/requirement_coverage.py

Збирає перелік вимог із `spec/srs.tex` і `spec/addendum-01-budgets.md`,
знаходить у каталозі `tests` позначки `@pytest.mark.requirement("REQ-...")`
і будує звіт `docs/requirement-coverage.md`.

Вимоги рівня інтерфейсу користувача свідомо не реалізуються в ЛР5, тому вони
перелічені окремо й не вважаються прогалиною.
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRS_PATH = PROJECT_ROOT / "spec" / "srs.tex"
ADDENDUM_PATH = PROJECT_ROOT / "spec" / "addendum-01-budgets.md"
TESTS_DIR = PROJECT_ROOT / "tests"
REPORT_PATH = PROJECT_ROOT / "docs" / "requirement-coverage.md"

SRS_REQUIREMENT = re.compile(r"\\req\{(REQ-[A-Z]+-\d+)\}")
ADDENDUM_REQUIREMENT = re.compile(r"^\|\s*(REQ-A-\d+)\s*\|", re.MULTILINE)
MARK = re.compile(r'@pytest\.mark\.requirement\("(REQ-[A-Z]+-\d+)"\)')
TEST_NAME = re.compile(r"^def (test_\w+)", re.MULTILINE)

#: Вимоги рівня інтерфейсу користувача: поза обсягом ЛР5 (серверна реалізація).
OUT_OF_SCOPE = {
    "REQ-I-001": "вебсторінка з формою, списком і графіком",
    "REQ-I-002": "вибір активного профілю в інтерфейсі",
    "REQ-I-004": "формати дати й часу в інтерфейсі",
    "REQ-NF-012": "файли перекладів для української та англійської",
    "REQ-NF-014": "побудова графіків бібліотекою Chart.js у браузері",
}

#: Вимоги процесу: перевіряються не тестом, а історією Git і записами в /logs.
PROCESS_REQUIREMENTS = {
    "REQ-NF-001": "порядок «тест раніше за код» — історія Git і logs/test-gate.md",
    "REQ-NF-002": "цей звіт",
    "REQ-NF-003": "запуск набору однією командою — tools/run_tests.py",
    "REQ-NF-004": "порядок комітів test: і feat: — історія Git",
    "REQ-NF-006": "записи сесій роботи з агентом — logs/agent-session-03.md",
    "REQ-NF-007": "позначка [agent] у повідомленнях комітів",
    "REQ-NF-011": "запис у базу в момент підтвердження — транзакції SQLite",
    "REQ-NF-013": "стек Python, FastAPI, SQLite",
    "REQ-NF-015": "розміщення коду в /src і тестів у /tests",
}


def declared_requirements() -> list[str]:
    requirements = SRS_REQUIREMENT.findall(SRS_PATH.read_text(encoding="utf-8"))
    requirements += ADDENDUM_REQUIREMENT.findall(ADDENDUM_PATH.read_text(encoding="utf-8"))
    seen: list[str] = []
    for requirement in requirements:
        if requirement not in seen:
            seen.append(requirement)
    return seen


def tests_by_requirement() -> dict[str, list[str]]:
    coverage: dict[str, list[str]] = defaultdict(list)
    for path in sorted(TESTS_DIR.glob("test_*.py")):
        text = path.read_text(encoding="utf-8")
        for match in MARK.finditer(text):
            name = TEST_NAME.search(text, match.end())
            if name is not None:
                coverage[match.group(1)].append(f"{path.name}::{name.group(1)}")
    return coverage


def main() -> int:
    requirements = declared_requirements()
    coverage = tests_by_requirement()

    covered, process, out_of_scope, missing = [], [], [], []
    for requirement in requirements:
        if coverage.get(requirement):
            covered.append(requirement)
        elif requirement in OUT_OF_SCOPE:
            out_of_scope.append(requirement)
        elif requirement in PROCESS_REQUIREMENTS:
            process.append(requirement)
        else:
            missing.append(requirement)

    lines = [
        "# Покриття вимог тестами",
        "",
        "Звіт формується автоматично: `python tools/requirement_coverage.py` (REQ-NF-002).",
        "",
        "| Показник | Кількість |",
        "|---|---|",
        f"| Вимог оголошено | {len(requirements)} |",
        f"| Покрито тестами | {len(covered)} |",
        f"| Перевіряються процесом, а не тестом | {len(process)} |",
        f"| Поза обсягом ЛР5 | {len(out_of_scope)} |",
        f"| Без покриття | {len(missing)} |",
        "",
        "## Вимоги, покриті тестами",
        "",
        "| Вимога | Тестів | Тести |",
        "|---|---|---|",
    ]
    for requirement in covered:
        tests = coverage[requirement]
        lines.append(f"| {requirement} | {len(tests)} | {'<br>'.join(tests)} |")

    lines += ["", "## Вимоги процесу", "", "| Вимога | Чим перевіряється |", "|---|---|"]
    for requirement in process:
        lines.append(f"| {requirement} | {PROCESS_REQUIREMENTS[requirement]} |")

    lines += ["", "## Поза обсягом ЛР5", "", "| Вимога | Зміст |", "|---|---|"]
    for requirement in out_of_scope:
        lines.append(f"| {requirement} | {OUT_OF_SCOPE[requirement]} |")

    if missing:
        lines += ["", "## Без покриття", ""]
        lines += [f"- {requirement}" for requirement in missing]

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Вимог оголошено: {len(requirements)}")
    print(f"Покрито тестами: {len(covered)}")
    print(f"Перевіряються процесом: {len(process)}")
    print(f"Поза обсягом ЛР5: {len(out_of_scope)}")
    print(f"Без покриття: {len(missing)}")
    for requirement in missing:
        print(f"  БЕЗ ТЕСТУ: {requirement}")
    print(f"Звіт: {REPORT_PATH.relative_to(PROJECT_ROOT)}")

    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
