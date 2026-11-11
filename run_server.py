#!/usr/bin/env python3
"""Локальний запуск сервера REST API.

    python run_server.py

Базова адреса — http://localhost:8080/api/v1, як указано в розділі `servers`
затвердженого контракту spec/api/openapi.yaml.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import uvicorn  # noqa: E402

from food_expenses.api.app import create_app  # noqa: E402

app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)
