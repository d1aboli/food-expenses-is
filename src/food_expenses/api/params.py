"""Параметри шляху, спільні для маршрутів.

Імена параметрів беруться з контракту (`{profileId}`, `{categoryId}`,
`{purchaseId}`, `{budgetId}`), а в коді лишаються звичні імена зі
знаком підкреслення. Оголошені в одному місці, щоб опис, який віддає
застосунок, не розійшовся з контрактом через описку в одному з маршрутів.
"""

from __future__ import annotations

from fastapi import Path

PROFILE_ID = Path(alias="profileId")
CATEGORY_ID = Path(alias="categoryId")
PURCHASE_ID = Path(alias="purchaseId")
BUDGET_ID = Path(alias="budgetId")
