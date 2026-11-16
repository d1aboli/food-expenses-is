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


#: Колонки бюджету без назви категорії: її додає кожен запит окремо,
#: бо не всім потрібне з'єднання з таблицею категорій.
SELECT_COLUMNS = "b.id, b.profile_id, b.category_id, b.monthly_limit, b.created_at"


class BudgetRepository:
    """Читання й запис бюджетів у межах профілю (ADD-01).

    Репозиторій зберігає лише місячний ліміт. Фактичні витрати й залишок
    не зберігаються ніде: вони обчислюються при кожному читанні
    `BudgetService`, інакше розійшлися б із покупками після редагування
    покупки (REQ-F-009, REQ-A-004).
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        """Прив'язує репозиторій до з'єднання з базою.

        Args:
            connection: Відкрите з'єднання; транзакціями керує той, хто
                викликає.
        """
        self._connection = connection

    def add(self, budget: Budget) -> None:
        """Записує новий бюджет (REQ-A-001).

        Args:
            budget: Бюджет із перевіреним місячним лімітом. Перевірку, що
                категорія ще не має бюджету, робить служба (REQ-A-003).
        """
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
        """Бюджети профілю разом із назвами категорій (REQ-A-004).

        Args:
            profile_id: Профіль, бюджети якого читаються.

        Returns:
            Пари «бюджет, назва категорії» в порядку створення. Бюджети
            інших профілів не повертаються (REQ-A-009).
        """
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
        """Шукає бюджет профілю за ідентифікатором.

        Args:
            profile_id: Профіль, у межах якого шукається бюджет.
            budget_id: Ідентифікатор бюджету.

        Returns:
            Пара «бюджет, назва категорії» або `None`, зокрема коли бюджет
            належить іншому профілю (REQ-A-009).
        """
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
        """Шукає бюджет категорії (REQ-A-003).

        Args:
            profile_id: Профіль, у межах якого шукається бюджет.
            category_id: Категорія, бюджет якої потрібен.

        Returns:
            Бюджет або `None`. Використовується, щоб відхилити повторне
            встановлення бюджету для категорії, яка вже його має.
        """
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
        """Змінює суму бюджету (REQ-A-006).

        Args:
            budget_id: Ідентифікатор бюджету.
            monthly_limit: Нова сума, уже перевірена службою.
        """
        self._connection.execute(
            "UPDATE budgets SET monthly_limit = ? WHERE id = ?",
            (str(monthly_limit), budget_id),
        )

    def delete(self, budget_id: str) -> None:
        """Видаляє бюджет (REQ-A-007).

        Покупки категорії при цьому не змінюються: бюджет — окрема
        сутність, зняття бюджету не стосується обліку витрат.

        Args:
            budget_id: Ідентифікатор бюджету.
        """
        self._connection.execute("DELETE FROM budgets WHERE id = ?", (budget_id,))

    def delete_for_category(self, category_id: str) -> int:
        """Видаляє бюджет категорії разом із самою категорією (REQ-A-008).

        Args:
            category_id: Категорія, яку видаляють.

        Returns:
            Кількість видалених бюджетів: 0 або 1, бо категорія може мати
            не більш ніж один бюджет (REQ-A-003).
        """
        cursor = self._connection.execute(
            "DELETE FROM budgets WHERE category_id = ?", (category_id,)
        )
        return cursor.rowcount
