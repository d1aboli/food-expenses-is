"""Схеми запитів і відповідей REST API.

Назви полів і їхні типи відповідають розділу `components/schemas`
затвердженого контракту spec/api/openapi.yaml.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel

from ..config import CURRENCY
from ..models import Category, Profile, Purchase
from ..money import format_money, format_quantity
from ..periods import Period
from ..services.backups import Backup
from ..services.budgets import BudgetState
from ..services.summaries import CategoryShare, ChartPoint, PeriodSummary


class ProfileCreateRequest(BaseModel):
    """Схема `ProfileCreate` з контракту.

    Довжина й непорожність назви перевіряються у службі, а не тут, щоб
    помилка мала єдину форму з усіма іншими порушеннями правил
    (REQ-F-019). Якби обмеження стояло в самій схемі, відповідь склав би
    фреймворк, і вона відрізнялася б від решти.

    Attributes:
        name: Назва профілю.
    """

    name: str


def profile_payload(profile: Profile) -> dict[str, str]:
    """Складає відповідь за схемою `Profile` з контракту.

    Args:
        profile: Профіль із бази.

    Returns:
        Словник із полями `id`, `name`, `createdAt`.
    """
    return {
        "id": profile.id,
        "name": profile.name,
        "createdAt": profile.created_at.isoformat(timespec="seconds"),
    }


class CategoryCreateRequest(BaseModel):
    """Схема `CategoryCreate` з контракту.

    Attributes:
        name: Назва категорії, унікальна в межах профілю (REQ-F-021).
    """

    name: str


class CategoryUpdateRequest(BaseModel):
    """Схема `CategoryUpdate` з контракту.

    Attributes:
        name: Нова назва категорії (REQ-F-022).
    """

    name: str


def category_payload(category: Category, purchase_count: int) -> dict[str, object]:
    """Складає відповідь за схемою `Category` з контракту.

    Args:
        category: Категорія з бази.
        purchase_count: Скільки покупок до неї прив'язано.

    Returns:
        Словник із полями `id`, `name`, `system`, `purchaseCount`. Поле
        `system` позначає службову категорію «Інше», яку не можна ні
        видалити, ні перейменувати (REQ-F-025).
    """
    return {
        "id": category.id,
        "name": category.name,
        "system": category.is_system,
        "purchaseCount": purchase_count,
    }


class PurchaseCreateRequest(BaseModel):
    """Схема `PurchaseCreate` з контракту.

    Поля названі так само, як у контракті, тому перетворення імен немає:
    те, що описано в `openapi.yaml`, те й приймається. Саме через це вони
    в mixedCase, а не в змійці — відхилення від конвенції оголошене в
    `ruff.toml`.

    Ціна й кількість приймаються рядками, а не числами: число з рухомою
    комою вже на розборі запиту втратило б копійки (REQ-NF-010).

    Attributes:
        name: Назва покупки.
        categoryId: Категорія покупки.
        unitPrice: Ціна за одиницю рядком, наприклад `80.00`.
        quantity: Кількість рядком, наприклад `0.7`.
    """

    name: str
    categoryId: str
    unitPrice: str
    quantity: str


class PurchaseUpdateRequest(BaseModel):
    """Схема `PurchaseUpdate` з контракту.

    Усі поля необов'язкові: вимога дозволяє змінити будь-яке одне, не
    надсилаючи решти (REQ-F-008). Поля `amount` тут немає — вартість
    перераховує сервер.

    Attributes:
        name: Нова назва покупки.
        categoryId: Нова категорія.
        unitPrice: Нова ціна за одиницю.
        quantity: Нова кількість.
        occurredAt: Нові дата й час покупки.
    """

    name: str | None = None
    categoryId: str | None = None
    unitPrice: str | None = None
    quantity: str | None = None
    occurredAt: str | None = None


def purchase_payload(purchase: Purchase, category_name: str) -> dict[str, object]:
    """Складає відповідь за схемою `Purchase` з контракту.

    Args:
        purchase: Покупка з бази.
        category_name: Назва категорії; у самій покупці зберігається лише
            ідентифікатор.

    Returns:
        Словник із полями покупки. Ціна й вартість подаються з двома
        знаками після коми, кількість — без зайвих нулів у кінці.
    """
    return {
        "id": purchase.id,
        "name": purchase.name,
        "categoryId": purchase.category_id,
        "categoryName": category_name,
        "unitPrice": format_money(purchase.unit_price),
        "quantity": format_quantity(purchase.quantity),
        "amount": format_money(purchase.amount),
        "occurredAt": purchase.occurred_at.isoformat(timespec="seconds"),
    }


def summary_payload(total: PeriodSummary) -> dict[str, object]:
    """Складає відповідь за схемою `Summary` з контракту.

    Args:
        total: Підсумок за період.

    Returns:
        Словник із межами періоду, сумою, валютою та кількістю покупок.
    """
    return {
        "period": total.period.kind,
        "from": total.period.start.isoformat(),
        "to": total.period.end.isoformat(),
        "total": format_money(total.amount),
        "currency": CURRENCY,
        "purchaseCount": total.purchase_count,
    }


def breakdown_payload(
    period: Period, total: Decimal, items: list[CategoryShare]
) -> dict[str, object]:
    """Складає відповідь за схемою `CategoryBreakdown` з контракту.

    Args:
        period: Період, за який зроблено розбивку.
        total: Загальна сума за період — знаменник, від якого рахувалися
            частки.
        items: Категорії з сумами й частками.

    Returns:
        Словник із межами періоду, загальною сумою та переліком категорій.
    """
    return {
        "period": period.kind,
        "from": period.start.isoformat(),
        "to": period.end.isoformat(),
        "total": format_money(total),
        "currency": CURRENCY,
        "items": [
            {
                "categoryId": item.category_id,
                "categoryName": item.category_name,
                "amount": format_money(item.amount),
                "share": item.share,
            }
            for item in items
        ],
    }


def chart_payload(scale: str, period: str, points: list[ChartPoint]) -> dict[str, object]:
    """Складає відповідь за схемою `ChartSeries` з контракту.

    Args:
        scale: `daily` або `monthly`.
        period: Період серії: `2026-10` для днів, `2026` для місяців.
        points: Точки серії; порожніх днів чи місяців у переліку не
            бракує — вони є з нулем (REQ-F-031, REQ-F-032).

    Returns:
        Словник із масштабом, періодом, валютою та точками.
    """
    return {
        "scale": scale,
        "period": period,
        "currency": CURRENCY,
        "points": [
            {"label": point.label, "amount": format_money(point.amount)} for point in points
        ],
    }


def backup_payload(backup: Backup) -> dict[str, object]:
    """Складає відповідь за схемою `Backup` з контракту.

    Args:
        backup: Опис створеної резервної копії.

    Returns:
        Словник із іменем файла, розміром у байтах і часом створення.
    """
    return {
        "id": backup.id,
        "fileName": backup.file_name,
        "sizeBytes": backup.size_bytes,
        "createdAt": backup.created_at.isoformat(timespec="seconds"),
    }


class BudgetCreateRequest(BaseModel):
    """Схема `BudgetCreate` з контракту 1.1.0 (адендум ADD-01).

    Attributes:
        categoryId: Категорія, на яку встановлюється бюджет.
        limit: Місячний ліміт рядком, наприклад `3000.00` (REQ-A-002).
    """

    categoryId: str
    limit: str


class BudgetUpdateRequest(BaseModel):
    """Схема `BudgetUpdate` з контракту 1.1.0 (адендум ADD-01).

    Attributes:
        limit: Нова сума бюджету (REQ-A-006).
    """

    limit: str


def budget_payload(state: BudgetState) -> dict[str, object]:
    """Складає відповідь за схемою `Budget` з контракту 1.1.0.

    Args:
        state: Бюджет разом із витратами за обраний місяць.

    Returns:
        Словник із лімітом, витратами, залишком, ознакою перевищення та
        сумою перевищення. Залишок і перевищення обчислюються при
        кожному читанні, у базі їх немає (REQ-A-004, REQ-A-005).
    """
    return {
        "id": state.budget.id,
        "categoryId": state.budget.category_id,
        "categoryName": state.category_name,
        "limit": format_money(state.budget.monthly_limit),
        "spent": format_money(state.spent),
        "remaining": format_money(state.remaining),
        "exceeded": state.exceeded,
        "exceededBy": format_money(state.exceeded_by),
    }
