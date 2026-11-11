"""Тести експорту у CSV та резервної копії бази (REQ-F-035, REQ-F-036, REQ-I-003).

Джерела: критерії прийняття у spec/srs.tex і операції `exportPurchases`,
`createBackup` затвердженого контракту.
"""

from __future__ import annotations

import csv
import io
import sqlite3

import pytest

from contract import assert_error, assert_response_matches_contract

BACKUPS = "/backups"
EXPECTED_HEADER = ["name", "category", "unitPrice", "quantity", "amount", "occurredAt"]


@pytest.fixture
def profile_id(client) -> str:
    return client.post("/profiles", json={"name": "Ілля"}).json()["id"]


@pytest.fixture
def category_id(client, profile_id) -> str:
    categories = client.get(f"/profiles/{profile_id}/categories").json()["items"]
    return next(item["id"] for item in categories if item["name"] == "Продукти")


def add_purchase_on(client, profile_id, category_id, day, price, quantity="1", name="Хліб"):
    created = client.post(
        f"/profiles/{profile_id}/purchases",
        json={
            "name": name,
            "categoryId": category_id,
            "unitPrice": price,
            "quantity": quantity,
        },
    ).json()
    client.patch(
        f"/profiles/{profile_id}/purchases/{created['id']}",
        json={"occurredAt": f"{day}T12:00:00+03:00"},
    )
    return created


def export(client, profile_id, **params):
    return client.get(f"/profiles/{profile_id}/purchases/export", params=params)


def rows_of(response) -> list[list[str]]:
    return list(csv.reader(io.StringIO(response.text)))


# --- Експорт у CSV (REQ-F-035, REQ-I-003) ------------------------------------


@pytest.mark.requirement("REQ-I-003")
def test_export_starts_with_the_agreed_header(client, profile_id, category_id):
    """REQ-I-003: назва, категорія, ціна за одиницю, кількість, вартість, дата й час."""

    add_purchase_on(client, profile_id, category_id, "2026-10-05", "25.50")

    rows = rows_of(export(client, profile_id))

    assert rows[0] == EXPECTED_HEADER


@pytest.mark.requirement("REQ-F-035")
def test_export_has_one_row_per_purchase(client, profile_id, category_id):
    """REQ-F-035: критерій прийняття — рядок заголовків і по рядку на покупку."""

    add_purchase_on(client, profile_id, category_id, "2026-10-05", "25.50", name="Хліб")
    add_purchase_on(client, profile_id, category_id, "2026-10-06", "80.00", "0.7", "Яблука")

    rows = rows_of(export(client, profile_id))

    assert len(rows) == 3


@pytest.mark.requirement("REQ-F-035")
def test_export_amounts_match_the_purchase_list(client, profile_id, category_id):
    """REQ-F-035: суми у файлі збігаються зі списком покупок."""

    add_purchase_on(client, profile_id, category_id, "2026-10-06", "80.00", "0.7", "Яблука")

    row = rows_of(export(client, profile_id))[1]

    assert row[0] == "Яблука"
    assert row[1] == "Продукти"
    assert row[2] == "80.00"
    assert row[3] == "0.7"
    assert row[4] == "56.00"
    assert row[5].startswith("2026-10-06T12:00:00")


@pytest.mark.requirement("REQ-I-003")
def test_export_is_utf8_and_keeps_ukrainian_names(client, profile_id, category_id):
    """REQ-I-003: кодування UTF-8."""

    add_purchase_on(client, profile_id, category_id, "2026-10-05", "12.00", name="Їжа «смачна»")

    response = export(client, profile_id)

    assert "utf-8" in response.headers["content-type"].lower()
    assert "Їжа «смачна»" in response.text


@pytest.mark.requirement("REQ-F-035")
def test_export_is_returned_as_a_csv_attachment(client, profile_id, category_id):
    """Контракт: тип вмісту text/csv і заголовок Content-Disposition."""

    add_purchase_on(client, profile_id, category_id, "2026-10-05", "12.00")

    response = export(client, profile_id)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    assert ".csv" in response.headers["content-disposition"]


