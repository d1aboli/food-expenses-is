"""Тести видалення непорожньої категорії (REQ-F-023, REQ-F-024, REQ-F-022).

Ці вимоги не можна було перевірити на етапі категорій: непорожню категорію
нічим було наповнити. Тепер покупки є, тому вимоги закриваються.
"""

from __future__ import annotations

import pytest

from contract import assert_error, assert_response_matches_contract

CATEGORY = "/profiles/{profileId}/categories/{categoryId}"
SYSTEM_CATEGORY_NAME = "Інше"


@pytest.fixture
def profile_id(client) -> str:
    return client.post("/profiles", json={"name": "Ілля"}).json()["id"]


def categories_of(client, profile_id) -> list[dict]:
    return client.get(f"/profiles/{profile_id}/categories").json()["items"]


def category_named(client, profile_id, name) -> dict:
    return next(item for item in categories_of(client, profile_id) if item["name"] == name)


@pytest.fixture
def category_with_three_purchases(client, profile_id) -> dict:
    category = client.post(
        f"/profiles/{profile_id}/categories", json={"name": "Ресторани"}
    ).json()
    for index in range(3):
        client.post(
            f"/profiles/{profile_id}/purchases",
            json={
                "name": f"Обід {index}",
                "categoryId": category["id"],
                "unitPrice": "120.00",
                "quantity": "1",
            },
        )
    return category


@pytest.mark.requirement("REQ-F-023")
def test_category_reports_the_number_of_its_purchases(
    client, profile_id, category_with_three_purchases
):
    """REQ-F-023: система знає, скільки покупок пов'язано з категорією."""

    category = category_named(client, profile_id, "Ресторани")

    assert category["purchaseCount"] == 3


@pytest.mark.requirement("REQ-F-023")
def test_non_empty_category_is_not_deleted_without_confirmation(
    client, profile_id, category_with_three_purchases
):
    """REQ-F-023: показується попередження з кількістю пов'язаних покупок."""

    response = client.delete(
        f"/profiles/{profile_id}/categories/{category_with_three_purchases['id']}"
    )

    payload = assert_error(
        response, 409, "CATEGORY_NOT_EMPTY", requirement="REQ-F-023", field="purchaseCount"
    )
    assert "3" in payload["error"]["message"]
    assert payload["error"]["details"][0]["issue"] == "3"
    assert category_named(client, profile_id, "Ресторани")


@pytest.mark.requirement("REQ-F-024")
def test_confirmed_deletion_moves_purchases_to_the_system_category(
    client, profile_id, category_with_three_purchases
):
    """REQ-F-024: після підтвердження покупки переходять до «Інше», категорія зникає."""

    response = client.delete(
        f"/profiles/{profile_id}/categories/{category_with_three_purchases['id']}?confirm=true"
    )

    assert response.status_code == 204

    names = [category["name"] for category in categories_of(client, profile_id)]
    assert "Ресторани" not in names

    system_category = category_named(client, profile_id, SYSTEM_CATEGORY_NAME)
    assert system_category["purchaseCount"] == 3


@pytest.mark.requirement("REQ-F-024")
def test_confirmed_deletion_keeps_the_purchases_themselves(
    client, profile_id, category_with_three_purchases
):
    """REQ-F-024: переносяться саме покупки, а не їхня кількість — дані не зникають."""

    client.delete(
        f"/profiles/{profile_id}/categories/{category_with_three_purchases['id']}?confirm=true"
    )

    purchases = client.get(f"/profiles/{profile_id}/purchases").json()
    assert purchases["total"] == 3
    assert {item["categoryName"] for item in purchases["items"]} == {SYSTEM_CATEGORY_NAME}


@pytest.mark.requirement("REQ-F-022")
def test_renamed_category_keeps_its_purchases(client, profile_id, category_with_three_purchases):
    """REQ-F-022: після перейменування покупки зберігають зв'язок із категорією."""

    response = client.patch(
        f"/profiles/{profile_id}/categories/{category_with_three_purchases['id']}",
        json={"name": "Кафе"},
    )

    payload = assert_response_matches_contract(response, CATEGORY, "patch", 200)
    assert payload["purchaseCount"] == 3

    purchases = client.get(f"/profiles/{profile_id}/purchases").json()
    assert {item["categoryName"] for item in purchases["items"]} == {"Кафе"}


@pytest.mark.requirement("REQ-F-024")
def test_moving_purchases_to_the_system_category_is_written_to_the_action_log(
    client, profile_id, category_with_three_purchases, settings
):
    """Перенесення покупок — дія, яка змінює дані, тому вона в журналі."""

    client.delete(
        f"/profiles/{profile_id}/categories/{category_with_three_purchases['id']}?confirm=true"
    )

    log = (settings.log_dir / "app.log").read_text(encoding="utf-8")
    assert "event=category.purchases_moved" in log
    assert "moved=3" in log
