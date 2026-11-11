"""Схеми запитів і відповідей REST API.

Назви полів і їхні типи відповідають розділу `components/schemas`
затвердженого контракту spec/api/openapi.yaml.
"""

from __future__ import annotations

from pydantic import BaseModel

from ..models import Category, Profile


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
