"""Доступ до таблиці категорій (REQ-F-020..REQ-F-025)."""

from __future__ import annotations

import sqlite3

from ..models import Category


def _to_category(row: sqlite3.Row) -> Category:
    return Category(
        id=row["id"],
        profile_id=row["profile_id"],
        name=row["name"],
        is_system=bool(row["is_system"]),
    )


class CategoryRepository:
    """Читання й запис категорій у межах профілю.

    Кожен запит обмежений профілем: категорія іншого профілю не
    знаходиться й не змінюється (REQ-F-003).
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        """Прив'язує репозиторій до з'єднання з базою.

        Args:
            connection: Відкрите з'єднання; транзакціями керує той, хто
                викликає.
        """
        self._connection = connection

    def add(self, category: Category) -> None:
        """Записує нову категорію.

        Args:
            category: Категорія з ознакою `is_system`. Службовою
                позначається лише «Інше» при створенні профілю
                (REQ-F-020, REQ-F-025).
        """
        self._connection.execute(
            "INSERT INTO categories (id, profile_id, name, is_system) VALUES (?, ?, ?, ?)",
            (category.id, category.profile_id, category.name, int(category.is_system)),
        )

    def list_for_profile(self, profile_id: str) -> list[tuple[Category, int]]:
        """Категорії профілю разом із кількістю покупок у кожній.

        Кількість рахується підзапитом в одному зверненні до бази, а не
        окремим запитом на категорію: вона потрібна і в переліку
        категорій, і в попередженні перед видаленням (REQ-F-023).

        Args:
            profile_id: Профіль, категорії якого читаються.

        Returns:
            Пари «категорія, кількість покупок» у порядку створення.
            Базові категорії йдуть першими, бо створюються з профілем.
        """
        rows = self._connection.execute(
            """
            SELECT c.id, c.profile_id, c.name, c.is_system,
                   (SELECT COUNT(*) FROM purchases p WHERE p.category_id = c.id)
                       AS purchase_count
            FROM categories c
            WHERE c.profile_id = ?
            ORDER BY c.rowid
            """,
            (profile_id,),
        ).fetchall()
        return [(_to_category(row), row["purchase_count"]) for row in rows]

    def get(self, profile_id: str, category_id: str) -> Category | None:
        """Шукає категорію профілю за ідентифікатором.

        Args:
            profile_id: Профіль, у межах якого шукається категорія.
            category_id: Ідентифікатор категорії.

        Returns:
            Категорія або `None`, зокрема коли категорія існує, але
            належить іншому профілю (REQ-F-003).
        """
        row = self._connection.execute(
            """
            SELECT id, profile_id, name, is_system
            FROM categories
            WHERE id = ? AND profile_id = ?
            """,
            (category_id, profile_id),
        ).fetchone()
        return _to_category(row) if row else None

    def find_by_name(self, profile_id: str, name: str) -> Category | None:
        """Шукає категорію профілю за назвою (REQ-F-021).

        Args:
            profile_id: Профіль, у межах якого шукається категорія.
            name: Назва; порівняння точне.

        Returns:
            Категорія або `None`. Використовується для перевірки
            унікальності назви в межах профілю — глобальної унікальності
            вимога не ставить.
        """
        row = self._connection.execute(
            """
            SELECT id, profile_id, name, is_system
            FROM categories
            WHERE profile_id = ? AND name = ?
            """,
            (profile_id, name),
        ).fetchone()
        return _to_category(row) if row else None

    def find_system(self, profile_id: str) -> Category | None:
        """Знаходить службову категорію профілю (REQ-F-025).

        Args:
            profile_id: Профіль, службова категорія якого потрібна.

        Returns:
            Категорія «Інше» або `None`. Пошук іде за ознакою
            `is_system`, а не за назвою: назва «Інше» могла б збігтися з
            власною категорією користувача в іншому профілі.
        """
        row = self._connection.execute(
            """
            SELECT id, profile_id, name, is_system
            FROM categories
            WHERE profile_id = ? AND is_system = 1
            """,
            (profile_id,),
        ).fetchone()
        return _to_category(row) if row else None

    def rename(self, category_id: str, name: str) -> None:
        """Змінює назву категорії (REQ-F-022).

        Зв'язок покупок із категорією від перейменування не змінюється:
        покупка посилається на ідентифікатор, а не на назву.

        Args:
            category_id: Ідентифікатор категорії.
            name: Нова назва, уже перевірена службою.
        """
        self._connection.execute("UPDATE categories SET name = ? WHERE id = ?", (name, category_id))

    def delete(self, category_id: str) -> None:
        """Видаляє категорію.

        Покупки до службової категорії цей метод не переносить. Порядок
        «спершу перенести, потім видалити» задано REQ-F-024 і виконується
        службою `CategoryService`.

        Args:
            category_id: Ідентифікатор категорії.
        """
        self._connection.execute("DELETE FROM categories WHERE id = ?", (category_id,))

    def purchase_count(self, category_id: str) -> int:
        """Скільки покупок прив'язано до категорії (REQ-F-023).

        Args:
            category_id: Ідентифікатор категорії.

        Returns:
            Кількість покупок; 0 для порожньої категорії.
        """
        row = self._connection.execute(
            "SELECT COUNT(*) AS total FROM purchases WHERE category_id = ?",
            (category_id,),
        ).fetchone()
        return int(row["total"])
