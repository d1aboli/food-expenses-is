"""Доступ до таблиці профілів."""

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
    """Читання й запис профілів."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add(self, profile: Profile) -> None:
        self._connection.execute(
            "INSERT INTO profiles (id, name, created_at) VALUES (?, ?, ?)",
            (profile.id, profile.name, profile.created_at.isoformat(timespec="seconds")),
        )

    def list_all(self) -> list[Profile]:
        """Профілі в порядку створення."""

        rows = self._connection.execute(
            "SELECT id, name, created_at FROM profiles ORDER BY created_at, rowid"
        ).fetchall()
        return [_to_profile(row) for row in rows]

    def get(self, profile_id: str) -> Profile | None:
        row = self._connection.execute(
            "SELECT id, name, created_at FROM profiles WHERE id = ?",
            (profile_id,),
        ).fetchone()
        return _to_profile(row) if row else None

    def find_by_name(self, name: str) -> Profile | None:
        row = self._connection.execute(
            "SELECT id, name, created_at FROM profiles WHERE name = ?",
            (name,),
        ).fetchone()
        return _to_profile(row) if row else None

    def exists(self, profile_id: str) -> bool:
        row = self._connection.execute(
            "SELECT 1 FROM profiles WHERE id = ?", (profile_id,)
        ).fetchone()
        return row is not None
