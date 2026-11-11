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
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from .errors import ErrorDetail, ValidationFailed
from .money import parse_money, parse_quantity
from .text import PURCHASE_NAME, clean_name
from .timeutils import now

#: Схема `Money` із затвердженого контракту: рівно два знаки після коми.
MONEY_PATTERN = re.compile(r"^\d+\.\d{2}$")

#: Схема `Quantity` із затвердженого контракту: до трьох знаків після коми.
QUANTITY_PATTERN = re.compile(r"^\d+(\.\d{1,3})?$")

def validate_purchase_name(raw: object) -> str:
    """REQ-F-015: назва покупки обов'язкова."""

    return clean_name(raw, PURCHASE_NAME)


@dataclass(frozen=True)
class MoneyRule:
    """Правило перевірки грошової суми, яку вводить користувач.

    Ціна за одиницю і сума бюджету перевіряються однаково: число, більше за
    нуль, записане з двома знаками після коми. Відрізняються лише поле, ID
    вимог і тексти повідомлень.
    """

    field: str
    positive_requirement: str
    format_requirement: str
    positive_message: str
    format_message: str


#: REQ-F-013, REQ-F-017: ціна за одиницю.
UNIT_PRICE = MoneyRule(
    field="unitPrice",
    positive_requirement="REQ-F-013",
    format_requirement="REQ-F-017",
    positive_message="Ціна має бути більшою за нуль.",
    format_message="Ціна вказується з двома знаками після коми, наприклад 80.00.",
)

#: REQ-A-002 (адендум ADD-01): сума місячного бюджету.
BUDGET_LIMIT = MoneyRule(
    field="limit",
    positive_requirement="REQ-A-002",
    format_requirement="REQ-A-002",
    positive_message="Сума бюджету має бути більшою за нуль.",
    format_message="Сума бюджету вказується з двома знаками після коми, наприклад 3000.00.",
)


def validate_money_amount(raw: object, rule: MoneyRule) -> Decimal:
    """Перевіряє значення, а потім формат запису.

    Порядок саме такий: для «-50.00» головна причина відмови — від'ємне
    значення, а не кількість знаків після коми.
    """

    amount = parse_money(raw, field=rule.field, requirement=rule.format_requirement)

    if amount <= 0:
        raise ValidationFailed(
            rule.positive_message,
            requirement=rule.positive_requirement,
            details=[ErrorDetail(rule.field, "must be > 0")],
        )

    if not MONEY_PATTERN.match(str(raw).strip()):
        raise ValidationFailed(
            rule.format_message,
            requirement=rule.format_requirement,
            details=[ErrorDetail(rule.field, r"must match ^\d+\.\d{2}$")],
        )

    return amount


def validate_unit_price(raw: object) -> Decimal:
    """REQ-F-013, REQ-F-017: ціна більша за нуль, рівно дві копійчані цифри.

    Верхня межа ціни не встановлюється (REQ-F-017).
    """

    return validate_money_amount(raw, UNIT_PRICE)


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


def validate_budget_limit(raw: object) -> Decimal:
    """REQ-A-002 (ADD-01): сума бюджету більша за нуль, з двома знаками після коми."""

    return validate_money_amount(raw, BUDGET_LIMIT)
