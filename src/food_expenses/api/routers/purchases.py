"""Маршрути покупок.

Операції `listPurchases`, `createPurchase`, `getPurchase`, `updatePurchase`,
`deletePurchase` та `exportPurchases` з контракту.
"""

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
    """Операція `listPurchases`: покупки профілю (REQ-F-012).

    Порядок — від новіших до старіших. Вибірку можна звузити періодом і
    категорією; разом зі сторінкою повертається повна кількість записів у
    вибірці, а не кількість на сторінці.
    """
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
    """Операція `createPurchase`: додавання покупки (REQ-F-005).

    Вартість обчислює сервер як добуток ціни на кількість (REQ-F-006);
    передане клієнтом значення не береться — поле `amount` у контракті
    позначене `readOnly`. Дата й час проставляються сервером (REQ-F-007).
    Ціна або кількість, менші чи рівні нулю, порожня назва — 422
    (REQ-F-013..REQ-F-015).
    """
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
    """Операція `exportPurchases`: вивантаження покупок у CSV (REQ-F-035).

    Маршрут оголошений раніше за `/purchases/{purchaseId}` навмисно:
    інакше адреса `/purchases/export` збіглася б із шаблоном
    ідентифікатора покупки, і сервер шукав би покупку з ідентифікатором
    «export». Помилку знайшов червоний тест, який отримав 404
    `PURCHASE_NOT_FOUND` замість файла.

    Відповідь — `text/csv; charset=utf-8` із заголовком
    `Content-Disposition` (REQ-I-003).
    """
    start = parse_date(since, "from") if since else None
    end = parse_date(until, "to") if until else None
    content = service.purchases_csv(profile_id, since=start, until=end)

    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{service.file_name(start, end)}"'},
    )


@router.get("/profiles/{profileId}/purchases/{purchaseId}")
def get_purchase(
    profile_id: str = PROFILE_ID,
    purchase_id: str = PURCHASE_ID,
    service: PurchaseService = Depends(get_purchase_service),
) -> dict:
    """Операція `getPurchase`: одна покупка (REQ-F-012).

    Відповідь 404 `PURCHASE_NOT_FOUND`, зокрема коли покупка існує, але
    належить іншому профілю (REQ-F-003).
    """
    purchase, category_name = service.get(profile_id, purchase_id)
    return purchase_payload(purchase, category_name)


@router.patch("/profiles/{profileId}/purchases/{purchaseId}")
def update_purchase(
    request_body: PurchaseUpdateRequest,
    profile_id: str = PROFILE_ID,
    purchase_id: str = PURCHASE_ID,
    service: PurchaseService = Depends(get_purchase_service),
) -> dict:
    """Операція `updatePurchase`: зміна покупки (REQ-F-008).

    Змінити можна будь-яке поле, зокрема дату й час. Вартість
    перераховується, а підсумки за всі зачеплені періоди змінюються
    самі, бо ніде не зберігаються (REQ-F-009). Дата в майбутньому — 422
    (REQ-F-016).
    """
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
    """Операція `deletePurchase`: видалення покупки (REQ-F-010).

    Підсумки за періоди, яких покупка стосувалася, змінюються самі
    (REQ-F-009). Відповідь 204 без тіла.
    """
    service.delete(profile_id, purchase_id)
    return Response(status_code=204)
