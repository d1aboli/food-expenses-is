# Матриця простежуваності

Версія SRS: 1.0 (базова) плюс адендум ADD-01. Контракт: `spec/api/openapi.yaml` 1.1.0.
Колонки «Тест» і «Код» заповнені за результатами ЛР5; у дужках — кількість тестів
із позначкою `@pytest.mark.requirement` для цієї вимоги.

Ланцюг простежуваності: **вимога → критерій прийняття → BDD-сценарій → тікет →
операція API → тест → код**.

## Базові вимоги (SRS 1.0)

| ID | Коротко | Критерій прийняття | BDD-сценарій | Тікет | API operation | Тест | Код |
|---|---|---|---|---|---|---|---|
| REQ-F-001 | Створення профілю | — | — | FEI-5, FEI-6, FEI-14 | `POST /profiles` | `test_profiles.py` (8) | `services/profiles.py`, `repositories/profiles.py`, `api/routers/profiles.py`, `text.py` |
| REQ-F-002 | Вибір активного профілю | — | Ізоляція профілів | FEI-5, FEI-6, FEI-14 | `GET /profiles`; `GET /profiles/{profileId}` | `test_profiles.py` (3) | `services/profiles.py`, `repositories/profiles.py`, `api/routers/profiles.py`, `text.py` |
| REQ-F-003 | Ізоляція даних профілю | КП REQ-F-003 | Ізоляція профілів | FEI-5, FEI-6, FEI-13, FEI-14 | `GET /profiles/{profileId}/categories`; `GET /profiles/{profileId}/purchases`; `GET /profiles/{profileId}/purchases/{purchaseId}` | `test_categories.py` (3); `test_export.py` (1); `test_profiles.py` (1); `test_purchases.py` (1); `test_summary.py` (1) | `services/profiles.py`, `repositories/profiles.py`, `api/routers/profiles.py`, `text.py` |
| REQ-F-004 | Перший профіль | — | — | FEI-5, FEI-6, FEI-14 | `POST /profiles` | `test_profiles.py` (1) | `services/profiles.py`, `repositories/profiles.py`, `api/routers/profiles.py`, `text.py` |
| REQ-F-005 | Додавання покупки | — | Додавання покупки з кількістю | FEI-9, FEI-10, FEI-14 | `POST /profiles/{profileId}/purchases` | `test_purchases.py` (4) | `services/purchases.py`, `repositories/purchases.py`, `api/routers/purchases.py`, `money.py` |
| REQ-F-006 | Вартість = ціна × кількість | КП REQ-F-006 | Додавання покупки з кількістю | FEI-9, FEI-10, FEI-14, FEI-21 | `POST /profiles/{profileId}/purchases` | `test_money.py` (3); `test_purchases.py` (1) | `services/purchases.py`, `repositories/purchases.py`, `api/routers/purchases.py`, `money.py` |
| REQ-F-007 | Автоматичні дата й час | КП REQ-F-007 | Додавання покупки з кількістю | FEI-9, FEI-10, FEI-14 | `POST /profiles/{profileId}/purchases` | `test_purchases.py` (2) | `services/purchases.py`, `repositories/purchases.py`, `api/routers/purchases.py`, `money.py` |
| REQ-F-008 | Редагування покупки | — | Перерахунок після зміни дати | FEI-9, FEI-10, FEI-14 | `PATCH /profiles/{profileId}/purchases/{purchaseId}` | `test_purchases.py` (3) | `services/purchases.py`, `repositories/purchases.py`, `api/routers/purchases.py`, `money.py` |
| REQ-F-009 | Перерахунок підсумків | КП REQ-F-009 | Перерахунок після зміни дати | FEI-9, FEI-10, FEI-14 | `PATCH /profiles/{profileId}/purchases/{purchaseId}`; `DELETE /profiles/{profileId}/purchases/{purchaseId}` | `test_purchases.py` (1); `test_summary.py` (2) | `services/purchases.py`, `repositories/purchases.py`, `api/routers/purchases.py`, `money.py` |
| REQ-F-010 | Видалення покупки | — | — | FEI-9, FEI-10, FEI-14 | `DELETE /profiles/{profileId}/purchases/{purchaseId}` | `test_purchases.py` (2) | `services/purchases.py`, `repositories/purchases.py`, `api/routers/purchases.py`, `money.py` |
| REQ-F-011 | Дублікати дозволені | — | Дублікати дозволені | FEI-9, FEI-10, FEI-14 | `POST /profiles/{profileId}/purchases` | `test_purchases.py` (1) | `services/purchases.py`, `repositories/purchases.py`, `api/routers/purchases.py`, `money.py` |
| REQ-F-012 | Список покупок за датою | — | — | FEI-9, FEI-10, FEI-14 | `GET /profiles/{profileId}/purchases`; `GET /profiles/{profileId}/purchases/{purchaseId}` | `test_purchases.py` (5) | `services/purchases.py`, `repositories/purchases.py`, `api/routers/purchases.py`, `money.py` |
| REQ-F-013 | Ціна більша за нуль | КП REQ-F-013 | Відмова від'ємної ціни | FEI-11, FEI-12, FEI-14 | `POST /profiles/{profileId}/purchases`; `PATCH /profiles/{profileId}/purchases/{purchaseId}` | `test_validation.py` (3) | `validation.py`, `services/purchases.py` |
| REQ-F-014 | Кількість більша за нуль | — | — | FEI-11, FEI-12, FEI-14 | `POST /profiles/{profileId}/purchases`; `PATCH /profiles/{profileId}/purchases/{purchaseId}` | `test_validation.py` (2) | `validation.py`, `services/purchases.py` |
| REQ-F-015 | Назва не порожня | — | Відмова порожньої назви | FEI-11, FEI-12, FEI-14 | `POST /profiles/{profileId}/purchases`; `PATCH /profiles/{profileId}/purchases/{purchaseId}` | `test_validation.py` (2) | `validation.py`, `services/purchases.py` |
| REQ-F-016 | Дата не в майбутньому | КП REQ-F-016 | Відмова дати в майбутньому | FEI-11, FEI-12, FEI-14 | `PATCH /profiles/{profileId}/purchases/{purchaseId}` | `test_validation.py` (4) | `validation.py`, `services/purchases.py` |
| REQ-F-017 | Формат ціни | — | Точність обчислення вартості | FEI-11, FEI-12, FEI-14 | `POST /profiles/{profileId}/purchases`; `PATCH /profiles/{profileId}/purchases/{purchaseId}` | `test_validation.py` (3) | `validation.py`, `services/purchases.py` |
| REQ-F-018 | Точність кількості | КП REQ-F-018 | — | FEI-11, FEI-12, FEI-14 | `POST /profiles/{profileId}/purchases`; `PATCH /profiles/{profileId}/purchases/{purchaseId}` | `test_money.py` (2); `test_validation.py` (2) | `validation.py`, `services/purchases.py` |
| REQ-F-019 | Повідомлення про помилку | КП REQ-F-013 | Відмова від'ємної ціни | FEI-11, FEI-12, FEI-14 | `POST /profiles/{profileId}/purchases` | `test_infrastructure.py` (1); `test_money.py` (2); `test_validation.py` (1) | `validation.py`, `services/purchases.py` |
| REQ-F-020 | Базові категорії | — | — | FEI-7, FEI-8, FEI-14 | `GET /profiles/{profileId}/categories` | `test_categories.py` (2) | `services/categories.py`, `repositories/categories.py`, `api/routers/categories.py` |
| REQ-F-021 | Власна категорія | — | — | FEI-7, FEI-8, FEI-14 | `POST /profiles/{profileId}/categories` | `test_categories.py` (9) | `services/categories.py`, `repositories/categories.py`, `api/routers/categories.py` |
| REQ-F-022 | Перейменування категорії | — | — | FEI-7, FEI-8, FEI-14 | `PATCH /profiles/{profileId}/categories/{categoryId}` | `test_categories.py` (2); `test_category_deletion.py` (1) | `services/categories.py`, `repositories/categories.py`, `api/routers/categories.py` |
| REQ-F-023 | Заборона видалення непорожньої | КП REQ-F-023 | Видалення непорожньої категорії | FEI-7, FEI-8, FEI-14 | `DELETE /profiles/{profileId}/categories/{categoryId}` | `test_categories.py` (1); `test_category_deletion.py` (2) | `services/categories.py`, `repositories/categories.py`, `api/routers/categories.py` |
| REQ-F-024 | Перенесення в «Інше» | КП REQ-F-024 | Видалення непорожньої категорії | FEI-7, FEI-8, FEI-14 | `DELETE /profiles/{profileId}/categories/{categoryId}` | `test_category_deletion.py` (3) | `services/categories.py`, `repositories/categories.py`, `api/routers/categories.py` |
| REQ-F-025 | «Інше» не видаляється і не перейменовується | КП REQ-F-025 | — | FEI-7, FEI-8, FEI-14 | `PATCH /profiles/{profileId}/categories/{categoryId}`; `DELETE /profiles/{profileId}/categories/{categoryId}` | `test_categories.py` (3) | `services/categories.py`, `repositories/categories.py`, `api/routers/categories.py` |
| REQ-F-026 | Підсумок за день | — | Дублікати дозволені | FEI-15, FEI-16, FEI-22 | `GET /profiles/{profileId}/summary` | `test_summary.py` (2) | `periods.py`, `services/summaries.py`, `services/aggregation.py`, `api/routers/summaries.py` |
| REQ-F-027 | Підсумок за тиждень | КП REQ-F-027 | Межа календарного тижня | FEI-15, FEI-16, FEI-22 | `GET /profiles/{profileId}/summary` | `test_summary.py` (2) | `periods.py`, `services/summaries.py`, `services/aggregation.py`, `api/routers/summaries.py` |
| REQ-F-028 | Підсумок за місяць | — | — | FEI-15, FEI-16, FEI-22 | `GET /profiles/{profileId}/summary` | `test_summary.py` (1) | `periods.py`, `services/summaries.py`, `services/aggregation.py`, `api/routers/summaries.py` |
| REQ-F-029 | Довільний діапазон | КП REQ-F-029 | Довільний діапазон дат | FEI-15, FEI-16, FEI-22 | `GET /profiles/{profileId}/summary` | `test_export.py` (1); `test_summary.py` (4); `test_validation.py` (1) | `periods.py`, `services/summaries.py`, `services/aggregation.py`, `api/routers/summaries.py` |
| REQ-F-030 | Розбивка за категоріями | КП REQ-F-030 | Розбивка за категоріями | FEI-17, FEI-18, FEI-22 | `GET /profiles/{profileId}/summary/categories` | `test_summary.py` (3) | `periods.py`, `services/summaries.py`, `services/aggregation.py`, `api/routers/summaries.py` |
| REQ-F-031 | Графік по днях місяця | КП REQ-F-031 | — | FEI-19, FEI-22 | `GET /profiles/{profileId}/charts/daily` | `test_charts.py` (4) | `periods.py`, `services/summaries.py`, `services/aggregation.py`, `api/routers/summaries.py` |
| REQ-F-032 | Графік по місяцях року | КП REQ-F-032 | — | FEI-19, FEI-22 | `GET /profiles/{profileId}/charts/monthly` | `test_charts.py` (4) | `periods.py`, `services/summaries.py`, `services/aggregation.py`, `api/routers/summaries.py` |
| REQ-F-033 | Порожній період | КП REQ-F-033 | Період без покупок | FEI-15, FEI-16, FEI-22 | `GET /profiles/{profileId}/summary`; `GET /profiles/{profileId}/summary/categories` | `test_charts.py` (1); `test_export.py` (1); `test_summary.py` (2) | `periods.py`, `services/summaries.py`, `services/aggregation.py`, `api/routers/summaries.py` |
| REQ-F-034 | Збереження даних | КП REQ-F-034 | Збереження даних між запусками | FEI-27 | — | `test_infrastructure.py` (2) | `db.py` |
| REQ-F-035 | Експорт у CSV | КП REQ-F-035 | — | FEI-23, FEI-24 | `GET /profiles/{profileId}/purchases/export` | `test_export.py` (5) | `services/exports.py`, `api/routers/purchases.py` |
| REQ-F-036 | Резервна копія бази | — | — | FEI-24 | `POST /backups` | `test_export.py` (4) | `services/backups.py`, `api/routers/backups.py` |
| REQ-NF-001 | Розробка за TDD | КП REQ-NF-001 | — | FEI-2, FEI-14, FEI-22, FEI-31 | — | — | — (процес: історія Git, `logs/test-gate.md`) |
| REQ-NF-002 | Покриття вимог тестами | КП REQ-NF-002 | — | FEI-2, FEI-14, FEI-22, FEI-31 | — | — | `tools/requirement_coverage.py` |
| REQ-NF-003 | Прогін тестів перед комітом | КП REQ-NF-001 | — | FEI-4 | — | — | `tools/run_tests.py` |
| REQ-NF-004 | test: раніше за feat: | КП REQ-NF-001 | — | FEI-2, FEI-14, FEI-22, FEI-31 | — | — | — (процес: історія Git) |
| REQ-NF-005 | Журнал прогону тестів | КП REQ-NF-005 | — | FEI-4 | — | `test_infrastructure.py` (2) | `run_log.py`, `tools/run_tests.py` |
| REQ-NF-006 | Журнал сесії агента | — | — | FEI-2, FEI-14, FEI-22, FEI-31 | — | — | — (процес: `logs/agent-session-03.md`) |
| REQ-NF-007 | Перегляд змін агента | — | — | FEI-2, FEI-14, FEI-22, FEI-31 | — | — | — (процес: позначка `[agent]` у комітах) |
| REQ-NF-008 | Журнал помилок | — | — |  | — | `test_infrastructure.py` (2) | `logging_setup.py`, `api/app.py` |
| REQ-NF-009 | Швидкодія підсумків | КП REQ-NF-009 | — | FEI-20 | — | `test_performance.py` (1) | `repositories/summaries.py`, `db.py` (індекс за датою) |
| REQ-NF-010 | Точність до копійок | КП REQ-NF-010 | Точність обчислення вартості | FEI-21 | — | `test_money.py` (3); `test_purchases.py` (1) | `money.py`, `services/aggregation.py` |
| REQ-NF-011 | Локальне зберігання | — | — | FEI-27 | — | — | `db.py` (транзакції) |
| REQ-NF-012 | Українська та англійська | КП REQ-NF-012 | — | FEI-26 | — | — | — (поза обсягом ЛР5) |
| REQ-NF-013 | Python, FastAPI, SQLite | — | — | FEI-3 | — | — | `api/app.py`, `db.py` |
| REQ-NF-014 | Chart.js | — | — | FEI-19 | — | — | — (поза обсягом ЛР5) |
| REQ-NF-015 | Структура /src і /tests | — | — | FEI-3, FEI-29 | — | — | структура `/src`, `/tests` |
| REQ-I-001 | Вебінтерфейс | — | — | FEI-25 | — | — | — (поза обсягом ЛР5) |
| REQ-I-002 | Вибір профілю | — | Ізоляція профілів | FEI-25 | — | — | — (поза обсягом ЛР5) |
| REQ-I-003 | Формат CSV | — | — | FEI-23 | `GET /profiles/{profileId}/purchases/export` | `test_export.py` (2) | `services/exports.py` |
| REQ-I-004 | Формат дати й часу | — | — | FEI-25 | — | — | — (поза обсягом ЛР5) |

