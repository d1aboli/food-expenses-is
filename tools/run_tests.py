#!/usr/bin/env python3
"""Запуск повного набору тестів однією командою (REQ-NF-003).

    python tools/run_tests.py

Скрипт викликає pytest, зчитує звіт у форматі JUnit XML і додає запис про
прогін у `logs/test-runs.md` (REQ-NF-005). Код повернення повторює код pytest,
тому скрипт можна використовувати як умову перед комітом.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from food_expenses.run_log import append_test_run  # noqa: E402

COMMAND = "python tools/run_tests.py"


def _parse_junit(report: Path) -> tuple[int, int, int]:
    """Повертає кортеж (усього, успішних, неуспішних)."""

    root = ET.parse(report).getroot()
    suites = [root] if root.tag == "testsuite" else list(root)
    total = failed = skipped = 0
    for suite in suites:
        total += int(suite.get("tests", 0))
        failed += int(suite.get("failures", 0)) + int(suite.get("errors", 0))
        skipped += int(suite.get("skipped", 0))
    return total, total - failed - skipped, failed


def main(argv: list[str]) -> int:
    with tempfile.TemporaryDirectory() as workdir:
        report = Path(workdir) / "report.xml"
        started = time.perf_counter()
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", f"--junitxml={report}", *argv],
            cwd=PROJECT_ROOT,
        )
        duration = time.perf_counter() - started

        if report.exists():
            total, passed, failed = _parse_junit(report)
        else:
            total = passed = 0
            failed = 1

    log_path = append_test_run(
        log_dir=PROJECT_ROOT / "logs",
        total=total,
        passed=passed,
        failed=failed,
        duration_seconds=duration,
        command=COMMAND if not argv else f"{COMMAND} {' '.join(argv)}",
    )
    print(f"\nПрогін записано: {log_path.relative_to(PROJECT_ROOT)}")
    print(f"Результат: усього {total}, успішних {passed}, неуспішних {failed}")
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
