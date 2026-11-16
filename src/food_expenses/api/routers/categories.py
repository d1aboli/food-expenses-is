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
    """Операція `listCategories`: категорії профілю (REQ-F-020).

    Кожна категорія повертається разом із кількістю покупок у ній: саме
    вона потрібна інтерфейсу для попередження перед видаленням
    (REQ-F-023). Категорії інших профілів не повертаються (REQ-F-003).
    """
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
    """Операція `createCategory`: власна категорія (REQ-F-021).

    Назва має бути унікальною в межах профілю, але не глобально.
    Відповідь 409 `CATEGORY_NAME_TAKEN`, якщо така назва вже є.
    """
    category, purchase_count = service.create(profile_id, request_body.name)
    return category_payload(category, purchase_count)


@router.patch("/profiles/{profileId}/categories/{categoryId}")
def rename_category(
    request_body: CategoryUpdateRequest,
    profile_id: str = PROFILE_ID,
    category_id: str = CATEGORY_ID,
    service: CategoryService = Depends(get_category_service),
) -> dict:
    """Операція `renameCategory`: зміна назви категорії (REQ-F-022).

    Покупки зберігають зв'язок із категорією: вони посилаються на
    ідентифікатор, а не на назву. Службову категорію «Інше»
    перейменувати не можна — 409 `CATEGORY_IS_SYSTEM` (REQ-F-025).
    """
    category, purchase_count = service.rename(profile_id, category_id, request_body.name)
    return category_payload(category, purchase_count)


@router.delete("/profiles/{profileId}/categories/{categoryId}", status_code=204)
def delete_category(
    profile_id: str = PROFILE_ID,
    category_id: str = CATEGORY_ID,
    confirm: bool = Query(default=False),
    service: CategoryService = Depends(get_category_service),
) -> Response:
    """Операція `deleteCategory`: видалення категорії (REQ-F-023).

    Непорожня категорія видаляється лише з підтвердженням: без нього —
    409 `CATEGORY_NOT_EMPTY` із кількістю пов'язаних покупок. З
    підтвердженням покупки спершу переносяться до службової категорії і
    лише потім категорія зникає (REQ-F-024). Службову категорію видалити
    не можна — 409 `CATEGORY_IS_SYSTEM` (REQ-F-025).
    """
    service.delete(profile_id, category_id, confirm=confirm)
    return Response(status_code=204)
