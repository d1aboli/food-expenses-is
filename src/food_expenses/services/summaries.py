"""Підсумки, розбивка за категоріями та дані графіків (REQ-F-026..REQ-F-033)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from ..db import Database
from ..errors import ProfileNotFound
from ..periods import Period, days_of, month_bounds, resolve
from ..repositories.profiles import ProfileRepository
from ..repositories.summaries import PurchaseAmount, SummaryRepository

ZERO = Decimal("0.00")
#: Частка у відсотках заокруглюється до сотих: сума часток тоді відрізняється
#: від 100% не більш ніж на 0,03%, що вкладається в критерій REQ-F-030 (0,1%).
SHARE_PRECISION = 2


@dataclass(frozen=True)
class Total:
    """Підсумок за період (REQ-F-026..REQ-F-029)."""

    period: Period
    amount: Decimal
    purchase_count: int


@dataclass(frozen=True)
class CategoryShare:
    """Рядок таблиці «категорія — сума — частка» (REQ-F-030)."""

    category_id: str
    category_name: str
    amount: Decimal
    share: float


@dataclass(frozen=True)
class ChartPoint:
    """Один стовпчик графіка (REQ-F-031, REQ-F-032)."""

    label: str
    amount: Decimal


class SummaryService:
    """Обчислення підсумків над покупками активного профілю."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def total(
        self,
        profile_id: str,
        kind: str | None,
        day: date | None = None,
        start: date | None = None,
        end: date | None = None,
    ) -> Total:
        """REQ-F-026..REQ-F-029, REQ-F-033: підсумок витрат за період."""

        period = resolve(kind, day=day, start=start, end=end)
        amounts = self._amounts(profile_id, period)
        return Total(period, _sum(amounts), len(amounts))

    def breakdown(
        self,
        profile_id: str,
        kind: str | None,
        day: date | None = None,
        start: date | None = None,
        end: date | None = None,
    ) -> tuple[Period, Decimal, list[CategoryShare]]:
        """REQ-F-030: розбивка витрат за категоріями."""

        period = resolve(kind, day=day, start=start, end=end)
        amounts = self._amounts(profile_id, period)
        total = _sum(amounts)

        grouped: dict[str, tuple[str, Decimal]] = {}
        for item in amounts:
            name, accumulated = grouped.get(item.category_id, (item.category_name, ZERO))
            grouped[item.category_id] = (name, accumulated + item.amount)

        items = [
            CategoryShare(
                category_id=category_id,
                category_name=name,
                amount=amount,
                share=_share(amount, total),
            )
            for category_id, (name, amount) in grouped.items()
        ]
        # Найбільша витрата — зверху: саме її шукають у таблиці найчастіше.
        items.sort(key=lambda item: (-item.amount, item.category_name))
        return period, total, items

    def daily_chart(self, profile_id: str, year: int, month: int) -> list[ChartPoint]:
        """REQ-F-031: один стовпчик на кожен день місяця.

        Дні без покупок лишаються в ряду зі значенням 0,00: за REQ-F-031
        стовпчик має бути на кожен день, а REQ-F-033 вимагає, щоб за порожній
        місяць жоден стовпчик не піднімався над нулем.
        """

        first, last = month_bounds(year, month)
        period = Period("month", first, last)
        totals = self._totals_by_day(profile_id, period)
        return [
            ChartPoint(label=day.isoformat(), amount=totals.get(day, ZERO))
            for day in days_of(period)
        ]

    def monthly_chart(self, profile_id: str, year: int) -> list[ChartPoint]:
        """REQ-F-032: один стовпчик на кожен місяць року."""

        period = Period("month", date(year, 1, 1), date(year, 12, 31))
        amounts = self._amounts(profile_id, period)

        totals: dict[str, Decimal] = {}
        for item in amounts:
            label = f"{item.occurred_date.year:04d}-{item.occurred_date.month:02d}"
            totals[label] = totals.get(label, ZERO) + item.amount

        return [
            ChartPoint(label=f"{year:04d}-{month:02d}", amount=totals.get(f"{year:04d}-{month:02d}", ZERO))
            for month in range(1, 13)
        ]

    def _amounts(self, profile_id: str, period: Period) -> list[PurchaseAmount]:
        with self._database.transaction() as connection:
            self._require_profile(connection, profile_id)
            return SummaryRepository(connection).amounts_between(
                profile_id, period.start, period.end
            )

    def _totals_by_day(self, profile_id: str, period: Period) -> dict[date, Decimal]:
        totals: dict[date, Decimal] = {}
        for item in self._amounts(profile_id, period):
            totals[item.occurred_date] = totals.get(item.occurred_date, ZERO) + item.amount
        return totals

    @staticmethod
    def _require_profile(connection: sqlite3.Connection, profile_id: str) -> None:
        if not ProfileRepository(connection).exists(profile_id):
            raise ProfileNotFound()


def _sum(amounts: list[PurchaseAmount]) -> Decimal:
    """REQ-F-033: за період без покупок підсумок дорівнює 0,00."""

    total = ZERO
    for item in amounts:
        total += item.amount
    return total


def _share(amount: Decimal, total: Decimal) -> float:
    if total == 0:
        return 0.0
    return round(float(amount / total * 100), SHARE_PRECISION)
