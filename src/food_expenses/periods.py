"""Календарні періоди (REQ-F-026..REQ-F-029).

Межі періодів зібрані в одному модулі навмисно. Це найдорожче місце системи:
помилка межі не падає, а тихо дає неправильну суму. Саме через межі тижня й
місяця в ЛР1 виник конфлікт між людиною й агентом, і саме тут його рішення
закріплене кодом.
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date

from .errors import ErrorDetail, InvalidPeriod
from .timeutils import now

DAY = "day"
WEEK = "week"
MONTH = "month"
RANGE = "range"
KINDS = (DAY, WEEK, MONTH, RANGE)

MONTH_PATTERN = re.compile(r"^(\d{4})-(\d{2})$")
MIN_YEAR, MAX_YEAR = 2000, 2100


@dataclass(frozen=True)
class Period:
    """Період із включними межами.

    Attributes:
        kind: Вид періоду: `day`, `week`, `month` або `range`.
        start: Перший день періоду, входить у період.
        end: Останній день періоду, теж входить у період.
    """

    kind: str
    start: date
    end: date


def resolve(
    kind: str | None,
    day: date | None = None,
    start: date | None = None,
    end: date | None = None,
) -> Period:
    """Будує період за його видом і опорною датою.

    Args:
        kind: Вид періоду: `day`, `week`, `month` або `range`.
        day: Будь-яка дата всередині періоду — для `day`, `week` і
            `month`. Якщо не задана, береться сьогоднішня.
        start: Початок діапазону; потрібен лише для `range`.
        end: Кінець діапазону; потрібен лише для `range`.

    Returns:
        Період із заповненими межами включно.

    Raises:
        InvalidPeriod: Невідомий вид періоду, або для `range` не задано
            межі, або кінець діапазону раніший за початок.
    """
    if kind not in KINDS:
        raise InvalidPeriod(
            f"Невідомий період. Допустимі значення: {', '.join(KINDS)}.",
            requirement="REQ-F-026",
            details=[ErrorDetail("period", f"must be one of: {', '.join(KINDS)}")],
        )

    if kind == RANGE:
        return _range_period(start, end)

    anchor = day or now().date()
    if kind == DAY:
        # REQ-F-026: календарна доба.
        return Period(DAY, anchor, anchor)
    if kind == WEEK:
        # REQ-F-027: з понеділка по неділю. weekday() повертає 0 для понеділка.
        monday = anchor.fromordinal(anchor.toordinal() - anchor.weekday())
        return Period(WEEK, monday, monday.fromordinal(monday.toordinal() + 6))
    # REQ-F-028: з 1-го по останнє число.
    first, last = month_bounds(anchor.year, anchor.month)
    return Period(MONTH, first, last)


def month_bounds(year: int, month: int) -> tuple[date, date]:
    """Перший і останній день місяця (REQ-F-028).

    Останній день береться з календаря, а не вираховується: лютий
    високосного року інакше дав би 28 замість 29.

    Args:
        year: Рік.
        month: Номер місяця, 1..12.

    Returns:
        Пара «перший день, останній день».
    """
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def days_of(period: Period) -> list[date]:
    """Усі дати періоду включно з межами.

    Потрібна графіку за днями: точка будується на кожен день місяця, а не
    лише на ті дні, коли були покупки (REQ-F-031).

    Args:
        period: Період із заповненими межами.

    Returns:
        Перелік дат у порядку зростання; щонайменше одна.
    """
    return [
        date.fromordinal(ordinal)
        for ordinal in range(period.start.toordinal(), period.end.toordinal() + 1)
    ]


def parse_month(raw: object) -> tuple[int, int]:
    """Розбирає параметр `month` вигляду РРРР-ММ (REQ-F-031).

    Args:
        raw: Значення параметра запиту; порожнє теж вважається помилкою.

    Returns:
        Пара «рік, номер місяця».

    Raises:
        InvalidPeriod: Значення не відповідає формату, місяць поза
            1..12 або рік поза дозволеним діапазоном. Відповідь 400, а не
            422: помилка в самому запиті, а не в даних обліку.
    """
    match = MONTH_PATTERN.match(str(raw or "").strip())
    if match is None:
        raise InvalidPeriod(
            "Місяць указується у форматі РРРР-ММ, наприклад 2026-10.",
            requirement="REQ-F-031",
            details=[ErrorDetail("month", "must match ^\\d{4}-\\d{2}$")],
        )
    year, month = int(match.group(1)), int(match.group(2))
    if not 1 <= month <= 12 or not MIN_YEAR <= year <= MAX_YEAR:
        raise InvalidPeriod(
            "Місяць указується у форматі РРРР-ММ, наприклад 2026-10.",
            requirement="REQ-F-031",
            details=[ErrorDetail("month", "month must be 01..12")],
        )
    return year, month


def parse_year(raw: object) -> int:
    """Розбирає параметр `year` (REQ-F-032).

    Args:
        raw: Значення параметра запиту.

    Returns:
        Рік числом.

    Raises:
        InvalidPeriod: Значення не є цілим числом або рік поза
            дозволеним діапазоном.
    """
    try:
        year = int(str(raw).strip())
    except (TypeError, ValueError):
        raise InvalidPeriod(
            f"Рік указується числом від {MIN_YEAR} до {MAX_YEAR}.",
            requirement="REQ-F-032",
            details=[ErrorDetail("year", "must be an integer")],
        ) from None
    if not MIN_YEAR <= year <= MAX_YEAR:
        raise InvalidPeriod(
            f"Рік указується числом від {MIN_YEAR} до {MAX_YEAR}.",
            requirement="REQ-F-032",
            details=[ErrorDetail("year", f"must be between {MIN_YEAR} and {MAX_YEAR}")],
        )
    return year


def _range_period(start: date | None, end: date | None) -> Period:
    """REQ-F-029: довільний діапазон, включно з обома межами."""
    if start is None or end is None:
        raise InvalidPeriod(
            "Для довільного діапазону потрібні обидві межі: from і to.",
            requirement="REQ-F-029",
            details=[ErrorDetail("from", "required"), ErrorDetail("to", "required")],
        )
    if end < start:
        raise InvalidPeriod(
            "Кінець періоду не може бути раніший за його початок.",
            requirement="REQ-F-029",
            details=[ErrorDetail("to", "must not be earlier than from")],
        )
    return Period(RANGE, start, end)
