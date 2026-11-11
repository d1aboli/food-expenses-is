"""Правила роботи з категоріями (REQ-F-020..REQ-F-025)."""

from __future__ import annotations

import sqlite3
import uuid

from ..db import Database
from ..errors import (
    CategoryIsSystem,
    CategoryNameTaken,
    CategoryNotEmpty,
    CategoryNotFound,
    ErrorDetail,
    ProfileNotFound,
    ValidationFailed,
)
from ..logging_setup import log_event
from ..models import Category
from ..repositories.categories import CategoryRepository
from ..repositories.profiles import ProfileRepository
from ..repositories.purchases import PurchaseRepository

MAX_NAME_LENGTH = 40

#: Службова категорія, до якої переносяться покупки з видалених (REQ-F-025).
SYSTEM_CATEGORY_NAME = "Інше"

#: Категорії, які створюються разом із профілем (REQ-F-020).
BASE_CATEGORY_NAMES = ["Продукти", "Ресторан", "Доставка", "Напої", SYSTEM_CATEGORY_NAME]


def create_base_categories(connection: sqlite3.Connection, profile_id: str) -> None:
    """REQ-F-020: створює базові категорії нового профілю.

    Викликається службою профілів у тій самій транзакції, що й створення
    профілю: профіль без категорій не має сенсу, бо до нього не можна додати
    жодної покупки.
    """

    repository = CategoryRepository(connection)
    for name in BASE_CATEGORY_NAMES:
        repository.add(
            Category(
                id=str(uuid.uuid4()),
                profile_id=profile_id,
                name=name,
                is_system=name == SYSTEM_CATEGORY_NAME,
            )
        )


class CategoryService:
    """Перелік, створення, перейменування та видалення категорій."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def list(self, profile_id: str) -> list[tuple[Category, int]]:
        """REQ-F-003: категорії лише вказаного профілю."""

        with self._database.transaction() as connection:
            self._require_profile(connection, profile_id)
            return CategoryRepository(connection).list_for_profile(profile_id)

    def create(self, profile_id: str, name: str) -> tuple[Category, int]:
        """REQ-F-021: власна категорія з унікальною в межах профілю назвою."""

        cleaned = self._clean_name(name)
        category = Category(
            id=str(uuid.uuid4()),
            profile_id=profile_id,
            name=cleaned,
            is_system=False,
        )

        with self._database.transaction() as connection:
            self._require_profile(connection, profile_id)
            repository = CategoryRepository(connection)
            self._require_name_is_free(repository, profile_id, cleaned)
            repository.add(category)

        log_event("category.created", profile=profile_id, category=category.id, name=cleaned)
        return category, 0

    def rename(self, profile_id: str, category_id: str, name: str) -> tuple[Category, int]:
        """REQ-F-022: перейменування; покупки зберігають зв'язок із категорією."""

        cleaned = self._clean_name(name)

        with self._database.transaction() as connection:
            self._require_profile(connection, profile_id)
            repository = CategoryRepository(connection)
            category = self._require_category(repository, profile_id, category_id)

            if category.is_system:
                # REQ-F-025: назва «Інше» закріплена за службовою категорією.
                raise CategoryIsSystem()

            self._require_name_is_free(repository, profile_id, cleaned, exclude=category_id)
            repository.rename(category_id, cleaned)
            purchase_count = repository.purchase_count(category_id)

        log_event(
            "category.renamed",
            profile=profile_id,
            category=category_id,
            name_from=category.name,
            name_to=cleaned,
        )
        renamed = Category(
            id=category.id,
            profile_id=category.profile_id,
            name=cleaned,
            is_system=category.is_system,
        )
        return renamed, purchase_count

    def delete(self, profile_id: str, category_id: str, confirm: bool = False) -> None:
        """REQ-F-023, REQ-F-025: видалення категорії.

        Службову категорію видалити не можна за жодних умов. Непорожня
        категорія не видаляється: у відповіді повертається кількість
        пов'язаних покупок.
        """

        with self._database.transaction() as connection:
            self._require_profile(connection, profile_id)
            repository = CategoryRepository(connection)
            category = self._require_category(repository, profile_id, category_id)

            if category.is_system:
                raise CategoryIsSystem()

            purchase_count = repository.purchase_count(category_id)
            if purchase_count > 0 and not confirm:
                # REQ-F-023: без підтвердження непорожня категорія не видаляється.
                raise CategoryNotEmpty(
                    f"Категорія містить {purchase_count} покупки. "
                    f"Підтвердіть перенесення до категорії «{SYSTEM_CATEGORY_NAME}».",
                    details=[ErrorDetail("purchaseCount", str(purchase_count))],
                )

            if purchase_count > 0:
                # REQ-F-024: спочатку покупки переходять до «Інше», і лише
                # потім категорія видаляється. Порядок саме такий: інакше
                # видалення категорії лишило б покупки без неї.
                system_category = repository.find_system(profile_id)
                if system_category is None:
                    raise CategoryNotFound(
                        f"У профілі немає службової категорії «{SYSTEM_CATEGORY_NAME}».",
                    )
                moved = PurchaseRepository(connection).move_to_category(
                    category_id, system_category.id
                )
                log_event(
                    "category.purchases_moved",
                    profile=profile_id,
                    category_from=category_id,
                    category_to=system_category.id,
                    moved=moved,
                )

            repository.delete(category_id)

        log_event("category.deleted", profile=profile_id, category=category_id, confirm=confirm)

    @staticmethod
    def _require_profile(connection: sqlite3.Connection, profile_id: str) -> None:
        if not ProfileRepository(connection).exists(profile_id):
            raise ProfileNotFound()

    @staticmethod
    def _require_category(
        repository: CategoryRepository, profile_id: str, category_id: str
    ) -> Category:
        category = repository.get(profile_id, category_id)
        if category is None:
            # REQ-F-003: чужа категорія для цього профілю просто не існує.
            raise CategoryNotFound()
        return category

    @staticmethod
    def _require_name_is_free(
        repository: CategoryRepository,
        profile_id: str,
        name: str,
        exclude: str | None = None,
    ) -> None:
        existing = repository.find_by_name(profile_id, name)
        if existing is not None and existing.id != exclude:
            raise CategoryNameTaken(details=[ErrorDetail("name", "must be unique within profile")])

    @staticmethod
    def _clean_name(name: str) -> str:
        """REQ-F-021: назва категорії непорожня і не довша за 40 символів."""

        cleaned = (name or "").strip()
        if not cleaned:
            raise ValidationFailed(
                "Назва категорії не може бути порожньою.",
                requirement="REQ-F-021",
                details=[ErrorDetail("name", "must not be blank")],
            )
        if len(cleaned) > MAX_NAME_LENGTH:
            raise ValidationFailed(
                f"Назва категорії довша за {MAX_NAME_LENGTH} символів.",
                requirement="REQ-F-021",
                details=[ErrorDetail("name", f"max length is {MAX_NAME_LENGTH}")],
            )
        return cleaned
