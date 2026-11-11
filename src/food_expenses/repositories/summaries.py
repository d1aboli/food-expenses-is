"""Вибірка даних для підсумків і графіків.

Суми не обчислюються в SQL навмисно. Грошові значення зберігаються текстом,
і функція `SUM` звела б їх до числа з рухомою комою, тобто втратила б копійки
(REQ-NF-010). Тому репозиторій віддає рядки, а підсумовує їх служба в
`Decimal`.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class PurchaseAmount:
    """Одна покупка в тому вигляді, який потрібен для підсумку."""

    occurred_date: date
    category_id: str
    category_name: str
    amount: Decimal


class SummaryRepository:
    """Читання покупок періоду для подальшого підсумовування."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def amounts_between(self, profile_id: str, start: date, end: date) -> list[PurchaseAmount]:
        """Покупки профілю за період, включно з обома межами (REQ-F-029)."""

        rows = self._connection.execute(
            """
            SELECT p.occurred_date, p.category_id, p.amount, c.name AS category_name
            FROM purchases p JOIN categories c ON c.id = p.category_id
            WHERE p.profile_id = ?
              AND p.occurred_date >= ?
              AND p.occurred_date <= ?
            """,
            (profile_id, start.isoformat(), end.isoformat()),
        ).fetchall()

        return [
            PurchaseAmount(
                occurred_date=date.fromisoformat(row["occurred_date"]),
                category_id=row["category_id"],
                category_name=row["category_name"],
                amount=Decimal(row["amount"]),
            )
            for row in rows
        ]
