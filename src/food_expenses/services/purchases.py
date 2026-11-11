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

DEFAULT_LIMIT = 50


class PurchaseService:
    """Додавання, перелік, зміна та видалення покупок."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def create(
        self,
        profile_id: str,
        name: str,
        category_id: str,
        unit_price: object,
        quantity: object,
    ) -> tuple[Purchase, str]:
        """REQ-F-005, REQ-F-006, REQ-F-007: додає покупку."""

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
        """REQ-F-012: список покупок від новіших до старіших."""

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
        """REQ-F-012, REQ-F-003: покупка активного профілю."""

        with self._database.transaction() as connection:
            require_profile(connection, profile_id)
            found = PurchaseRepository(connection).get(profile_id, purchase_id)
        if found is None:
            raise PurchaseNotFound()
        return found

    def update(
        self, profile_id: str, purchase_id: str, changes: dict[str, Any]
    ) -> tuple[Purchase, str]:
        """REQ-F-008, REQ-F-009: змінює поля покупки й перераховує вартість."""

        with self._database.transaction() as connection:
            require_profile(connection, profile_id)
            repository = PurchaseRepository(connection)
            found = repository.get(profile_id, purchase_id)
            if found is None:
                raise PurchaseNotFound()

            purchase, category_name = found
            updated = self._apply_changes(connection, profile_id, purchase, changes)
            if updated.category_id != purchase.category_id:
                category_name = require_category(
                    connection, profile_id, updated.category_id
                ).name
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
        """REQ-F-010, REQ-F-009: видаляє покупку."""

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
        """Збирає новий запис покупки з урахуванням переданих змін."""

        name = (
            validate_purchase_name(changes["name"])
            if "name" in changes
            else purchase.name
        )
        category_id = changes.get("categoryId", purchase.category_id)
        unit_price: Decimal = (
            validate_unit_price(changes["unitPrice"])
            if "unitPrice" in changes
            else purchase.unit_price
        )
        quantity: Decimal = (
            validate_quantity(changes["quantity"])
            if "quantity" in changes
            else purchase.quantity
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

