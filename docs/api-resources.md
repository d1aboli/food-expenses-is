# Модель REST-ресурсів і простежуваність API

Контракт: `spec/api/openapi.yaml` (OpenAPI 3.0.3). Джерело — SRS v1.0.
Кожна операція містить поле `x-requirements` з ID вимог.

## Ресурси

| Ресурс | URI | Опис |
|---|---|---|
| Профіль | `/profiles`, `/profiles/{profileId}` | Іменований набір даних однієї людини |
| Категорія | `/profiles/{profileId}/categories[/{categoryId}]` | Тип витрати в межах профілю |
| Покупка | `/profiles/{profileId}/purchases[/{purchaseId}]` | Запис про витрату |
| Експорт | `/profiles/{profileId}/purchases/export` | Вивантаження покупок у CSV |
| Підсумок | `/profiles/{profileId}/summary`, `/summary/categories` | Похідний ресурс: суми за період |
| Графік | `/profiles/{profileId}/charts/daily`, `/charts/monthly` | Похідний ресурс: точки графіка |
| Резервна копія | `/backups` | Службовий ресурс |

Категорії та покупки вкладені в профіль: ізоляція даних (REQ-F-003) забезпечується вже на рівні URI.

## Операції та зв'язок з вимогами

| Метод | URI | Призначення | Вимоги | Коди |
|---|---|---|---|---|
| `GET` | `/profiles` | Список профілів | REQ-F-002 | 200 |
| `POST` | `/profiles` | Створити профіль | REQ-F-001, REQ-F-004 | 201, 409, 422 |
| `GET` | `/profiles/{profileId}` | Отримати профіль | REQ-F-002 | 200, 404 |
| `GET` | `/profiles/{profileId}/categories` | Категорії профілю | REQ-F-020, REQ-F-003 | 200, 404 |
| `POST` | `/profiles/{profileId}/categories` | Створити власну категорію | REQ-F-021 | 201, 404, 409, 422 |
| `PATCH` | `/profiles/{profileId}/categories/{categoryId}` | Перейменувати категорію | REQ-F-022, REQ-F-025 | 200, 404, 409, 422 |
| `DELETE` | `/profiles/{profileId}/categories/{categoryId}` | Видалити категорію | REQ-F-023, REQ-F-024, REQ-F-025 | 204, 404, 409 |
| `GET` | `/profiles/{profileId}/purchases` | Список покупок профілю | REQ-F-012, REQ-F-003 | 200, 400, 404 |
| `POST` | `/profiles/{profileId}/purchases` | Додати покупку | REQ-F-005, REQ-F-006, REQ-F-007, REQ-F-011, REQ-F-013, REQ-F-014, REQ-F-015, REQ-F-017, REQ-F-018, REQ-F-019 | 201, 404, 422 |
| `GET` | `/profiles/{profileId}/purchases/{purchaseId}` | Одна покупка | REQ-F-012, REQ-F-003 | 200, 404 |
| `PATCH` | `/profiles/{profileId}/purchases/{purchaseId}` | Змінити покупку | REQ-F-008, REQ-F-009, REQ-F-013, REQ-F-014, REQ-F-015, REQ-F-016, REQ-F-017, REQ-F-018 | 200, 404, 422 |
| `DELETE` | `/profiles/{profileId}/purchases/{purchaseId}` | Видалити покупку | REQ-F-010, REQ-F-009 | 204, 404 |
| `GET` | `/profiles/{profileId}/purchases/export` | Експорт покупок у CSV | REQ-F-035, REQ-I-003 | 200, 400, 404 |
| `GET` | `/profiles/{profileId}/summary` | Підсумок витрат за період | REQ-F-026, REQ-F-027, REQ-F-028, REQ-F-029, REQ-F-033 | 200, 400, 404 |
| `GET` | `/profiles/{profileId}/summary/categories` | Розбивка витрат за категоріями | REQ-F-030, REQ-F-033 | 200, 400, 404 |
| `GET` | `/profiles/{profileId}/charts/daily` | Дані графіка витрат по днях місяця | REQ-F-031 | 200, 400, 404 |
| `GET` | `/profiles/{profileId}/charts/monthly` | Дані графіка витрат по місяцях року | REQ-F-032 | 200, 400, 404 |
| `POST` | `/backups` | Створити резервну копію бази даних | REQ-F-036 | 201, 500 |

## Зворотна таблиця: вимога → операції

