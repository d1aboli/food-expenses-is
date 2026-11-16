"""Операція `createBackup` з контракту (REQ-F-036)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ...services.backups import BackupService
from ..dependencies import get_backup_service
from ..schemas import backup_payload

router = APIRouter(tags=["system"])


@router.post("/backups", status_code=201)
def create_backup(service: BackupService = Depends(get_backup_service)) -> dict:
    """Операція `createBackup`: резервна копія бази даних (REQ-F-036).

    Копія робиться засобом SQLite, а не копіюванням файла: копіювання
    під час незавершеної транзакції дало б непридатний до відновлення
    файл. Відповідь 500 `BACKUP_FAILED`, якщо запис не вдався.
    """
    return backup_payload(service.create())
