#!/usr/bin/env bash
# ==========================================
# Kairo Health & Readiness Probe Script
# Queries live, ready, and version endpoints
# ==========================================
set -euo pipefail

TARGET_URL="${1:-${KAIRO_HOST_URL:-http://localhost:8000}}"

echo "=========================================="
echo "Kairo Healthcheck: ${TARGET_URL}"
echo "=========================================="

# 1. Liveness Probe
echo "[+] Checking Liveness (${TARGET_URL}/health/live)..."
LIVE_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "${TARGET_URL}/health/live" || echo "000")
if [ "$LIVE_CODE" -eq 200 ]; then
  echo "    ✓ Liveness Probe PASSED (HTTP 200)"
else
  echo "    ✗ Liveness Probe FAILED (HTTP ${LIVE_CODE})" >&2
  exit 1
fi

# 2. Readiness Probe
echo "[+] Checking Readiness (${TARGET_URL}/health/ready)..."
READY_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "${TARGET_URL}/health/ready" || echo "000")
if [ "$READY_CODE" -eq 200 ]; then
  echo "    ✓ Readiness Probe PASSED (HTTP 200)"
else
  echo "    ✗ Readiness Probe FAILED (HTTP ${READY_CODE})" >&2
  READY_BODY=$(curl -s --max-time 5 "${TARGET_URL}/health/ready" || echo "")
  echo "    Details: ${READY_BODY}" >&2
  exit 1
fi

# 3. Version Metadata
echo "[+] Checking Version Metadata (${TARGET_URL}/health/version)..."
VERSION_RESPONSE=$(curl -s --max-time 5 "${TARGET_URL}/health/version" || echo "")
if [ -n "$VERSION_RESPONSE" ]; then
  echo "    ✓ Version info: ${VERSION_RESPONSE}"
else
  echo "    ✗ Version check returned empty response." >&2
  exit 1
fi

echo "=========================================="
echo "All Kairo health checks PASSED successfully."
echo "=========================================="
exit 0
