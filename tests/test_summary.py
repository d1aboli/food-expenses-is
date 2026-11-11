"""Тести підсумків за періодами і розбивки за категоріями.

Вимоги: REQ-F-026..REQ-F-030, REQ-F-033.
Джерела: критерії прийняття у spec/srs.tex і операції `getSummary`,
`getCategoryBreakdown` затвердженого контракту.

Межі періодів — найдорожче місце цієї системи: саме через них у ЛР1 виник
конфлікт між людиною й агентом. Тому кожна межа перевіряється з обох боків:
останній день усередині періоду і перший день за ним.
"""

from __future__ import annotations

import pytest

from contract import assert_error, assert_response_matches_contract

SUMMARY = "/profiles/{profileId}/summary"
BREAKDOWN = "/profiles/{profileId}/summary/categories"


@pytest.fixture
def profile_id(client) -> str:
    return client.post("/profiles", json={"name": "Ілля"}).json()["id"]


@pytest.fixture
def category_id(client, profile_id) -> str:
    categories = client.get(f"/profiles/{profile_id}/categories").json()["items"]
    return next(item["id"] for item in categories if item["name"] == "Продукти")


def add_purchase_on(client, profile_id, category_id, day: str, amount: str, name="Покупка"):
    """Додає покупку із заданою вартістю і переносить її на вказаний день."""

    created = client.post(
        f"/profiles/{profile_id}/purchases",
        json={
            "name": name,
            "categoryId": category_id,
            "unitPrice": amount,
            "quantity": "1",
        },
    ).json()
    client.patch(
        f"/profiles/{profile_id}/purchases/{created['id']}",
        json={"occurredAt": f"{day}T12:00:00+03:00"},
    )
    return created


def summary(client, profile_id, **params):
    response = client.get(f"/profiles/{profile_id}/summary", params=params)
    return assert_response_matches_contract(response, SUMMARY, "get", 200)


def breakdown(client, profile_id, **params):
    response = client.get(f"/profiles/{profile_id}/summary/categories", params=params)
    return assert_response_matches_contract(response, BREAKDOWN, "get", 200)


# --- Календарний день (REQ-F-026) -------------------------------------------


@pytest.mark.requirement("REQ-F-026")
def test_daily_total_counts_only_that_day(client, profile_id, category_id):
    """REQ-F-026: підсумок за календарну добу."""

    add_purchase_on(client, profile_id, category_id, "2026-10-05", "100.00")
    add_purchase_on(client, profile_id, category_id, "2026-10-05", "50.00")
    add_purchase_on(client, profile_id, category_id, "2026-10-06", "70.00")

    payload = summary(client, profile_id, period="day", date="2026-10-05")

    assert payload["total"] == "150.00"
    assert payload["purchaseCount"] == 2
    assert payload["from"] == "2026-10-05"
    assert payload["to"] == "2026-10-05"


# --- Календарний тиждень (REQ-F-027) ----------------------------------------


@pytest.mark.requirement("REQ-F-027")
def test_weekly_total_runs_from_monday_to_sunday(client, profile_id, category_id):
    """REQ-F-027: критерій прийняття зі специфікації.

    Понеділок 05.10 — 100,00, неділя 11.10 — 50,00, разом 150,00.
    Покупка наступного понеділка 12.10 у підсумок не входить.
    """

    add_purchase_on(client, profile_id, category_id, "2026-10-05", "100.00")
    add_purchase_on(client, profile_id, category_id, "2026-10-11", "50.00")
    add_purchase_on(client, profile_id, category_id, "2026-10-12", "999.00")

    payload = summary(client, profile_id, period="week", date="2026-10-07")

    assert payload["total"] == "150.00"
    assert payload["from"] == "2026-10-05"
    assert payload["to"] == "2026-10-11"


@pytest.mark.requirement("REQ-F-027")
def test_week_boundaries_are_the_same_for_any_day_inside_it(client, profile_id, category_id):
    """REQ-F-027: тиждень визначається днем, а не порядком звернення."""

    add_purchase_on(client, profile_id, category_id, "2026-10-08", "25.00")

    for day in ["2026-10-05", "2026-10-08", "2026-10-11"]:
        payload = summary(client, profile_id, period="week", date=day)
        assert (payload["from"], payload["to"]) == ("2026-10-05", "2026-10-11")
        assert payload["total"] == "25.00"


