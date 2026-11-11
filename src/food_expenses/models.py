"""Записи предметної області.

Це прості незмінні структури, спільні для шару служб і шару доступу до даних.
Термінологія — за `spec/glossary.md`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class Profile:
    """Профіль користувача (REQ-F-001)."""

    id: str
    name: str
    created_at: datetime


@dataclass(frozen=True)
class Category:
    """Категорія витрат у межах профілю (REQ-F-020, REQ-F-021).

    Службова категорія «Інше» позначена `is_system`: її не можна ані
    перейменувати, ані видалити, бо до неї переносяться покупки з видалених
    категорій (REQ-F-025).
    """

    id: str
    profile_id: str
    name: str
    is_system: bool


@dataclass(frozen=True)
class Purchase:
    """Покупка активного профілю (REQ-F-005, REQ-F-006).

    `amount` обчислюється системою як добуток ціни за одиницю та кількості
    і зберігається разом із записом, щоб підсумки не перераховували його
    щоразу заново.
    """

    id: str
    profile_id: str
    category_id: str
    name: str
    unit_price: Decimal
    quantity: Decimal
    amount: Decimal
    occurred_at: datetime


@dataclass(frozen=True)
class Budget:
    """Місячний бюджет на категорію (адендум ADD-01, REQ-A-001).

    Сума одна й діє для кожного календарного місяця: різні суми для різних
    місяців до адендуму не входять і залишені відкритим питанням ВП-04.
    """

    id: str
    profile_id: str
    category_id: str
    monthly_limit: Decimal
    created_at: datetime
