"""Тести перевірки вхідних даних (REQ-F-013..REQ-F-019).

Джерела: критерії прийняття у spec/srs.tex і приклади помилок у розділі
`components/responses/UnprocessableEntity` затвердженого контракту.

Головне, що перевіряється: відхилений запит не створює й не змінює запис.
Повідомлення про помилку — не заміна цієї перевірки, а доповнення до неї.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from contract import assert_error
from food_expenses.timeutils import now


@pytest.fixture
def profile_id(client) -> str:
    return client.post("/profiles", json={"name": "Ілля"}).json()["id"]


@pytest.fixture
def category_id(client, profile_id) -> str:
    categories = client.get(f"/profiles/{profile_id}/categories").json()["items"]
    return next(item["id"] for item in categories if item["name"] == "Продукти")


def try_to_add(client, profile_id, category_id, **overrides):
    body = {
        "name": "Хліб",
        "categoryId": category_id,
        "unitPrice": "25.50",
        "quantity": "1",
    }
    body.update(overrides)
    return client.post(f"/profiles/{profile_id}/purchases", json=body)


def purchase_count(client, profile_id) -> int:
    return client.get(f"/profiles/{profile_id}/purchases").json()["total"]


# --- Ціна за одиницю (REQ-F-013, REQ-F-017) ---------------------------------


@pytest.mark.requirement("REQ-F-013")
@pytest.mark.parametrize("price", ["0.00", "-50.00"])
def test_purchase_with_non_positive_price_is_rejected(client, profile_id, category_id, price):
    """REQ-F-013: ціна 0 або -50 відхиляється, запис не створюється."""

    response = try_to_add(client, profile_id, category_id, unitPrice=price)

    assert_error(response, 422, "VALIDATION_FAILED", requirement="REQ-F-013", field="unitPrice")
    assert purchase_count(client, profile_id) == 0


@pytest.mark.requirement("REQ-F-017")
def test_price_with_more_than_two_decimal_places_is_rejected(client, profile_id, category_id):
    """REQ-F-017: не більш ніж два знаки після коми."""

    response = try_to_add(client, profile_id, category_id, unitPrice="10.123")

    assert_error(response, 422, "VALIDATION_FAILED", requirement="REQ-F-017", field="unitPrice")


@pytest.mark.requirement("REQ-F-017")
def test_price_without_kopiikas_is_rejected_by_the_contract_format(
    client, profile_id, category_id
):
    """Контракт: схема `Money` вимагає рівно два знаки після коми.

    REQ-F-017 дозволяє вводити ціле число, але зведення до вигляду «80.00»
    належить інтерфейсу користувача. На вхід API подається вже нормалізоване
    значення. Розбіжність між формулюванням REQ-F-017 і схемою `Money`
    зафіксована як відкрите питання ВП-03.
    """

    response = try_to_add(client, profile_id, category_id, unitPrice="80")

    assert_error(response, 422, "VALIDATION_FAILED", requirement="REQ-F-017", field="unitPrice")


@pytest.mark.requirement("REQ-F-017")
def test_price_has_no_upper_limit(client, profile_id, category_id):
    """REQ-F-017: верхня межа ціни не встановлюється."""

    response = try_to_add(client, profile_id, category_id, unitPrice="1000000.00")

    assert response.status_code == 201
    assert response.json()["amount"] == "1000000.00"


@pytest.mark.requirement("REQ-F-013")
def test_price_that_is_not_a_number_is_rejected(client, profile_id, category_id):
    """REQ-F-019: нечислова ціна відхиляється із зазначенням поля."""

    response = try_to_add(client, profile_id, category_id, unitPrice="вісімдесят")

    assert_error(response, 422, "VALIDATION_FAILED", field="unitPrice")
    assert purchase_count(client, profile_id) == 0


# --- Кількість (REQ-F-014, REQ-F-018) ---------------------------------------


@pytest.mark.requirement("REQ-F-014")
@pytest.mark.parametrize("quantity", ["0", "-1"])
def test_purchase_with_non_positive_quantity_is_rejected(
    client, profile_id, category_id, quantity
):
    """REQ-F-014: кількість, менша або рівна нулю, відхиляється."""

    response = try_to_add(client, profile_id, category_id, quantity=quantity)

    assert_error(response, 422, "VALIDATION_FAILED", requirement="REQ-F-014", field="quantity")
    assert purchase_count(client, profile_id) == 0


@pytest.mark.requirement("REQ-F-018")
def test_quantity_with_three_decimal_places_is_accepted(client, profile_id, category_id):
    """REQ-F-018: кількість 0,125 приймається."""

    response = try_to_add(client, profile_id, category_id, quantity="0.125")

    assert response.status_code == 201
    assert response.json()["quantity"] == "0.125"


@pytest.mark.requirement("REQ-F-018")
def test_quantity_with_four_decimal_places_is_rejected(client, profile_id, category_id):
    """REQ-F-018: кількість 0,1255 відхиляється."""

    response = try_to_add(client, profile_id, category_id, quantity="0.1255")

    assert_error(response, 422, "VALIDATION_FAILED", requirement="REQ-F-018", field="quantity")
    assert purchase_count(client, profile_id) == 0


# --- Назва покупки (REQ-F-015) ----------------------------------------------


@pytest.mark.requirement("REQ-F-015")
@pytest.mark.parametrize("name", ["", "   "])
def test_purchase_with_blank_name_is_rejected(client, profile_id, category_id, name):
    """REQ-F-015: покупка з порожньою назвою не створюється."""

    response = try_to_add(client, profile_id, category_id, name=name)

    assert_error(response, 422, "VALIDATION_FAILED", requirement="REQ-F-015", field="name")
    assert purchase_count(client, profile_id) == 0


@pytest.mark.requirement("REQ-F-015")
def test_purchase_name_longer_than_hundred_characters_is_rejected(
    client, profile_id, category_id
):
    """Контракт: maxLength назви покупки — 100 символів."""

    response = try_to_add(client, profile_id, category_id, name="х" * 101)

    assert_error(response, 422, "VALIDATION_FAILED", requirement="REQ-F-015", field="name")


# --- Дата й час (REQ-F-016) --------------------------------------------------


@pytest.mark.requirement("REQ-F-016")
def test_purchase_cannot_be_moved_into_the_future(client, profile_id, category_id):
    """REQ-F-016: дата й час, пізніші за поточний момент, не зберігаються."""

    created = try_to_add(client, profile_id, category_id).json()
    future = (now() + timedelta(days=1)).isoformat(timespec="seconds")

    response = client.patch(
        f"/profiles/{profile_id}/purchases/{created['id']}", json={"occurredAt": future}
    )

    assert_error(response, 422, "VALIDATION_FAILED", requirement="REQ-F-016", field="occurredAt")


@pytest.mark.requirement("REQ-F-016")
def test_rejected_date_change_leaves_the_purchase_untouched(client, profile_id, category_id):
    """REQ-F-019: відхилений запит не змінює запис."""

    created = try_to_add(client, profile_id, category_id).json()
    future = (now() + timedelta(hours=2)).isoformat(timespec="seconds")

    client.patch(f"/profiles/{profile_id}/purchases/{created['id']}", json={"occurredAt": future})

    stored = client.get(f"/profiles/{profile_id}/purchases/{created['id']}").json()
    assert stored == created


@pytest.mark.requirement("REQ-F-016")
def test_purchase_time_in_the_past_is_accepted(client, profile_id, category_id):
    """REQ-F-016: обмеження стосується лише майбутнього."""

    created = try_to_add(client, profile_id, category_id).json()

    response = client.patch(
        f"/profiles/{profile_id}/purchases/{created['id']}",
        json={"occurredAt": "2026-10-04T19:00:00+03:00"},
    )

    assert response.status_code == 200


@pytest.mark.requirement("REQ-F-016")
def test_unparsable_date_is_rejected(client, profile_id, category_id):
    """REQ-F-019: дата в невідомому форматі відхиляється."""

    created = try_to_add(client, profile_id, category_id).json()

    response = client.patch(
        f"/profiles/{profile_id}/purchases/{created['id']}", json={"occurredAt": "04.10.2026"}
    )

    assert_error(response, 422, "VALIDATION_FAILED", field="occurredAt")


# --- Зміна покупки (REQ-F-008 разом із REQ-F-013, REQ-F-014) -----------------


@pytest.mark.requirement("REQ-F-013")
def test_price_rules_apply_to_changes_as_well(client, profile_id, category_id):
    """REQ-F-013: ті самі правила діють і при редагуванні, а не лише при додаванні."""

    created = try_to_add(client, profile_id, category_id).json()

    response = client.patch(
        f"/profiles/{profile_id}/purchases/{created['id']}", json={"unitPrice": "0.00"}
    )

    assert_error(response, 422, "VALIDATION_FAILED", requirement="REQ-F-013", field="unitPrice")


@pytest.mark.requirement("REQ-F-014")
def test_quantity_rules_apply_to_changes_as_well(client, profile_id, category_id):
    """REQ-F-014: те саме для кількості."""

    created = try_to_add(client, profile_id, category_id).json()

    response = client.patch(
        f"/profiles/{profile_id}/purchases/{created['id']}", json={"quantity": "0"}
    )

    assert_error(response, 422, "VALIDATION_FAILED", requirement="REQ-F-014", field="quantity")


# --- Параметри запиту (контракт: 400 BadRequest) -----------------------------


@pytest.mark.requirement("REQ-F-029")
def test_unparsable_date_range_is_a_bad_request(client, profile_id):
    """Контракт: некоректний параметр запиту — це 400, а не 422."""

    response = client.get(f"/profiles/{profile_id}/purchases", params={"from": "04.10.2026"})

    assert_error(response, 400, "INVALID_PERIOD", field="from")


@pytest.mark.requirement("REQ-F-019")
def test_rejection_message_is_in_ukrainian_and_names_the_requirement(
    client, profile_id, category_id
):
    """REQ-F-019: повідомлення пояснює причину і посилається на вимогу."""

    response = try_to_add(client, profile_id, category_id, unitPrice="0.00")

    error = response.json()["error"]
    assert error["requirement"] == "REQ-F-013"
    assert "більш" in error["message"].lower() or "нуль" in error["message"].lower()
