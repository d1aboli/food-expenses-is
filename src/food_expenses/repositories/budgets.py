"""Доступ до таблиці бюджетів (адендум ADD-01)."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from decimal import Decimal

from ..models import Budget


def _to_budget(row: sqlite3.Row) -> Budget:
    return Budget(
        id=row["id"],
        profile_id=row["profile_id"],
        category_id=row["category_id"],
        monthly_limit=Decimal(row["monthly_limit"]),
        created_at=datetime.fromisoformat(row["created_at"]),
    )


SELECT_COLUMNS = "b.id, b.profile_id, b.category_id, b.monthly_limit, b.created_at"


class BudgetRepository:
    """Читання й запис бюджетів у межах профілю."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add(self, budget: Budget) -> None:
        self._connection.execute(
            """
            INSERT INTO budgets (id, profile_id, category_id, monthly_limit, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                budget.id,
                budget.profile_id,
                budget.category_id,
                str(budget.monthly_limit),
                budget.created_at.isoformat(timespec="seconds"),
            ),
        )

    def list_for_profile(self, profile_id: str) -> list[tuple[Budget, str]]:
        """Бюджети профілю разом із назвами категорій, у порядку створення."""

        rows = self._connection.execute(
            f"""
            SELECT {SELECT_COLUMNS}, c.name AS category_name
            FROM budgets b JOIN categories c ON c.id = b.category_id
            WHERE b.profile_id = ?
            ORDER BY b.rowid
            """,
            (profile_id,),
        ).fetchall()
        return [(_to_budget(row), row["category_name"]) for row in rows]

    def get(self, profile_id: str, budget_id: str) -> tuple[Budget, str] | None:
        row = self._connection.execute(
            f"""
            SELECT {SELECT_COLUMNS}, c.name AS category_name
            FROM budgets b JOIN categories c ON c.id = b.category_id
            WHERE b.id = ? AND b.profile_id = ?
            """,
            (budget_id, profile_id),
        ).fetchone()
        return (_to_budget(row), row["category_name"]) if row else None

    def find_by_category(self, profile_id: str, category_id: str) -> Budget | None:
        row = self._connection.execute(
            f"""
            SELECT {SELECT_COLUMNS}
            FROM budgets b
            WHERE b.profile_id = ? AND b.category_id = ?
            """,
            (profile_id, category_id),
        ).fetchone()
        return _to_budget(row) if row else None

    def set_limit(self, budget_id: str, monthly_limit: Decimal) -> None:
        self._connection.execute(
            "UPDATE budgets SET monthly_limit = ? WHERE id = ?",
            (str(monthly_limit), budget_id),
        )

    def delete(self, budget_id: str) -> None:
        self._connection.execute("DELETE FROM budgets WHERE id = ?", (budget_id,))

    def delete_for_category(self, category_id: str) -> int:
        """REQ-A-008: разом із категорією зникає і її бюджет."""

        cursor = self._connection.execute(
            "DELETE FROM budgets WHERE category_id = ?", (category_id,)
        )
        return cursor.rowcount
