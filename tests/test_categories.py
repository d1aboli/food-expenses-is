"""Тести категорій (REQ-F-020, REQ-F-021, REQ-F-022, REQ-F-025, REQ-F-003).

Джерела: spec/srs.tex і операції `listCategories`, `createCategory`,
`renameCategory`, `deleteCategory` затвердженого контракту.

Правила видалення непорожньої категорії (REQ-F-023, REQ-F-024) перевіряються
на етапі покупок: до появи покупок непорожню категорію створити неможливо.
"""

from __future__ import annotations

import pytest

from contract import assert_error, assert_response_matches_contract

CATEGORIES = "/profiles/{profileId}/categories"
CATEGORY = "/profiles/{profileId}/categories/{categoryId}"
UNKNOWN_ID = "00000000-0000-4000-8000-000000000000"

BASE_CATEGORY_NAMES = ["Продукти", "Ресторан", "Доставка", "Напої", "Інше"]
SYSTEM_CATEGORY_NAME = "Інше"


@pytest.fixture
def profile_id(client) -> str:
    return client.post("/profiles", json={"name": "Ілля"}).json()["id"]


def categories_of(client, profile_id: str) -> list[dict]:
    response = client.get(f"/profiles/{profile_id}/categories")
    return assert_response_matches_contract(response, CATEGORIES, "get", 200)["items"]


def category_named(client, profile_id: str, name: str) -> dict:
    for category in categories_of(client, profile_id):
        if category["name"] == name:
            return category
    raise AssertionError(f"категорії {name} немає у профілі")


@pytest.mark.requirement("REQ-F-020")
def test_new_profile_gets_the_five_base_categories(client, profile_id):
    """REQ-F-020: при створенні профілю створюються базові категорії."""

    names = [category["name"] for category in categories_of(client, profile_id)]

    assert names == BASE_CATEGORY_NAMES


@pytest.mark.requirement("REQ-F-025")
def test_only_the_other_category_is_marked_as_system(client, profile_id):
    """REQ-F-025: службовою є лише категорія «Інше»."""

    system_flags = {
        category["name"]: category["system"] for category in categories_of(client, profile_id)
    }

    assert system_flags[SYSTEM_CATEGORY_NAME] is True
    assert all(
        flag is False for name, flag in system_flags.items() if name != SYSTEM_CATEGORY_NAME
    )


@pytest.mark.requirement("REQ-F-020")
def test_base_categories_start_without_purchases(client, profile_id):
    """Щойно створений профіль не має покупок у жодній категорії."""

    assert all(category["purchaseCount"] == 0 for category in categories_of(client, profile_id))


@pytest.mark.requirement("REQ-F-003")
def test_categories_of_one_profile_are_not_visible_in_another(client, profile_id):
    """REQ-F-003: категорії інших профілів недоступні."""

    other_profile = client.post("/profiles", json={"name": "Гість"}).json()["id"]
    client.post(f"/profiles/{profile_id}/categories", json={"name": "Перекуси"})

    names = [category["name"] for category in categories_of(client, other_profile)]

    assert "Перекуси" not in names
    assert names == BASE_CATEGORY_NAMES


@pytest.mark.requirement("REQ-F-003")
def test_categories_of_unknown_profile_are_reported_as_not_found(client):
    """REQ-F-003: звернення до чужого або неіснуючого профілю відхиляється."""

    response = client.get(f"/profiles/{UNKNOWN_ID}/categories")

    assert_error(response, 404, "PROFILE_NOT_FOUND")


@pytest.mark.requirement("REQ-F-021")
def test_custom_category_is_created(client, profile_id):
    """REQ-F-021: користувач створює власну категорію."""

    response = client.post(f"/profiles/{profile_id}/categories", json={"name": "Перекуси"})

    payload = assert_response_matches_contract(response, CATEGORIES, "post", 201)
    assert payload["name"] == "Перекуси"
    assert payload["system"] is False
    assert payload["purchaseCount"] == 0
    assert "Перекуси" in [c["name"] for c in categories_of(client, profile_id)]


@pytest.mark.requirement("REQ-F-021")
def test_category_name_must_be_unique_within_the_profile(client, profile_id):
    """REQ-F-021: назва категорії унікальна в межах профілю."""

    client.post(f"/profiles/{profile_id}/categories", json={"name": "Перекуси"})

    response = client.post(f"/profiles/{profile_id}/categories", json={"name": "Перекуси"})

    assert_error(response, 409, "CATEGORY_NAME_TAKEN", requirement="REQ-F-021", field="name")


@pytest.mark.requirement("REQ-F-021")
def test_category_name_collides_with_a_base_category(client, profile_id):
    """REQ-F-021: базові категорії теж зайняли свої назви."""

    response = client.post(f"/profiles/{profile_id}/categories", json={"name": "Продукти"})

    assert_error(response, 409, "CATEGORY_NAME_TAKEN")


@pytest.mark.requirement("REQ-F-021")
def test_same_category_name_is_allowed_in_another_profile(client, profile_id):
    """REQ-F-021: унікальність обмежена профілем, а не всією системою."""

    other_profile = client.post("/profiles", json={"name": "Гість"}).json()["id"]
    client.post(f"/profiles/{profile_id}/categories", json={"name": "Перекуси"})

    response = client.post(f"/profiles/{other_profile}/categories", json={"name": "Перекуси"})

    assert response.status_code == 201


