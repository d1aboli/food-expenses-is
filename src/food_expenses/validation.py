"""Перевірка вхідних даних покупки (REQ-F-013..REQ-F-019).

Правила зібрані в одному місці навмисно: вони однакові для додавання і для
редагування покупки (REQ-F-008), тому не повинні бути написані двічі.

Порядок перевірок має значення. Спочатку перевіряється значення (ціна чи
кількість більша за нуль), потім — формат запису. Завдяки цьому для ціни
«-50.00» система повідомляє про порушення REQ-F-013, а не про кількість
знаків після коми.
"""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal

from .errors import ErrorDetail, ValidationFailed
from .money import parse_money, parse_quantity
from .timeutils import now

#: Схема `Money` із затвердженого контракту: рівно два знаки після коми.
MONEY_PATTERN = re.compile(r"^\d+\.\d{2}$")

#: Схема `Quantity` із затвердженого контракту: до трьох знаків після коми.
QUANTITY_PATTERN = re.compile(r"^\d+(\.\d{1,3})?$")

#: Схема `Purchase` із контракту: maxLength назви покупки.
MAX_PURCHASE_NAME_LENGTH = 100


def validate_purchase_name(raw: object) -> str:
    """REQ-F-015: назва покупки обов'язкова."""

    name = str(raw or "").strip()
    if not name:
        raise ValidationFailed(
            "Назва не може бути порожньою.",
            requirement="REQ-F-015",
            details=[ErrorDetail("name", "must not be blank")],
        )
    if len(name) > MAX_PURCHASE_NAME_LENGTH:
        raise ValidationFailed(
            f"Назва покупки довша за {MAX_PURCHASE_NAME_LENGTH} символів.",
            requirement="REQ-F-015",
            details=[ErrorDetail("name", f"max length is {MAX_PURCHASE_NAME_LENGTH}")],
        )
    return name


def validate_unit_price(raw: object) -> Decimal:
    """REQ-F-013, REQ-F-017: ціна більша за нуль, рівно дві копійчані цифри.

    Верхня межа ціни не встановлюється (REQ-F-017).
    """

    price = parse_money(raw, field="unitPrice", requirement="REQ-F-017")

    if price <= 0:
        raise ValidationFailed(
            "Ціна має бути більшою за нуль.",
            requirement="REQ-F-013",
            details=[ErrorDetail("unitPrice", "must be > 0")],
        )

    if not MONEY_PATTERN.match(str(raw).strip()):
        raise ValidationFailed(
            "Ціна вказується з двома знаками після коми, наприклад 80.00.",
            requirement="REQ-F-017",
            details=[ErrorDetail("unitPrice", "must match ^\\d+\\.\\d{2}$")],
        )

    return price


def validate_quantity(raw: object) -> Decimal:
    """REQ-F-014, REQ-F-018: кількість більша за нуль, до трьох знаків після коми."""

    quantity = parse_quantity(raw, field="quantity", requirement="REQ-F-018")

    if quantity <= 0:
        raise ValidationFailed(
            "Кількість має бути більшою за нуль.",
            requirement="REQ-F-014",
            details=[ErrorDetail("quantity", "must be > 0")],
        )

    if not QUANTITY_PATTERN.match(str(raw).strip()):
        raise ValidationFailed(
            "Кількість приймається не більш ніж з трьома знаками після коми.",
            requirement="REQ-F-018",
            details=[ErrorDetail("quantity", "max 3 decimal places")],
        )

    return quantity


def validate_occurred_at(moment: datetime) -> datetime:
    """REQ-F-016: дата й час покупки не можуть бути в майбутньому."""

    if moment > now():
        raise ValidationFailed(
            "Дата не може бути в майбутньому.",
            requirement="REQ-F-016",
            details=[ErrorDetail("occurredAt", "must not be in the future")],
        )
    return moment
