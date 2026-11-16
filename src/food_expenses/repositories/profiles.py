"""Доступ до таблиці профілів (REQ-F-001, REQ-F-002, REQ-F-034)."""

from __future__ import annotations

import sqlite3
from datetime import datetime

from ..models import Profile


def _to_profile(row: sqlite3.Row) -> Profile:
    return Profile(
        id=row["id"],
        name=row["name"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


class ProfileRepository:
    """Читання й запис профілів.

    Репозиторій не перевіряє правил предметної області: унікальність назви,
    права доступу й порядок операцій — відповідальність служби
    `ProfileService`. Тут лише SQL.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        """Прив'язує репозиторій до з'єднання з базою.

        Args:
            connection: Відкрите з'єднання. Транзакціями керує той, хто
                викликає репозиторій, а не сам репозиторій.
        """
        self._connection = connection

    def add(self, profile: Profile) -> None:
        """Записує новий профіль.

        Args:
            profile: Профіль із уже заповненими ідентифікатором і часом
                створення.

        Raises:
            sqlite3.IntegrityError: Профіль із таким ідентифікатором або
                назвою вже є. Назву слід перевіряти заздалегідь через
                `find_by_name`, щоб користувач отримав помилку
                `PROFILE_NAME_TAKEN`, а не помилку бази.
        """
        self._connection.execute(
            "INSERT INTO profiles (id, name, created_at) VALUES (?, ?, ?)",
            (profile.id, profile.name, profile.created_at.isoformat(timespec="seconds")),
        )

    def list_all(self) -> list[Profile]:
        """Усі профілі системи (REQ-F-002).

        Returns:
            Профілі в порядку створення, від найстарішого. Порядок
            стабільний: за однакового часу створення вирішує `rowid`.
        """
        rows = self._connection.execute(
            "SELECT id, name, created_at FROM profiles ORDER BY created_at, rowid"
        ).fetchall()
        return [_to_profile(row) for row in rows]

    def get(self, profile_id: str) -> Profile | None:
        """Шукає профіль за ідентифікатором.

        Args:
            profile_id: Ідентифікатор профілю.

        Returns:
            Профіль або `None`, якщо такого немає. Перетворення `None` на
            помилку `PROFILE_NOT_FOUND` — справа служби, не репозиторію.
        """
        row = self._connection.execute(
            "SELECT id, name, created_at FROM profiles WHERE id = ?",
            (profile_id,),
        ).fetchone()
        return _to_profile(row) if row else None

    def find_by_name(self, name: str) -> Profile | None:
        """Шукає профіль за назвою (REQ-F-001).

        Args:
            name: Назва профілю; порівняння точне, без зведення регістру.

        Returns:
            Профіль або `None`. Використовується для перевірки
            унікальності назви перед створенням.
        """
        row = self._connection.execute(
            "SELECT id, name, created_at FROM profiles WHERE name = ?",
            (name,),
        ).fetchone()
        return _to_profile(row) if row else None

    def exists(self, profile_id: str) -> bool:
        """Перевіряє існування профілю, не читаючи його даних (REQ-F-003).

        Args:
            profile_id: Ідентифікатор профілю.

        Returns:
            `True`, якщо профіль є. Дешевше за `get`, коли потрібен лише
            факт існування — так працює `require_profile`.
        """
        row = self._connection.execute(
            "SELECT 1 FROM profiles WHERE id = ?", (profile_id,)
        ).fetchone()
        return row is not None
