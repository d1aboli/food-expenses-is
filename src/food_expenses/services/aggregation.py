"""Підсумовування покупок (REQ-NF-010).

Три способи згорнути список покупок у суми: загальну, за категоріями і за
днями. Усі три потрібні і підсумкам, і бюджетам, тому лежать окремо від
обох служб.

Складання завжди в `Decimal`: жодне проміжне значення не перетворюється на
число з рухомою комою, інакше губляться копійки.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from ..repositories.summaries import PurchaseAmount

ZERO = Decimal("0.00")


def total_of(amounts: list[PurchaseAmount]) -> Decimal:
    """Загальна сума; для порожнього переліку — 0,00 (REQ-F-033)."""

    total = ZERO
    for item in amounts:
        total += item.amount
    return total


def by_category(amounts: list[PurchaseAmount]) -> dict[str, Decimal]:
    """Суми за категоріями (REQ-F-030, REQ-A-004)."""

    totals: dict[str, Decimal] = {}
    for item in amounts:
        totals[item.category_id] = totals.get(item.category_id, ZERO) + item.amount
    return totals


def by_day(amounts: list[PurchaseAmount]) -> dict[date, Decimal]:
    """Суми за днями (REQ-F-031)."""

    totals: dict[date, Decimal] = {}
    for item in amounts:
        totals[item.occurred_date] = totals.get(item.occurred_date, ZERO) + item.amount
    return totals


def category_names(amounts: list[PurchaseAmount]) -> dict[str, str]:
    """Назви категорій, які трапилися в переліку."""

    return {item.category_id: item.category_name for item in amounts}
