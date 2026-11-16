"""Місячні бюджети на категорії (адендум ADD-01, REQ-A-001..REQ-A-009)."""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from decimal import Decimal

from ..db import Database
from ..errors import BudgetAlreadySet, BudgetNotFound, ErrorDetail
from ..logging_setup import log_event
from ..models import Budget
from ..periods import month_bounds
from ..repositories.budgets import BudgetRepository
from ..repositories.summaries import SummaryRepository
from ..timeutils import now
from ..validation import validate_budget_limit
from . import aggregation
from .guards import require_category, require_profile

#: Нуль у грошовому поданні. Виділений у сталу, щоб залишок і сума
#: перевищення ніколи не поверталися як -0,00 або як ціле 0.
ZERO = Decimal("0.00")


@dataclass(frozen=True)
class BudgetState:
    """Бюджет разом із показниками за конкретний місяць (REQ-A-004, REQ-A-005).

    Залишок і перевищення не зберігаються в базі, а обчислюються при
    кожному читанні. Інакше після редагування або видалення покупки вони
    розійшлися б із фактичними витратами (REQ-F-009).

    Attributes:
        budget: Сам бюджет із місячним лімітом.
        category_name: Назва категорії; потрібна у відповіді API.
        spent: Фактичні витрати за цією категорією за обраний місяць.
    """

    budget: Budget
    category_name: str
    spent: Decimal

    @property
    def remaining(self) -> Decimal:
        """Залишок бюджету (REQ-A-004).

        Returns:
            Ліміт мінус витрати, але не менше нуля: від'ємний залишок
            показував би ту саму інформацію, що й сума перевищення, тільки
            зі зворотним знаком.
        """
        return max(self.budget.monthly_limit - self.spent, ZERO)

    @property
    def exceeded(self) -> bool:
        """Чи перевищено бюджет (REQ-A-005).

        Returns:
            `True`, якщо витрати **більші** за ліміт. Витрати, що точно
            дорівнюють ліміту, перевищенням не вважаються: вимога говорить
            «перевищують», а не «досягають».
        """
        return self.spent > self.budget.monthly_limit

    @property
    def exceeded_by(self) -> Decimal:
        """Сума перевищення бюджету (REQ-A-005).

        Returns:
            Витрати мінус ліміт, але не менше нуля: 0,00, якщо бюджет не
            перевищено.
        """
        return max(self.spent - self.budget.monthly_limit, ZERO)


