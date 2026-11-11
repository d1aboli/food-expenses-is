"""Тести даних графіків (REQ-F-031, REQ-F-032, REQ-F-033).

Джерела: критерії прийняття у spec/srs.tex і операції `getDailyChart`,
`getMonthlyChart` затвердженого контракту.

У ЛР5 реалізується серверна частина: система повертає готові точки графіка.
Малювання стовпчиків у браузері (REQ-NF-014) до обсягу цієї роботи не входить.
"""

from __future__ import annotations

import pytest

from contract import assert_error, assert_response_matches_contract

DAILY = "/profiles/{profileId}/charts/daily"
MONTHLY = "/profiles/{profileId}/charts/monthly"


@pytest.fixture
def profile_id(client) -> str:
    return client.post("/profiles", json={"name": "Ілля"}).json()["id"]


@pytest.fixture
def category_id(client, profile_id) -> str:
    categories = client.get(f"/profiles/{profile_id}/categories").json()["items"]
    return next(item["id"] for item in categories if item["name"] == "Продукти")


def add_purchase_on(client, profile_id, category_id, day: str, amount: str):
    created = client.post(
        f"/profiles/{profile_id}/purchases",
        json={
            "name": "Покупка",
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


def point_for(points: list[dict], label: str) -> dict:
    return next(point for point in points if point["label"] == label)


@pytest.mark.requirement("REQ-F-031")
def test_daily_chart_has_one_point_for_every_day_of_the_month(
    client, profile_id, category_id
):
    """REQ-F-031: для жовтня 2026 графік містить 31 стовпчик."""

    add_purchase_on(client, profile_id, category_id, "2026-10-04", "60.00")

    response = client.get(f"/profiles/{profile_id}/charts/daily", params={"month": "2026-10"})
    payload = assert_response_matches_contract(response, DAILY, "get", 200)

    assert payload["scale"] == "daily"
    assert payload["period"] == "2026-10"
    assert len(payload["points"]) == 31
    assert payload["points"][0]["label"] == "2026-10-01"
    assert payload["points"][-1]["label"] == "2026-10-31"


@pytest.mark.requirement("REQ-F-031")
def test_daily_chart_bar_equals_the_total_of_that_day(client, profile_id, category_id):
    """REQ-F-031: висота стовпчика за 04.10 дорівнює підсумку за 04.10."""

    add_purchase_on(client, profile_id, category_id, "2026-10-04", "60.00")
    add_purchase_on(client, profile_id, category_id, "2026-10-05", "81.50")

    points = client.get(
        f"/profiles/{profile_id}/charts/daily", params={"month": "2026-10"}
    ).json()["points"]

    assert point_for(points, "2026-10-04")["amount"] == "60.00"
    assert point_for(points, "2026-10-05")["amount"] == "81.50"
    assert point_for(points, "2026-10-06")["amount"] == "0.00"


@pytest.mark.requirement("REQ-F-031")
def test_daily_chart_length_follows_the_length_of_the_month(client, profile_id):
    """REQ-F-031: лютий 2026 має 28 днів, тому й стовпчиків 28."""

    points = client.get(
        f"/profiles/{profile_id}/charts/daily", params={"month": "2026-02"}
    ).json()["points"]

    assert len(points) == 28


@pytest.mark.requirement("REQ-F-033")
def test_daily_chart_of_an_empty_month_has_only_zero_bars(client, profile_id):
    """REQ-F-033: за місяць без покупок графік порожній.

    «Порожній» означає, що жоден стовпчик не піднімається над нулем. Самі
    точки лишаються, інакше порушився б REQ-F-031 про стовпчик на кожен день.
    """

    points = client.get(
        f"/profiles/{profile_id}/charts/daily", params={"month": "2026-03"}
    ).json()["points"]

    assert len(points) == 31
    assert {point["amount"] for point in points} == {"0.00"}


@pytest.mark.requirement("REQ-F-031")
def test_daily_chart_rejects_an_unparsable_month(client, profile_id):
    """Контракт: параметр `month` має вигляд РРРР-ММ."""

    response = client.get(f"/profiles/{profile_id}/charts/daily", params={"month": "жовтень"})

    assert_error(response, 400, "INVALID_PERIOD", field="month")


@pytest.mark.requirement("REQ-F-032")
def test_monthly_chart_has_one_point_for_every_month_of_the_year(
    client, profile_id, category_id
):
    """REQ-F-032: для 2026 року графік містить 12 стовпчиків."""

    add_purchase_on(client, profile_id, category_id, "2026-10-04", "400.00")

    response = client.get(f"/profiles/{profile_id}/charts/monthly", params={"year": 2026})
    payload = assert_response_matches_contract(response, MONTHLY, "get", 200)

    assert payload["scale"] == "monthly"
    assert payload["period"] == "2026"
    assert len(payload["points"]) == 12
    assert payload["points"][0]["label"] == "2026-01"
    assert payload["points"][-1]["label"] == "2026-12"


@pytest.mark.requirement("REQ-F-032")
def test_monthly_chart_bar_equals_the_total_of_that_month(client, profile_id, category_id):
    """REQ-F-032: висота стовпчика за жовтень дорівнює підсумку за жовтень."""

    add_purchase_on(client, profile_id, category_id, "2026-10-04", "300.00")
    add_purchase_on(client, profile_id, category_id, "2026-10-20", "100.00")
    add_purchase_on(client, profile_id, category_id, "2026-09-15", "70.00")

    points = client.get(
        f"/profiles/{profile_id}/charts/monthly", params={"year": 2026}
    ).json()["points"]

    assert point_for(points, "2026-10")["amount"] == "400.00"
    assert point_for(points, "2026-09")["amount"] == "70.00"
    assert point_for(points, "2026-08")["amount"] == "0.00"


@pytest.mark.requirement("REQ-F-032")
def test_monthly_chart_does_not_mix_years(client, profile_id, category_id):
    """REQ-F-032: графік за рік не бачить покупок інших років."""

    add_purchase_on(client, profile_id, category_id, "2025-10-04", "999.00")

    points = client.get(
        f"/profiles/{profile_id}/charts/monthly", params={"year": 2026}
    ).json()["points"]

    assert {point["amount"] for point in points} == {"0.00"}


@pytest.mark.requirement("REQ-F-032")
def test_monthly_chart_rejects_an_unparsable_year(client, profile_id):
    """Контракт: `year` — ціле число від 2000 до 2100."""

    response = client.get(f"/profiles/{profile_id}/charts/monthly", params={"year": "позаминулий"})

    assert_error(response, 400, "INVALID_PERIOD", field="year")
