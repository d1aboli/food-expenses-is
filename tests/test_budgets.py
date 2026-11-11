"""Тести місячного бюджету на категорію (адендум ADD-01).

Вимоги REQ-A-001..REQ-A-009 і критерії прийняття — `spec/addendum-01-budgets.md`.
Операції `listBudgets`, `createBudget`, `updateBudget`, `deleteBudget` —
`spec/api/openapi.yaml` версії 1.1.0.

Адендум не скасовує TDD: ці тести написані до того, як з'явився код бюджетів.
"""

from __future__ import annotations

import pytest

from contract import assert_error, assert_response_matches_contract

BUDGETS = "/profiles/{profileId}/budgets"
BUDGET = "/profiles/{profileId}/budgets/{budgetId}"
UNKNOWN_ID = "00000000-0000-4000-8000-000000000000"
OCTOBER = "2026-10"


@pytest.fixture
def profile_id(client) -> str:
    return client.post("/profiles", json={"name": "Ілля"}).json()["id"]


@pytest.fixture
def category_id(client, profile_id) -> str:
    categories = client.get(f"/profiles/{profile_id}/categories").json()["items"]
    return next(item["id"] for item in categories if item["name"] == "Продукти")


def set_budget(client, profile_id, category_id, limit="3000.00"):
    return client.post(
        f"/profiles/{profile_id}/budgets", json={"categoryId": category_id, "limit": limit}
    )


def budgets_of(client, profile_id, **params) -> dict:
    response = client.get(f"/profiles/{profile_id}/budgets", params=params)
    return assert_response_matches_contract(response, BUDGETS, "get", 200)


def spend(client, profile_id, category_id, amount, day=None, name="Покупка"):
    created = client.post(
        f"/profiles/{profile_id}/purchases",
        json={
            "name": name,
            "categoryId": category_id,
            "unitPrice": amount,
            "quantity": "1",
        },
    ).json()
    if day is not None:
        client.patch(
            f"/profiles/{profile_id}/purchases/{created['id']}",
            json={"occurredAt": f"{day}T12:00:00+02:00"},
        )
    return created


# --- Встановлення бюджету (REQ-A-001, REQ-A-002, REQ-A-003) ------------------


@pytest.mark.requirement("REQ-A-001")
def test_budget_is_set_for_a_category(client, profile_id, category_id):
    """REQ-A-001: бюджет 3000,00 грн на категорію «Продукти»."""

    response = set_budget(client, profile_id, category_id, "3000.00")

    payload = assert_response_matches_contract(response, BUDGETS, "post", 201)
    assert payload["categoryId"] == category_id
    assert payload["categoryName"] == "Продукти"
    assert payload["limit"] == "3000.00"
    assert payload["spent"] == "0.00"
    assert payload["remaining"] == "3000.00"
    assert payload["exceeded"] is False
    assert payload["exceededBy"] == "0.00"


@pytest.mark.requirement("REQ-A-001")
def test_set_budget_appears_in_the_list(client, profile_id, category_id):
    """REQ-A-001: встановлений бюджет видно в переліку бюджетів профілю."""

    created = set_budget(client, profile_id, category_id).json()

    payload = budgets_of(client, profile_id, month=OCTOBER)

    assert payload["month"] == OCTOBER
    assert [item["id"] for item in payload["items"]] == [created["id"]]


@pytest.mark.requirement("REQ-A-001")
def test_created_budget_response_carries_location_header(client, profile_id, category_id):
    """Контракт: відповідь 201 містить заголовок Location."""

    response = set_budget(client, profile_id, category_id)

    assert response.headers["Location"].endswith(response.json()["id"])


@pytest.mark.requirement("REQ-A-002")
@pytest.mark.parametrize("limit", ["0.00", "-100.00"])
def test_budget_must_be_greater_than_zero(client, profile_id, category_id, limit):
    """REQ-A-002: бюджет 0,00 або -100,00 відхиляється, запис не створюється."""

    response = set_budget(client, profile_id, category_id, limit)

    assert_error(response, 422, "VALIDATION_FAILED", requirement="REQ-A-002", field="limit")
    assert budgets_of(client, profile_id, month=OCTOBER)["items"] == []


@pytest.mark.requirement("REQ-A-002")
def test_budget_without_kopiikas_is_rejected(client, profile_id, category_id):
    """REQ-A-002: сума задається у тому ж форматі, що й ціна — з двома знаками."""

    response = set_budget(client, profile_id, category_id, "3000")

    assert_error(response, 422, "VALIDATION_FAILED", field="limit")


