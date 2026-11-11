"""Операції `listCategories`, `createCategory`, `renameCategory`, `deleteCategory`."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response

from ...services.categories import CategoryService
from ..dependencies import get_category_service
from ..params import CATEGORY_ID, PROFILE_ID
from ..schemas import CategoryCreateRequest, CategoryUpdateRequest, category_payload

router = APIRouter(tags=["categories"])


@router.get("/profiles/{profileId}/categories")
def list_categories(
    profile_id: str = PROFILE_ID,
    service: CategoryService = Depends(get_category_service),
) -> dict:
    """REQ-F-020, REQ-F-003: категорії активного профілю."""

    return {
        "items": [
            category_payload(category, purchase_count)
            for category, purchase_count in service.list(profile_id)
        ]
    }


@router.post("/profiles/{profileId}/categories", status_code=201)
def create_category(
    request_body: CategoryCreateRequest,
    profile_id: str = PROFILE_ID,
    service: CategoryService = Depends(get_category_service),
) -> dict:
    """REQ-F-021: власна категорія."""

    category, purchase_count = service.create(profile_id, request_body.name)
    return category_payload(category, purchase_count)


@router.patch("/profiles/{profileId}/categories/{categoryId}")
def rename_category(
    request_body: CategoryUpdateRequest,
    profile_id: str = PROFILE_ID,
    category_id: str = CATEGORY_ID,
    service: CategoryService = Depends(get_category_service),
) -> dict:
    """REQ-F-022, REQ-F-025: перейменування категорії."""

    category, purchase_count = service.rename(profile_id, category_id, request_body.name)
    return category_payload(category, purchase_count)


@router.delete("/profiles/{profileId}/categories/{categoryId}", status_code=204)
def delete_category(
    profile_id: str = PROFILE_ID,
    category_id: str = CATEGORY_ID,
    confirm: bool = Query(default=False),
    service: CategoryService = Depends(get_category_service),
) -> Response:
    """REQ-F-023, REQ-F-025: видалення категорії."""

    service.delete(profile_id, category_id, confirm=confirm)
    return Response(status_code=204)
