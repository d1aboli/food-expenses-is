"""Схеми запитів і відповідей REST API.

Назви полів і їхні типи відповідають розділу `components/schemas`
затвердженого контракту spec/api/openapi.yaml.
"""

from __future__ import annotations

from pydantic import BaseModel

from ..models import Profile


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
