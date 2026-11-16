"""Операції `listBudgets`, `createBudget`, `updateBudget`, `deleteBudget`.

Ресурс доданий адендумом ADD-01; контракт — `spec/api/openapi.yaml` 1.1.0.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response

from ...config import API_PREFIX
from ...periods import parse_month
from ...services.budgets import BudgetService
from ...timeutils import now
from ..dependencies import get_budget_service
from ..params import BUDGET_ID, PROFILE_ID
from ..schemas import BudgetCreateRequest, BudgetUpdateRequest, budget_payload

router = APIRouter(tags=["budgets"])


@router.get("/profiles/{profileId}/budgets")
def list_budgets(
    profile_id: str = PROFILE_ID,
    month: str | None = Query(default=None),
    service: BudgetService = Depends(get_budget_service),
) -> dict:
    """Операція `listBudgets`: бюджети профілю за місяць (REQ-A-004).

    Витрати, залишок і перевищення обчислюються при кожному читанні, а не
    зберігаються: інакше вони розійшлися б із покупками після
    редагування покупки (REQ-F-009). Без параметра місяця береться
    поточний. Перевищений бюджет позначається окремо, із сумою
    перевищення (REQ-A-005).
    """
    year, month_number = parse_month(month) if month else (now().year, now().month)
    states = service.list(profile_id, month=(year, month_number))
    return {
        "month": f"{year:04d}-{month_number:02d}",
        "currency": "UAH",
        "items": [budget_payload(state) for state in states],
    }


@router.post("/profiles/{profileId}/budgets", status_code=201)
def create_budget(
    request_body: BudgetCreateRequest,
    response: Response,
    profile_id: str = PROFILE_ID,
    service: BudgetService = Depends(get_budget_service),
) -> dict:
    """Операція `createBudget`: місячний бюджет на категорію (REQ-A-001).

    Категорія може мати не більш ніж один бюджет: повторне встановлення —
    409 `BUDGET_ALREADY_SET` (REQ-A-003). Сума має бути більшою за нуль —
    інакше 422 (REQ-A-002).
    """
    state = service.create(profile_id, request_body.categoryId, request_body.limit)
    response.headers["Location"] = f"{API_PREFIX}/profiles/{profile_id}/budgets/{state.budget.id}"
    return budget_payload(state)


@router.patch("/profiles/{profileId}/budgets/{budgetId}")
def update_budget(
    request_body: BudgetUpdateRequest,
    profile_id: str = PROFILE_ID,
    budget_id: str = BUDGET_ID,
    service: BudgetService = Depends(get_budget_service),
) -> dict:
    """Операція `updateBudget`: зміна суми бюджету (REQ-A-006).

    Залишок і перевищення перераховуються за новою сумою при наступному
    читанні. Відповідь 404 `BUDGET_NOT_FOUND`, якщо бюджету немає.
    """
    return budget_payload(service.update(profile_id, budget_id, request_body.limit))


@router.delete("/profiles/{profileId}/budgets/{budgetId}", status_code=204)
def delete_budget(
    profile_id: str = PROFILE_ID,
    budget_id: str = BUDGET_ID,
    service: BudgetService = Depends(get_budget_service),
) -> Response:
    """Операція `deleteBudget`: зняття бюджету з категорії (REQ-A-007).

    Покупки категорії не змінюються: бюджет — окрема сутність, і зняття
    бюджету обліку витрат не стосується.
    """
    service.delete(profile_id, budget_id)
    return Response(status_code=204)
