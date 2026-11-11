"""Залежності маршрутів: доступ до служб застосунку."""

from __future__ import annotations

from fastapi import Request

from ..db import Database
from ..services.categories import CategoryService
from ..services.profiles import ProfileService
from ..services.purchases import PurchaseService
from ..services.summaries import SummaryService


def get_database(request: Request) -> Database:
    return request.app.state.database


def get_profile_service(request: Request) -> ProfileService:
    return ProfileService(get_database(request))


def get_category_service(request: Request) -> CategoryService:
    return CategoryService(get_database(request))


def get_purchase_service(request: Request) -> PurchaseService:
    return PurchaseService(get_database(request))


def get_summary_service(request: Request) -> SummaryService:
    return SummaryService(get_database(request))
