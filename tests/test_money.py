"""Тести грошових обчислень (REQ-F-006, REQ-F-018, REQ-NF-010).

Нижній рівень тестової піраміди: перевіряється лише обчислення, без бази
даних і без HTTP. Приклади взяті з критеріїв прийняття у spec/srs.tex.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from food_expenses.errors import ValidationFailed
from food_expenses.money import (
    calculate_amount,
    format_money,
    format_quantity,
    parse_money,
    parse_quantity,
)


@pytest.mark.requirement("REQ-F-006")
def test_amount_for_weighted_purchase_from_acceptance_criteria():
    """REQ-F-006: ціна 80,00 за кілограм і кількість 0,7 дають 56,00."""

    assert calculate_amount(Decimal("80.00"), Decimal("0.7")) == Decimal("56.00")


@pytest.mark.requirement("REQ-NF-010")
def test_amount_does_not_lose_kopiikas_on_repeated_price():
    """REQ-NF-010: ціна 33,33 і кількість 3 дають 99,99, а не 100,00."""

    assert calculate_amount(Decimal("33.33"), Decimal("3")) == Decimal("99.99")


@pytest.mark.requirement("REQ-F-006")
def test_amount_is_rounded_half_up():
    """REQ-F-006: половина копійки заокруглюється вгору.

    0,05 × 0,5 = 0,025. Математичне заокруглення дає 0,03; банківське дало б
    0,02, тому цей приклад відрізняє правильну реалізацію від типової помилки.
    """

    assert calculate_amount(Decimal("0.05"), Decimal("0.5")) == Decimal("0.03")


@pytest.mark.requirement("REQ-F-006")
def test_amount_for_whole_quantity_equals_price():
    """REQ-F-006: кількість 1 не змінює ціну."""

    assert calculate_amount(Decimal("25.50"), Decimal("1")) == Decimal("25.50")


@pytest.mark.requirement("REQ-F-018")
def test_amount_for_three_decimal_quantity():
    """REQ-F-018: кількість із трьома знаками після коми (0,125 кг)."""

    assert calculate_amount(Decimal("10.00"), Decimal("0.125")) == Decimal("1.25")


@pytest.mark.requirement("REQ-NF-010")
def test_money_is_formatted_with_two_decimal_places():
    """REQ-NF-010: суми відображаються з точністю до копійки."""

    assert format_money(Decimal("56")) == "56.00"
    assert format_money(Decimal("99.99")) == "99.99"
    assert format_money(Decimal("0")) == "0.00"


@pytest.mark.requirement("REQ-F-018")
def test_quantity_is_formatted_without_trailing_zeros():
    """Контракт: схема Quantity допускає від нуля до трьох знаків після коми."""

    assert format_quantity(Decimal("0.70")) == "0.7"
    assert format_quantity(Decimal("1.000")) == "1"
    assert format_quantity(Decimal("0.125")) == "0.125"
    assert format_quantity(Decimal("100")) == "100"


@pytest.mark.requirement("REQ-F-019")
def test_unparsable_price_is_rejected_with_the_field_name():
    """REQ-F-019: у разі відхилення вказується причина і поле."""

    with pytest.raises(ValidationFailed) as failure:
        parse_money("вісімдесят", field="unitPrice")

    assert failure.value.details[0].field_name == "unitPrice"


@pytest.mark.requirement("REQ-F-019")
def test_unparsable_quantity_is_rejected_with_the_field_name():
    """REQ-F-019: те саме для кількості."""

    with pytest.raises(ValidationFailed) as failure:
        parse_quantity("дві", field="quantity")

    assert failure.value.details[0].field_name == "quantity"


@pytest.mark.requirement("REQ-NF-010")
def test_price_is_parsed_without_binary_floating_point():
    """REQ-NF-010: проміжні обчислення не втрачають копійки.

    0,1 + 0,2 у числах з рухомою комою дає 0,30000000000000004. Якщо ціни
    зберігаються як Decimal, такої похибки немає.
    """

    assert parse_money("0.10") + parse_money("0.20") == Decimal("0.30")