## Вимоги адендуму ADD-01

| ID | Коротко | Критерій прийняття | BDD-сценарій | Тікет | API operation | Тест | Код |
|---|---|---|---|---|---|---|---|
| REQ-A-001 | Встановлення місячного бюджету | КП REQ-A-001 | — | FEI-32 | `POST /profiles/{profileId}/budgets` | `test_budgets.py` (5) | `services/budgets.py`, `repositories/budgets.py`, `api/routers/budgets.py` |
| REQ-A-002 | Сума бюджету більша за нуль | КП REQ-A-002 | — | FEI-32 | `POST /profiles/{profileId}/budgets`; `PATCH /profiles/{profileId}/budgets/{budgetId}` | `test_budgets.py` (2) | `services/budgets.py`, `repositories/budgets.py`, `api/routers/budgets.py` |
| REQ-A-003 | Один бюджет на категорію | КП REQ-A-003 | — | FEI-32 | `POST /profiles/{profileId}/budgets` | `test_budgets.py` (1) | `services/budgets.py`, `repositories/budgets.py`, `api/routers/budgets.py` |
| REQ-A-004 | Витрати й залишок за місяць | КП REQ-A-004 | — | FEI-32 | `GET /profiles/{profileId}/budgets` | `test_budgets.py` (4) | `services/budgets.py`, `repositories/budgets.py`, `api/routers/budgets.py` |
| REQ-A-005 | Позначка перевищення | КП REQ-A-005 | — | FEI-32 | `GET /profiles/{profileId}/budgets` | `test_budgets.py` (2) | `services/budgets.py`, `repositories/budgets.py`, `api/routers/budgets.py` |
| REQ-A-006 | Зміна суми бюджету | КП REQ-A-006 | — | FEI-32 | `PATCH /profiles/{profileId}/budgets/{budgetId}` | `test_budgets.py` (2) | `services/budgets.py`, `repositories/budgets.py`, `api/routers/budgets.py` |
| REQ-A-007 | Видалення бюджету | КП REQ-A-007 | — | FEI-32 | `DELETE /profiles/{profileId}/budgets/{budgetId}` | `test_budgets.py` (2) | `services/budgets.py`, `repositories/budgets.py`, `api/routers/budgets.py` |
| REQ-A-008 | Видалення бюджету з категорією | КП REQ-A-008 | — | FEI-32 | `DELETE /profiles/{profileId}/categories/{categoryId}` | `test_budgets.py` (1) | `services/budgets.py`, `repositories/budgets.py`, `api/routers/budgets.py` |
| REQ-A-009 | Ізоляція бюджетів за профілями | КП REQ-A-009 | — | FEI-32 | `GET /profiles/{profileId}/budgets` | `test_budgets.py` (2) | `services/budgets.py`, `repositories/budgets.py`, `api/routers/budgets.py` |

