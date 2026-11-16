"""Експорт покупок у CSV (REQ-F-035, REQ-I-003)."""

from __future__ import annotations

import csv
import io
from datetime import date

from ..db import Database
from ..logging_setup import log_event
from ..money import format_money, format_quantity
from ..repositories.purchases import PurchaseRepository
from .guards import require_profile

#: REQ-I-003: склад і порядок колонок файлу експорту.
#: Рядок заголовків вивантаження. Склад і порядок колонок задані
#: REQ-I-003; імена збігаються з полями схеми `Purchase` контракту.
CSV_HEADER = ["name", "category", "unitPrice", "quantity", "amount", "occurredAt"]


class ExportService:
    """Формування файлу CSV з покупками профілю за період."""

    def __init__(self, database: Database) -> None:
        """Прив'язує службу до бази даних.

        Args:
            database: Доступ до бази. Служба відкриває транзакцію на кожну
                операцію й не тримає з'єднання між викликами.
        """
        self._database = database

    def purchases_csv(
        self, profile_id: str, since: date | None = None, until: date | None = None
    ) -> str:
        """Складає вміст файла CSV із покупками періоду (REQ-F-035).

        Args:
            profile_id: Профіль, покупки якого вивантажуються.
            since: Нижня межа за датою покупки, включно.
            until: Верхня межа за датою покупки, включно.

        Returns:
            Текст файла: рядок заголовків і по одному рядку на покупку, у
            тому самому порядку, що й у списку покупок. Обмеження на
            кількість записів немає — вивантажується вся вибірка.

        Raises:
            ProfileNotFound: Профілю немає.

        Note:
            Текст повертається в UTF-8 без позначки BOM, як вимагає
            REQ-I-003. Excel під Windows без BOM показує українські назви
            нечитними; розбіжність зафіксована як відкрите питання ВП-06
            і потребує адендуму, бо змінює зовнішню поведінку операції.
        """
        with self._database.transaction() as connection:
            require_profile(connection, profile_id)
            items, _ = PurchaseRepository(connection).list_for_profile(
                profile_id, since=since, until=until, limit=None
            )

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(CSV_HEADER)
        for purchase, category_name in items:
            writer.writerow(
                [
                    purchase.name,
                    category_name,
                    format_money(purchase.unit_price),
                    format_quantity(purchase.quantity),
                    format_money(purchase.amount),
                    purchase.occurred_at.isoformat(timespec="seconds"),
                ]
            )

        log_event("purchases.exported", profile=profile_id, rows=len(items))
        return buffer.getvalue()

    @staticmethod
    def file_name(since: date | None, until: date | None) -> str:
        """Складає ім'я файла вивантаження.

        Ім'я відображає період, щоб кілька вивантажень поспіль не
        затирали одне одного в теці завантажень.

        Args:
            since: Нижня межа періоду або `None`.
            until: Верхня межа періоду або `None`.

        Returns:
            Ім'я файла, наприклад `purchases-2026-10-01_2026-10-31.csv`
            або `purchases-all.csv`, якщо межі не задані.
        """
        if since and until:
            return f"purchases-{since.isoformat()}_{until.isoformat()}.csv"
        if since:
            return f"purchases-from-{since.isoformat()}.csv"
        if until:
            return f"purchases-to-{until.isoformat()}.csv"
        return "purchases-all.csv"
