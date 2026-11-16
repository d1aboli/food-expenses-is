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
    """Профіль користувача (REQ-F-001).

    Attributes:
        id: Ідентифікатор профілю.
        name: Назва профілю, унікальна в системі.
        created_at: Час створення в часовому поясі застосунку.
    """

    id: str
    name: str
    created_at: datetime


@dataclass(frozen=True)
class Category:
    """Категорія витрат у межах профілю (REQ-F-020, REQ-F-021).

    Службова категорія «Інше» позначена `is_system`: її не можна ані
    перейменувати, ані видалити, бо до неї переносяться покупки з видалених
    категорій (REQ-F-025).

    Attributes:
        id: Ідентифікатор категорії.
        profile_id: Профіль, якому належить категорія.
        name: Назва, унікальна в межах профілю.
        is_system: Ознака службової категорії «Інше».
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

    Attributes:
        id: Ідентифікатор покупки.
        profile_id: Профіль, якому належить покупка.
        category_id: Категорія покупки.
        name: Назва покупки.
        unit_price: Ціна за одиницю.
        quantity: Кількість.
        amount: Вартість покупки — добуток ціни на кількість.
        occurred_at: Дата й час покупки.
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

    Attributes:
        id: Ідентифікатор бюджету.
        profile_id: Профіль, якому належить бюджет.
        category_id: Категорія, на яку встановлено бюджет.
        monthly_limit: Місячний ліміт витрат.
        created_at: Час встановлення бюджету.
    """

    id: str
    profile_id: str
    category_id: str
    monthly_limit: Decimal
    created_at: datetime
