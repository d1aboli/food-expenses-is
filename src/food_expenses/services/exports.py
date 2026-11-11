"""Експорт покупок у CSV (REQ-F-035, REQ-I-003)."""

from __future__ import annotations

import csv
import io
from datetime import date

from ..db import Database
from ..logging_setup import log_event
from ..money import format_money, format_quantity
from ..repositories.purchases import PurchaseRepository
from .guards import require_profile

#: REQ-I-003: склад і порядок колонок файлу експорту.
CSV_HEADER = ["name", "category", "unitPrice", "quantity", "amount", "occurredAt"]


class ExportService:
    """Формування файлу CSV з покупками профілю за період."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def purchases_csv(
        self, profile_id: str, since: date | None = None, until: date | None = None
    ) -> str:
        """REQ-F-035: рядок заголовків і по одному рядку на кожну покупку періоду."""

        with self._database.transaction() as connection:
            require_profile(connection, profile_id)
            items, _ = PurchaseRepository(connection).list_for_profile(
                profile_id, since=since, until=until, limit=None
            )

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(CSV_HEADER)
        for purchase, category_name in items:
            writer.writerow(
                [
                    purchase.name,
                    category_name,
                    format_money(purchase.unit_price),
                    format_quantity(purchase.quantity),
                    format_money(purchase.amount),
                    purchase.occurred_at.isoformat(timespec="seconds"),
                ]
            )

        log_event("purchases.exported", profile=profile_id, rows=len(items))
        return buffer.getvalue()

    @staticmethod
    def file_name(since: date | None, until: date | None) -> str:
        """Ім'я файлу відображає період, за який зроблено вибірку."""

        if since and until:
            return f"purchases-{since.isoformat()}_{until.isoformat()}.csv"
        if since:
            return f"purchases-from-{since.isoformat()}.csv"
        if until:
            return f"purchases-to-{until.isoformat()}.csv"
        return "purchases-all.csv"