# --- Календарний місяць (REQ-F-028) -----------------------------------------


@pytest.mark.requirement("REQ-F-028")
def test_monthly_total_runs_from_the_first_to_the_last_day(client, profile_id, category_id):
    """REQ-F-028: місяць з 1-го по останнє число включно."""

    add_purchase_on(client, profile_id, category_id, "2026-10-01", "10.00")
    add_purchase_on(client, profile_id, category_id, "2026-10-31", "20.00")
    add_purchase_on(client, profile_id, category_id, "2026-09-30", "999.00")

    payload = summary(client, profile_id, period="month", date="2026-10-15")

    assert payload["total"] == "30.00"
    assert payload["from"] == "2026-10-01"
    assert payload["to"] == "2026-10-31"


# --- Довільний діапазон (REQ-F-029) -----------------------------------------


@pytest.mark.requirement("REQ-F-029")
def test_range_includes_both_boundary_days(client, profile_id, category_id):
    """REQ-F-029: критерій прийняття — діапазон 01.10–03.10 включно з межами."""

    add_purchase_on(client, profile_id, category_id, "2026-10-01", "10.00")
    add_purchase_on(client, profile_id, category_id, "2026-10-03", "30.00")
    add_purchase_on(client, profile_id, category_id, "2026-10-04", "999.00")

    payload = summary(
        client, profile_id, period="range", **{"from": "2026-10-01", "to": "2026-10-03"}
    )

    assert payload["total"] == "40.00"
    assert payload["purchaseCount"] == 2


@pytest.mark.requirement("REQ-F-029")
def test_range_of_a_single_day_is_allowed(client, profile_id, category_id):
    """REQ-F-029: діапазон з однієї доби — припустимий випадок."""

    add_purchase_on(client, profile_id, category_id, "2026-10-02", "15.00")

    payload = summary(
        client, profile_id, period="range", **{"from": "2026-10-02", "to": "2026-10-02"}
    )

    assert payload["total"] == "15.00"


@pytest.mark.requirement("REQ-F-029")
def test_range_with_reversed_boundaries_is_a_bad_request(client, profile_id):
    """REQ-F-029: кінець періоду не може бути раніший за початок."""

    response = client.get(
        f"/profiles/{profile_id}/summary",
        params={"period": "range", "from": "2026-10-05", "to": "2026-10-01"},
    )

    assert_error(response, 400, "INVALID_PERIOD")


@pytest.mark.requirement("REQ-F-029")
def test_range_without_boundaries_is_a_bad_request(client, profile_id):
    """Контракт: для `period=range` потрібні обидві межі."""

    response = client.get(f"/profiles/{profile_id}/summary", params={"period": "range"})

    assert_error(response, 400, "INVALID_PERIOD")


@pytest.mark.requirement("REQ-F-026")
def test_unknown_period_is_a_bad_request(client, profile_id):
    """Контракт: допустимі значення — day, week, month, range."""

    response = client.get(f"/profiles/{profile_id}/summary", params={"period": "quarter"})

    assert_error(response, 400, "INVALID_PERIOD", field="period")


# --- Порожній період (REQ-F-033) ---------------------------------------------


@pytest.mark.requirement("REQ-F-033")
def test_empty_period_returns_zero(client, profile_id):
    """REQ-F-033: за період без покупок підсумок дорівнює 0,00."""

    payload = summary(client, profile_id, period="month", date="2026-03-15")

    assert payload["total"] == "0.00"
    assert payload["purchaseCount"] == 0
    assert payload["currency"] == "UAH"


@pytest.mark.requirement("REQ-F-003")
def test_summary_counts_only_the_purchases_of_its_own_profile(client, profile_id, category_id):
    """REQ-F-003: підсумок не бачить покупок інших профілів."""

    add_purchase_on(client, profile_id, category_id, "2026-10-05", "100.00")
    guest = client.post("/profiles", json={"name": "Гість"}).json()["id"]

    payload = summary(client, guest, period="day", date="2026-10-05")

    assert payload["total"] == "0.00"


# --- Розбивка за категоріями (REQ-F-030) -------------------------------------


