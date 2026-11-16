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
    """Перетворює значення на грошову суму.

    Args:
        raw: Значення з запиту; перетворюється на рядок і розбирається як
            `Decimal`. Через рядок, а не через `float`: `float("0.1")` уже
            не дорівнює одній десятій.
        field: Ім'я поля — потрапляє в повідомлення й у `details` помилки.
        requirement: ID вимоги, яку порушено; потрапляє у відповідь.

    Returns:
        Сума в `Decimal` без перевірки знака, межі та кількості знаків —
        це робить модуль `validation`.

    Raises:
        ValidationFailed: Значення не є скінченним числом.
    """
    return _parse(raw, field, requirement, "must be a decimal number")


def parse_quantity(raw: object, field: str = "quantity", requirement: str = "REQ-F-018") -> Decimal:
    """Перетворює значення на кількість.

    Args:
        raw: Значення з запиту.
        field: Ім'я поля для повідомлення про помилку.
        requirement: ID вимоги, яку порушено.

    Returns:
        Кількість у `Decimal`.

    Raises:
        ValidationFailed: Значення не є скінченним числом.
    """
    return _parse(raw, field, requirement, "must be a decimal number")


def calculate_amount(unit_price: Decimal, quantity: Decimal) -> Decimal:
    """Вартість покупки: ціна за одиницю, помножена на кількість (REQ-F-006).

    Заокруглення математичне (`ROUND_HALF_UP`), а не банківське. Вбудована
    `round` у Python заокруглює половину до парного, і на звичайних числах
    різниці не видно — але 0,05 × 0,5 дало б 0,02 замість 0,03. У SRS
    прямо сказано: половина заокруглюється вгору.

    Args:
        unit_price: Ціна за одиницю, уже перевірена `validate_unit_price`.
        quantity: Кількість, уже перевірена `validate_quantity`.

    Returns:
        Вартість покупки, заокруглена до копійки.
    """
    return (unit_price * quantity).quantize(CENT, rounding=ROUND_HALF_UP)


def format_money(value: Decimal) -> str:
    """Подає суму рядком із двома знаками після коми (REQ-NF-010).

    Args:
        value: Сума в `Decimal`.

    Returns:
        Рядок вигляду `100.00`. Саме такий формат вимагає схема `Money`
        затвердженого контракту, тож ціле число теж отримує «.00».
    """
    return f"{value.quantize(CENT, rounding=ROUND_HALF_UP):f}"


def format_quantity(value: Decimal) -> str:
    """Подає кількість рядком без зайвих нулів у кінці.

    Кількість, на відміну від суми, не має сталої точності: 0,7 кг
    записується як `0.7`, а не `0.700`, бо вимога дозволяє до трьох
    знаків, а не вимагає трьох (REQ-F-018).

    Args:
        value: Кількість у `Decimal`.

    Returns:
        Рядок без хвостових нулів; для нуля — `0`.
    """
    text = f"{value:f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def decimal_places(value: Decimal) -> int:
    """Кількість знаків після коми в записаному значенні.

    Рахується саме записана точність, а не математична: `Decimal("1.50")`
    має два знаки, хоча дорівнює `1.5`. Це те, що треба перевірці формату
    ціни й кількості.

    Args:
        value: Значення в `Decimal`.

    Returns:
        Кількість знаків після коми; 0 для цілого.
    """
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
