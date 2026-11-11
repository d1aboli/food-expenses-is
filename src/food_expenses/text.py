"""Перевірка назв (REQ-F-001, REQ-F-015, REQ-F-021).

Профіль, категорія й покупка мають назву, і правило для всіх трьох однакове:
крайові пробіли прибираються, порожня назва не приймається, довжина обмежена.
Відрізняються лише межа довжини, ID вимоги та текст повідомлення, тому вони
винесені в опис правила, а сама перевірка існує в одному примірнику.
"""

from __future__ import annotations

from dataclasses import dataclass

from .errors import ErrorDetail, ValidationFailed


@dataclass(frozen=True)
class NameRule:
    """Правило перевірки назви для однієї сутності."""

    field: str
    requirement: str
    max_length: int
    blank_message: str
    too_long_message: str


#: REQ-F-001: назва профілю, maxLength 60 за схемою `Profile` контракту.
PROFILE_NAME = NameRule(
    field="name",
    requirement="REQ-F-001",
    max_length=60,
    blank_message="Назва профілю не може бути порожньою.",
    too_long_message="Назва профілю довша за 60 символів.",
)

#: REQ-F-021: назва категорії, maxLength 40 за схемою `Category` контракту.
CATEGORY_NAME = NameRule(
    field="name",
    requirement="REQ-F-021",
    max_length=40,
    blank_message="Назва категорії не може бути порожньою.",
    too_long_message="Назва категорії довша за 40 символів.",
)

#: REQ-F-015: назва покупки, maxLength 100 за схемою `Purchase` контракту.
PURCHASE_NAME = NameRule(
    field="name",
    requirement="REQ-F-015",
    max_length=100,
    blank_message="Назва не може бути порожньою.",
    too_long_message="Назва покупки довша за 100 символів.",
)


def clean_name(raw: object, rule: NameRule) -> str:
    """Зводить назву до збереженого вигляду або відхиляє її.

    Крайові пробіли прибираються: інакше «Хліб» і «Хліб » були б різними
    назвами, а назва саме для того й потрібна, щоб відрізняти записи.
    """

    cleaned = str(raw or "").strip()

    if not cleaned:
        raise ValidationFailed(
            rule.blank_message,
            requirement=rule.requirement,
            details=[ErrorDetail(rule.field, "must not be blank")],
        )

    if len(cleaned) > rule.max_length:
        raise ValidationFailed(
            rule.too_long_message,
            requirement=rule.requirement,
            details=[ErrorDetail(rule.field, f"max length is {rule.max_length}")],
        )

    return cleaned