| Вимога | API operations |
|---|---|
| REQ-F-001 | `POST /profiles` |
| REQ-F-002 | `GET /profiles`; `GET /profiles/{profileId}` |
| REQ-F-003 | `GET /profiles/{profileId}/categories`; `GET /profiles/{profileId}/purchases`; `GET /profiles/{profileId}/purchases/{purchaseId}` |
| REQ-F-004 | `POST /profiles` |
| REQ-F-005 | `POST /profiles/{profileId}/purchases` |
| REQ-F-006 | `POST /profiles/{profileId}/purchases` |
| REQ-F-007 | `POST /profiles/{profileId}/purchases` |
| REQ-F-008 | `PATCH /profiles/{profileId}/purchases/{purchaseId}` |
| REQ-F-009 | `PATCH /profiles/{profileId}/purchases/{purchaseId}`; `DELETE /profiles/{profileId}/purchases/{purchaseId}` |
| REQ-F-010 | `DELETE /profiles/{profileId}/purchases/{purchaseId}` |
| REQ-F-011 | `POST /profiles/{profileId}/purchases` |
| REQ-F-012 | `GET /profiles/{profileId}/purchases`; `GET /profiles/{profileId}/purchases/{purchaseId}` |
| REQ-F-013 | `POST /profiles/{profileId}/purchases`; `PATCH /profiles/{profileId}/purchases/{purchaseId}` |
| REQ-F-014 | `POST /profiles/{profileId}/purchases`; `PATCH /profiles/{profileId}/purchases/{purchaseId}` |
| REQ-F-015 | `POST /profiles/{profileId}/purchases`; `PATCH /profiles/{profileId}/purchases/{purchaseId}` |
| REQ-F-016 | `PATCH /profiles/{profileId}/purchases/{purchaseId}` |
| REQ-F-017 | `POST /profiles/{profileId}/purchases`; `PATCH /profiles/{profileId}/purchases/{purchaseId}` |
| REQ-F-018 | `POST /profiles/{profileId}/purchases`; `PATCH /profiles/{profileId}/purchases/{purchaseId}` |
| REQ-F-019 | `POST /profiles/{profileId}/purchases` |
| REQ-F-020 | `GET /profiles/{profileId}/categories` |
| REQ-F-021 | `POST /profiles/{profileId}/categories` |
| REQ-F-022 | `PATCH /profiles/{profileId}/categories/{categoryId}` |
| REQ-F-023 | `DELETE /profiles/{profileId}/categories/{categoryId}` |
| REQ-F-024 | `DELETE /profiles/{profileId}/categories/{categoryId}` |
| REQ-F-025 | `PATCH /profiles/{profileId}/categories/{categoryId}`; `DELETE /profiles/{profileId}/categories/{categoryId}` |
| REQ-F-026 | `GET /profiles/{profileId}/summary` |
| REQ-F-027 | `GET /profiles/{profileId}/summary` |
| REQ-F-028 | `GET /profiles/{profileId}/summary` |
| REQ-F-029 | `GET /profiles/{profileId}/summary` |
| REQ-F-030 | `GET /profiles/{profileId}/summary/categories` |
| REQ-F-031 | `GET /profiles/{profileId}/charts/daily` |
| REQ-F-032 | `GET /profiles/{profileId}/charts/monthly` |
| REQ-F-033 | `GET /profiles/{profileId}/summary`; `GET /profiles/{profileId}/summary/categories` |
| REQ-F-035 | `GET /profiles/{profileId}/purchases/export` |
| REQ-F-036 | `POST /backups` |
| REQ-I-003 | `GET /profiles/{profileId}/purchases/export` |

## Вимоги, які свідомо не виносяться в API

| Вимога | Чому |
|---|---|
| REQ-I-001, REQ-I-002, REQ-I-004 | Стосуються інтерфейсу користувача, а не контракту |
| REQ-F-034, REQ-NF-009…011 | Властивості реалізації; у контракті відображені лише формат сум і коди помилок |
| REQ-NF-001…008 | Вимоги до процесу розробки |
| Видалення профілю | Вимоги немає в SRS, питання ВП-01 відкрите. Операція не додана: нова поведінка оформлюється адендумом |

## Єдина модель помилки

Усі помилки повертають одну структуру `Error`:

```json
{ "error": { "code": "VALIDATION_FAILED",
             "message": "Ціна має бути більшою за нуль.",
             "requirement": "REQ-F-013",
             "details": [ { "field": "unitPrice", "issue": "must be > 0" } ] },
  "traceId": "7f3a1c2e-0000-4000-8000-00000000ff01" }
```

Поле `requirement` вказує ID порушеної вимоги — це дає простежуваність від помилки до специфікації й буде використано в тестах ЛР5.

| Код HTTP | Коли |
|---|---|
| 200 | Успішне читання або зміна |
| 201 | Ресурс створено |
| 204 | Видалено, тіла немає |
| 400 | Некоректні параметри запиту (невідомий `period`) |
| 404 | Ресурсу не існує або він належить іншому профілю |
| 409 | Конфлікт стану: непорожня або службова категорія, дублікат назви |
| 422 | Порушено правило предметної області: ціна ≤ 0, порожня назва, дата в майбутньому |
