"""Маршрути підсумків і даних графіків.

Операції `getSummary`, `getCategoryBreakdown`, `getDailyChart` та
`getMonthlyChart` з контракту.

Параметри запиту приймаються рядками й розбираються власним кодом, щоб
некоректне значення давало відповідь 400 за єдиною моделлю помилки
(`BadRequest` у контракті), а не стандартну відповідь фреймворку.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ...periods import parse_month, parse_year
from ...services.summaries import SummaryService
from ...timeutils import parse_date
from ..dependencies import get_summary_service
from ..params import PROFILE_ID
from ..schemas import breakdown_payload, chart_payload, summary_payload

router = APIRouter(tags=["summary"])


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
    """Операція `getSummary`: підсумок витрат за період (REQ-F-026..REQ-F-029).

    Тиждень — з понеділка по неділю, місяць — з 1-го по останнє число,
    довільний діапазон включає обидві межі. Якщо покупок за період немає,
    повертається 0.00, а не помилка (REQ-F-033). Некоректні межі —
    400 `INVALID_PERIOD`.
    """
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
    """Операція `getCategoryBreakdown`: розбивка за категоріями (REQ-F-030).

    Для кожної категорії — сума й частка у відсотках із двома знаками
    після коми. Категорії без покупок за період у розбивку не
    потрапляють.
    """
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
    """Операція `getDailyChart`: витрати за днями місяця (REQ-F-031).

    Повертається по одній точці на кожен день місяця, включно з днями
    без покупок: графік має показувати провали, а не стискатися. У
    порожньому місяці це 28–31 точка з нулем, а не порожній перелік —
    так узгоджено REQ-F-031 з REQ-F-033.
    """
    year, month_number = parse_month(month)
    points = service.daily_chart(profile_id, year, month_number)
    return chart_payload("daily", f"{year:04d}-{month_number:02d}", points)


@router.get("/profiles/{profileId}/charts/monthly")
def get_monthly_chart(
    profile_id: str = PROFILE_ID,
    year: str | None = Query(default=None),
    service: SummaryService = Depends(get_summary_service),
) -> dict:
    """Операція `getMonthlyChart`: витрати за місяцями року (REQ-F-032).

    Дванадцять точок незалежно від того, у яких місяцях були покупки — з
    тієї самої причини, що й у графіку за днями.
    """
    parsed_year = parse_year(year)
    points = service.monthly_chart(profile_id, parsed_year)
    return chart_payload("monthly", f"{parsed_year:04d}", points)
