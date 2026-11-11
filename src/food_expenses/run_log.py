"""Журнал прогонів тестів (REQ-NF-005).

Після кожного запуску повного набору тестів у `logs/test-runs.md` додається
запис із датою, часом і рядком «усього N, успішних M, неуспішних K».
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .config import APP_TIMEZONE

RUN_LOG_FILE = "test-runs.md"
HEADER = "# Журнал прогонів тестів\n\nФайл формується автоматично скриптом `tools/run_tests.py` (REQ-NF-005).\n"


def append_test_run(
    log_dir: Path,
    total: int,
    passed: int,
    failed: int,
    duration_seconds: float,
    command: str,
    moment: datetime | None = None,
) -> Path:
    """Додає запис про прогін тестів і повертає шлях до файлу журналу."""

    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / RUN_LOG_FILE

    if not path.exists():
        path.write_text(HEADER, encoding="utf-8")

    stamp = (moment or datetime.now(tz=APP_TIMEZONE)).isoformat(timespec="seconds")
    record = (
        f"\n## {stamp}\n\n"
        f"- Команда: `{command}`\n"
        f"- Результат: усього {total}, успішних {passed}, неуспішних {failed}\n"
        f"- Тривалість: {duration_seconds:.2f} с\n"
    )
    with path.open("a", encoding="utf-8") as stream:
        stream.write(record)
    return path
