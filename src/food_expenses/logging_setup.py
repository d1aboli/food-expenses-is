"""Система журналювання дій і помилок.

Усі дії в системі пишуться в `logs/app.log`, помилки виконання додатково
дублюються в `logs/errors.log` із датою, часом і текстом помилки (REQ-NF-008).

Рядок журналу має формат «ключ=значення», щоб його можна було і прочитати
очима, і перевірити автоматичним тестом:

    2026-11-11T10:04:32+02:00 | INFO  | trace=... | event=purchase.created | ...
"""

from __future__ import annotations

import logging
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path

from .config import APP_TIMEZONE

LOGGER_NAME = "food_expenses"
APP_LOG_FILE = "app.log"
ERROR_LOG_FILE = "errors.log"

#: ID запиту, який підставляється в кожен рядок журналу цього запиту.
current_trace_id: ContextVar[str] = ContextVar("current_trace_id", default="-")


class _TraceFilter(logging.Filter):
    """Додає до запису поточний trace-ID, навіть якщо його не передали."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "trace"):
            record.trace = current_trace_id.get()
        return True


class _LocalTimeFormatter(logging.Formatter):
    """Форматує час у локальному часовому поясі застосунку з указанням зсуву."""

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        moment = datetime.fromtimestamp(record.created, tz=APP_TIMEZONE)
        return moment.isoformat(timespec="seconds")


def configure_logging(log_dir: Path) -> logging.Logger:
    """Налаштовує журнали застосунку (REQ-NF-006, REQ-NF-008).

    Створюються два обробники: `app.log` приймає всі дії системи від рівня
    INFO, `errors.log` — лише помилки. Другий потрібен саме окремо: у
    спільному файлі помилка губиться серед звичайних записів.

    Повторний виклик не множить обробники, а замінює їх. Це важливо для
    тестів: кожен тест створює застосунок заново, і без заміни записи
    дублювалися б із кожним прогоном.

    Args:
        log_dir: Каталог журналів; створюється за потреби.

    Returns:
        Логер системи, уже з обробниками.
    """
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Повторний виклик не повинен множити обробники (важливо для тестів).
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    formatter = _LocalTimeFormatter(
        fmt="%(asctime)s | %(levelname)-5s | trace=%(trace)s | %(message)s"
    )
    trace_filter = _TraceFilter()

    app_handler = logging.FileHandler(log_dir / APP_LOG_FILE, encoding="utf-8")
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(formatter)
    app_handler.addFilter(trace_filter)
    logger.addHandler(app_handler)

    error_handler = logging.FileHandler(log_dir / ERROR_LOG_FILE, encoding="utf-8")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    error_handler.addFilter(trace_filter)
    logger.addHandler(error_handler)

    return logger


def get_logger() -> logging.Logger:
    """Повертає логер системи.

    Returns:
        Логер із іменем `food_expenses`. Якщо `configure_logging` ще не
        викликали, логер повернеться без обробників — записи просто
        нікуди не підуть, помилки не буде.
    """
    return logging.getLogger(LOGGER_NAME)


def log_event(event: str, level: int = logging.INFO, **fields: object) -> None:
    """Записує одну дію системи (REQ-NF-006).

    Формат рядка — `event=<назва> ключ=значення`, однаковий для всіх
    подій: такий запис і читається людиною, і розбирається пошуком.

    Args:
        event: Назва події, наприклад `purchase.created`.
        level: Рівень запису; помилки рівня ERROR потрапляють ще й до
            `errors.log`.
        **fields: Додаткові поля події. Поля зі значенням `None`
            пропускаються, щоб у журналі не з'являлося `category=None`.
    """
    parts = [f"event={event}"]
    parts.extend(f"{key}={value}" for key, value in fields.items() if value is not None)
    get_logger().log(level, " | ".join(parts))
