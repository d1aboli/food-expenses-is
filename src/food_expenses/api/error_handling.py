"""Єдина модель помилки для всіх операцій API.

Форма тіла відповіді визначена схемою `Error` у spec/api/openapi.yaml:

    {"error": {"code", "message", "requirement", "details": [...]}, "traceId": ...}

Обробники перетворюють помилки предметної області та помилки розбору запиту
в цю єдину форму, щоб клієнт не бачив двох різних форматів (REQ-F-019).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ..errors import DomainError, ErrorDetail
from ..logging_setup import current_trace_id, log_event


def error_body(
    code: str,
    message: str,
    requirement: str | None = None,
    details: list[ErrorDetail] | None = None,
    trace_id: str | None = None,
) -> dict[str, Any]:
    """Збирає тіло відповіді за схемою `Error` затвердженого контракту."""

    error: dict[str, Any] = {"code": code, "message": message}
    if requirement:
        error["requirement"] = requirement
    error["details"] = [detail.as_dict() for detail in (details or [])]
    return {"error": error, "traceId": trace_id or current_trace_id.get()}


def domain_error_response(exc: DomainError) -> JSONResponse:
    """Відповідь на помилку предметної області."""

    log_event(
        "request.rejected",
        level=logging.WARNING,
        code=exc.code,
        requirement=exc.requirement,
        message=exc.message,
    )
    return JSONResponse(
        status_code=exc.status,
        content=error_body(exc.code, exc.message, exc.requirement, exc.details),
    )


def _details_from_request_validation(exc: RequestValidationError) -> list[ErrorDetail]:
    details: list[ErrorDetail] = []
    for error in exc.errors():
        location = [str(part) for part in error.get("loc", []) if part != "body"]
        details.append(ErrorDetail(".".join(location) or "body", error.get("msg", "invalid")))
    return details


def register_error_handlers(app: FastAPI) -> None:
    """Реєструє обробники помилок у застосунку."""

    @app.exception_handler(DomainError)
    async def _handle_domain_error(_: Request, exc: DomainError) -> JSONResponse:
        return domain_error_response(exc)

    @app.exception_handler(RequestValidationError)
    async def _handle_request_validation(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Порушення структури тіла запиту — це порушення правила предметної
        # області, контракт відповідає на нього кодом 422 (UnprocessableEntity).
        details = _details_from_request_validation(exc)
        log_event(
            "request.rejected",
            level=logging.WARNING,
            code="VALIDATION_FAILED",
            fields=",".join(detail.field_name for detail in details),
        )
        return JSONResponse(
            status_code=422,
            content=error_body(
                "VALIDATION_FAILED",
                "Запит не відповідає очікуваній структурі.",
                "REQ-F-019",
                details,
            ),
        )

    # Для непередбачених помилок контракт не описує тіла відповіді: перелік
    # кодів у схемі `Error` їх не містить. Щоб не вводити поведінку, якої немає
    # в затвердженій специфікації, такі помилки лише записуються в журнал
    # (REQ-NF-008) посередником `trace_requests`, а відповідь формує сервер
    # застосунків. Розбіжність зафіксована як відкрите питання ВП-02.
