"""Операції `getSummary`, `getCategoryBreakdown`, `getDailyChart`,
`getMonthlyChart` з контракту.

Параметри запиту приймаються рядками й розбираються власним кодом, щоб
некоректне значення давало відповідь 400 за єдиною моделлю помилки
(`BadRequest` у контракті), а не стандартну відповідь фреймворку.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query

from ...periods import parse_month, parse_year
from ...services.summaries import SummaryService
from ...timeutils import parse_date
from ..dependencies import get_summary_service
from ..schemas import breakdown_payload, chart_payload, summary_payload

router = APIRouter(tags=["summary"])

PROFILE_ID = Path(alias="profileId")


def _period_arguments(
    period: str | None, day: str | None, since: str | None, until: str | None
) -> dict:
    return {
        "kind": period,
        "day": parse_date(day, "date") if day else None,
        "start": parse_date(since, "from") if since else None,
        "end": parse_date(until, "to") if until else None,
    }


@router.get("/profiles/{profileId}/summary")
def get_summary(
    profile_id: str = PROFILE_ID,
    period: str | None = Query(default=None),
    day: str | None = Query(default=None, alias="date"),
    since: str | None = Query(default=None, alias="from"),
    until: str | None = Query(default=None, alias="to"),
    service: SummaryService = Depends(get_summary_service),
) -> dict:
    """REQ-F-026..REQ-F-029, REQ-F-033: підсумок витрат за період."""

    total = service.total(profile_id, **_period_arguments(period, day, since, until))
    return summary_payload(total)


@router.get("/profiles/{profileId}/summary/categories")
def get_category_breakdown(
    profile_id: str = PROFILE_ID,
    period: str | None = Query(default=None),
    day: str | None = Query(default=None, alias="date"),
    since: str | None = Query(default=None, alias="from"),
    until: str | None = Query(default=None, alias="to"),
    service: SummaryService = Depends(get_summary_service),
) -> dict:
    """REQ-F-030: розбивка витрат за категоріями."""

    resolved, total, items = service.breakdown(
        profile_id, **_period_arguments(period, day, since, until)
    )
    return breakdown_payload(resolved, total, items)


@router.get("/profiles/{profileId}/charts/daily")
def get_daily_chart(
    profile_id: str = PROFILE_ID,
    month: str | None = Query(default=None),
    service: SummaryService = Depends(get_summary_service),
) -> dict:
    """REQ-F-031: витрати за днями обраного місяця."""

    year, month_number = parse_month(month)
    points = service.daily_chart(profile_id, year, month_number)
    return chart_payload("daily", f"{year:04d}-{month_number:02d}", points)


@router.get("/profiles/{profileId}/charts/monthly")
def get_monthly_chart(
    profile_id: str = PROFILE_ID,
    year: str | None = Query(default=None),
    service: SummaryService = Depends(get_summary_service),
) -> dict:
    """REQ-F-032: витрати за місяцями обраного року."""

    parsed_year = parse_year(year)
    points = service.monthly_chart(profile_id, parsed_year)
    return chart_payload("monthly", f"{parsed_year:04d}", points)
