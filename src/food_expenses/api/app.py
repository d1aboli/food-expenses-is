"""Збирання застосунку REST API.

Застосунок складається з окремих компонентів: маршрути (`api/routers`),
прикладні служби (`services`), доступ до бази (`repositories`), журналювання
(`logging_setup`) та обробники помилок (`api/error_handling`).
"""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI, Request

from ..config import API_PREFIX, Settings, load_settings
from ..db import Database
from ..logging_setup import configure_logging, current_trace_id, log_event
from .error_handling import register_error_handlers

TITLE = "Food Expenses IS API"
VERSION = "1.0.0"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Створює застосунок із заданими налаштуваннями.

    Тести передають власні налаштування з тимчасовим каталогом, тому жоден
    прогін тестів не чіпає робочу базу й робочі журнали.
    """

    settings = settings or load_settings()
    settings.ensure_directories()
    configure_logging(settings.log_dir)

    database = Database(settings.database_path)
    database.migrate()

    app = FastAPI(title=TITLE, version=VERSION, docs_url="/docs", openapi_url="/openapi.json")
    app.state.settings = settings
    app.state.database = database

    register_error_handlers(app)

    @app.middleware("http")
    async def trace_requests(request: Request, call_next):
        """Присвоює запиту trace-ID і пише в журнал кожну дію (REQ-NF-008)."""

        trace_id = str(uuid.uuid4())
        token = current_trace_id.set(trace_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:  # pragma: no cover - перевіряється окремим тестом
            log_event(
                "request.failed",
                level=logging.ERROR,
                method=request.method,
                path=request.url.path,
                error=type(exc).__name__,
                message=str(exc),
            )
            raise
        else:
            log_event(
                "request.handled",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                ms=f"{(time.perf_counter() - started) * 1000:.1f}",
            )
            response.headers["X-Trace-Id"] = trace_id
            return response
        finally:
            current_trace_id.reset(token)

    for router in _routers():
        app.include_router(router, prefix=API_PREFIX)

    log_event("application.started", database=str(settings.database_path))
    return app


def _routers() -> list:
    """Перелік маршрутів застосунку.

    Маршрути додаються етапами плану `docs/plan.md`, кожен — після того, як
    пройдено відповідний TEST-GATE.
    """

    from .routers import categories, profiles

    return [profiles.router, categories.router]
