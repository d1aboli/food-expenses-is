"""Робота з датою й часом у часовому поясі застосунку.

Календарні межі періодів визначаються в поясі `Europe/Kyiv` (REQ-F-026..029),
тому будь-яка дата, що приходить ззовні, зводиться до цього поясу.
"""

from __future__ import annotations

from datetime import date, datetime

from .config import APP_TIMEZONE
from .errors import ErrorDetail, InvalidPeriod, ValidationFailed


def now() -> datetime:
    """Поточний момент у часовому поясі застосунку.

    Єдина точка, де система дізнається поточний час. Прямі виклики
    `datetime.now()` деінде заборонені: тест не зміг би підмінити час, а
    межа доби в іншому поясі зсунулася б (REQ-F-007).

    Returns:
        Поточний момент із зсувом `Europe/Kyiv`.
    """
    return datetime.now(tz=APP_TIMEZONE)


def to_app_timezone(moment: datetime) -> datetime:
    """Зводить момент до часового поясу застосунку.

    Args:
        moment: Момент із зсувом або без нього. Значення без зсуву
            вважається записаним у місцевому часі, а не в UTC: саме так
            його вводить людина.

    Returns:
        Той самий момент із зсувом `Europe/Kyiv`.
    """
    if moment.tzinfo is None:
        return moment.replace(tzinfo=APP_TIMEZONE)
    return moment.astimezone(APP_TIMEZONE)


def parse_datetime(raw: object, field: str, requirement: str = "REQ-F-008") -> datetime:
    """Розбирає дату й час із тіла запиту (REQ-F-008).

    Args:
        raw: Значення поля; очікується рядок у форматі ISO 8601.
        field: Ім'я поля для повідомлення про помилку.
        requirement: ID вимоги, яку порушено.

    Returns:
        Момент, зведений до часового поясу застосунку.

    Raises:
        ValidationFailed: Значення не розбирається як дата й час.
            Відповідь 422: помилка в даних покупки, а не в самому запиті.
    """
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
    """Розбирає календарну дату з параметра запиту (REQ-F-029).

    Args:
        raw: Значення параметра; очікується рядок РРРР-ММ-ДД.
        field: Ім'я параметра для повідомлення про помилку.
        requirement: ID вимоги, яку порушено.

    Returns:
        Дату без часу.

    Raises:
        InvalidPeriod: Значення не розбирається як дата. Відповідь 400, а
            не 422, на відміну від `parse_datetime`: некоректний параметр
            запиту — це некоректний запит, а не некоректні дані обліку.
    """
    try:
        return date.fromisoformat(str(raw))
    except (TypeError, ValueError):
        raise InvalidPeriod(
            f"Параметр «{field}» має містити дату у форматі РРРР-ММ-ДД.",
            requirement=requirement,
            details=[ErrorDetail(field, "must be an ISO 8601 date")],
        ) from None
