#!/bin/bash
# Integration test — verifies both production endpoints are reachable and auth works.
# Run: bash tests/test_integration.sh
# Requires: curl, a valid znl_ API key (or beta key)

set -uo pipefail

WORKER="https://zdrive-neuro-lens.kwame-laryea.workers.dev"
FLYIO="https://zdrive-neuro-lens.fly.dev"
KEY="znl_integration_test_key"
PASS=0
FAIL=0

check() {
  local desc="$1" expected="$2" actual="$3"
  if [ "$expected" = "$actual" ]; then
    echo "  ✓ $desc"
    PASS=$((PASS + 1))
  else
    echo "  ✗ $desc (expected $expected, got $actual)"
    FAIL=$((FAIL + 1))
  fi
}

echo "== CF Worker =="

# Health
code=$(curl -s -o /dev/null -w "%{http_code}" "$WORKER/health")
check "health returns 200" "200" "$code"

# No auth → 401
code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$WORKER/analyze" \
  -H "Content-Type: application/json" \
  -d '{"text":"test","mode":"fast"}')
check "no auth → 401" "401" "$code"

# Short key → 401
code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$WORKER/analyze" \
  -H "Content-Type: application/json" \
  -H "X-ZDrive-API-Key: znl_short" \
  -d '{"text":"test","mode":"fast"}')
check "short key → 401" "401" "$code"

# Wrong prefix → 401
code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$WORKER/analyze" \
  -H "Content-Type: application/json" \
  -H "X-ZDrive-API-Key: sk_random_key_1234567890" \
  -d '{"text":"test","mode":"fast"}')
check "wrong prefix → 401" "401" "$code"

# Valid key → 200 (actual LLM call)
code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$WORKER/analyze" \
  -H "Content-Type: application/json" \
  -H "X-ZDrive-API-Key: $KEY" \
  -d '{"text":"Breaking news: major policy change announced today. Officials warn of dire consequences.","mode":"fast"}' \
  --max-time 30)
check "valid key fast scan → 200" "200" "$code"

# Response shape check
body=$(curl -s -X POST "$WORKER/analyze" \
  -H "Content-Type: application/json" \
  -H "X-ZDrive-API-Key: $KEY" \
  -d '{"text":"A balanced report on recent developments in technology and science.","mode":"fast"}' \
  --max-time 30)
has_mi=$(echo "$body" | python3 -c "import sys,json; d=json.load(sys.stdin); print('yes' if 'manipulation_index' in d and 'limbic_score' in d and 'pfc_score' in d else 'no')" 2>/dev/null || echo "no")
check "response has required fields" "yes" "$has_mi"

echo ""
echo "== Fly.io Backend =="

# Health (no auth needed)
code=$(curl -s -o /dev/null -w "%{http_code}" "$FLYIO/health")
check "health returns 200" "200" "$code"

# No auth → 401
code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$FLYIO/analyze" \
  -H "Content-Type: application/json" \
  -d '{"text":"test","mode":"fast"}')
check "no auth → 401" "401" "$code"

# Valid key → 200
code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$FLYIO/analyze" \
  -H "Content-Type: application/json" \
  -H "X-ZDrive-API-Key: $KEY" \
  -d '{"text":"Test authenticated access to Fly.io backend.","mode":"fast"}' \
  --max-time 30)
check "valid key fast scan → 200" "200" "$code"

echo ""
echo "========================================"
echo "Results: $PASS passed, $FAIL failed"
if [ "$FAIL" -eq 0 ]; then exit 0; else exit 1; fi