@pytest.mark.requirement("REQ-F-035")
def test_export_covers_only_the_requested_period(client, profile_id, category_id):
    """REQ-F-035: експортуються покупки за обраний період."""

    add_purchase_on(client, profile_id, category_id, "2026-10-01", "10.00", name="Усередині")
    add_purchase_on(client, profile_id, category_id, "2026-10-09", "20.00", name="Поза межами")

    rows = rows_of(export(client, profile_id, **{"from": "2026-10-01", "to": "2026-10-03"}))

    assert len(rows) == 2
    assert rows[1][0] == "Усередині"


@pytest.mark.requirement("REQ-F-033")
def test_export_of_an_empty_period_has_only_the_header(client, profile_id):
    """За період без покупок файл містить лише рядок заголовків."""

    rows = rows_of(export(client, profile_id, **{"from": "2026-03-01", "to": "2026-03-31"}))

    assert rows == [EXPECTED_HEADER]


@pytest.mark.requirement("REQ-F-003")
def test_export_of_an_unknown_profile_is_not_found(client):
    """REQ-F-003: експорт можливий лише для наявного профілю."""

    response = export(client, "00000000-0000-4000-8000-000000000000")

    assert_error(response, 404, "PROFILE_NOT_FOUND")


@pytest.mark.requirement("REQ-F-029")
def test_export_with_unparsable_dates_is_a_bad_request(client, profile_id):
    """Контракт: некоректний параметр запиту — 400."""

    response = export(client, profile_id, **{"from": "05.10.2026"})

    assert_error(response, 400, "INVALID_PERIOD", field="from")


@pytest.mark.requirement("REQ-F-035")
def test_export_is_written_to_the_action_log(client, profile_id, category_id, settings):
    """Експорт — дія в системі, тому вона в журналі."""

    add_purchase_on(client, profile_id, category_id, "2026-10-05", "12.00")

    export(client, profile_id)

    log = (settings.log_dir / "app.log").read_text(encoding="utf-8")
    assert "event=purchases.exported" in log


# --- Резервна копія бази (REQ-F-036) -----------------------------------------


@pytest.mark.requirement("REQ-F-036")
def test_backup_is_created(client, settings, profile_id):
    """REQ-F-036: система створює резервну копію файлу бази даних."""

    response = client.post(BACKUPS)

    payload = assert_response_matches_contract(response, BACKUPS, "post", 201)
    assert payload["fileName"].endswith(".db")
    assert payload["sizeBytes"] > 0
    assert (settings.backup_dir / payload["fileName"]).exists()


@pytest.mark.requirement("REQ-F-036")
def test_backup_contains_the_stored_data(client, settings, profile_id, category_id):
    """REQ-F-036: копія придатна для відновлення, а не просто порожній файл."""

    client.post(
        f"/profiles/{profile_id}/purchases",
        json={
            "name": "Хліб",
            "categoryId": category_id,
            "unitPrice": "25.50",
            "quantity": "1",
        },
    )

    file_name = client.post(BACKUPS).json()["fileName"]

    connection = sqlite3.connect(settings.backup_dir / file_name)
    try:
        stored = connection.execute("SELECT COUNT(*) FROM purchases").fetchone()[0]
    finally:
        connection.close()
    assert stored == 1


@pytest.mark.requirement("REQ-F-036")
def test_repeated_backups_do_not_overwrite_each_other(client, settings, profile_id):
    """REQ-F-036: нова копія не знищує попередню."""

    first = client.post(BACKUPS).json()["fileName"]
    second = client.post(BACKUPS).json()["fileName"]

    assert first != second
    assert (settings.backup_dir / first).exists()
    assert (settings.backup_dir / second).exists()


@pytest.mark.requirement("REQ-F-036")
def test_backup_is_written_to_the_action_log(client, settings, profile_id):
    """Створення копії — дія в системі, тому вона в журналі."""

    client.post(BACKUPS)

    log = (settings.log_dir / "app.log").read_text(encoding="utf-8")
    assert "event=backup.created" in log
