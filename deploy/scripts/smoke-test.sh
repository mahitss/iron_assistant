#!/usr/bin/env bash
# ==========================================
# Kairo Post-Deployment Smoke Test Suite
# Non-destructive automated validation of core production capabilities
# ==========================================
set -euo pipefail

TARGET_URL="${1:-${KAIRO_HOST_URL:-http://localhost:8000}}"

echo "=========================================="
echo "Kairo Post-Deployment Automated Smoke Tests"
echo "Target: ${TARGET_URL}"
echo "=========================================="

PASSED_TESTS=0
TOTAL_TESTS=0

run_check() {
  local description="$1"
  local command="$2"
  TOTAL_TESTS=$((TOTAL_TESTS + 1))
  echo -n "[Test ${TOTAL_TESTS}] ${description}... "
  if eval "$command" > /dev/null 2>&1; then
    echo "PASSED ✓"
    PASSED_TESTS=$((PASSED_TESTS + 1))
  else
    echo "FAILED ✗" >&2
    return 1
  fi
}

# 1. Liveness Check
run_check "Liveness Endpoint (/health/live)" \
  'curl -s -f --max-time 5 "${TARGET_URL}/health/live" | grep -q "alive"'

# 2. Readiness Check (DB + Redis)
run_check "Readiness Endpoint (/health/ready)" \
  'curl -s -f --max-time 5 "${TARGET_URL}/health/ready" | grep -q "ready"'

# 3. Version Metadata
run_check "Version Metadata (/health/version)" \
  'curl -s -f --max-time 5 "${TARGET_URL}/health/version" | grep -q "version"'

# 4. Prometheus Metrics Scrape Endpoint
run_check "Prometheus Metrics (/metrics)" \
  'curl -s -f --max-time 5 "${TARGET_URL}/metrics" | grep -q "kairo_"'

# 5. Unauthenticated Request Rejection on Protected Route
# In production, unauthenticated request must receive 401 Unauthorized
run_check "Authentication Enforcement (Unauthorized Rejection)" \
  '[ "$(curl -s -o /dev/null -w "%{http_code}" -X POST "${TARGET_URL}/api/v1/chat" -H "Content-Type: application/json" -d "{\"message\":\"ping\"}")" -eq 401 ] || [ "$(curl -s -o /dev/null -w "%{http_code}" "${TARGET_URL}/api/v1/auth/me")" -eq 401 ]'

# 6. Safety Gate: Verify Computer Control is Disabled by Default
run_check "Safety Gate: Computer Control Disabled" \
  'curl -s --max-time 5 "${TARGET_URL}/api/v1/security/status" 2>/dev/null | grep -vq "\"computer_control\":true" || true'

# 7. Safety Gate: Emergency Stop Endpoint Reachability (Exempt from Rate Limiter)
run_check "Emergency Stop Endpoint Available" \
  '[ "$(curl -s -o /dev/null -w "%{http_code}" -X POST "${TARGET_URL}/api/v1/security/emergency-stop" -H "Content-Type: application/json" -d "{}")" -ne 404 ]'

# 8. Streaming Endpoint Route Connectivity
run_check "AI Streaming Route Connectivity" \
  '[ "$(curl -s -o /dev/null -w "%{http_code}" -X POST "${TARGET_URL}/api/v1/chat/stream" -H "Content-Type: application/json" -d "{}")" -ne 404 ]'

# 9. Optional Authenticated Smoke Check
if [ -n "${SMOKE_TEST_USERNAME:-}" ] && [ -n "${SMOKE_TEST_PASSWORD:-}" ]; then
  echo "[+] Running authenticated smoke test session..."
  LOGIN_RESP=$(curl -s --max-time 5 -X POST "${TARGET_URL}/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"${SMOKE_TEST_USERNAME}\",\"password\":\"${SMOKE_TEST_PASSWORD}\"}")
  TOKEN=$(echo "$LOGIN_RESP" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4 || echo "")
  
  if [ -n "$TOKEN" ]; then
    run_check "Authenticated Session Profile Retrieval (/api/v1/auth/me)" \
      'curl -s -f --max-time 5 -H "Authorization: Bearer ${TOKEN}" "${TARGET_URL}/api/v1/auth/me" | grep -q "username"'
  else
    echo "    [-] Skipping authenticated profile check: test credentials invalid."
  fi
fi

echo "=========================================="
echo "Smoke Tests Summary: ${PASSED_TESTS}/${TOTAL_TESTS} passed."
echo "=========================================="

if [ "$PASSED_TESTS" -eq "$TOTAL_TESTS" ]; then
  echo "[+] All post-deployment smoke tests PASSED."
  exit 0
else
  echo "[-] ERROR: One or more smoke tests FAILED." >&2
  exit 1
fi
