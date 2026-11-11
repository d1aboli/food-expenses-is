"""Тести каркаса системи: база даних, журнали, журнал прогонів тестів.

Джерело вимог — spec/srs.tex (версія 1.0), розділи «Процес розробки»,
«Журналювання» та «Збереження даних».
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

import pytest

from food_expenses.api.app import create_app
from food_expenses.api.error_handling import error_body
from food_expenses.config import Settings
from food_expenses.db import Database
from food_expenses.errors import ErrorDetail
from food_expenses.logging_setup import configure_logging, log_event
from food_expenses.run_log import append_test_run

ISO_WITH_OFFSET = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}")


@pytest.mark.requirement("REQ-F-034")
def test_migration_creates_tables_for_profiles_categories_and_purchases(settings: Settings):
    """REQ-F-034: дані зберігаються в локальній базі даних."""

    database = Database(settings.database_path)
    database.migrate()

    assert {"profiles", "categories", "purchases"} <= database.table_names()


@pytest.mark.requirement("REQ-F-034")
def test_migration_is_idempotent(settings: Settings):
    """REQ-F-034: повторний запуск застосунку не руйнує наявну базу."""

    database = Database(settings.database_path)
    first = database.migrate()
    second = database.migrate()

    assert first == second
    assert {"profiles", "categories", "purchases"} <= database.table_names()


def test_application_start_is_written_to_action_log(settings: Settings):
    """Усі дії системи потрапляють у журнал app.log."""

    create_app(settings)

    content = (settings.log_dir / "app.log").read_text(encoding="utf-8")
    assert "event=application.started" in content


@pytest.mark.requirement("REQ-NF-008")
def test_runtime_error_is_written_to_error_log_with_date_and_text(settings: Settings):
    """REQ-NF-008: помилки виконання пишуться з датою, часом і текстом."""

    configure_logging(settings.log_dir)
    log_event("request.failed", level=logging.ERROR, message="база даних недоступна")

    lines = (settings.log_dir / "errors.log").read_text(encoding="utf-8").splitlines()

    assert len(lines) == 1
    assert "база даних недоступна" in lines[0]
    assert ISO_WITH_OFFSET.match(lines[0]), lines[0]


@pytest.mark.requirement("REQ-NF-008")
def test_error_log_does_not_collect_ordinary_actions(settings: Settings):
    """REQ-NF-008: у журналі помилок немає звичайних дій."""

    configure_logging(settings.log_dir)
    log_event("purchase.created", purchase="22222222-0000-4000-8000-000000000001")

    assert (settings.log_dir / "errors.log").read_text(encoding="utf-8") == ""
    assert "event=purchase.created" in (settings.log_dir / "app.log").read_text(encoding="utf-8")


@pytest.mark.requirement("REQ-NF-005")
def test_test_run_journal_records_date_and_counts(settings: Settings):
    """REQ-NF-005: запис прогону містить дату й рядок «усього N, успішних M, неуспішних K»."""

    path = append_test_run(
        log_dir=settings.log_dir,
        total=3,
        passed=2,
        failed=1,
        duration_seconds=1.234,
        command="python tools/run_tests.py",
    )

    content = path.read_text(encoding="utf-8")
    assert path.name == "test-runs.md"
    assert "усього 3, успішних 2, неуспішних 1" in content
    assert datetime.now().strftime("%Y-%m-%d") in content


@pytest.mark.requirement("REQ-NF-005")
def test_test_run_journal_keeps_previous_records(settings: Settings):
    """REQ-NF-005: журнал накопичує прогони, а не перезаписує останній."""

    append_test_run(settings.log_dir, 1, 1, 0, 0.1, "перший прогін")
    path = append_test_run(settings.log_dir, 2, 2, 0, 0.2, "другий прогін")

    content = path.read_text(encoding="utf-8")
    assert "перший прогін" in content
    assert "другий прогін" in content


@pytest.mark.requirement("REQ-F-019")
def test_error_body_matches_contract_error_schema():
    """REQ-F-019: єдина модель помилки зі spec/api/openapi.yaml."""

    body = error_body(
        code="VALIDATION_FAILED",
        message="Ціна має бути більшою за нуль.",
        requirement="REQ-F-013",
        details=[ErrorDetail("unitPrice", "must be > 0")],
        trace_id="7f3a1c2e-0000-4000-8000-00000000ff01",
    )

    assert body == {
        "error": {
            "code": "VALIDATION_FAILED",
            "message": "Ціна має бути більшою за нуль.",
            "requirement": "REQ-F-013",
            "details": [{"field": "unitPrice", "issue": "must be > 0"}],
        },
        "traceId": "7f3a1c2e-0000-4000-8000-00000000ff01",
    }
