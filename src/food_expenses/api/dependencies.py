"""Залежності маршрутів: доступ до служб застосунку.

Кожна функція тут — постачальник однієї служби для механізму `Depends`
у FastAPI. Служба створюється на кожен запит заново; стану між запитами
вона не має, а спільний ресурс — об'єкт `Database` — живе в стані
застосунку і створюється один раз при старті.

Такий поділ дає ще одну річ: у тесті достатньо підмінити
`app.state.database`, щоб уся гілка маршрут — служба — репозиторій
працювала з тимчасовим файлом бази (`tests/conftest.py`).
"""

from __future__ import annotations

from fastapi import Request

from ..db import Database
from ..services.backups import BackupService
from ..services.budgets import BudgetService
from ..services.categories import CategoryService
from ..services.exports import ExportService
from ..services.profiles import ProfileService
from ..services.purchases import PurchaseService
from ..services.summaries import SummaryService


def get_database(request: Request) -> Database:
    """Повертає спільний об'єкт доступу до бази даних.

    Об'єкт створюється один раз при старті застосунку й зберігається в
    `app.state`: відкривати файл бази на кожен запит не треба.

    Args:
        request: Поточний запит; через нього доступний стан застосунку.

    Returns:
        Об'єкт `Database`, прив'язаний до файлу з налаштувань.
    """
    return request.app.state.database


def get_profile_service(request: Request) -> ProfileService:
    """Створює службу профілів (REQ-F-001..REQ-F-004).

    Args:
        request: Поточний запит; через нього доступний стан застосунку.

    Returns:
        Нова `ProfileService` для цього запиту.
    """
    return ProfileService(get_database(request))


def get_category_service(request: Request) -> CategoryService:
    """Створює службу категорій (REQ-F-020..REQ-F-025).

    Args:
        request: Поточний запит; через нього доступний стан застосунку.

    Returns:
        Нова `CategoryService` для цього запиту.
    """
    return CategoryService(get_database(request))


def get_purchase_service(request: Request) -> PurchaseService:
    """Створює службу покупок (REQ-F-005..REQ-F-012).

    Args:
        request: Поточний запит; через нього доступний стан застосунку.

    Returns:
        Нова `PurchaseService` для цього запиту.
    """
    return PurchaseService(get_database(request))


def get_summary_service(request: Request) -> SummaryService:
    """Створює службу підсумків і графіків (REQ-F-026..REQ-F-033).

    Args:
        request: Поточний запит; через нього доступний стан застосунку.

    Returns:
        Нова `SummaryService` для цього запиту.
    """
    return SummaryService(get_database(request))


def get_export_service(request: Request) -> ExportService:
    """Створює службу експорту у CSV (REQ-F-035).

    Args:
        request: Поточний запит; через нього доступний стан застосунку.

    Returns:
        Нова `ExportService` для цього запиту.
    """
    return ExportService(get_database(request))


def get_backup_service(request: Request) -> BackupService:
    """Створює службу резервного копіювання (REQ-F-036).

    Окремо передається каталог для копій: він задається налаштуваннями, а
    не виводиться зі шляху до бази.

    Args:
        request: Поточний запит; через нього доступний стан застосунку.

    Returns:
        Нова `BackupService` для цього запиту.
    """
    return BackupService(get_database(request), request.app.state.settings.backup_dir)


def get_budget_service(request: Request) -> BudgetService:
    """Створює службу бюджетів (ADD-01, REQ-A-001..REQ-A-009).

    Args:
        request: Поточний запит; через нього доступний стан застосунку.

    Returns:
        Нова `BudgetService` для цього запиту.
    """
    return BudgetService(get_database(request))
