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
        """Прив'язує службу до бази даних.

        Args:
            database: Доступ до бази. Служба відкриває транзакцію на кожну
                операцію й не тримає з'єднання між викликами.
        """
        self._database = database

    def create(self, name: str) -> Profile:
        """Створює профіль (REQ-F-001).

        Разом із профілем в одній транзакції створюються п'ять базових
        категорій (REQ-F-020): профіль без категорій не має сенсу, бо до
        нього не можна додати жодної покупки.

        Args:
            name: Назва профілю.

        Returns:
            Створений профіль із новим ідентифікатором і часом створення.

        Raises:
            ValidationFailed: Назва порожня або довша за 60 символів.
            ProfileNameTaken: Профіль із такою назвою вже існує.
        """
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
        """Перелік наявних профілів (REQ-F-002).

        Returns:
            Профілі в порядку створення; можливо порожній перелік. Порожній —
            це не помилка, а сигнал інтерфейсу запропонувати створити перший
            профіль (REQ-F-004).
        """
        with self._database.transaction() as connection:
            return ProfileRepository(connection).list_all()

    def get(self, profile_id: str) -> Profile:
        """Читає один профіль (REQ-F-002).

        Args:
            profile_id: Ідентифікатор профілю.

        Returns:
            Профіль.

        Raises:
            ProfileNotFound: Профілю немає.
        """
        with self._database.transaction() as connection:
            profile = ProfileRepository(connection).get(profile_id)
        if profile is None:
            raise ProfileNotFound()
        return profile
