"""Записи предметної області.

Це прості незмінні структури, спільні для шару служб і шару доступу до даних.
Термінологія — за `spec/glossary.md`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Profile:
    """Профіль користувача (REQ-F-001)."""

    id: str
    name: str
    created_at: datetime


@dataclass(frozen=True)
class Category:
    """Категорія витрат у межах профілю (REQ-F-020, REQ-F-021).

    Службова категорія «Інше» позначена `is_system`: її не можна ані
    перейменувати, ані видалити, бо до неї переносяться покупки з видалених
    категорій (REQ-F-025).
    """

    id: str
    profile_id: str
    name: str
    is_system: bool
