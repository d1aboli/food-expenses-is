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
    """Період із включними межами."""

    kind: str
    start: date
    end: date


def resolve(
    kind: str | None,
    day: date | None = None,
    start: date | None = None,
    end: date | None = None,
) -> Period:
    """Будує період за його видом.

    `day` — будь-яка дата всередині періоду для day, week і month;
    `start` і `end` — межі для довільного діапазону.
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
    """Перший і останній день місяця."""

    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def days_of(period: Period) -> list[date]:
    """Усі дати періоду включно з межами."""

    return [
        date.fromordinal(ordinal)
        for ordinal in range(period.start.toordinal(), period.end.toordinal() + 1)
    ]


def parse_month(raw: object) -> tuple[int, int]:
    """Розбирає параметр `month` вигляду РРРР-ММ (REQ-F-031)."""

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
    """Розбирає параметр `year` (REQ-F-032)."""

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
