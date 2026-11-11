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
    """REQ-F-002, REQ-F-004: список наявних профілів."""

    return {"items": [profile_payload(profile) for profile in service.list()]}


@router.post("/profiles", status_code=201)
def create_profile(
    request_body: ProfileCreateRequest,
    response: Response,
    service: ProfileService = Depends(get_profile_service),
) -> dict:
    """REQ-F-001: створення профілю."""

    profile = service.create(request_body.name)
    response.headers["Location"] = f"{API_PREFIX}/profiles/{profile.id}"
    return profile_payload(profile)


@router.get("/profiles/{profileId}")
def get_profile(
    profile_id: str = PROFILE_ID,
    service: ProfileService = Depends(get_profile_service),
) -> dict:
    """REQ-F-002: читання одного профілю."""

    return profile_payload(service.get(profile_id))
