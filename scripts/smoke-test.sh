#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
API="${BASE_URL}/api/v1"

echo "[1/5] Health check"
HEALTH="$(curl -sS "${BASE_URL}/health")"
echo "$HEALTH"

echo "[2/5] Register test user (idempotency not guaranteed)"
REGISTER_JSON="$(curl -sS -X POST "${API}/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username":"smoke_user",
    "email":"smoke_user@example.com",
    "password":"pass1234",
    "hotel_name":"Smoke Hotel",
    "hotel_location":{"lat":31.23,"lng":121.47}
  }' || true)"
echo "$REGISTER_JSON"

echo "[3/5] Login"
LOGIN_JSON="$(curl -sS -X POST "${API}/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"smoke_user","password":"pass1234"}')"
echo "$LOGIN_JSON"
TOKEN="$(echo "$LOGIN_JSON" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("data",{}).get("access_token",""))')"
if [[ -z "${TOKEN}" ]]; then
  echo "ERROR: login token is empty"
  exit 1
fi

echo "[4/5] Create competitor"
curl -sS -X POST "${API}/competitors" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name":"Smoke Competitor",
    "platform":"meituan",
    "external_id":"smoke-001",
    "room_types":["豪华大床房"]
  }' || true

echo "[5/5] Fetch notifications (page=1,page_size=5)"
curl -sS "${API}/notifications?page=1&page_size=5" \
  -H "Authorization: Bearer ${TOKEN}"

echo
echo "Smoke test completed."
