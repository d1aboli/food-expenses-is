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
)
from ..logging_setup import log_event
from ..models import Category
from ..repositories.budgets import BudgetRepository
from ..repositories.categories import CategoryRepository
from ..repositories.purchases import PurchaseRepository
from ..text import CATEGORY_NAME, clean_name
from .guards import require_category, require_profile

#: Службова категорія, до якої переносяться покупки з видалених (REQ-F-025).
SYSTEM_CATEGORY_NAME = "Інше"

#: Категорії, які створюються разом із профілем (REQ-F-020).
BASE_CATEGORY_NAMES = ["Продукти", "Ресторан", "Доставка", "Напої", SYSTEM_CATEGORY_NAME]


def create_base_categories(connection: sqlite3.Connection, profile_id: str) -> None:
    """Створює базові категорії нового профілю (REQ-F-020).

    Викликається службою профілів у тій самій транзакції, що й створення
    профілю: профіль без категорій не має сенсу, бо до нього не можна
    додати жодної покупки.

    Остання з категорій — «Інше» — позначається службовою: саме до неї
    переносяться покупки з видалених категорій (REQ-F-025).

    Args:
        connection: З'єднання в межах транзакції створення профілю.
        profile_id: Профіль, для якого створюються категорії.
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
        """Прив'язує службу до бази даних.

        Args:
            database: Доступ до бази. Служба відкриває транзакцію на кожну
                операцію й не тримає з'єднання між викликами.
        """
        self._database = database

    def list(self, profile_id: str) -> list[tuple[Category, int]]:
        """Категорії профілю разом із кількістю покупок (REQ-F-020).

        Args:
            profile_id: Профіль, категорії якого потрібні.

        Returns:
            Пари «категорія, кількість покупок» у порядку створення.

        Raises:
            ProfileNotFound: Профілю немає (REQ-F-003).
        """
        with self._database.transaction() as connection:
            require_profile(connection, profile_id)
            return CategoryRepository(connection).list_for_profile(profile_id)

    def create(self, profile_id: str, name: str) -> tuple[Category, int]:
        """Створює власну категорію (REQ-F-021).

        Args:
            profile_id: Профіль, у якому створюється категорія.
            name: Назва, унікальна в межах цього профілю.

        Returns:
            Пару «категорія, кількість покупок». Кількість завжди 0: нова
            категорія порожня. Пара повертається, щоб відповідь складалася
            тим самим кодом, що й для переліку.

        Raises:
            ValidationFailed: Назва порожня або довша за 40 символів.
            ProfileNotFound: Профілю немає.
            CategoryNameTaken: Така назва вже є в цьому профілі.
        """
        cleaned = clean_name(name, CATEGORY_NAME)
        category = Category(
            id=str(uuid.uuid4()),
            profile_id=profile_id,
            name=cleaned,
            is_system=False,
        )

        with self._database.transaction() as connection:
            require_profile(connection, profile_id)
            repository = CategoryRepository(connection)
            self._require_name_is_free(repository, profile_id, cleaned)
            repository.add(category)

        log_event("category.created", profile=profile_id, category=category.id, name=cleaned)
        return category, 0

    def rename(self, profile_id: str, category_id: str, name: str) -> tuple[Category, int]:
        """Перейменовує категорію (REQ-F-022).

        Покупки зберігають зв'язок із категорією: вони посилаються на
        ідентифікатор, а не на назву.

        Args:
            profile_id: Профіль, якому належить категорія.
            category_id: Категорія, яку перейменовують.
            name: Нова назва.

        Returns:
            Пару «категорія з новою назвою, кількість покупок у ній».

        Raises:
            ValidationFailed: Назва порожня або довша за 40 символів.
            ProfileNotFound: Профілю немає.
            CategoryNotFound: Категорії немає або вона належить іншому профілю.
            CategoryIsSystem: Це службова категорія «Інше» (REQ-F-025).
            CategoryNameTaken: Така назва вже є в цьому профілі. Власна
                поточна назва категорії при перевірці не враховується, тому
                перейменування «в саму себе» помилки не дає.
        """
        cleaned = clean_name(name, CATEGORY_NAME)

        with self._database.transaction() as connection:
            require_profile(connection, profile_id)
            repository = CategoryRepository(connection)
            category = require_category(connection, profile_id, category_id)

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
        """Видаляє категорію (REQ-F-023, REQ-F-024).

        Порядок дій для непорожньої категорії з підтвердженням заданий
        вимогою і саме в такому порядку й виконується: спершу покупки
        переходять до службової категорії, і лише потім категорія
        зникає. Зворотний порядок лишив би покупки без категорії.

        Разом із категорією видаляється і її бюджет (ADD-01, REQ-A-008).

        Усе це відбувається в одній транзакції: якщо видалення не
        вдасться, покупки не лишаться перенесеними наполовину.

        Args:
            profile_id: Профіль, якому належить категорія.
            category_id: Категорія, яку видаляють.
            confirm: Підтвердження переносу покупок. Без нього непорожня
                категорія не видаляється.

        Raises:
            ProfileNotFound: Профілю немає.
            CategoryNotFound: Категорії немає, вона належить іншому
                профілю, або в профілі бракує службової категорії.
            CategoryIsSystem: Це службова категорія «Інше» — її не можна
                видалити за жодних умов (REQ-F-025).
            CategoryNotEmpty: Категорія містить покупки, а підтвердження
                немає. У `details` повертається їхня кількість, щоб
                інтерфейс міг показати попередження (REQ-F-023).
        """
        with self._database.transaction() as connection:
            require_profile(connection, profile_id)
            repository = CategoryRepository(connection)
            category = require_category(connection, profile_id, category_id)

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

            # REQ-A-008 (адендум ADD-01): разом із категорією зникає і її бюджет.
            removed_budgets = BudgetRepository(connection).delete_for_category(category_id)
            repository.delete(category_id)

        if removed_budgets:
            log_event("budget.deleted_with_category", profile=profile_id, category=category_id)
        log_event("category.deleted", profile=profile_id, category=category_id, confirm=confirm)

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
