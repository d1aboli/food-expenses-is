"""Тести покупок (REQ-F-005..REQ-F-012, REQ-F-003).

Джерела: spec/srs.tex, критерії прийняття та операції `createPurchase`,
`listPurchases`, `getPurchase`, `updatePurchase`, `deletePurchase`
затвердженого контракту.

Перевірка вхідних даних (REQ-F-013..REQ-F-019) — окремий етап і окремий файл.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from contract import assert_error, assert_response_matches_contract

PURCHASES = "/profiles/{profileId}/purchases"
PURCHASE = "/profiles/{profileId}/purchases/{purchaseId}"
UNKNOWN_ID = "00000000-0000-4000-8000-000000000000"


@pytest.fixture
def profile_id(client) -> str:
    return client.post("/profiles", json={"name": "Ілля"}).json()["id"]


@pytest.fixture
def category_id(client, profile_id) -> str:
    categories = client.get(f"/profiles/{profile_id}/categories").json()["items"]
    return next(item["id"] for item in categories if item["name"] == "Продукти")


def add_purchase(client, profile_id, category_id, **overrides) -> dict:
    body = {
        "name": "Хліб",
        "categoryId": category_id,
        "unitPrice": "25.50",
        "quantity": "1",
    }
    body.update(overrides)
    response = client.post(f"/profiles/{profile_id}/purchases", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def purchases_of(client, profile_id, **params) -> dict:
    response = client.get(f"/profiles/{profile_id}/purchases", params=params)
    return assert_response_matches_contract(response, PURCHASES, "get", 200)


@pytest.mark.requirement("REQ-F-005")
def test_purchase_is_created_with_name_category_price_and_quantity(
    client, profile_id, category_id
):
    """REQ-F-005: покупка додається із зазначеними полями."""

    response = client.post(
        f"/profiles/{profile_id}/purchases",
        json={
            "name": "Яблука",
            "categoryId": category_id,
            "unitPrice": "80.00",
            "quantity": "0.7",
        },
    )

    payload = assert_response_matches_contract(response, PURCHASES, "post", 201)
    assert payload["name"] == "Яблука"
    assert payload["categoryId"] == category_id
    assert payload["categoryName"] == "Продукти"
    assert payload["unitPrice"] == "80.00"
    assert payload["quantity"] == "0.7"


@pytest.mark.requirement("REQ-F-006")
def test_purchase_amount_is_price_multiplied_by_quantity(client, profile_id, category_id):
    """REQ-F-006: для ціни 80,00 і кількості 0,7 вартість дорівнює 56,00."""

    purchase = add_purchase(client, profile_id, category_id, unitPrice="80.00", quantity="0.7")

    assert purchase["amount"] == "56.00"


@pytest.mark.requirement("REQ-NF-010")
def test_purchase_amount_keeps_kopiikas(client, profile_id, category_id):
    """REQ-NF-010: ціна 33,33 і кількість 3 дають 99,99."""

    purchase = add_purchase(client, profile_id, category_id, unitPrice="33.33", quantity="3")

    assert purchase["amount"] == "99.99"


@pytest.mark.requirement("REQ-F-005")
def test_created_purchase_response_carries_location_header(client, profile_id, category_id):
    """Контракт: відповідь 201 містить заголовок Location."""

    response = client.post(
        f"/profiles/{profile_id}/purchases",
        json={
            "name": "Хліб",
            "categoryId": category_id,
            "unitPrice": "25.50",
            "quantity": "1",
        },
    )

    assert response.headers["Location"].endswith(response.json()["id"])


@pytest.mark.requirement("REQ-F-007")
def test_purchase_time_is_set_by_the_server(client, profile_id, category_id):
    """REQ-F-007: дата й час збігаються з системним часом з точністю до хвилини."""

    purchase = add_purchase(client, profile_id, category_id)

    occurred_at = datetime.fromisoformat(purchase["occurredAt"])
    assert abs(datetime.now(tz=occurred_at.tzinfo) - occurred_at) < timedelta(minutes=1)


@pytest.mark.requirement("REQ-F-007")
def test_client_cannot_set_the_time_while_adding_a_purchase(client, profile_id, category_id):
    """REQ-F-007: час проставляє система, а не клієнт.

    Схема `PurchaseCreate` не має поля `occurredAt`, тому передане значення
    не повинно вплинути на запис.
    """

    purchase = add_purchase(
        client, profile_id, category_id, occurredAt="2020-01-01T00:00:00+02:00"
    )

    assert not purchase["occurredAt"].startswith("2020-01-01")


@pytest.mark.requirement("REQ-F-011")
def test_identical_purchases_are_two_different_records(client, profile_id, category_id):
    """REQ-F-011: покупки з однаковими назвою, категорією та датою дозволені."""

    first = add_purchase(client, profile_id, category_id)
    second = add_purchase(client, profile_id, category_id)

    assert first["id"] != second["id"]
    assert purchases_of(client, profile_id)["total"] == 2


@pytest.mark.requirement("REQ-F-012")
def test_purchases_are_listed_from_newer_to_older(client, profile_id, category_id):
    """REQ-F-012: список упорядкований за датою й часом від новіших до старіших."""

    oldest = add_purchase(client, profile_id, category_id, name="Перша")
    middle = add_purchase(client, profile_id, category_id, name="Друга")
    newest = add_purchase(client, profile_id, category_id, name="Третя")

    patch = f"/profiles/{profile_id}/purchases"
    client.patch(f"{patch}/{oldest['id']}", json={"occurredAt": "2026-10-01T09:00:00+03:00"})
    client.patch(f"{patch}/{middle['id']}", json={"occurredAt": "2026-10-05T09:00:00+03:00"})
    client.patch(f"{patch}/{newest['id']}", json={"occurredAt": "2026-10-09T09:00:00+03:00"})

    names = [item["name"] for item in purchases_of(client, profile_id)["items"]]

    assert names == ["Третя", "Друга", "Перша"]


@pytest.mark.requirement("REQ-F-012")
def test_single_purchase_is_available_by_its_identifier(client, profile_id, category_id):
    """REQ-F-012: покупка читається за своїм ідентифікатором."""

    created = add_purchase(client, profile_id, category_id)

    response = client.get(f"/profiles/{profile_id}/purchases/{created['id']}")

    payload = assert_response_matches_contract(response, PURCHASE, "get", 200)
    assert payload == created


@pytest.mark.requirement("REQ-F-012")
def test_unknown_purchase_is_reported_as_not_found(client, profile_id):
    """REQ-F-012: неіснуюча покупка повертає помилку за контрактом."""

    response = client.get(f"/profiles/{profile_id}/purchases/{UNKNOWN_ID}")

    assert_error(response, 404, "PURCHASE_NOT_FOUND", requirement="REQ-F-012")


@pytest.mark.requirement("REQ-F-003")
def test_purchases_of_one_profile_are_invisible_in_another(client, profile_id, category_id):
    """REQ-F-003: покупки інших профілів недоступні.

    Це критерій прийняття REQ-F-003 зі специфікації: у профілі «Ілля»
    створено покупку, у профілі «Гість» список порожній.
    """

    created = add_purchase(client, profile_id, category_id)
    guest = client.post("/profiles", json={"name": "Гість"}).json()["id"]

    assert purchases_of(client, guest)["items"] == []
    assert_error(
        client.get(f"/profiles/{guest}/purchases/{created['id']}"), 404, "PURCHASE_NOT_FOUND"
    )


@pytest.mark.requirement("REQ-F-005")
def test_purchase_cannot_be_added_to_a_category_of_another_profile(client, profile_id):
    """REQ-F-003: категорія чужого профілю для цього профілю не існує."""

    guest = client.post("/profiles", json={"name": "Гість"}).json()["id"]
    foreign_category = client.get(f"/profiles/{guest}/categories").json()["items"][0]["id"]

    response = client.post(
        f"/profiles/{profile_id}/purchases",
        json={
            "name": "Хліб",
            "categoryId": foreign_category,
            "unitPrice": "25.50",
            "quantity": "1",
        },
    )

    assert_error(response, 404, "CATEGORY_NOT_FOUND")


@pytest.mark.requirement("REQ-F-008")
def test_purchase_fields_can_be_changed_and_amount_is_recalculated(
    client, profile_id, category_id
):
    """REQ-F-008: можна змінити будь-яке поле покупки."""

    created = add_purchase(client, profile_id, category_id)

    response = client.patch(
        f"/profiles/{profile_id}/purchases/{created['id']}",
        json={"name": "Батон", "unitPrice": "30.00", "quantity": "2"},
    )

    payload = assert_response_matches_contract(response, PURCHASE, "patch", 200)
    assert payload["name"] == "Батон"
    assert payload["amount"] == "60.00"


@pytest.mark.requirement("REQ-F-008")
def test_purchase_time_can_be_changed(client, profile_id, category_id):
    """REQ-F-008: дату й час покупки можна змінити."""

    created = add_purchase(client, profile_id, category_id)

    response = client.patch(
        f"/profiles/{profile_id}/purchases/{created['id']}",
        json={"occurredAt": "2026-10-04T19:00:00+03:00"},
    )

    assert response.json()["occurredAt"].startswith("2026-10-04T19:00:00")


@pytest.mark.requirement("REQ-F-008")
def test_purchase_category_can_be_changed(client, profile_id, category_id):
    """REQ-F-008: покупку можна перенести в іншу категорію."""

    created = add_purchase(client, profile_id, category_id)
    other = client.post(f"/profiles/{profile_id}/categories", json={"name": "Перекуси"}).json()

    response = client.patch(
        f"/profiles/{profile_id}/purchases/{created['id']}", json={"categoryId": other["id"]}
    )

    assert response.json()["categoryId"] == other["id"]
    assert response.json()["categoryName"] == "Перекуси"


@pytest.mark.requirement("REQ-F-009")
def test_changing_the_date_moves_the_purchase_between_periods(
    client, profile_id, category_id
):
    """REQ-F-009: після зміни дати покупка належить іншому періоду.

    Критерій прийняття REQ-F-009 сформульований через підсумки; підсумки
    з'являються на наступному етапі, тому тут перевіряється те саме на рівні
    вибірки за діапазоном дат.
    """

    created = add_purchase(client, profile_id, category_id)
    url = f"/profiles/{profile_id}/purchases/{created['id']}"
    client.patch(url, json={"occurredAt": "2026-10-05T18:00:00+03:00"})

    assert purchases_of(client, profile_id, **{"from": "2026-10-05", "to": "2026-10-05"})["total"] == 1

    client.patch(url, json={"occurredAt": "2026-10-04T18:00:00+03:00"})

    assert purchases_of(client, profile_id, **{"from": "2026-10-05", "to": "2026-10-05"})["total"] == 0
    assert purchases_of(client, profile_id, **{"from": "2026-10-04", "to": "2026-10-04"})["total"] == 1


@pytest.mark.requirement("REQ-F-010")
def test_purchase_is_deleted(client, profile_id, category_id):
    """REQ-F-010: покупку можна видалити."""

    created = add_purchase(client, profile_id, category_id)

    response = client.delete(f"/profiles/{profile_id}/purchases/{created['id']}")

    assert response.status_code == 204
    assert purchases_of(client, profile_id)["total"] == 0


@pytest.mark.requirement("REQ-F-010")
def test_deleting_an_unknown_purchase_is_reported_as_not_found(client, profile_id):
    """REQ-F-010: видалення неіснуючої покупки відхиляється."""

    response = client.delete(f"/profiles/{profile_id}/purchases/{UNKNOWN_ID}")

    assert_error(response, 404, "PURCHASE_NOT_FOUND")


@pytest.mark.requirement("REQ-F-012")
def test_purchases_can_be_filtered_by_category(client, profile_id, category_id):
    """Контракт: параметр `categoryId` звужує список покупок."""

    add_purchase(client, profile_id, category_id, name="Хліб")
    other = client.post(f"/profiles/{profile_id}/categories", json={"name": "Перекуси"}).json()
    add_purchase(client, profile_id, other["id"], name="Горішки")

    payload = purchases_of(client, profile_id, categoryId=other["id"])

    assert payload["total"] == 1
    assert payload["items"][0]["name"] == "Горішки"


@pytest.mark.requirement("REQ-F-012")
def test_purchase_list_is_paginated_and_reports_the_total(client, profile_id, category_id):
    """Контракт: `limit` і `offset` ділять список, `total` лишається повним."""

    for index in range(3):
        add_purchase(client, profile_id, category_id, name=f"Покупка {index}")

    payload = purchases_of(client, profile_id, limit=2, offset=0)

    assert payload["total"] == 3
    assert len(payload["items"]) == 2


@pytest.mark.requirement("REQ-F-005")
def test_purchase_creation_is_written_to_the_action_log(client, profile_id, category_id, settings):
    """Усі дії в системі потрапляють у журнал."""

    created = add_purchase(client, profile_id, category_id)

    log = (settings.log_dir / "app.log").read_text(encoding="utf-8")
    assert "event=purchase.created" in log
    assert created["id"] in log
