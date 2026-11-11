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
