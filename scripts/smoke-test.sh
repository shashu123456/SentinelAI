#!/usr/bin/env bash
# SentinelAI — Deployment Smoke Test
# Verifies all services are running and responding correctly.
#
# Usage:
#   ./scripts/smoke-test.sh                    # Test localhost:8000
#   ./scripts/smoke-test.sh https://api.example.com  # Test remote

set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"
PASS=0
FAIL=0

check() {
    local name="$1"
    local url="$2"
    local expected_code="${3:-200}"

    status=$(curl -sf -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
    if [ "$status" = "$expected_code" ]; then
        echo "  ✅ $name (HTTP $status)"
        PASS=$((PASS + 1))
    else
        echo "  ❌ $name (expected $expected_code, got $status)"
        FAIL=$((FAIL + 1))
    fi
}

echo "═══════════════════════════════════════════════════"
echo " SentinelAI — Deployment Smoke Test"
echo " Target: $BASE_URL"
echo "═══════════════════════════════════════════════════"
echo ""

# ── Liveness ───────────────────────────────────────────────────
echo "1. Health Endpoints"
check "Liveness probe"     "$BASE_URL/api/v1/live"
check "Readiness probe"    "$BASE_URL/api/v1/ready"
check "Full health check"  "$BASE_URL/api/v1/health"
check "Legacy health"      "$BASE_URL/health/detailed"
check "Root health"        "$BASE_URL/"
echo ""

# ── API Endpoints (unauthenticated) ───────────────────────────
echo "2. Public Endpoints"
check "OpenAPI docs"       "$BASE_URL/docs"           200
check "Testimonials API"   "$BASE_URL/api/testimonials"
echo ""

# ── Auth Flow ─────────────────────────────────────────────────
echo "3. Authentication Flow"
REGISTER=$(curl -sf -X POST "$BASE_URL/api/auth/register" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"smoke_test_$(date +%s)\",\"email\":\"smoke$(date +%s)@test.com\",\"password\":\"Test1234!\"}" \
    -w "\n%{http_code}" 2>/dev/null || echo "000")
REG_CODE=$(echo "$REGISTER" | tail -1)
if [ "$REG_CODE" = "201" ]; then
    TOKEN=$(echo "$REGISTER" | head -1 | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null || echo "")
    echo "  ✅ User registration (HTTP 201)"
    PASS=$((PASS + 1))

    if [ -n "$TOKEN" ]; then
        ME_STATUS=$(curl -sf -o /dev/null -w "%{http_code}" "$BASE_URL/api/auth/me" -H "Authorization: Bearer $TOKEN" 2>/dev/null || echo "000")
        if [ "$ME_STATUS" = "200" ]; then
            echo "  ✅ Token validation (HTTP 200)"
            PASS=$((PASS + 1))
        else
            echo "  ❌ Token validation (HTTP $ME_STATUS)"
            FAIL=$((FAIL + 1))
        fi
    fi
else
    echo "  ❌ User registration (HTTP $REG_CODE)"
    FAIL=$((FAIL + 1))
fi
echo ""

# ── Metrics ───────────────────────────────────────────────────
echo "4. Observability"
check "Prometheus metrics" "$BASE_URL/metrics"
echo ""

# ── Summary ───────────────────────────────────────────────────
echo "═══════════════════════════════════════════════════"
TOTAL=$((PASS + FAIL))
if [ "$FAIL" -eq 0 ]; then
    echo " ✅ ALL $TOTAL CHECKS PASSED"
    exit 0
else
    echo " ❌ $FAIL/$TOTAL CHECKS FAILED"
    exit 1
fi
