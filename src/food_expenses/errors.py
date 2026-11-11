"""Помилки предметної області.

Кожна помилка несе код, статус HTTP та ID порушеної вимоги — рівно ті значення,
що перелічені в схемі `Error` затвердженого контракту spec/api/openapi.yaml
(REQ-F-019).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorDetail:
    """Один рядок масиву `details` у моделі помилки."""

    field_name: str
    issue: str

    def as_dict(self) -> dict[str, str]:
        return {"field": self.field_name, "issue": self.issue}


class DomainError(Exception):
    """Базова помилка предметної області.

    Підкласи задають `status`, `code` і типову вимогу; конкретне повідомлення
    та перелік полів передаються під час створення.
    """

    status: int = 422
    code: str = "VALIDATION_FAILED"
    requirement: str = ""

    def __init__(
        self,
        message: str,
        requirement: str | None = None,
        details: list[ErrorDetail] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.requirement = requirement or self.__class__.requirement
        self.details: list[ErrorDetail] = details or []


class ValidationFailed(DomainError):
    status = 422
    code = "VALIDATION_FAILED"
    requirement = "REQ-F-019"


class ProfileNotFound(DomainError):
    status = 404
    code = "PROFILE_NOT_FOUND"
    requirement = "REQ-F-003"

    def __init__(self, message: str = "Профіль не знайдено.", **kwargs) -> None:
        super().__init__(message, **kwargs)


class CategoryNotFound(DomainError):
    status = 404
    code = "CATEGORY_NOT_FOUND"
    requirement = "REQ-F-021"

    def __init__(self, message: str = "Категорію не знайдено.", **kwargs) -> None:
        super().__init__(message, **kwargs)


class PurchaseNotFound(DomainError):
    status = 404
    code = "PURCHASE_NOT_FOUND"
    requirement = "REQ-F-012"

    def __init__(self, message: str = "Покупку не знайдено.", **kwargs) -> None:
        super().__init__(message, **kwargs)


class ProfileNameTaken(DomainError):
    status = 409
    code = "PROFILE_NAME_TAKEN"
    requirement = "REQ-F-001"

    def __init__(self, message: str = "Профіль з такою назвою вже існує.", **kwargs) -> None:
        super().__init__(message, **kwargs)


class CategoryNameTaken(DomainError):
    status = 409
    code = "CATEGORY_NAME_TAKEN"
    requirement = "REQ-F-021"

    def __init__(
        self,
        message: str = "Категорія з такою назвою вже існує в цьому профілі.",
        **kwargs,
    ) -> None:
        super().__init__(message, **kwargs)


class CategoryNotEmpty(DomainError):
    status = 409
    code = "CATEGORY_NOT_EMPTY"
    requirement = "REQ-F-023"


class CategoryIsSystem(DomainError):
    status = 409
    code = "CATEGORY_IS_SYSTEM"
    requirement = "REQ-F-025"

    def __init__(
        self,
        message: str = "Категорія «Інше» є службовою, її не можна видалити або перейменувати.",
        **kwargs,
    ) -> None:
        super().__init__(message, **kwargs)


class InvalidPeriod(DomainError):
    status = 400
    code = "INVALID_PERIOD"
    requirement = "REQ-F-026"


class BackupFailed(DomainError):
    status = 500
    code = "BACKUP_FAILED"
    requirement = "REQ-F-036"

    def __init__(
        self,
        message: str = "Не вдалося створити резервну копію бази даних.",
        **kwargs,
    ) -> None:
        super().__init__(message, **kwargs)
