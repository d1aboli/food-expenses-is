"""Доступ до таблиці категорій."""

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
    """Читання й запис категорій у межах профілю."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add(self, category: Category) -> None:
        self._connection.execute(
            "INSERT INTO categories (id, profile_id, name, is_system) VALUES (?, ?, ?, ?)",
            (category.id, category.profile_id, category.name, int(category.is_system)),
        )

    def list_for_profile(self, profile_id: str) -> list[tuple[Category, int]]:
        """Категорії профілю в порядку створення разом з кількістю покупок."""

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
        self._connection.execute(
            "UPDATE categories SET name = ? WHERE id = ?", (name, category_id)
        )

    def delete(self, category_id: str) -> None:
        self._connection.execute("DELETE FROM categories WHERE id = ?", (category_id,))

    def purchase_count(self, category_id: str) -> int:
        row = self._connection.execute(
            "SELECT COUNT(*) AS total FROM purchases WHERE category_id = ?",
            (category_id,),
        ).fetchone()
        return int(row["total"])
