#!/usr/bin/env python3
"""Контрактна перевірка реалізації (крок 3 і крок 7 ЛР5).

    python tools/check_contract.py

Перевіряє дві речі:

1. Затверджений контракт `spec/api/openapi.yaml` лишається коректним описом
   OpenAPI 3.0.
2. Набір операцій, які віддає сам застосунок, збігається з контрактом —
   жодної операції не бракує і жодної зайвої не додано.

Друга перевірка потрібна саме після рефакторингу: вона показує, що внутрішня
перебудова коду не змінила зовнішнього інтерфейсу.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import yaml  # noqa: E402
from openapi_spec_validator import validate  # noqa: E402

from food_expenses.api.app import create_app  # noqa: E402
from food_expenses.config import API_PREFIX, Settings  # noqa: E402

CONTRACT_PATH = PROJECT_ROOT / "spec" / "api" / "openapi.yaml"
METHODS = {"get", "post", "put", "patch", "delete"}


def contract_operations(document: dict) -> set[tuple[str, str]]:
    return {
        (path, method)
        for path, item in document["paths"].items()
        for method in item
        if method in METHODS
    }


def implemented_operations() -> set[tuple[str, str]]:
    workdir = Path(tempfile.mkdtemp())
    app = create_app(
        Settings(
            database_path=workdir / "check.db",
            log_dir=workdir / "logs",
            backup_dir=workdir / "backups",
        )
    )
    return {
        (path[len(API_PREFIX):], method)
        for path, item in app.openapi()["paths"].items()
        for method in item
        if method in METHODS
    }


def main() -> int:
    document = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))

    validate(document)
    print(f"{CONTRACT_PATH.relative_to(PROJECT_ROOT)}: опис OpenAPI коректний")

    declared = contract_operations(document)
    implemented = implemented_operations()
    missing = sorted(declared - implemented)
    extra = sorted(implemented - declared)

    print(f"Операцій у контракті: {len(declared)}")
    print(f"Реалізовано операцій:  {len(implemented)}")

    for path, method in missing:
        print(f"  БРАКУЄ: {method.upper()} {path}")
    for path, method in extra:
        print(f"  ПОЗА КОНТРАКТОМ: {method.upper()} {path}")

    if missing or extra:
        print("Результат: реалізація не збігається з контрактом")
        return 1

    print("Результат: реалізація повністю відповідає затвердженому контракту")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
