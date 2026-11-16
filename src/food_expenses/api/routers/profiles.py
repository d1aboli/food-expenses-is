"""Операції `listProfiles`, `createProfile`, `getProfile` з контракту.

Шаблони адрес повторюють контракт дослівно, разом з іменами параметрів шляху
(`{profileId}`), щоб опис, який віддає сам застосунок, збігався з
`spec/api/openapi.yaml`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from ...config import API_PREFIX
from ...services.profiles import ProfileService
from ..dependencies import get_profile_service
from ..params import PROFILE_ID
from ..schemas import ProfileCreateRequest, profile_payload

router = APIRouter(tags=["profiles"])


@router.get("/profiles")
def list_profiles(service: ProfileService = Depends(get_profile_service)) -> dict:
    """Операція `listProfiles`: перелік наявних профілів (REQ-F-002).

    Порожній перелік — звичайна відповідь 200, а не помилка: саме за ним
    інтерфейс розуміє, що треба запропонувати створити перший профіль
    (REQ-F-004).
    """
    return {"items": [profile_payload(profile) for profile in service.list()]}


@router.post("/profiles", status_code=201)
def create_profile(
    request_body: ProfileCreateRequest,
    response: Response,
    service: ProfileService = Depends(get_profile_service),
) -> dict:
    """Операція `createProfile`: створення профілю (REQ-F-001).

    Разом із профілем створюються п'ять базових категорій (REQ-F-020).
    Відповідь 201 із заголовком `Location`; 409 `PROFILE_NAME_TAKEN`,
    якщо назву вже зайнято; 422, якщо назва порожня або задовга.
    """
    profile = service.create(request_body.name)
    response.headers["Location"] = f"{API_PREFIX}/profiles/{profile.id}"
    return profile_payload(profile)


@router.get("/profiles/{profileId}")
def get_profile(
    profile_id: str = PROFILE_ID,
    service: ProfileService = Depends(get_profile_service),
) -> dict:
    """Операція `getProfile`: один профіль за ідентифікатором (REQ-F-002).

    Відповідь 404 `PROFILE_NOT_FOUND`, якщо профілю немає.
    """
    return profile_payload(service.get(profile_id))
