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
        """Подання рядка в тому вигляді, у якому його чекає контракт.

        Returns:
            Словник із ключами `field` та `issue` — саме ці імена задані
            схемою `Error` у `spec/api/openapi.yaml`.
        """
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
        """Створює помилку з повідомленням і подробицями.

        Args:
            message: Повідомлення для людини, українською. Потрапляє у
                відповідь як є.
            requirement: ID вимоги, яку порушено. Якщо не заданий,
                береться типовий для цього класу.
            details: Поля, що не пройшли перевірку; кожне окремим рядком
                масиву `details` у відповіді.
        """
        super().__init__(message)
        self.message = message
        self.requirement = requirement or self.__class__.requirement
        self.details: list[ErrorDetail] = details or []


class ValidationFailed(DomainError):
    """Вхідні дані не пройшли перевірку (REQ-F-019).

    Збуджується модулями `validation` і `text`. Перелік полів, що не
    пройшли перевірку, передається в `details`.
    """

    status = 422
    code = "VALIDATION_FAILED"
    requirement = "REQ-F-019"


class ProfileNotFound(DomainError):
    """Профілю із заданим ідентифікатором не існує (REQ-F-003).

    Типове повідомлення: «Профіль не знайдено.»
    """

    status = 404
    code = "PROFILE_NOT_FOUND"
    requirement = "REQ-F-003"

    def __init__(self, message: str = "Профіль не знайдено.", **kwargs) -> None:
        super().__init__(message, **kwargs)


class CategoryNotFound(DomainError):
    """Категорії із заданим ідентифікатором немає в цьому профілі (REQ-F-021).

    Категорія іншого профілю теж вважається не знайденою: профілі ізольовані.
    Типове повідомлення: «Категорію не знайдено.»
    """

    status = 404
    code = "CATEGORY_NOT_FOUND"
    requirement = "REQ-F-021"

    def __init__(self, message: str = "Категорію не знайдено.", **kwargs) -> None:
        super().__init__(message, **kwargs)


class PurchaseNotFound(DomainError):
    """Покупки із заданим ідентифікатором немає в цьому профілі (REQ-F-012).

    Типове повідомлення: «Покупку не знайдено.»
    """

    status = 404
    code = "PURCHASE_NOT_FOUND"
    requirement = "REQ-F-012"

    def __init__(self, message: str = "Покупку не знайдено.", **kwargs) -> None:
        super().__init__(message, **kwargs)


class ProfileNameTaken(DomainError):
    """Профіль із такою назвою вже існує (REQ-F-001).

    Типове повідомлення: «Профіль з такою назвою вже існує.»
    """

    status = 409
    code = "PROFILE_NAME_TAKEN"
    requirement = "REQ-F-001"

    def __init__(self, message: str = "Профіль з такою назвою вже існує.", **kwargs) -> None:
        super().__init__(message, **kwargs)


class CategoryNameTaken(DomainError):
    """Категорія з такою назвою вже є в цьому профілі (REQ-F-021).

    Унікальність назви вимагається в межах профілю, а не глобально: дві
    різні людини можуть мати категорію з однаковою назвою.
    Типове повідомлення: «Категорія з такою назвою вже існує в цьому профілі.»
    """

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
    """Спроба видалити категорію, до якої прив'язані покупки (REQ-F-023).

    Повідомлення складається на місці й містить кількість пов'язаних
    покупок, тому типового повідомлення цей клас не задає. Видалення
    все ж можливе з підтвердженням (REQ-F-024).
    """

    status = 409
    code = "CATEGORY_NOT_EMPTY"
    requirement = "REQ-F-023"


class CategoryIsSystem(DomainError):
    """Спроба видалити або перейменувати службову категорію (REQ-F-025).

    Категорія «Інше» захищена, бо саме до неї переносяться покупки з
    видалених категорій.
    Типове повідомлення: «Категорія «Інше» є службовою, її не можна
    видалити або перейменувати.»
    """

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
    """Межі періоду задано некоректно (REQ-F-026..REQ-F-029).

    Охоплює невідому назву періоду, дату в неприйнятному форматі,
    відсутні межі діапазону та кінець діапазону, раніший за початок.
    Єдина помилка предметної області зі статусом 400: решта стосується
    змісту даних, а ця — самого запиту.
    """

    status = 400
    code = "INVALID_PERIOD"
    requirement = "REQ-F-026"


class BackupFailed(DomainError):
    """Не вдалося створити резервну копію бази даних (REQ-F-036).

    Єдина помилка зі статусом 500: причина лежить поза системою — немає
    прав на запис, бракує місця на диску.
    Типове повідомлення: «Не вдалося створити резервну копію бази даних.»
    """

    status = 500
    code = "BACKUP_FAILED"
    requirement = "REQ-F-036"

    def __init__(
        self,
        message: str = "Не вдалося створити резервну копію бази даних.",
        **kwargs,
    ) -> None:
        super().__init__(message, **kwargs)


class BudgetNotFound(DomainError):
    """Бюджету із заданим ідентифікатором немає в цьому профілі (ADD-01, REQ-A-009).

    Типове повідомлення: «Бюджет не знайдено.»
    """

    status = 404
    code = "BUDGET_NOT_FOUND"
    requirement = "REQ-A-009"

    def __init__(self, message: str = "Бюджет не знайдено.", **kwargs) -> None:
        super().__init__(message, **kwargs)


class BudgetAlreadySet(DomainError):
    """Категорія вже має бюджет (ADD-01, REQ-A-003).

    Категорія може мати не більш ніж один бюджет у межах профілю, тому
    повторне встановлення відхиляється, а наявний бюджет не змінюється.
    Змінити суму можна операцією `updateBudget`.
    Типове повідомлення: «Для цієї категорії бюджет уже встановлено.»
    """

    status = 409
    code = "BUDGET_ALREADY_SET"
    requirement = "REQ-A-003"

    def __init__(
        self, message: str = "Для цієї категорії бюджет уже встановлено.", **kwargs
    ) -> None:
        super().__init__(message, **kwargs)
