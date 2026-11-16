"""Доступ до таблиці покупок (REQ-F-005..REQ-F-012, REQ-F-034)."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from decimal import Decimal

from ..models import Purchase

#: Перелік колонок покупки разом із назвою категорії. Виділений у сталу,
#: щоб усі запити читали однаковий набір і `_to_purchase` не залежав від
#: того, який саме метод його викликав.
SELECT_COLUMNS = """
    p.id, p.profile_id, p.category_id, p.name,
    p.unit_price, p.quantity, p.amount, p.occurred_at,
    c.name AS category_name
"""


def _to_purchase(row: sqlite3.Row) -> Purchase:
    return Purchase(
        id=row["id"],
        profile_id=row["profile_id"],
        category_id=row["category_id"],
        name=row["name"],
        unit_price=Decimal(row["unit_price"]),
        quantity=Decimal(row["quantity"]),
        amount=Decimal(row["amount"]),
        occurred_at=datetime.fromisoformat(row["occurred_at"]),
    )


class PurchaseRepository:
    """Читання й запис покупок у межах профілю.

    Грошові величини зберігаються текстом, а не числом: двійкове число з
    рухомою комою не подає 0,01 точно, тому `Decimal` перетворюється на
    рядок при записі й назад при читанні (REQ-NF-010).

    Разом із `occurred_at` записується окрема колонка `occurred_date` — та
    сама дата без часу. Вона потрібна індексові: фільтр за періодом
    порівнює дати, і без окремої колонки довелося б обрізати час у
    кожному рядку, а індекс не працював би (REQ-NF-011).
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        """Прив'язує репозиторій до з'єднання з базою.

        Args:
            connection: Відкрите з'єднання; транзакціями керує той, хто
                викликає.
        """
        self._connection = connection

    def add(self, purchase: Purchase) -> None:
        """Записує нову покупку (REQ-F-005).

        Вартість (`amount`) береться з переданого об'єкта вже обчисленою:
        рахувати її має `PurchaseService` через `calculate_amount`, а не
        репозиторій і не база.

        Args:
            purchase: Покупка з обчисленою вартістю та проставленим часом.
        """
        self._connection.execute(
            """
            INSERT INTO purchases
                (id, profile_id, category_id, name, unit_price, quantity,
                 amount, occurred_at, occurred_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                purchase.id,
                purchase.profile_id,
                purchase.category_id,
                purchase.name,
                str(purchase.unit_price),
                str(purchase.quantity),
                str(purchase.amount),
                purchase.occurred_at.isoformat(timespec="seconds"),
                purchase.occurred_at.date().isoformat(),
            ),
        )

    def update(self, purchase: Purchase) -> None:
        """Перезаписує всі змінні поля покупки (REQ-F-008).

        Колонка `occurred_date` перераховується разом з `occurred_at`:
        інакше зміна дати покупки не потрапила б у підсумки за періоди
        (REQ-F-009).

        Args:
            purchase: Покупка з новими значеннями полів і тим самим
                ідентифікатором.
        """
        self._connection.execute(
            """
            UPDATE purchases
               SET category_id = ?, name = ?, unit_price = ?, quantity = ?,
                   amount = ?, occurred_at = ?, occurred_date = ?
             WHERE id = ?
            """,
            (
                purchase.category_id,
                purchase.name,
                str(purchase.unit_price),
                str(purchase.quantity),
                str(purchase.amount),
                purchase.occurred_at.isoformat(timespec="seconds"),
                purchase.occurred_at.date().isoformat(),
                purchase.id,
            ),
        )

    def get(self, profile_id: str, purchase_id: str) -> tuple[Purchase, str] | None:
        """Шукає покупку профілю за ідентифікатором.

        Args:
            profile_id: Профіль, у межах якого шукається покупка.
            purchase_id: Ідентифікатор покупки.

        Returns:
            Пара «покупка, назва категорії» або `None`. Назва категорії
            читається тим самим запитом, бо потрібна в кожній відповіді
            API (поле `categoryName` схеми `Purchase`).
        """
        row = self._connection.execute(
            f"""
            SELECT {SELECT_COLUMNS}
            FROM purchases p JOIN categories c ON c.id = p.category_id
            WHERE p.id = ? AND p.profile_id = ?
            """,
            (purchase_id, profile_id),
        ).fetchone()
        return (_to_purchase(row), row["category_name"]) if row else None

    def list_for_profile(
        self,
        profile_id: str,
        since: date | None = None,
        until: date | None = None,
        category_id: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> tuple[list[tuple[Purchase, str]], int]:
        """Сторінка списку покупок і повна кількість записів у вибірці.

        Args:
            profile_id: Профіль, покупки якого читаються.
            since: Нижня межа за датою покупки, включно.
            until: Верхня межа за датою покупки, включно.
            category_id: Обмежити вибірку однією категорією.
            limit: Розмір сторінки; `None` — без обмеження.
            offset: Скільки записів пропустити.

        Returns:
            Пара «список пар (покупка, назва категорії), повна кількість».
            Повна кількість рахується до застосування `limit`, бо
            відповідь API повідомляє, скільки записів у вибірці всього, а
            не скільки влізло на сторінку.

        Note:
            Упорядкування — від новіших до старіших (REQ-F-012). За
            однакового часу вирішує `rowid`, тому порядок стабільний:
            REQ-F-011 дозволяє покупки з однаковими назвою, категорією і
            датою.
        """
        where, parameters = self._build_filter(profile_id, since, until, category_id)

        total = int(
            self._connection.execute(
                f"SELECT COUNT(*) AS total FROM purchases p WHERE {where}", parameters
            ).fetchone()["total"]
        )

        query = (
            f"SELECT {SELECT_COLUMNS} "
            "FROM purchases p JOIN categories c ON c.id = p.category_id "
            f"WHERE {where} ORDER BY p.occurred_at DESC, p.rowid DESC"
        )
        page_parameters = list(parameters)
        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            page_parameters.extend([limit, offset])

        rows = self._connection.execute(query, page_parameters).fetchall()
        return [(_to_purchase(row), row["category_name"]) for row in rows], total

    def delete(self, purchase_id: str) -> None:
        """Видаляє покупку (REQ-F-010).

        Args:
            purchase_id: Ідентифікатор покупки.
        """
        self._connection.execute("DELETE FROM purchases WHERE id = ?", (purchase_id,))

    def move_to_category(self, from_category_id: str, to_category_id: str) -> int:
        """Переносить покупки однієї категорії до іншої (REQ-F-024).

        Викликається перед видаленням непорожньої категорії. Вартість
        покупок не змінюється — змінюється лише категорія, тому підсумок
        за період лишається тим самим, а розбивка за категоріями
        змінюється.

        Args:
            from_category_id: Категорія, з якої переносяться покупки.
            to_category_id: Службова категорія «Інше».

        Returns:
            Кількість перенесених покупок.
        """
        cursor = self._connection.execute(
            "UPDATE purchases SET category_id = ? WHERE category_id = ?",
            (to_category_id, from_category_id),
        )
        return cursor.rowcount

    @staticmethod
    def _build_filter(
        profile_id: str,
        since: date | None,
        until: date | None,
        category_id: str | None,
    ) -> tuple[str, list[object]]:
        conditions = ["p.profile_id = ?"]
        parameters: list[object] = [profile_id]
        if since is not None:
            conditions.append("p.occurred_date >= ?")
            parameters.append(since.isoformat())
        if until is not None:
            conditions.append("p.occurred_date <= ?")
            parameters.append(until.isoformat())
        if category_id is not None:
            conditions.append("p.category_id = ?")
            parameters.append(category_id)
        return " AND ".join(conditions), parameters
