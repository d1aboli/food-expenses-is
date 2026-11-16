"""Налаштування застосунку.

Шляхи до бази даних, журналів і резервних копій визначаються тут, щоб тести
могли працювати з тимчасовим каталогом і не чіпати робочі дані (REQ-F-034).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

#: Корінь репозиторію: src/food_expenses/config.py -> ../../..
PROJECT_ROOT = Path(__file__).resolve().parents[2]

#: Часовий пояс, у якому визначаються календарні межі періодів (REQ-F-026..029).
APP_TIMEZONE = ZoneInfo("Europe/Kyiv")

#: Єдина валюта системи (обмеження зі spec/idea.md).
CURRENCY = "UAH"

#: Префікс усіх операцій REST API згідно з spec/api/openapi.yaml.
API_PREFIX = "/api/v1"


@dataclass(frozen=True)
class Settings:
    """Шляхи, від яких залежить робота застосунку."""

    database_path: Path
    log_dir: Path
    backup_dir: Path

    def ensure_directories(self) -> None:
        """Створює каталоги бази, журналів і резервних копій, якщо їх немає.

        Викликається при старті застосунку до налаштування журналювання:
        обробник запису у файл не створює каталог сам і впав би при
        першому ж записі.
        """
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)


def load_settings(root: Path | None = None) -> Settings:
    """Збирає налаштування зі змінних середовища або з типових шляхів.

    Змінні середовища: `FOOD_EXPENSES_DB`, `FOOD_EXPENSES_LOG_DIR`,
    `FOOD_EXPENSES_BACKUP_DIR`. Кожна з них незалежна: можна змінити лише
    каталог копій, не чіпаючи решти.

    Args:
        root: Корінь, відносно якого будуються типові шляхи. Якщо не
            заданий, береться корінь репозиторію.

    Returns:
        Налаштування з готовими шляхами; каталоги при цьому ще не
        створюються — це робить `Settings.ensure_directories`.
    """
    base = Path(root) if root is not None else PROJECT_ROOT
    database_path = Path(os.environ.get("FOOD_EXPENSES_DB", base / "data" / "food-expenses.db"))
    log_dir = Path(os.environ.get("FOOD_EXPENSES_LOG_DIR", base / "logs"))
    backup_dir = Path(os.environ.get("FOOD_EXPENSES_BACKUP_DIR", base / "data" / "backups"))
    return Settings(database_path=database_path, log_dir=log_dir, backup_dir=backup_dir)
