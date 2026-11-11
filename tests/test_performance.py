"""Тест швидкодії підсумків (REQ-NF-009).

Критерій прийняття: на базі з 10 000 покупок обчислення підсумку за місяць
триває менше ніж 1 секунду.

Покупки додаються прямо в базу, а не через API: вимірюється обчислення
підсумку, а не швидкість вставляння 10 000 записів через HTTP.
"""

from __future__ import annotations

import time
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from food_expenses.config import APP_TIMEZONE, Settings
from food_expenses.db import Database
from food_expenses.models import Purchase
from food_expenses.repositories.purchases import PurchaseRepository

PURCHASE_COUNT = 10_000
TIME_LIMIT_SECONDS = 1.0


def fill_with_purchases(settings: Settings, profile_id: str, category_id: str) -> None:
    database = Database(settings.database_path)
    first_day = date(2026, 1, 1)
    with database.transaction() as connection:
        repository = PurchaseRepository(connection)
        for index in range(PURCHASE_COUNT):
            moment = datetime.combine(
                first_day + timedelta(days=index % 365),
                datetime.min.time(),
                tzinfo=APP_TIMEZONE,
            )
            repository.add(
                Purchase(
                    id=str(uuid.uuid4()),
                    profile_id=profile_id,
                    category_id=category_id,
                    name=f"Покупка {index}",
                    unit_price=Decimal("10.00"),
                    quantity=Decimal("1"),
                    amount=Decimal("10.00"),
                    occurred_at=moment,
                )
            )


@pytest.mark.requirement("REQ-NF-009")
def test_monthly_summary_on_ten_thousand_purchases_is_under_one_second(client, settings):
    """REQ-NF-009: підсумок за період обчислюється менше ніж за секунду."""

    profile_id = client.post("/profiles", json={"name": "Ілля"}).json()["id"]
    category_id = client.get(f"/profiles/{profile_id}/categories").json()["items"][0]["id"]

    fill_with_purchases(settings, profile_id, category_id)

    started = time.perf_counter()
    response = client.get(
        f"/profiles/{profile_id}/summary", params={"period": "month", "date": "2026-03-15"}
    )
    elapsed = time.perf_counter() - started

    assert response.status_code == 200
    assert response.json()["purchaseCount"] > 0
    assert elapsed < TIME_LIMIT_SECONDS, f"підсумок обчислювався {elapsed:.3f} с"
