"""Робота з датою й часом у часовому поясі застосунку.

Календарні межі періодів визначаються в поясі `Europe/Kyiv` (REQ-F-026..029),
тому будь-яка дата, що приходить ззовні, зводиться до цього поясу.
"""

from __future__ import annotations

from datetime import date, datetime

from .config import APP_TIMEZONE
from .errors import ErrorDetail, InvalidPeriod, ValidationFailed


def now() -> datetime:
    """Поточний момент у часовому поясі застосунку."""

    return datetime.now(tz=APP_TIMEZONE)


def to_app_timezone(moment: datetime) -> datetime:
    """Зводить момент до часового поясу застосунку.

    Значення без зсуву вважається записаним у місцевому часі.
    """

    if moment.tzinfo is None:
        return moment.replace(tzinfo=APP_TIMEZONE)
    return moment.astimezone(APP_TIMEZONE)


def parse_datetime(raw: object, field: str, requirement: str = "REQ-F-008") -> datetime:
    """Розбирає дату й час із запиту або відхиляє значення."""

    try:
        moment = datetime.fromisoformat(str(raw))
    except (TypeError, ValueError):
        raise ValidationFailed(
            f"Поле «{field}» має містити дату й час у форматі ISO 8601.",
            requirement=requirement,
            details=[ErrorDetail(field, "must be an ISO 8601 date-time")],
        ) from None
    return to_app_timezone(moment)


def parse_date(raw: object, field: str, requirement: str = "REQ-F-029") -> date:
    """Розбирає календарну дату з параметра запиту.

    Некоректна дата в параметрі запиту — це некоректний запит, тому
    контракт відповідає на неї кодом 400 (REQ-F-029).
    """

    try:
        return date.fromisoformat(str(raw))
    except (TypeError, ValueError):
        raise InvalidPeriod(
            f"Параметр «{field}» має містити дату у форматі РРРР-ММ-ДД.",
            requirement=requirement,
            details=[ErrorDetail(field, "must be an ISO 8601 date")],
        ) from None