@pytest.mark.requirement("REQ-F-030")
def test_category_breakdown_shows_amount_and_share(client, profile_id, category_id):
    """REQ-F-030: таблиця «категорія — сума — частка у відсотках»."""

    restaurant = client.post(
        f"/profiles/{profile_id}/categories", json={"name": "Ресторан"}
    ).json()
    add_purchase_on(client, profile_id, category_id, "2026-10-05", "300.00")
    add_purchase_on(client, profile_id, restaurant["id"], "2026-10-06", "100.00")

    payload = breakdown(client, profile_id, period="month", date="2026-10-15")

    assert payload["total"] == "400.00"
    assert [item["categoryName"] for item in payload["items"]] == ["Продукти", "Ресторан"]
    assert payload["items"][0]["amount"] == "300.00"
    assert payload["items"][0]["share"] == pytest.approx(75.0, abs=0.1)
    assert payload["items"][1]["share"] == pytest.approx(25.0, abs=0.1)


@pytest.mark.requirement("REQ-F-030")
def test_category_shares_add_up_to_one_hundred_percent(client, profile_id, category_id):
    """REQ-F-030: сума часток дорівнює 100% з точністю до 0,1%."""

    names = ["Ресторан", "Доставка", "Напої"]
    categories = [category_id] + [
        category["id"]
        for category in client.get(f"/profiles/{profile_id}/categories").json()["items"]
        if category["name"] in names
    ]
    for index, category in enumerate(categories):
        add_purchase_on(client, profile_id, category, "2026-10-05", f"{33 + index}.33")

    payload = breakdown(client, profile_id, period="month", date="2026-10-15")

    assert sum(item["share"] for item in payload["items"]) == pytest.approx(100.0, abs=0.1)


@pytest.mark.requirement("REQ-F-030")
def test_breakdown_skips_categories_without_purchases(client, profile_id, category_id):
    """REQ-F-030: у таблиці лише категорії, у яких є витрати за період."""

    add_purchase_on(client, profile_id, category_id, "2026-10-05", "100.00")

    payload = breakdown(client, profile_id, period="month", date="2026-10-15")

    assert len(payload["items"]) == 1


@pytest.mark.requirement("REQ-F-033")
def test_breakdown_for_empty_period_is_empty(client, profile_id):
    """REQ-F-033: за період без покупок таблиця порожня, підсумок 0,00."""

    payload = breakdown(client, profile_id, period="month", date="2026-03-15")

    assert payload["items"] == []
    assert payload["total"] == "0.00"


@pytest.mark.requirement("REQ-F-009")
def test_totals_are_recalculated_after_a_purchase_is_deleted(client, profile_id, category_id):
    """REQ-F-009: після видалення покупки підсумки перераховуються."""

    created = add_purchase_on(client, profile_id, category_id, "2026-10-05", "100.00")
    add_purchase_on(client, profile_id, category_id, "2026-10-05", "50.00")

    client.delete(f"/profiles/{profile_id}/purchases/{created['id']}")

    assert summary(client, profile_id, period="day", date="2026-10-05")["total"] == "50.00"


@pytest.mark.requirement("REQ-F-009")
def test_totals_follow_the_purchase_when_its_date_changes(client, profile_id, category_id):
    """REQ-F-009: критерій прийняття зі специфікації.

    Після перенесення покупки з 05.10 на 04.10 підсумок за 05.10 зменшується
    на її вартість, а підсумок за 04.10 зростає на ту саму суму.
    """

    created = add_purchase_on(client, profile_id, category_id, "2026-10-05", "80.00")
    add_purchase_on(client, profile_id, category_id, "2026-10-05", "20.00")

    assert summary(client, profile_id, period="day", date="2026-10-05")["total"] == "100.00"
    assert summary(client, profile_id, period="day", date="2026-10-04")["total"] == "0.00"

    client.patch(
        f"/profiles/{profile_id}/purchases/{created['id']}",
        json={"occurredAt": "2026-10-04T19:00:00+03:00"},
    )

    assert summary(client, profile_id, period="day", date="2026-10-05")["total"] == "20.00"
    assert summary(client, profile_id, period="day", date="2026-10-04")["total"] == "80.00"
