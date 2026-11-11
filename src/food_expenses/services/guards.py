"""Спільні перевірки наявності записів (REQ-F-003).

Кожна операція над даними профілю починається однаково: переконатися, що
профіль існує, а категорія належить саме йому. Ця перевірка — суть REQ-F-003
про ізоляцію даних, тому вона лежить в одному місці, а не повторюється в
кожній службі.
"""

from __future__ import annotations

import sqlite3

from ..errors import CategoryNotFound, ProfileNotFound
from ..models import Category
from ..repositories.categories import CategoryRepository
from ..repositories.profiles import ProfileRepository


def require_profile(connection: sqlite3.Connection, profile_id: str) -> None:
    """REQ-F-003: операція можлива лише в наявному профілі."""

    if not ProfileRepository(connection).exists(profile_id):
        raise ProfileNotFound()


def require_category(
    connection: sqlite3.Connection, profile_id: str, category_id: str
) -> Category:
    """REQ-F-003: категорія чужого профілю для цього профілю не існує.

    Саме «не існує», а не «заборонена»: відповідь 404 не повідомляє, що такий
    запис є в когось іншого.
    """

    category = CategoryRepository(connection).get(profile_id, category_id)
    if category is None:
        raise CategoryNotFound()
    return category
