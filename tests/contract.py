"""Перевірка відповідей затвердженому контракту spec/api/openapi.yaml.

Тести не описують форму відповіді власними словами, а звіряють її зі схемою
з контракту. Завдяки цьому розбіжність між реалізацією і контрактом виявляється
тестом, а не очима під час перегляду.
"""

from __future__ import annotations

import functools
import re
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

CONTRACT_PATH = Path(__file__).resolve().parents[1] / "spec" / "api" / "openapi.yaml"

UUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
ISO_DATETIME_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)$"
)


@functools.lru_cache(maxsize=1)
def contract() -> dict[str, Any]:
    """Завантажує затверджений контракт."""

    return yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))


def _resolvable(schema: dict[str, Any]) -> dict[str, Any]:
    """Додає до схеми розділ `components`, щоб у ній працювали посилання `$ref`."""

    return {**schema, "components": contract()["components"]}


def schema_ref(name: str) -> dict[str, Any]:
    """Схема з розділу `components/schemas` контракту."""

    if name not in contract()["components"]["schemas"]:
        raise KeyError(f"У контракті немає схеми {name}")
    return _resolvable({"$ref": f"#/components/schemas/{name}"})


def response_schema(
    path: str,
    method: str,
    status: int | str,
    media_type: str = "application/json",
) -> dict[str, Any]:
    """Схема тіла відповіді конкретної операції контракту."""

    document = contract()
    operation = document["paths"][path][method.lower()]
    response = operation["responses"][str(status)]

    if "$ref" in response:
        name = response["$ref"].rsplit("/", 1)[-1]
        response = document["components"]["responses"][name]

    return _resolvable(response["content"][media_type]["schema"])


def assert_matches(payload: Any, schema: dict[str, Any]) -> None:
    """Перевіряє, що значення відповідає схемі контракту."""

    Draft202012Validator(schema).validate(payload)


def assert_response_matches_contract(
    response, path: str, method: str, status: int | str | None = None
) -> dict[str, Any]:
    """Звіряє код і тіло відповіді з контрактом; повертає розібране тіло."""

    expected_status = int(status) if status is not None else response.status_code
    assert response.status_code == expected_status, (
        f"{method.upper()} {path}: очікувався статус {expected_status}, "
        f"отримано {response.status_code}, тіло {response.text}"
    )
    payload = response.json()
    assert_matches(payload, response_schema(path, method, expected_status))
    return payload


def assert_error(
    response,
    status: int,
    code: str,
    requirement: str | None = None,
    field: str | None = None,
) -> dict[str, Any]:
    """Перевіряє, що помилка відповідає єдиній моделі `Error` з контракту."""

    assert response.status_code == status, (
        f"очікувався статус {status}, отримано {response.status_code}, "
        f"тіло {response.text}"
    )
    payload = response.json()
    assert_matches(payload, schema_ref("Error"))

    error = payload["error"]
    assert error["code"] == code, f"очікувався код {code}, отримано {error['code']}"
    assert error["message"].strip(), "повідомлення про помилку не може бути порожнім"

    if requirement is not None:
        assert error.get("requirement") == requirement, (
            f"очікувалося посилання на {requirement}, отримано {error.get('requirement')}"
        )
    if field is not None:
        fields = [detail["field"] for detail in error.get("details", [])]
        assert field in fields, f"у деталях помилки немає поля {field}: {fields}"

    assert UUID_PATTERN.match(payload["traceId"]), payload["traceId"]
    return payload