class BudgetService:
    """Встановлення, перегляд, зміна та видалення бюджетів."""

    def __init__(self, database: Database) -> None:
        """Прив'язує службу до бази даних.

        Args:
            database: Доступ до бази. Служба відкриває транзакцію на кожну
                операцію й не тримає з'єднання між викликами.
        """
        self._database = database

    def list(self, profile_id: str, month: tuple[int, int] | None = None) -> list[BudgetState]:
        """Бюджети профілю з витратами й залишком за місяць (REQ-A-004).

        Args:
            profile_id: Профіль, бюджети якого потрібні.
            month: Пара «рік, номер місяця». Якщо не задана, береться
                поточний місяць.

        Returns:
            Перелік бюджетів із фактичними витратами, залишком і ознакою
            перевищення. Витрати рахуються лише за вказаний місяць:
            покупка 1 листопада на показники жовтня не впливає.

        Raises:
            ProfileNotFound: Профілю немає.
        """
        year, month_number = month or self._current_month()

        with self._database.transaction() as connection:
            require_profile(connection, profile_id)
            budgets = BudgetRepository(connection).list_for_profile(profile_id)
            spending = self._spending_by_category(connection, profile_id, year, month_number)

        return [
            BudgetState(budget, category_name, spending.get(budget.category_id, ZERO))
            for budget, category_name in budgets
        ]

    def create(self, profile_id: str, category_id: str, limit: object) -> BudgetState:
        """Встановлює місячний бюджет на категорію (REQ-A-001).

        Args:
            profile_id: Профіль, у якому встановлюється бюджет.
            category_id: Категорія, на яку встановлюється бюджет.
            limit: Сума бюджету; приймається рядком.

        Returns:
            Новий бюджет разом із витратами за поточний місяць: одразу
            видно, скільки вже витрачено й скільки лишилося.

        Raises:
            ValidationFailed: Сума не більша за нуль або записана не з
                двома знаками після коми (REQ-A-002).
            ProfileNotFound: Профілю немає.
            CategoryNotFound: Категорії немає або вона чужа.
            BudgetAlreadySet: Категорія вже має бюджет (REQ-A-003).
        """
        monthly_limit = validate_budget_limit(limit)
        year, month_number = self._current_month()

        budget = Budget(
            id=str(uuid.uuid4()),
            profile_id=profile_id,
            category_id=category_id,
            monthly_limit=monthly_limit,
            created_at=now(),
        )

        with self._database.transaction() as connection:
            require_profile(connection, profile_id)
            category = require_category(connection, profile_id, category_id)

            repository = BudgetRepository(connection)
            if repository.find_by_category(profile_id, category_id) is not None:
                # REQ-A-003: категорія має не більш ніж один бюджет.
                raise BudgetAlreadySet(details=[ErrorDetail("categoryId", "budget already exists")])

            repository.add(budget)
            spending = self._spending_by_category(connection, profile_id, year, month_number)

        log_event(
            "budget.created",
            profile=profile_id,
            budget=budget.id,
            category=category_id,
            limit=str(monthly_limit),
        )
        return BudgetState(budget, category.name, spending.get(category_id, ZERO))

    def update(self, profile_id: str, budget_id: str, limit: object) -> BudgetState:
        """Змінює суму бюджету (REQ-A-006).

        Правила перевірки суми ті самі, що й при встановленні
        (REQ-A-002). Залишок і перевищення перераховуються за новою
        сумою одразу, бо ніде не зберігаються.

        Args:
            profile_id: Профіль, якому належить бюджет.
            budget_id: Ідентифікатор бюджету.
            limit: Нова сума; приймається рядком.

        Returns:
            Змінений бюджет із витратами за поточний місяць.

        Raises:
            ValidationFailed: Нова сума не пройшла перевірку.
            ProfileNotFound: Профілю немає.
            BudgetNotFound: Бюджету немає або він чужий (REQ-A-009).
        """
        monthly_limit = validate_budget_limit(limit)
        year, month_number = self._current_month()

        with self._database.transaction() as connection:
            require_profile(connection, profile_id)
            repository = BudgetRepository(connection)
            found = repository.get(profile_id, budget_id)
            if found is None:
                raise BudgetNotFound()

            budget, category_name = found
            repository.set_limit(budget_id, monthly_limit)
            spending = self._spending_by_category(connection, profile_id, year, month_number)

        log_event(
            "budget.updated",
            profile=profile_id,
            budget=budget_id,
            limit_from=str(budget.monthly_limit),
            limit_to=str(monthly_limit),
        )
        updated = Budget(
            id=budget.id,
            profile_id=budget.profile_id,
            category_id=budget.category_id,
            monthly_limit=monthly_limit,
            created_at=budget.created_at,
        )
        return BudgetState(updated, category_name, spending.get(budget.category_id, ZERO))

    def delete(self, profile_id: str, budget_id: str) -> None:
        """Видаляє бюджет (REQ-A-007).

        Покупки категорії не змінюються: бюджет — окрема сутність, і його
        зняття обліку витрат не стосується.

        Args:
            profile_id: Профіль, якому належить бюджет.
            budget_id: Ідентифікатор бюджету.

        Raises:
            ProfileNotFound: Профілю немає.
            BudgetNotFound: Бюджету немає або він чужий (REQ-A-009).
        """
        with self._database.transaction() as connection:
            require_profile(connection, profile_id)
            repository = BudgetRepository(connection)
            if repository.get(profile_id, budget_id) is None:
                raise BudgetNotFound()
            repository.delete(budget_id)

        log_event("budget.deleted", profile=profile_id, budget=budget_id)

    @staticmethod
    def _spending_by_category(
        connection: sqlite3.Connection, profile_id: str, year: int, month: int
    ) -> dict[str, Decimal]:
        """Витрати профілю за місяць, згруповані за категоріями.

        Args:
            connection: З'єднання в межах поточної транзакції.
            profile_id: Профіль, витрати якого рахуються.
            year: Рік.
            month: Номер місяця, 1..12.

        Returns:
            Відображення «ідентифікатор категорії -> сума за місяць».
            Категорії без покупок у результат не потрапляють, тому
            читати з нього треба зі значенням за замовчуванням 0,00.
        """
        first, last = month_bounds(year, month)
        amounts = SummaryRepository(connection).amounts_between(profile_id, first, last)
        return aggregation.by_category(amounts)

    @staticmethod
    def _current_month() -> tuple[int, int]:
        moment = now()
        return moment.year, moment.month
