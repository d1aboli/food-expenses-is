"""Правила роботи з покупками (REQ-F-005..REQ-F-012)."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from ..db import Database
from ..errors import PurchaseNotFound
from ..logging_setup import log_event
from ..models import Purchase
from ..money import calculate_amount
from ..repositories.purchases import PurchaseRepository
from ..timeutils import now, parse_datetime
from ..validation import (
    validate_occurred_at,
    validate_purchase_name,
    validate_quantity,
    validate_unit_price,
)
from .guards import require_category, require_profile

#: Розмір сторінки списку покупок за замовчуванням: стільки записів
#: повертається, якщо клієнт не задав `limit`.
DEFAULT_LIMIT = 50


class PurchaseService:
    """Додавання, перелік, зміна та видалення покупок."""

    def __init__(self, database: Database) -> None:
        """Прив'язує службу до бази даних.

        Args:
            database: Доступ до бази. Служба відкриває транзакцію на кожну
                операцію й не тримає з'єднання між викликами.
        """
        self._database = database

    def create(
        self,
        profile_id: str,
        name: str,
        category_id: str,
        unit_price: object,
        quantity: object,
    ) -> tuple[Purchase, str]:
        """Додає покупку (REQ-F-005).

        Дані перевіряються до будь-якого звернення до бази, тому
        відхилений запит не лишає по собі запису (REQ-F-013..REQ-F-019).

        Вартість обчислює сам сервер як добуток ціни на кількість
        (REQ-F-006), а час проставляє за своїм годинником (REQ-F-007).
        Ні того, ні іншого клієнт задати не може.

        Args:
            profile_id: Профіль, до якого додається покупка.
            name: Назва покупки.
            category_id: Категорія покупки.
            unit_price: Ціна за одиницю; приймається рядком.
            quantity: Кількість; приймається рядком.

        Returns:
            Пару «покупка, назва категорії».

        Raises:
            ValidationFailed: Дані не пройшли перевірку.
            ProfileNotFound: Профілю немає.
            CategoryNotFound: Категорії немає або вона чужа.
        """
        # REQ-F-013..REQ-F-019: дані перевіряються до будь-якого запису в базу,
        # тому відхилений запит не створює покупки.
        clean_name = validate_purchase_name(name)
        price = validate_unit_price(unit_price)
        amount_of = validate_quantity(quantity)

        purchase = Purchase(
            id=str(uuid.uuid4()),
            profile_id=profile_id,
            category_id=category_id,
            name=clean_name,
            unit_price=price,
            quantity=amount_of,
            amount=calculate_amount(price, amount_of),
            # REQ-F-007: час проставляє система, а не клієнт.
            occurred_at=now(),
        )

        with self._database.transaction() as connection:
            require_profile(connection, profile_id)
            category = require_category(connection, profile_id, category_id)
            PurchaseRepository(connection).add(purchase)

        log_event(
            "purchase.created",
            profile=profile_id,
            purchase=purchase.id,
            category=category_id,
            amount=str(purchase.amount),
        )
        return purchase, category.name

    def list(
        self,
        profile_id: str,
        since: date | None = None,
        until: date | None = None,
        category_id: str | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> tuple[list[tuple[Purchase, str]], int]:
        """Список покупок профілю (REQ-F-012).

        Args:
            profile_id: Профіль, покупки якого потрібні.
            since: Нижня межа за датою покупки, включно.
            until: Верхня межа за датою покупки, включно.
            category_id: Обмежити вибірку однією категорією.
            limit: Розмір сторінки.
            offset: Скільки записів пропустити.

        Returns:
            Пару «список пар (покупка, назва категорії), повна кількість
            записів у вибірці». Повна кількість рахується до застосування
            `limit`.

        Raises:
            ProfileNotFound: Профілю немає.
        """
        with self._database.transaction() as connection:
            require_profile(connection, profile_id)
            return PurchaseRepository(connection).list_for_profile(
                profile_id,
                since=since,
                until=until,
                category_id=category_id,
                limit=limit,
                offset=offset,
            )

    def get(self, profile_id: str, purchase_id: str) -> tuple[Purchase, str]:
        """Читає одну покупку (REQ-F-012).

        Args:
            profile_id: Профіль, якому належить покупка.
            purchase_id: Ідентифікатор покупки.

        Returns:
            Пару «покупка, назва категорії».

        Raises:
            ProfileNotFound: Профілю немає.
            PurchaseNotFound: Покупки немає або вона належить іншому
                профілю (REQ-F-003).
        """
        with self._database.transaction() as connection:
            require_profile(connection, profile_id)
            found = PurchaseRepository(connection).get(profile_id, purchase_id)
        if found is None:
            raise PurchaseNotFound()
        return found

    def update(
        self, profile_id: str, purchase_id: str, changes: dict[str, Any]
    ) -> tuple[Purchase, str]:
        """Змінює покупку (REQ-F-008).

        Змінити можна будь-яке поле, зокрема дату й час. Вартість після
        зміни ціни або кількості перераховується завжди: задати її ззовні
        не можна (REQ-F-006).

        Підсумки за періоди, яких покупка стосувалася, перераховувати
        окремо не треба — вони ніде не зберігаються й обчислюються при
        кожному читанні (REQ-F-009).

        Args:
            profile_id: Профіль, якому належить покупка.
            purchase_id: Ідентифікатор покупки.
            changes: Поля, які змінюються, під іменами з контракту:
                `name`, `categoryId`, `unitPrice`, `quantity`,
                `occurredAt`. Відсутнє поле лишається без зміни.

        Returns:
            Пару «змінена покупка, назва її категорії».

        Raises:
            ValidationFailed: Нові значення не пройшли перевірку.
            ProfileNotFound: Профілю немає.
            PurchaseNotFound: Покупки немає або вона чужа.
            CategoryNotFound: Нова категорія не існує або чужа.
        """
        with self._database.transaction() as connection:
            require_profile(connection, profile_id)
            repository = PurchaseRepository(connection)
            found = repository.get(profile_id, purchase_id)
            if found is None:
                raise PurchaseNotFound()

            purchase, category_name = found
            updated = self._apply_changes(connection, profile_id, purchase, changes)
            if updated.category_id != purchase.category_id:
                category_name = require_category(connection, profile_id, updated.category_id).name
            repository.update(updated)

        log_event(
            "purchase.updated",
            profile=profile_id,
            purchase=purchase_id,
            fields=",".join(sorted(changes)),
            amount=str(updated.amount),
        )
        return updated, category_name

    def delete(self, profile_id: str, purchase_id: str) -> None:
        """Видаляє покупку (REQ-F-010).

        Підсумки за періоди змінюються самі, бо ніде не зберігаються
        (REQ-F-009).

        Args:
            profile_id: Профіль, якому належить покупка.
            purchase_id: Ідентифікатор покупки.

        Raises:
            ProfileNotFound: Профілю немає.
            PurchaseNotFound: Покупки немає або вона чужа.
        """
        with self._database.transaction() as connection:
            require_profile(connection, profile_id)
            repository = PurchaseRepository(connection)
            if repository.get(profile_id, purchase_id) is None:
                raise PurchaseNotFound()
            repository.delete(purchase_id)

        log_event("purchase.deleted", profile=profile_id, purchase=purchase_id)

    def _apply_changes(
        self,
        connection: sqlite3.Connection,
        profile_id: str,
        purchase: Purchase,
        changes: dict[str, Any],
    ) -> Purchase:
        """Збирає новий запис покупки з урахуванням переданих змін.

        Args:
            connection: З'єднання в межах поточної транзакції.
            profile_id: Профіль, якому належить покупка.
            purchase: Покупка в поточному вигляді.
            changes: Поля, які змінюються.

        Returns:
            Новий запис покупки з тим самим ідентифікатором.
        """
        name = validate_purchase_name(changes["name"]) if "name" in changes else purchase.name
        category_id = changes.get("categoryId", purchase.category_id)
        unit_price: Decimal = (
            validate_unit_price(changes["unitPrice"])
            if "unitPrice" in changes
            else purchase.unit_price
        )
        quantity: Decimal = (
            validate_quantity(changes["quantity"]) if "quantity" in changes else purchase.quantity
        )
        occurred_at = (
            validate_occurred_at(parse_datetime(changes["occurredAt"], field="occurredAt"))
            if "occurredAt" in changes
            else purchase.occurred_at
        )

        if category_id != purchase.category_id:
            require_category(connection, profile_id, category_id)

        return Purchase(
            id=purchase.id,
            profile_id=purchase.profile_id,
            category_id=category_id,
            name=name,
            unit_price=unit_price,
            quantity=quantity,
            # REQ-F-006: вартість завжди перераховується, її не можна задати ззовні.
            amount=calculate_amount(unit_price, quantity),
            occurred_at=occurred_at,
        )