@pytest.mark.requirement("REQ-F-021")
def test_category_with_blank_name_is_rejected(client, profile_id):
    """REQ-F-021: категорія без назви не створюється."""

    response = client.post(f"/profiles/{profile_id}/categories", json={"name": "  "})

    assert_error(response, 422, "VALIDATION_FAILED", field="name")


@pytest.mark.requirement("REQ-F-021")
def test_category_name_longer_than_forty_characters_is_rejected(client, profile_id):
    """Контракт: maxLength назви категорії — 40 символів."""

    response = client.post(f"/profiles/{profile_id}/categories", json={"name": "к" * 41})

    assert_error(response, 422, "VALIDATION_FAILED", field="name")


@pytest.mark.requirement("REQ-F-021")
def test_category_cannot_be_created_in_unknown_profile(client):
    """REQ-F-003: категорія створюється лише в наявному профілі."""

    response = client.post(f"/profiles/{UNKNOWN_ID}/categories", json={"name": "Перекуси"})

    assert_error(response, 404, "PROFILE_NOT_FOUND")


@pytest.mark.requirement("REQ-F-022")
def test_category_is_renamed_and_keeps_its_identifier(client, profile_id):
    """REQ-F-022: категорія перейменовується, залишаючись тією самою категорією."""

    created = client.post(
        f"/profiles/{profile_id}/categories", json={"name": "Ресторани"}
    ).json()

    response = client.patch(
        f"/profiles/{profile_id}/categories/{created['id']}", json={"name": "Кафе"}
    )

    payload = assert_response_matches_contract(response, CATEGORY, "patch", 200)
    assert payload["id"] == created["id"]
    assert payload["name"] == "Кафе"
    assert "Кафе" in [c["name"] for c in categories_of(client, profile_id)]


@pytest.mark.requirement("REQ-F-022")
def test_category_cannot_be_renamed_to_an_existing_name(client, profile_id):
    """REQ-F-022: перейменування не може порушити унікальність назв."""

    created = client.post(
        f"/profiles/{profile_id}/categories", json={"name": "Перекуси"}
    ).json()

    response = client.patch(
        f"/profiles/{profile_id}/categories/{created['id']}", json={"name": "Продукти"}
    )

    assert_error(response, 409, "CATEGORY_NAME_TAKEN")


@pytest.mark.requirement("REQ-F-025")
def test_system_category_cannot_be_renamed(client, profile_id):
    """REQ-F-025: категорію «Інше» перейменувати не можна."""

    system_category = category_named(client, profile_id, SYSTEM_CATEGORY_NAME)

    response = client.patch(
        f"/profiles/{profile_id}/categories/{system_category['id']}", json={"name": "Різне"}
    )

    assert_error(response, 409, "CATEGORY_IS_SYSTEM", requirement="REQ-F-025")


@pytest.mark.requirement("REQ-F-025")
def test_system_category_cannot_be_deleted_even_with_confirmation(client, profile_id):
    """REQ-F-025: «Інше» не видаляється за жодних умов."""

    system_category = category_named(client, profile_id, SYSTEM_CATEGORY_NAME)

    response = client.delete(
        f"/profiles/{profile_id}/categories/{system_category['id']}?confirm=true"
    )

    assert_error(response, 409, "CATEGORY_IS_SYSTEM", requirement="REQ-F-025")


@pytest.mark.requirement("REQ-F-023")
def test_empty_category_is_deleted_without_confirmation(client, profile_id):
    """REQ-F-023: порожню категорію видаляють без додаткових умов."""

    created = client.post(
        f"/profiles/{profile_id}/categories", json={"name": "Перекуси"}
    ).json()

    response = client.delete(f"/profiles/{profile_id}/categories/{created['id']}")

    assert response.status_code == 204
    assert "Перекуси" not in [c["name"] for c in categories_of(client, profile_id)]


@pytest.mark.requirement("REQ-F-021")
def test_unknown_category_is_reported_as_not_found(client, profile_id):
    """Звернення до неіснуючої категорії відхиляється за контрактом."""

    response = client.delete(f"/profiles/{profile_id}/categories/{UNKNOWN_ID}")

    assert_error(response, 404, "CATEGORY_NOT_FOUND")


@pytest.mark.requirement("REQ-F-003")
def test_category_of_another_profile_cannot_be_renamed(client, profile_id):
    """REQ-F-003: чужа категорія недоступна навіть за відомим ідентифікатором."""

    other_profile = client.post("/profiles", json={"name": "Гість"}).json()["id"]
    foreign = category_named(client, other_profile, "Продукти")

    response = client.patch(
        f"/profiles/{profile_id}/categories/{foreign['id']}", json={"name": "Їжа"}
    )

    assert_error(response, 404, "CATEGORY_NOT_FOUND")


@pytest.mark.requirement("REQ-F-021")
def test_category_creation_is_written_to_the_action_log(client, profile_id, settings):
    """Усі дії в системі потрапляють у журнал."""

    created = client.post(
        f"/profiles/{profile_id}/categories", json={"name": "Перекуси"}
    ).json()

    log = (settings.log_dir / "app.log").read_text(encoding="utf-8")
    assert "event=category.created" in log
    assert created["id"] in log