@pytest.mark.requirement("REQ-A-003")
def test_category_cannot_have_two_budgets(client, profile_id, category_id):
    """REQ-A-003: повторне встановлення відхиляється, наявний бюджет не змінюється."""

    set_budget(client, profile_id, category_id, "3000.00")

    response = set_budget(client, profile_id, category_id, "500.00")

    assert_error(response, 409, "BUDGET_ALREADY_SET", requirement="REQ-A-003", field="categoryId")
    assert budgets_of(client, profile_id, month=OCTOBER)["items"][0]["limit"] == "3000.00"


@pytest.mark.requirement("REQ-A-001")
def test_budget_for_unknown_category_is_rejected(client, profile_id):
    """Бюджет встановлюється лише для наявної категорії профілю."""

    response = set_budget(client, profile_id, UNKNOWN_ID)

    assert_error(response, 404, "CATEGORY_NOT_FOUND")


# --- Витрати, залишок і перевищення (REQ-A-004, REQ-A-005) -------------------


@pytest.mark.requirement("REQ-A-004")
def test_budget_shows_spending_and_remainder_for_the_month(client, profile_id, category_id):
    """REQ-A-004: бюджет 3000,00 і витрати 1200,00 дають залишок 1800,00."""

    set_budget(client, profile_id, category_id, "3000.00")
    spend(client, profile_id, category_id, "1200.00", day="2026-10-05")

    budget = budgets_of(client, profile_id, month=OCTOBER)["items"][0]

    assert budget["spent"] == "1200.00"
    assert budget["remaining"] == "1800.00"
    assert budget["exceeded"] is False


@pytest.mark.requirement("REQ-A-005")
def test_exceeded_budget_is_marked_and_reports_the_excess(client, profile_id, category_id):
    """REQ-A-005: бюджет 1000,00 і витрати 1250,00 — перевищення 250,00."""

    set_budget(client, profile_id, category_id, "1000.00")
    spend(client, profile_id, category_id, "1250.00", day="2026-10-05")

    budget = budgets_of(client, profile_id, month=OCTOBER)["items"][0]

    assert budget["exceeded"] is True
    assert budget["exceededBy"] == "250.00"
    assert budget["remaining"] == "0.00"


@pytest.mark.requirement("REQ-A-005")
def test_spending_of_another_month_does_not_affect_the_budget(client, profile_id, category_id):
    """REQ-A-005: покупка 01.11 не впливає на показники за жовтень."""

    set_budget(client, profile_id, category_id, "1000.00")
    spend(client, profile_id, category_id, "900.00", day="2026-11-01")

    budget = budgets_of(client, profile_id, month=OCTOBER)["items"][0]

    assert budget["spent"] == "0.00"
    assert budget["remaining"] == "1000.00"


@pytest.mark.requirement("REQ-A-004")
def test_spending_of_another_category_does_not_affect_the_budget(
    client, profile_id, category_id
):
    """REQ-A-004: бюджет рахує витрати лише своєї категорії."""

    set_budget(client, profile_id, category_id, "1000.00")
    other = next(
        item["id"]
        for item in client.get(f"/profiles/{profile_id}/categories").json()["items"]
        if item["name"] == "Ресторан"
    )
    spend(client, profile_id, other, "900.00", day="2026-10-05")

    budget = budgets_of(client, profile_id, month=OCTOBER)["items"][0]

    assert budget["spent"] == "0.00"


@pytest.mark.requirement("REQ-A-004")
def test_budget_month_defaults_to_the_current_one(client, profile_id, category_id):
    """Контракт: без параметра `month` береться поточний місяць."""

    set_budget(client, profile_id, category_id, "1000.00")
    spend(client, profile_id, category_id, "150.00")

    budget = budgets_of(client, profile_id)["items"][0]

    assert budget["spent"] == "150.00"


@pytest.mark.requirement("REQ-A-004")
def test_budget_list_rejects_an_unparsable_month(client, profile_id):
    """Контракт: некоректний параметр запиту — 400."""

    response = client.get(f"/profiles/{profile_id}/budgets", params={"month": "жовтень"})

    assert_error(response, 400, "INVALID_PERIOD", field="month")


# --- Зміна і видалення (REQ-A-006, REQ-A-007) --------------------------------