## Вимоги поза обсягом ЛР5

Завдання ЛР5 — серверна реалізація REST API, тому вимоги рівня інтерфейсу
користувача свідомо не реалізовані. Вони лишаються в матриці, щоб було видно,
що про них не забули.

| ID | Зміст | Коли реалізується |
|---|---|---|
| REQ-I-001 | Вебсторінка з формою, списком, періодом, таблицею та графіком | наступна робота |
| REQ-I-002 | Вибір активного профілю в інтерфейсі | наступна робота |
| REQ-I-004 | Формати дати й часу в інтерфейсі | наступна робота |
| REQ-NF-012 | Файли перекладів для української та англійської | наступна робота |
| REQ-NF-014 | Побудова графіків бібліотекою Chart.js у браузері | наступна робота |

## Відкриті питання

| ID | Питання | Звідки | Статус |
|---|---|---|---|
| ВП-01 | Чи потрібне видалення профілю разом з усіма його даними | ЛР2 | відкрите; операції немає в контракті, не реалізовано |
| ВП-02 | Контракт не описує тіла відповіді для непередбаченої помилки сервера | ЛР5, етап 0 | відкрите; такі помилки лише пишуться в журнал |
| ВП-03 | REQ-F-017 дозволяє ціле число, схема `Money` вимагає два знаки після коми | ЛР5, TEST-GATE 4 | відкрите; підтверджено валідацією людиною |
| ВП-04 | Чи потрібні різні суми бюджету для різних місяців | адендум ADD-01 | відкрите |
| ВП-05 | Чи має сенс бюджет для службової категорії «Інше» | адендум ADD-01 | відкрите |
| ВП-06 | Чи має експорт CSV містити BOM, щоб Excel читав українські назви | ЛР5, валідація | відкрите; потребує адендуму |

## Суперечності між артефактами, розв'язані тлумаченням

| Артефакти | Суть | Рішення |
|---|---|---|
| КП REQ-F-031 і КП REQ-F-033 | один критерій вимагає стовпчик на кожен день місяця, другий — порожній графік за місяць без покупок | точок стільки, скільки днів у місяці; «порожній» означає, що жоден стовпчик не піднімається над нулем; закріплено тестом |
| SRS і контракт | базові категорії у SRS з малої літери, у прикладах контракту — з великої | реалізовано за контрактом як за зовнішнім інтерфейсом; редакційне уточнення до SRS |
