"""Підсумки, розбивка за категоріями та дані графіків (REQ-F-026..REQ-F-033)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from ..db import Database
from ..periods import Period, days_of, month_bounds, resolve
from ..repositories.summaries import PurchaseAmount, SummaryRepository
from . import aggregation
from .guards import require_profile

ZERO = Decimal("0.00")
#: Частка у відсотках заокруглюється до сотих: сума часток тоді відрізняється
#: від 100% не більш ніж на 0,03%, що вкладається в критерій REQ-F-030 (0,1%).
SHARE_PRECISION = 2


@dataclass(frozen=True)
class PeriodSummary:
    """Підсумок за період (REQ-F-026..REQ-F-029).

    Attributes:
        period: Період із заповненими межами.
        amount: Сума вартостей усіх покупок періоду.
        purchase_count: Скільки покупок потрапило в період.
    """

    period: Period
    amount: Decimal
    purchase_count: int


@dataclass(frozen=True)
class CategoryShare:
    """Рядок таблиці «категорія — сума — частка» (REQ-F-030).

    Attributes:
        category_id: Ідентифікатор категорії.
        category_name: Назва категорії.
        amount: Сума витрат за категорією в межах періоду.
        share: Частка у відсотках від підсумку, з двома знаками після
            коми. Саме тут, і лише тут, значення переходить у число з
            рухомою комою: частка — показник для ока, а не для обліку.
    """

    category_id: str
    category_name: str
    amount: Decimal
    share: float


@dataclass(frozen=True)
class ChartPoint:
    """Один стовпчик графіка (REQ-F-031, REQ-F-032).

    Attributes:
        label: Мітка стовпчика: `2026-10-05` для днів, `2026-10` для
            місяців.
        amount: Сума за цей день або місяць; може бути 0,00.
    """

    label: str
    amount: Decimal


class SummaryService:
    """Обчислення підсумків над покупками активного профілю."""

    def __init__(self, database: Database) -> None:
        """Прив'язує службу до бази даних.

        Args:
            database: Доступ до бази. Служба відкриває транзакцію на кожну
                операцію й не тримає з'єднання між викликами.
        """
        self._database = database

    def total(
        self,
        profile_id: str,
        kind: str | None,
        day: date | None = None,
        start: date | None = None,
        end: date | None = None,
    ) -> PeriodSummary:
        """Підсумок витрат за період (REQ-F-026..REQ-F-029).

        Args:
            profile_id: Профіль, витрати якого рахуються.
            kind: Вид періоду: `day`, `week`, `month` або `range`.
            day: Будь-яка дата всередині періоду — для `day`, `week`,
                `month`.
            start: Початок діапазону — для `range`.
            end: Кінець діапазону — для `range`.

        Returns:
            Підсумок із межами періоду, сумою та кількістю покупок. За
            період без покупок сума дорівнює 0,00, а не `None`
            (REQ-F-033).

        Raises:
            ProfileNotFound: Профілю немає.
            InvalidPeriod: Межі періоду задано некоректно.
        """
        period = resolve(kind, day=day, start=start, end=end)
        amounts = self._amounts(profile_id, period)
        return PeriodSummary(period, aggregation.total_of(amounts), len(amounts))

    def breakdown(
        self,
        profile_id: str,
        kind: str | None,
        day: date | None = None,
        start: date | None = None,
        end: date | None = None,
    ) -> tuple[Period, Decimal, list[CategoryShare]]:
        """Розбивка витрат за категоріями (REQ-F-030).

        Args:
            profile_id: Профіль, витрати якого рахуються.
            kind: Вид періоду.
            day: Будь-яка дата всередині періоду.
            start: Початок діапазону — для `range`.
            end: Кінець діапазону — для `range`.

        Returns:
            Трійку «період, загальна сума, рядки розбивки». Рядки
            впорядковані від більшої суми до меншої: найбільшу витрату в
            такій таблиці шукають найчастіше. За однакових сум вирішує
            назва категорії, тому порядок стабільний.

        Raises:
            ProfileNotFound: Профілю немає.
            InvalidPeriod: Межі періоду задано некоректно.
        """
        period = resolve(kind, day=day, start=start, end=end)
        amounts = self._amounts(profile_id, period)
        total = aggregation.total_of(amounts)
        names = aggregation.category_names(amounts)

        items = [
            CategoryShare(
                category_id=category_id,
                category_name=names[category_id],
                amount=amount,
                share=_share(amount, total),
            )
            for category_id, amount in aggregation.by_category(amounts).items()
        ]
        # Найбільша витрата — зверху: саме її шукають у таблиці найчастіше.
        items.sort(key=lambda item: (-item.amount, item.category_name))
        return period, total, items

    def daily_chart(self, profile_id: str, year: int, month: int) -> list[ChartPoint]:
        """Дані графіка витрат за днями місяця (REQ-F-031).

        Args:
            profile_id: Профіль, витрати якого рахуються.
            year: Рік.
            month: Номер місяця, 1..12.

        Returns:
            Точку на кожен день місяця — 28, 29, 30 або 31, залежно від
            місяця. Дні без покупок лишаються в ряду зі значенням 0,00.

        Raises:
            ProfileNotFound: Профілю немає.

        Note:
            Порожній місяць дає не порожній перелік, а 28–31 точку з
            нулем. Так узгоджено REQ-F-031, який вимагає стовпчик на
            кожен день, із REQ-F-033, який вимагає порожнього графіка:
            «порожній» тут означає «жоден стовпчик не піднімається над
            нулем», а не «стовпчиків немає». Інакше графік за порожній
            місяць стискався б до нічого, а за місяць із двома покупками
            показував би два стовпчики поряд, ніби витрати були щодня.
        """
        first, last = month_bounds(year, month)
        period = Period("month", first, last)
        totals = self._totals_by_day(profile_id, period)
        return [
            ChartPoint(label=day.isoformat(), amount=totals.get(day, ZERO))
            for day in days_of(period)
        ]

    def monthly_chart(self, profile_id: str, year: int) -> list[ChartPoint]:
        """Дані графіка витрат за місяцями року (REQ-F-032).

        Args:
            profile_id: Профіль, витрати якого рахуються.
            year: Рік.

        Returns:
            Дванадцять точок незалежно від того, у яких місяцях були
            покупки — з тієї самої причини, що й у графіку за днями.

        Raises:
            ProfileNotFound: Профілю немає.
        """
        period = Period("month", date(year, 1, 1), date(year, 12, 31))
        totals: dict[str, Decimal] = {}
        for day, amount in aggregation.by_day(self._amounts(profile_id, period)).items():
            label = f"{day.year:04d}-{day.month:02d}"
            totals[label] = totals.get(label, ZERO) + amount

        labels = [f"{year:04d}-{month:02d}" for month in range(1, 13)]
        return [ChartPoint(label=label, amount=totals.get(label, ZERO)) for label in labels]

    def _amounts(self, profile_id: str, period: Period) -> list[PurchaseAmount]:
        with self._database.transaction() as connection:
            require_profile(connection, profile_id)
            return SummaryRepository(connection).amounts_between(
                profile_id, period.start, period.end
            )

    def _totals_by_day(self, profile_id: str, period: Period) -> dict[date, Decimal]:
        return aggregation.by_day(self._amounts(profile_id, period))


def _share(amount: Decimal, total: Decimal) -> float:
    if total == 0:
        return 0.0
    return round(float(amount / total * 100), SHARE_PRECISION)
