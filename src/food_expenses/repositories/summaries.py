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
    """Одна покупка в тому вигляді, який потрібен для підсумку.

    Назва покупки, ціна за одиницю й кількість тут відсутні: для підсумку
    за період, розбивки за категоріями й даних графіка їх не треба, а на
    десяти тисячах записів зайві поля дають відчутну різницю
    (REQ-NF-011).

    Attributes:
        occurred_date: Дата покупки без часу — за нею визначається, у який
            період і в який стовпчик графіка покупка потрапляє.
        category_id: Категорія покупки.
        category_name: Назва категорії; потрібна для розбивки, щоб не
            робити другий запит.
        amount: Вартість покупки в `Decimal`.
    """

    occurred_date: date
    category_id: str
    category_name: str
    amount: Decimal


class SummaryRepository:
    """Читання покупок періоду для подальшого підсумовування."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        """Прив'язує репозиторій до з'єднання з базою.

        Args:
            connection: Відкрите з'єднання; транзакціями керує той, хто
                викликає.
        """
        self._connection = connection

    def amounts_between(self, profile_id: str, start: date, end: date) -> list[PurchaseAmount]:
        """Покупки профілю за період, включно з обома межами (REQ-F-029).

        Args:
            profile_id: Профіль, покупки якого читаються.
            start: Перший день періоду, входить у вибірку.
            end: Останній день періоду, входить у вибірку.

        Returns:
            Усі покупки періоду окремими записами, без підсумовування й
            без упорядкування: порядок для суми `Decimal` не має значення,
            а групування за категорією й за днем робить
            `services.aggregation`.

        Note:
            Фільтр іде по колонці `occurred_date`, на якій є індекс, а не
            по `occurred_at` з обрізанням часу.
        """
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
