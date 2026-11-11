"""Грошові суми та кількості (REQ-F-006, REQ-F-017, REQ-F-018, REQ-NF-010).

Усі обчислення виконуються в `Decimal`. Числа з рухомою комою не
використовуються ніде: саме вони втрачають копійки на кшталт
0,1 + 0,2 = 0,30000000000000004.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from .errors import ErrorDetail, ValidationFailed

#: Крок заокруглення грошової суми — одна копійка.
CENT = Decimal("0.01")


def parse_money(raw: object, field: str = "amount", requirement: str = "REQ-F-017") -> Decimal:
    """Перетворює значення на грошову суму або відхиляє його."""

    return _parse(raw, field, requirement, "must be a decimal number")


def parse_quantity(
    raw: object, field: str = "quantity", requirement: str = "REQ-F-018"
) -> Decimal:
    """Перетворює значення на кількість або відхиляє його."""

    return _parse(raw, field, requirement, "must be a decimal number")


def calculate_amount(unit_price: Decimal, quantity: Decimal) -> Decimal:
    """REQ-F-006: вартість покупки з заокругленням половини копійки вгору.

    Заокруглення саме математичне (ROUND_HALF_UP), а не банківське: у SRS
    прямо сказано, що половина заокруглюється вгору.
    """

    return (unit_price * quantity).quantize(CENT, rounding=ROUND_HALF_UP)


def format_money(value: Decimal) -> str:
    """REQ-NF-010: сума завжди з двома знаками після коми."""

    return f"{value.quantize(CENT, rounding=ROUND_HALF_UP):f}"


def format_quantity(value: Decimal) -> str:
    """Кількість без зайвих нулів у кінці: 0,70 показується як 0,7."""

    text = f"{value:f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def decimal_places(value: Decimal) -> int:
    """Кількість знаків після коми у записаному значенні."""

    exponent = value.as_tuple().exponent
    return -exponent if isinstance(exponent, int) and exponent < 0 else 0


def _parse(raw: object, field: str, requirement: str, issue: str) -> Decimal:
    try:
        value = Decimal(str(raw).strip())
    except (InvalidOperation, ValueError, ArithmeticError):
        raise ValidationFailed(
            f"Поле «{field}» має бути числом.",
            requirement=requirement,
            details=[ErrorDetail(field, issue)],
        ) from None
    if not value.is_finite():
        raise ValidationFailed(
            f"Поле «{field}» має бути числом.",
            requirement=requirement,
            details=[ErrorDetail(field, issue)],
        )
    return value
