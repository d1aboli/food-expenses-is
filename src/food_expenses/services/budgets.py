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
from .guards import require_category, require_profile

ZERO = Decimal("0.00")


@dataclass(frozen=True)
class BudgetState:
    """Бюджет разом із показниками за конкретний місяць (REQ-A-004, REQ-A-005)."""

    budget: Budget
    category_name: str
    spent: Decimal

    @property
    def remaining(self) -> Decimal:
        """Залишок бюджету; 0,00, якщо бюджет перевищено."""

        return max(self.budget.monthly_limit - self.spent, ZERO)

    @property
    def exceeded(self) -> bool:
        return self.spent > self.budget.monthly_limit

    @property
    def exceeded_by(self) -> Decimal:
        """Сума перевищення; 0,00, якщо бюджет не перевищено."""

        return max(self.spent - self.budget.monthly_limit, ZERO)


class BudgetService:
    """Встановлення, перегляд, зміна та видалення бюджетів."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def list(self, profile_id: str, month: tuple[int, int] | None = None) -> list[BudgetState]:
        """REQ-A-004, REQ-A-005: бюджети з витратами й залишком за місяць."""

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
        """REQ-A-001, REQ-A-002, REQ-A-003: встановлює бюджет на категорію."""

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
                raise BudgetAlreadySet(
                    details=[ErrorDetail("categoryId", "budget already exists")]
                )

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
        """REQ-A-006: змінює суму бюджету; правила REQ-A-002 діють і тут."""

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
        """REQ-A-007: видаляє бюджет; покупки категорії не змінюються."""

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
        """Витрати профілю за місяць, згруповані за категоріями."""

        first, last = month_bounds(year, month)
        totals: dict[str, Decimal] = {}
        for item in SummaryRepository(connection).amounts_between(profile_id, first, last):
            totals[item.category_id] = totals.get(item.category_id, ZERO) + item.amount
        return totals

    @staticmethod
    def _current_month() -> tuple[int, int]:
        moment = now()
        return moment.year, moment.month
