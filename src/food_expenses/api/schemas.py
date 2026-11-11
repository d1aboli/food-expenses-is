"""Схеми запитів і відповідей REST API.

Назви полів і їхні типи відповідають розділу `components/schemas`
затвердженого контракту spec/api/openapi.yaml.
"""

from __future__ import annotations

from pydantic import BaseModel

from decimal import Decimal

from ..config import CURRENCY
from ..models import Category, Profile, Purchase
from ..periods import Period
from ..services.summaries import CategoryShare, ChartPoint, Total
from ..money import format_money, format_quantity


class ProfileCreateRequest(BaseModel):
    """Схема `ProfileCreate` з контракту.

    Довжина й непорожність назви перевіряються у службі, щоб помилка мала
    єдину форму з усіма іншими порушеннями правил (REQ-F-019).
    """

    name: str


def profile_payload(profile: Profile) -> dict[str, str]:
    """Схема `Profile` з контракту."""

    return {
        "id": profile.id,
        "name": profile.name,
        "createdAt": profile.created_at.isoformat(timespec="seconds"),
    }


class CategoryCreateRequest(BaseModel):
    """Схема `CategoryCreate` з контракту."""

    name: str


class CategoryUpdateRequest(BaseModel):
    """Схема `CategoryUpdate` з контракту."""

    name: str


def category_payload(category: Category, purchase_count: int) -> dict[str, object]:
    """Схема `Category` з контракту."""

    return {
        "id": category.id,
        "name": category.name,
        "system": category.is_system,
        "purchaseCount": purchase_count,
    }


class PurchaseCreateRequest(BaseModel):
    """Схема `PurchaseCreate` з контракту.

    Поля названі так само, як у контракті, тому тут немає перетворення імен:
    те, що описано в `openapi.yaml`, те й приймається.
    """

    name: str
    categoryId: str
    unitPrice: str
    quantity: str


class PurchaseUpdateRequest(BaseModel):
    """Схема `PurchaseUpdate` з контракту: будь-яка підмножина полів (REQ-F-008)."""

    name: str | None = None
    categoryId: str | None = None
    unitPrice: str | None = None
    quantity: str | None = None
    occurredAt: str | None = None


def purchase_payload(purchase: Purchase, category_name: str) -> dict[str, object]:
    """Схема `Purchase` з контракту."""

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


def summary_payload(total: Total) -> dict[str, object]:
    """Схема `Summary` з контракту."""

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
    """Схема `CategoryBreakdown` з контракту."""

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
    """Схема `ChartSeries` з контракту."""

    return {
        "scale": scale,
        "period": period,
        "currency": CURRENCY,
        "points": [
            {"label": point.label, "amount": format_money(point.amount)} for point in points
        ],
    }
