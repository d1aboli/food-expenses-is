"""Локальна база даних SQLite (REQ-F-034, REQ-NF-013).

Грошові суми та кількості зберігаються як текст, щоб жодне проміжне
перетворення у число з рухомою комою не втратило копійки (REQ-NF-010).

Разом із датою й часом покупки зберігається окреме поле `occurred_date` —
календарна дата в часовому поясі застосунку. Саме за ним будуються межі
календарних періодів (REQ-F-026..029).
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

#: Послідовність міграцій. Номер застосованої міграції зберігається
#: у `PRAGMA user_version`, тому нова міграція додається в кінець списку.
MIGRATIONS: list[str] = [
    # 1 — базова схема за SRS v1.0
    """
    CREATE TABLE profiles (
        id          TEXT PRIMARY KEY,
        name        TEXT NOT NULL UNIQUE,
        created_at  TEXT NOT NULL
    );

    CREATE TABLE categories (
        id          TEXT PRIMARY KEY,
        profile_id  TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
        name        TEXT NOT NULL,
        is_system   INTEGER NOT NULL DEFAULT 0,
        UNIQUE (profile_id, name)
    );

    CREATE TABLE purchases (
        id            TEXT PRIMARY KEY,
        profile_id    TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
        category_id   TEXT NOT NULL REFERENCES categories(id),
        name          TEXT NOT NULL,
        unit_price    TEXT NOT NULL,
        quantity      TEXT NOT NULL,
        amount        TEXT NOT NULL,
        occurred_at   TEXT NOT NULL,
        occurred_date TEXT NOT NULL
    );

    CREATE INDEX idx_purchases_period
        ON purchases (profile_id, occurred_date);
    CREATE INDEX idx_purchases_category
        ON purchases (category_id);
    """,
]


class Database:
    """Доступ до файлу бази даних."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Відкриває з'єднання і підтверджує зміни лише за відсутності помилок.

        Покупка потрапляє до файлу бази в момент підтвердження, тому аварійне
        завершення застосунку не втрачає вже збережені записи (REQ-NF-011).
        """

        connection = self.connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def migrate(self) -> int:
        """Доводить схему до останньої версії та повертає її номер."""

        with self.transaction() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            for number, script in enumerate(MIGRATIONS[version:], start=version + 1):
                connection.executescript(script)
                connection.execute(f"PRAGMA user_version = {number}")
            return len(MIGRATIONS)

    def table_names(self) -> set[str]:
        with self.transaction() as connection:
            rows = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        return {row["name"] for row in rows}