@pytest.mark.requirement("REQ-A-006")
def test_budget_amount_can_be_changed(client, profile_id, category_id):
    """REQ-A-006: після зміни з 3000,00 на 2000,00 залишок перераховано."""

    created = set_budget(client, profile_id, category_id, "3000.00").json()
    # Витрата за поточний місяць: відповідь на зміну бюджету показує
    # показники саме за нього, бо операція `updateBudget` не має параметра
    # місяця в контракті.
    spend(client, profile_id, category_id, "1200.00")

    response = client.patch(
        f"/profiles/{profile_id}/budgets/{created['id']}", json={"limit": "2000.00"}
    )

    payload = assert_response_matches_contract(response, BUDGET, "patch", 200)
    assert payload["limit"] == "2000.00"
    assert payload["remaining"] == "800.00"


@pytest.mark.requirement("REQ-A-006")
def test_changed_budget_must_also_be_greater_than_zero(client, profile_id, category_id):
    """REQ-A-006: правила REQ-A-002 діють і при зміні."""

    created = set_budget(client, profile_id, category_id).json()

    response = client.patch(
        f"/profiles/{profile_id}/budgets/{created['id']}", json={"limit": "0.00"}
    )

    assert_error(response, 422, "VALIDATION_FAILED", requirement="REQ-A-002", field="limit")


@pytest.mark.requirement("REQ-A-007")
def test_budget_is_deleted_and_purchases_stay(client, profile_id, category_id):
    """REQ-A-007: бюджет зникає з переліку, покупки категорії лишаються."""

    created = set_budget(client, profile_id, category_id).json()
    spend(client, profile_id, category_id, "120.00", day="2026-10-05")

    response = client.delete(f"/profiles/{profile_id}/budgets/{created['id']}")

    assert response.status_code == 204
    assert budgets_of(client, profile_id, month=OCTOBER)["items"] == []
    assert client.get(f"/profiles/{profile_id}/purchases").json()["total"] == 1


@pytest.mark.requirement("REQ-A-007")
def test_unknown_budget_is_reported_as_not_found(client, profile_id):
    """Звернення до неіснуючого бюджету відхиляється за контрактом."""

    response = client.delete(f"/profiles/{profile_id}/budgets/{UNKNOWN_ID}")

    assert_error(response, 404, "BUDGET_NOT_FOUND")


# --- Зв'язок з категоріями та ізоляція (REQ-A-008, REQ-A-009) ----------------


@pytest.mark.requirement("REQ-A-008")
def test_deleting_a_category_deletes_its_budget(client, profile_id):
    """REQ-A-008: разом із категорією зникає і її бюджет."""

    category = client.post(
        f"/profiles/{profile_id}/categories", json={"name": "Ресторани"}
    ).json()
    set_budget(client, profile_id, category["id"], "800.00")
    spend(client, profile_id, category["id"], "100.00", day="2026-10-05")

    client.delete(f"/profiles/{profile_id}/categories/{category['id']}?confirm=true")

    assert budgets_of(client, profile_id, month=OCTOBER)["items"] == []


@pytest.mark.requirement("REQ-A-009")
def test_budgets_of_one_profile_are_invisible_in_another(client, profile_id, category_id):
    """REQ-A-009: бюджет профілю «Ілля» не видно в профілі «Гість»."""

    created = set_budget(client, profile_id, category_id).json()
    guest = client.post("/profiles", json={"name": "Гість"}).json()["id"]

    assert budgets_of(client, guest, month=OCTOBER)["items"] == []
    assert_error(
        client.delete(f"/profiles/{guest}/budgets/{created['id']}"), 404, "BUDGET_NOT_FOUND"
    )


@pytest.mark.requirement("REQ-A-009")
def test_budgets_of_unknown_profile_are_reported_as_not_found(client):
    """REQ-A-009: ізоляція діє і на рівні профілю."""

    response = client.get(f"/profiles/{UNKNOWN_ID}/budgets")

    assert_error(response, 404, "PROFILE_NOT_FOUND")


@pytest.mark.requirement("REQ-A-001")
def test_setting_a_budget_is_written_to_the_action_log(client, profile_id, category_id, settings):
    """Усі дії в системі потрапляють у журнал."""

    created = set_budget(client, profile_id, category_id).json()

    log = (settings.log_dir / "app.log").read_text(encoding="utf-8")
    assert "event=budget.created" in log
    assert created["id"] in log
