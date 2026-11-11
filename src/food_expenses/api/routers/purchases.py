"""Операції `listPurchases`, `createPurchase`, `getPurchase`,
`updatePurchase`, `deletePurchase` з контракту."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response

from ...config import API_PREFIX
from ...services.exports import ExportService
from ...services.purchases import DEFAULT_LIMIT, PurchaseService
from ...timeutils import parse_date
from ..dependencies import get_export_service, get_purchase_service
from ..params import PROFILE_ID, PURCHASE_ID
from ..schemas import PurchaseCreateRequest, PurchaseUpdateRequest, purchase_payload

router = APIRouter(tags=["purchases"])


@router.get("/profiles/{profileId}/purchases")
def list_purchases(
    profile_id: str = PROFILE_ID,
    since: str | None = Query(default=None, alias="from"),
    until: str | None = Query(default=None, alias="to"),
    category_id: str | None = Query(default=None, alias="categoryId"),
    limit: int = Query(default=DEFAULT_LIMIT),
    offset: int = Query(default=0),
    service: PurchaseService = Depends(get_purchase_service),
) -> dict:
    """REQ-F-012: список покупок активного профілю."""

    items, total = service.list(
        profile_id,
        since=parse_date(since, "from") if since else None,
        until=parse_date(until, "to") if until else None,
        category_id=category_id,
        limit=limit,
        offset=offset,
    )
    return {
        "total": total,
        "items": [purchase_payload(purchase, name) for purchase, name in items],
    }


@router.post("/profiles/{profileId}/purchases", status_code=201)
def create_purchase(
    request_body: PurchaseCreateRequest,
    response: Response,
    profile_id: str = PROFILE_ID,
    service: PurchaseService = Depends(get_purchase_service),
) -> dict:
    """REQ-F-005: додавання покупки."""

    purchase, category_name = service.create(
        profile_id,
        name=request_body.name,
        category_id=request_body.categoryId,
        unit_price=request_body.unitPrice,
        quantity=request_body.quantity,
    )
    response.headers["Location"] = f"{API_PREFIX}/profiles/{profile_id}/purchases/{purchase.id}"
    return purchase_payload(purchase, category_name)


@router.get("/profiles/{profileId}/purchases/export")
def export_purchases(
    profile_id: str = PROFILE_ID,
    since: str | None = Query(default=None, alias="from"),
    until: str | None = Query(default=None, alias="to"),
    service: ExportService = Depends(get_export_service),
) -> Response:
    """REQ-F-035, REQ-I-003: експорт покупок у CSV.

    Цей маршрут оголошений раніше за `/purchases/{purchaseId}` навмисно:
    інакше адреса `/purchases/export` збіглася б із шаблоном ідентифікатора
    покупки, і сервер шукав би покупку з ідентифікатором «export».
    """

    start = parse_date(since, "from") if since else None
    end = parse_date(until, "to") if until else None
    content = service.purchases_csv(profile_id, since=start, until=end)

    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{service.file_name(start, end)}"'
        },
    )


@router.get("/profiles/{profileId}/purchases/{purchaseId}")
def get_purchase(
    profile_id: str = PROFILE_ID,
    purchase_id: str = PURCHASE_ID,
    service: PurchaseService = Depends(get_purchase_service),
) -> dict:
    """REQ-F-012: одна покупка."""

    purchase, category_name = service.get(profile_id, purchase_id)
    return purchase_payload(purchase, category_name)


@router.patch("/profiles/{profileId}/purchases/{purchaseId}")
def update_purchase(
    request_body: PurchaseUpdateRequest,
    profile_id: str = PROFILE_ID,
    purchase_id: str = PURCHASE_ID,
    service: PurchaseService = Depends(get_purchase_service),
) -> dict:
    """REQ-F-008, REQ-F-009: зміна покупки."""

    purchase, category_name = service.update(
        profile_id, purchase_id, request_body.model_dump(exclude_unset=True)
    )
    return purchase_payload(purchase, category_name)


@router.delete("/profiles/{profileId}/purchases/{purchaseId}", status_code=204)
def delete_purchase(
    profile_id: str = PROFILE_ID,
    purchase_id: str = PURCHASE_ID,
    service: PurchaseService = Depends(get_purchase_service),
) -> Response:
    """REQ-F-010, REQ-F-009: видалення покупки."""

    service.delete(profile_id, purchase_id)
    return Response(status_code=204)
