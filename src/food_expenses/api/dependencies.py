"""Залежності маршрутів: доступ до служб застосунку."""

from __future__ import annotations

from fastapi import Request

from ..db import Database
from ..services.profiles import ProfileService


def get_database(request: Request) -> Database:
    return request.app.state.database


def get_profile_service(request: Request) -> ProfileService:
    return ProfileService(get_database(request))
