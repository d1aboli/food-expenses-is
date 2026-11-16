#!/usr/bin/env python3
"""Локальний запуск сервера REST API.

    python run_server.py
    python run_server.py --port 9000

Базова адреса — http://127.0.0.1:8080/api/v1, як указано в розділі `servers`
затвердженого контракту spec/api/openapi.yaml.

Каталог `src` додається до шляху імпорту тут, а не в змінній середовища: так
команда запуску однакова на Windows і на Linux. Проєкт не встановлюється як
пакет, бо це навчальний практикум, а не бібліотека.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import uvicorn  # noqa: E402

from food_expenses.api.app import create_app  # noqa: E402

#: Адреса за замовчуванням. Саме локальна, а не 0.0.0.0: система працює з
#: особистими витратами, і виставляти її в мережу без потреби не слід.
DEFAULT_HOST = "127.0.0.1"

#: Порт за замовчуванням; збігається з розділом `servers` контракту.
DEFAULT_PORT = 8080

app = create_app()


def main(argv: list[str] | None = None) -> None:
    """Запускає сервер із параметрами командного рядка.

    Args:
        argv: Аргументи командного рядка; якщо не задані, беруться з
            `sys.argv`.
    """
    parser = argparse.ArgumentParser(description="Сервер REST API системи обліку витрат.")
    parser.add_argument("--host", default=DEFAULT_HOST, help="адреса, яку слухати")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="порт, який слухати")
    arguments = parser.parse_args(argv)
    uvicorn.run(app, host=arguments.host, port=arguments.port)


if __name__ == "__main__":
    main()
