#!/usr/bin/env bash
# Перевірка контракту через mock API (Prism). Сервер: prism mock openapi.yaml -p 4010
BASE=http://127.0.0.1:4010
P=018f2b10-0000-7000-8000-000000000001
CAT=11111111-0000-4000-8000-000000000001
CAT_NAPOI=11111111-0000-4000-8000-000000000004
CAT_INSHE=11111111-0000-4000-8000-000000000005
PUR=22222222-0000-4000-8000-000000000002

hdr(){ printf '\n=== %s ===\n' "$1"; }
call(){ # метод URL [дані] [prefer]
  local m=$1 u=$2 d=$3 pref=$4
  local args=(-s -w '\nHTTP %{http_code}\n' -X "$m" "$BASE$u" -H 'Accept: application/json')
  [ -n "$d" ] && args+=(-H 'Content-Type: application/json' -d "$d")
  [ -n "$pref" ] && args+=(-H "Prefer: $pref")
  curl "${args[@]}"
}

echo '################  ПОЗИТИВНІ СЦЕНАРІЇ  ################'
hdr 'P1. Список профілів (REQ-F-002)'
call GET /profiles

hdr 'P2. Створення профілю (REQ-F-001)'
call POST /profiles '{"name":"Ілля"}' 'code=201'

hdr 'P3. Базові категорії профілю (REQ-F-020, REQ-F-003)'
call GET "/profiles/$P/categories"

hdr 'P4. Додавання покупки на вагу: 80.00 x 0.7 = 56.00 (REQ-F-005, REQ-F-006, REQ-F-007)'
call POST "/profiles/$P/purchases" '{"name":"Яблука","categoryId":"'$CAT'","unitPrice":"80.00","quantity":"0.7"}' 'code=201'

hdr 'P5. Список покупок від новіших до старіших (REQ-F-012)'
call GET "/profiles/$P/purchases?from=2026-10-01&to=2026-10-31"

hdr 'P6. Підсумок за календарний тиждень: 100.00 + 50.00 = 150.00 (REQ-F-027)'
call GET "/profiles/$P/summary?period=week&date=2026-10-05" '' 'code=200,example=week'

hdr 'P7. Порожній місяць повертає 0.00 (REQ-F-033)'
call GET "/profiles/$P/summary?period=month&date=2026-03-15" '' 'code=200,example=emptyMonth'

hdr 'P8. Розбивка за категоріями, сума часток 100% (REQ-F-030)'
call GET "/profiles/$P/summary/categories?period=month&date=2026-10-15"

hdr 'P9. Дані графіка по днях місяця (REQ-F-031)'
call GET "/profiles/$P/charts/daily?month=2026-10"

hdr 'P10. Перенесення покупки на інший день, перерахунок підсумків (REQ-F-008, REQ-F-009)'
call PATCH "/profiles/$P/purchases/$PUR" '{"occurredAt":"2026-10-04T19:00:00+03:00"}'

hdr 'P11. Видалення покупки (REQ-F-010)'
call DELETE "/profiles/$P/purchases/$PUR" '' 'code=204'

hdr 'P12. Експорт у CSV (REQ-F-035, REQ-I-003)'
curl -s -w '\nHTTP %{http_code}\n' "$BASE/profiles/$P/purchases/export?from=2026-10-01&to=2026-10-31" -H 'Accept: text/csv'

echo
echo '################  НЕГАТИВНІ СЦЕНАРІЇ  ################'
hdr 'N1. Ціна дорівнює нулю (REQ-F-013) -> 422'
call POST "/profiles/$P/purchases" '{"name":"Кава","categoryId":"'$CAT'","unitPrice":"0.00","quantity":"1"}' 'code=422,example=priceNotPositive'

hdr 'N2. Порожня назва покупки (REQ-F-015) -> 422'
call POST "/profiles/$P/purchases" '{"name":"","categoryId":"'$CAT'","unitPrice":"20.00","quantity":"1"}' 'code=422,example=emptyName'

hdr 'N3. Дата й час у майбутньому (REQ-F-016) -> 422'
call PATCH "/profiles/$P/purchases/$PUR" '{"occurredAt":"2030-01-01T10:00:00+02:00"}' 'code=422,example=futureDate'

hdr 'N4. Кількість із чотирма знаками після коми (REQ-F-018) -> 422'
call POST "/profiles/$P/purchases" '{"name":"Цукерки","categoryId":"'$CAT'","unitPrice":"150.00","quantity":"0.1255"}' 'code=422,example=quantityPrecision'

hdr 'N5. Видалення непорожньої категорії без confirm (REQ-F-023) -> 409'
call DELETE "/profiles/$P/categories/$CAT_NAPOI" '' 'code=409,example=notEmpty'

hdr 'N6. Видалення службової категорії «Інше» (REQ-F-025) -> 409'
call DELETE "/profiles/$P/categories/$CAT_INSHE" '' 'code=409,example=systemCategory'

hdr 'N7. Неіснуюча покупка (REQ-F-012) -> 404'
call GET "/profiles/$P/purchases/99999999-0000-4000-8000-000000000000" '' 'code=404,example=purchaseNotFound'

hdr 'N8. Неіснуючий профіль, спроба доступу до чужих даних (REQ-F-003) -> 404'
call GET "/profiles/99999999-0000-4000-8000-000000000000/categories" '' 'code=404,example=profileNotFound'

hdr 'N9. Невідоме значення period (REQ-F-026) -> 400'
call GET "/profiles/$P/summary?period=quarter" '' 'code=400,example=invalidPeriod'

hdr 'N10. Дублікат назви категорії (REQ-F-021) -> 409'
call POST "/profiles/$P/categories" '{"name":"Продукти"}' 'code=409,example=nameTaken'
