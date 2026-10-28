# Сценарії перевірки контракту через mock API

Mock запускається з самої специфікації, серверного коду немає:

```bash
npx @stoplight/prism-cli mock spec/api/openapi.yaml -p 4010
./spec/api/run-scenarios.sh > docs/api-scenarios-output.txt
```

Потрібну відповідь обирає заголовок `Prefer: code=..., example=...` — так один
контракт перевіряється і на успішних, і на помилкових шляхах.

## Позитивні сценарії

| # | Сценарій | Запит | Очікувано | Вимоги |
|---|---|---|---|---|
| P1 | Список профілів | `GET /profiles` | 200, масив профілів | REQ-F-002 |
| P2 | Створення профілю | `POST /profiles {"name":"Ілля"}` | 201, профіль з id | REQ-F-001 |
| P3 | Базові категорії | `GET /profiles/{id}/categories` | 200, п'ять категорій, «Інше» з `system: true` | REQ-F-020, REQ-F-003 |
| P4 | Покупка на вагу | `POST .../purchases` ціна 80.00, кількість 0.7 | 201, `amount: "56.00"` | REQ-F-005…007 |
| P5 | Список покупок | `GET .../purchases?from=&to=` | 200, від новіших до старіших | REQ-F-012 |
| P6 | Підсумок за тиждень | `GET .../summary?period=week&date=2026-10-05` | 200, `total: "150.00"`, межі 05.10–11.10 | REQ-F-027 |
| P7 | Порожній місяць | `GET .../summary?period=month&date=2026-03-15` | 200, `total: "0.00"` | REQ-F-033 |
| P8 | Розбивка за категоріями | `GET .../summary/categories` | 200, частки 75 і 25, разом 100 | REQ-F-030 |
| P9 | Графік по днях | `GET .../charts/daily?month=2026-10` | 200, точки з сумами за день | REQ-F-031 |
| P10 | Перенесення на інший день | `PATCH .../purchases/{id}` нова `occurredAt` | 200, оновлена дата | REQ-F-008, REQ-F-009 |
| P11 | Видалення покупки | `DELETE .../purchases/{id}` | 204, без тіла | REQ-F-010 |
| P12 | Експорт у CSV | `GET .../purchases/export` | 200, `text/csv` із заголовком колонок | REQ-F-035, REQ-I-003 |

## Негативні сценарії

| # | Сценарій | Запит | Очікувано | Вимоги |
|---|---|---|---|---|
| N1 | Ціна дорівнює нулю | `POST .../purchases` `unitPrice: "0.00"` | 422, `VALIDATION_FAILED`, `requirement: REQ-F-013` | REQ-F-013 |
| N2 | Порожня назва | `POST .../purchases` `name: ""` | 422, `requirement: REQ-F-015` | REQ-F-015 |
| N3 | Дата в майбутньому | `PATCH .../purchases/{id}` `occurredAt: 2030-01-01` | 422, `requirement: REQ-F-016` | REQ-F-016 |
| N4 | Чотири знаки в кількості | `POST .../purchases` `quantity: "0.1255"` | 422, `requirement: REQ-F-018` | REQ-F-018 |
| N5 | Видалення непорожньої категорії | `DELETE .../categories/{id}` без `confirm` | 409, `CATEGORY_NOT_EMPTY`, кількість покупок | REQ-F-023 |
| N6 | Видалення категорії «Інше» | `DELETE .../categories/{id службової}` | 409, `CATEGORY_IS_SYSTEM` | REQ-F-025 |
| N7 | Неіснуюча покупка | `GET .../purchases/{невідомий id}` | 404, `PURCHASE_NOT_FOUND` | REQ-F-012 |
| N8 | Чужий або неіснуючий профіль | `GET /profiles/{невідомий id}/categories` | 404, `PROFILE_NOT_FOUND` | REQ-F-003 |
| N9 | Невідомий період | `GET .../summary?period=quarter` | 400, `INVALID_PERIOD` | REQ-F-026 |
| N10 | Дублікат назви категорії | `POST .../categories {"name":"Продукти"}` | 409, `CATEGORY_NAME_TAKEN` | REQ-F-021 |

## Результат прогону

Усі 22 сценарії відтворені mock-сервером, повний вивід — `docs/api-scenarios-output.txt`.

| Код | Кількість відповідей |
|---|---|
| 200 | 9 |
| 201 | 2 |
| 204 | 1 |
| 400 | 1 |
| 404 | 2 |
| 409 | 3 |
| 422 | 4 |

Mock повернув саме ті структури, що описані в контракті: обчислену вартість `56.00`,
підсумок `150.00` з межами тижня понеділок–неділя, `0.00` для порожнього місяця,
частки категорій 75 і 25, CSV із потрібними колонками та єдину модель помилки з полем
`requirement`. Це підтверджує, що контракт відтворюваний до написання серверного коду.
