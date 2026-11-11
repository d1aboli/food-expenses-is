"""Правила роботи з профілями (REQ-F-001, REQ-F-002, REQ-F-004)."""

from __future__ import annotations

import uuid
from datetime import datetime

from ..config import APP_TIMEZONE
from ..db import Database
from ..errors import ErrorDetail, ProfileNameTaken, ProfileNotFound
from ..logging_setup import log_event
from ..models import Profile
from ..repositories.profiles import ProfileRepository
from ..text import PROFILE_NAME, clean_name
from .categories import create_base_categories


class ProfileService:
    """Створення, перелік і читання профілів."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def create(self, name: str) -> Profile:
        """REQ-F-001: створює профіль із зазначеною назвою."""

        cleaned = clean_name(name, PROFILE_NAME)
        profile = Profile(
            id=str(uuid.uuid4()),
            name=cleaned,
            created_at=datetime.now(tz=APP_TIMEZONE),
        )

        with self._database.transaction() as connection:
            repository = ProfileRepository(connection)
            if repository.find_by_name(cleaned) is not None:
                raise ProfileNameTaken(
                    details=[ErrorDetail("name", "must be unique")],
                )
            repository.add(profile)
            # REQ-F-020: профіль одразу отримує базові категорії.
            create_base_categories(connection, profile.id)

        log_event("profile.created", profile=profile.id, name=profile.name)
        return profile

    def list(self) -> list[Profile]:
        """REQ-F-002, REQ-F-004: перелік наявних профілів, можливо порожній."""

        with self._database.transaction() as connection:
            return ProfileRepository(connection).list_all()

    def get(self, profile_id: str) -> Profile:
        """REQ-F-002: читає профіль або повідомляє, що його немає."""

        with self._database.transaction() as connection:
            profile = ProfileRepository(connection).get(profile_id)
        if profile is None:
            raise ProfileNotFound()
        return profile

