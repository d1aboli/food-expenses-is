"""Спільні умови для всіх тестів.

Кожен тест отримує власний каталог: окремий файл бази даних і окремі журнали.
Тому прогін тестів не залежить від порядку тестів і не чіпає робочі дані.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from food_expenses.api.app import create_app
from food_expenses.config import API_PREFIX, Settings


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_path=tmp_path / "data" / "food-expenses.db",
        log_dir=tmp_path / "logs",
        backup_dir=tmp_path / "data" / "backups",
    )


@pytest.fixture
def client(settings: Settings) -> TestClient:
    """Клієнт REST API з базовою адресою /api/v1, як у контракті."""

    app = create_app(settings)
    with TestClient(app, base_url=f"http://localhost{API_PREFIX}") as test_client:
        yield test_client
