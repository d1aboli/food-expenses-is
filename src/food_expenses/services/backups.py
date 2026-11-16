"""Резервна копія бази даних (REQ-F-036)."""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ..db import Database
from ..errors import BackupFailed
from ..logging_setup import log_event
from ..timeutils import now


@dataclass(frozen=True)
class Backup:
    """Створена копія файлу бази."""

    id: str
    file_name: str
    size_bytes: int
    created_at: datetime


class BackupService:
    """Створення копії бази засобами самої SQLite."""

    def __init__(self, database: Database, backup_dir: Path) -> None:
        """Прив'язує службу до бази та каталогу копій.

        Args:
            database: Доступ до бази, яку копіюємо.
            backup_dir: Каталог, куди складаються копії. Задається
                налаштуваннями, а не виводиться зі шляху до бази: копії
                можуть лежати на іншому носії.
        """
        self._database = database
        self._backup_dir = Path(backup_dir)

    def create(self) -> Backup:
        """Створює придатну для відновлення копію файлу бази (REQ-F-036).

        Копія робиться вбудованим механізмом SQLite, а не копіюванням
        файла: копіювання під час незавершеної транзакції дало б файл
        потрібного розміру, який неможливо прочитати.

        Ім'я копії містить час до секунди; якщо такий файл уже є, до імені
        додається порядковий номер. Дві копії поспіль не затирають одна
        одну навіть у межах однієї секунди.

        Returns:
            Опис створеної копії: ім'я файла, розмір і час створення.

        Raises:
            BackupFailed: Не вдалося прочитати базу або записати копію —
            немає прав, бракує місця.
        """
        self._backup_dir.mkdir(parents=True, exist_ok=True)
        moment = now()
        target = self._unique_path(moment)

        try:
            source = self._database.connect()
            try:
                destination = sqlite3.connect(target)
                try:
                    source.backup(destination)
                finally:
                    destination.close()
            finally:
                source.close()
        except sqlite3.Error as error:
            log_event("backup.failed", message=str(error))
            raise BackupFailed() from error

        backup = Backup(
            id=str(uuid.uuid4()),
            file_name=target.name,
            size_bytes=target.stat().st_size,
            created_at=moment,
        )
        log_event("backup.created", file=backup.file_name, bytes=backup.size_bytes)
        return backup

    def _unique_path(self, moment: datetime) -> Path:
        """Нова копія не перезаписує попередню."""
        stamp = moment.strftime("%Y-%m-%dT%H-%M-%S")
        candidate = self._backup_dir / f"backup-{stamp}.db"
        attempt = 2
        while candidate.exists():
            candidate = self._backup_dir / f"backup-{stamp}-{attempt}.db"
            attempt += 1
        return candidate
