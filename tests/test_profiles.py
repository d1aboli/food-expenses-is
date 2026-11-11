"""Тести профілів (REQ-F-001, REQ-F-002, REQ-F-004).

Джерела тестів: spec/srs.tex (вимоги й критерії прийняття) та затверджений
контракт spec/api/openapi.yaml (операції `createProfile`, `listProfiles`,
`getProfile`). Код реалізації на момент написання цих тестів не існує.
"""

from __future__ import annotations

import pytest

from contract import (
    ISO_DATETIME_PATTERN,
    UUID_PATTERN,
    assert_error,
    assert_response_matches_contract,
)

PROFILES = "/profiles"
PROFILE = "/profiles/{profileId}"
UNKNOWN_ID = "00000000-0000-4000-8000-000000000000"


@pytest.mark.requirement("REQ-F-004")
def test_profile_list_is_empty_before_the_first_profile_is_created(client):
    """REQ-F-004: поки профілів немає, список порожній."""

    response = client.get(PROFILES)

    payload = assert_response_matches_contract(response, PROFILES, "get", 200)
    assert payload["items"] == []


@pytest.mark.requirement("REQ-F-001")
def test_profile_is_created_with_the_given_name(client):
    """REQ-F-001: профіль створюється із зазначеною назвою."""

    response = client.post(PROFILES, json={"name": "Ілля"})

    payload = assert_response_matches_contract(response, PROFILES, "post", 201)
    assert payload["name"] == "Ілля"
    assert UUID_PATTERN.match(payload["id"]), payload["id"]
    assert ISO_DATETIME_PATTERN.match(payload["createdAt"]), payload["createdAt"]


@pytest.mark.requirement("REQ-F-001")
def test_created_profile_response_carries_location_header(client):
    """Контракт: відповідь 201 містить заголовок Location з URI створеного профілю."""

    response = client.post(PROFILES, json={"name": "Ілля"})

    assert response.status_code == 201
    assert response.headers["Location"].endswith(response.json()["id"])


@pytest.mark.requirement("REQ-F-002")
def test_created_profiles_appear_in_the_list(client):
    """REQ-F-002: система відображає список наявних профілів."""

    client.post(PROFILES, json={"name": "Ілля"})
    client.post(PROFILES, json={"name": "Гість"})

    payload = assert_response_matches_contract(client.get(PROFILES), PROFILES, "get", 200)

    assert [item["name"] for item in payload["items"]] == ["Ілля", "Гість"]


@pytest.mark.requirement("REQ-F-002")
def test_single_profile_is_available_by_its_identifier(client):
    """REQ-F-002: обраний профіль читається за своїм ідентифікатором."""

    created = client.post(PROFILES, json={"name": "Ілля"}).json()

    response = client.get(f"{PROFILES}/{created['id']}")

    payload = assert_response_matches_contract(response, PROFILE, "get", 200)
    assert payload == created


@pytest.mark.requirement("REQ-F-002")
def test_unknown_profile_identifier_is_reported_as_not_found(client):
    """REQ-F-002: звернення до неіснуючого профілю повертає помилку за контрактом."""

    response = client.get(f"{PROFILES}/{UNKNOWN_ID}")

    assert_error(response, 404, "PROFILE_NOT_FOUND", requirement="REQ-F-003")


@pytest.mark.requirement("REQ-F-001")
def test_profile_name_must_be_unique(client):
    """REQ-F-001: назва профілю відрізняє його від інших, тому не повторюється."""

    client.post(PROFILES, json={"name": "Ілля"})

    response = client.post(PROFILES, json={"name": "Ілля"})

    assert_error(response, 409, "PROFILE_NAME_TAKEN", field="name")


@pytest.mark.requirement("REQ-F-001")
def test_profile_with_blank_name_is_rejected(client):
    """REQ-F-001: профіль без назви створити не можна."""

    response = client.post(PROFILES, json={"name": "   "})

    assert_error(response, 422, "VALIDATION_FAILED", field="name")


@pytest.mark.requirement("REQ-F-001")
def test_profile_without_name_field_is_rejected(client):
    """Контракт: поле `name` обов'язкове у схемі ProfileCreate."""

    response = client.post(PROFILES, json={})

    assert_error(response, 422, "VALIDATION_FAILED", field="name")


@pytest.mark.requirement("REQ-F-001")
def test_profile_name_longer_than_sixty_characters_is_rejected(client):
    """Контракт: maxLength назви профілю — 60 символів."""

    response = client.post(PROFILES, json={"name": "я" * 61})

    assert_error(response, 422, "VALIDATION_FAILED", field="name")


@pytest.mark.requirement("REQ-F-001")
def test_profile_name_keeps_leading_and_trailing_spaces_trimmed(client):
    """Назва зберігається без крайових пробілів, інакше «Ілля» і «Ілля » були б різними."""

    payload = client.post(PROFILES, json={"name": "  Ілля  "}).json()

    assert payload["name"] == "Ілля"


@pytest.mark.requirement("REQ-F-001")
def test_profile_creation_is_written_to_the_action_log(client, settings):
    """Усі дії в системі потрапляють у журнал."""

    created = client.post(PROFILES, json={"name": "Ілля"}).json()

    log = (settings.log_dir / "app.log").read_text(encoding="utf-8")
    assert "event=profile.created" in log
    assert created["id"] in log


@pytest.mark.requirement("REQ-F-003")
def test_profiles_are_stored_independently_of_each_other(client):
    """REQ-F-003: дані одного профілю не з'являються в іншому.

    На рівні профілів перевіряється лише те, що вони не зливаються в один
    запис. Повна перевірка ізоляції покупок і категорій — у тестах відповідних
    етапів (`test_categories.py`, `test_purchases.py`).
    """

    first = client.post(PROFILES, json={"name": "Ілля"}).json()
    second = client.post(PROFILES, json={"name": "Гість"}).json()

    assert first["id"] != second["id"]
    assert client.get(f"{PROFILES}/{first['id']}").json()["name"] == "Ілля"
    assert client.get(f"{PROFILES}/{second['id']}").json()["name"] == "Гість"
