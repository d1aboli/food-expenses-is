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
    """Перевіряє назву покупки (REQ-F-015).

    Args:
        raw: Значення поля `name` із запиту.

    Returns:
        Назву без крайових пробілів.

    Raises:
        ValidationFailed: Назва порожня або довша за 100 символів.
    """
    return clean_name(raw, PURCHASE_NAME)


@dataclass(frozen=True)
class MoneyRule:
    """Правило перевірки грошової суми, яку вводить користувач.

    Ціна за одиницю і сума бюджету перевіряються однаково: число, більше за
    нуль, записане з двома знаками після коми. Відрізняються лише поле, ID
    вимог і тексти повідомлень.

    Attributes:
        field: Ім'я поля у відповіді про помилку.
        positive_requirement: ID вимоги про додатність значення.
        format_requirement: ID вимоги про формат запису.
        positive_message: Повідомлення, коли значення не додатне.
        format_message: Повідомлення, коли формат запису не той.
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
    """Перевіряє значення суми, а потім формат її запису.

    Порядок саме такий: для «-50.00» головна причина відмови — від'ємне
    значення, а не кількість знаків після коми. Зворотний порядок давав би
    формально правильну, але марну відповідь.

    Args:
        raw: Значення поля із запиту.
        rule: Правило для цього поля: `UNIT_PRICE` або `BUDGET_LIMIT`.

    Returns:
        Суму в `Decimal`.

    Raises:
        ValidationFailed: Значення не є числом, не більше за нуль або
            записане не з двома знаками після коми.
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
    """Перевіряє ціну за одиницю (REQ-F-013, REQ-F-017).

    Верхня межа ціни не встановлюється: вимога її не задає, і покупка на
    сто тисяч гривень так само законна, як і на десять.

    Args:
        raw: Значення поля `unitPrice` із запиту.

    Returns:
        Ціну в `Decimal`.

    Raises:
        ValidationFailed: Ціна не більша за нуль або записана не з двома
            знаками після коми.

    Note:
        Запис «100» відхиляється, хоча REQ-F-017 дозволяє ціле число:
        схема `Money` затвердженого контракту вимагає рівно два знаки.
        Розбіжність зафіксована як відкрите питання ВП-03 і закривається
        на рівні інтерфейсу користувача, а не тут.
    """
    return validate_money_amount(raw, UNIT_PRICE)


def validate_quantity(raw: object) -> Decimal:
    """Перевіряє кількість (REQ-F-014, REQ-F-018).

    Args:
        raw: Значення поля `quantity` із запиту.

    Returns:
        Кількість у `Decimal`.

    Raises:
        ValidationFailed: Кількість не більша за нуль або записана більш
            ніж із трьома знаками після коми. Три знаки — це грами:
            0,125 кг зважити можна, 0,1255 кг на кухонних вагах — ні.
    """
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
    """Перевіряє, що покупка не в майбутньому (REQ-F-016).

    Args:
        moment: Момент покупки, уже зведений до часового поясу застосунку.

    Returns:
        Той самий момент без змін.

    Raises:
        ValidationFailed: Момент пізніший за поточний. Облік фіксує те, що
            вже сталося; запис наперед означав би планування, а воно поза
            межами системи.
    """
    if moment > now():
        raise ValidationFailed(
            "Дата не може бути в майбутньому.",
            requirement="REQ-F-016",
            details=[ErrorDetail("occurredAt", "must not be in the future")],
        )
    return moment


def validate_budget_limit(raw: object) -> Decimal:
    """Перевіряє суму місячного бюджету (ADD-01, REQ-A-002).

    Args:
        raw: Значення поля `limit` із запиту.

    Returns:
        Суму бюджету в `Decimal`.

    Raises:
        ValidationFailed: Сума не більша за нуль або записана не з двома
            знаками після коми. Бюджет 0,00 відхиляється: його зміст —
            «на цю категорію не витрачати», а це не бюджет, а заборона,
            якої вимоги не передбачають.
    """
    return validate_money_amount(raw, BUDGET_LIMIT)
