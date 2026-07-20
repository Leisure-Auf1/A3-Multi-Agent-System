#!/bin/bash
# scripts/verify-release.sh — Release Candidate Verification
# Usage: bash scripts/verify-release.sh [API_URL]
# Default: http://localhost:8000

set -e

API="${1:-http://localhost:8000}"
PASS=0
FAIL=0

green() { echo -e "\033[32m  ✓ $1\033[0m"; PASS=$((PASS + 1)); }
red()   { echo -e "\033[31m  ✗ $1\033[0m"; FAIL=$((FAIL + 1)); }
section() { echo ""; echo "── [$1] $2 ──"; }

section "1" "Health Check"
if curl -sf "$API/health" > /dev/null 2>&1; then
    green "GET /health → 200"
else
    red "GET /health → FAILED (is the API running?)"
    exit 1
fi

section "2" "Authentication"
EMAIL="rc_verify_$(date +%s)@test.local"
PASSWD="rc_secret_42"
T1=$(mktemp)
T2=$(mktemp)

# Register
HTTP=$(curl -s -o "$T1" -w "%{http_code}" -X POST "$API/api/v2/auth/register" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWD\",\"display_name\":\"RC Verify\"}")
if [ "$HTTP" = "201" ]; then
    green "POST /auth/register → 201"
    TOKEN=$(python3 -c "import json;print(json.load(open('$T1'))['token'])" 2>/dev/null)
else
    red "POST /auth/register → $HTTP"
    TOKEN=""
fi

if [ -n "$TOKEN" ]; then
    # Login
    HTTP=$(curl -s -o "$T2" -w "%{http_code}" -X POST "$API/api/v2/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWD\"}")
    if [ "$HTTP" = "200" ]; then
        green "POST /auth/login → 200"
    else
        red "POST /auth/login → $HTTP"
    fi

    # Me
    HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$API/api/v2/auth/me" \
        -H "Authorization: Bearer $TOKEN")
    [ "$HTTP" = "200" ] && green "GET /auth/me → 200" || red "GET /auth/me → $HTTP"

    section "3" "Profile"
    HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API/api/v2/profile/assess" \
        -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
        -d '{"text":"Python developer learning AI systems"}')
    [ "$HTTP" = "200" ] && green "POST /profile/assess → 200" || red "POST /profile/assess → $HTTP"

    HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$API/api/v2/profile" \
        -H "Authorization: Bearer $TOKEN")
    [ "$HTTP" = "200" ] && green "GET /profile → 200" || red "GET /profile → $HTTP"

    section "4" "Learning Pipeline"
    RUN_RESULT=$(curl -s -X POST "$API/api/v2/learning/run" \
        -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
        -d '{"goal":"Learn Python async programming patterns"}')
    if echo "$RUN_RESULT" | python3 -c "import sys,json;d=json.load(sys.stdin);assert d['status']=='success'" 2>/dev/null; then
        ARTIFACTS=$(echo "$RUN_RESULT" | python3 -c "import sys,json;print(len(json.load(sys.stdin)['artifacts_saved']))")
        green "POST /learning/run → success ($ARTIFACTS artifacts)"
    else
        red "POST /learning/run → FAILED"
    fi

    HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$API/api/v2/learning/history" \
        -H "Authorization: Bearer $TOKEN")
    [ "$HTTP" = "200" ] && green "GET /learning/history → 200" || red "GET /learning/history → $HTTP"

    section "5" "Security"
    HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API/api/v2/learning/run" \
        -H "Content-Type: application/json" -d '{"goal":"Test"}')
    [ "$HTTP" = "401" ] && green "Unauthenticated → 401 (blocked)" || red "Unauthenticated → $HTTP (expected 401)"

    section "6" "Logout"
    HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API/api/v2/auth/logout" \
        -H "Authorization: Bearer $TOKEN")
    [ "$HTTP" = "200" ] && green "POST /auth/logout → 200" || red "POST /auth/logout → $HTTP"
fi

rm -f "$T1" "$T2"

echo ""
echo "============================================"
echo "  Results: $PASS passed, $FAIL failed"
echo "============================================"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
