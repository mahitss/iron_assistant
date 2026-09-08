#!/usr/bin/env bash
# ==========================================
# Kairo Production Deployment Script
# Automates pre-flight validation, migrations, container rollout, and smoke testing
# ==========================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "=========================================="
echo "Starting Kairo Production Deployment"
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "=========================================="

# 1. Validate Required Environment Variables
echo "[+] Validating deployment environment variables..."
REQUIRED_VARS=("ENVIRONMENT" "DATABASE_URL" "AUTH_SECRET_KEY")
for var in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!var:-}" ]; then
    echo "[-] ERROR: Required environment variable '${var}' is not set." >&2
    exit 1
  fi
done

if [ "${ENVIRONMENT}" = "production" ]; then
  if [ "${#AUTH_SECRET_KEY}" -lt 32 ]; then
    echo "[-] ERROR: AUTH_SECRET_KEY must have at least 32 characters in production." >&2
    exit 1
  fi
fi

# 2. Run Database Migrations Before Routing Traffic
echo "[+] Step 1/4: Running database migrations..."
if bash "${SCRIPT_DIR}/migrate.sh"; then
  echo "    ✓ Database migrations successfully applied."
else
  echo "[-] ERROR: Database migration failed. Aborting deployment." >&2
  exit 1
fi

# 3. Rollout Application Containers
echo "[+] Step 2/4: Deploying application containers..."
if command -v docker &> /dev/null; then
  if [ -f "${ROOT_DIR}/docker-compose.yml" ]; then
    echo "    Recreating service containers via Docker Compose..."
    docker compose -f "${ROOT_DIR}/docker-compose.yml" up -d --remove-orphans api worker
  fi
fi

# 4. Wait for Healthcheck to Pass
echo "[+] Step 3/4: Awaiting application readiness..."
TARGET_URL="${KAIRO_HOST_URL:-http://localhost:8000}"
MAX_RETRIES=30
RETRY_COUNT=0
HEALTHY=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
  if bash "${SCRIPT_DIR}/healthcheck.sh" "${TARGET_URL}" > /dev/null 2>&1; then
    HEALTHY=true
    break
  fi
  RETRY_COUNT=$((RETRY_COUNT + 1))
  echo "    Waiting for service readiness (${RETRY_COUNT}/${MAX_RETRIES})..."
  sleep 2
done

if [ "$HEALTHY" = false ]; then
  echo "[-] ERROR: Application failed health readiness checks after deployment." >&2
  echo "[-] Consider running rollback script: bash deploy/scripts/rollback.sh" >&2
  exit 1
fi

# 5. Run Post-Deployment Smoke Tests
echo "[+] Step 4/4: Executing post-deployment smoke test suite..."
if bash "${SCRIPT_DIR}/smoke-test.sh" "${TARGET_URL}"; then
  echo "    ✓ Smoke tests PASSED."
else
  echo "[-] ERROR: Smoke tests failed. Deployment requires immediate investigation." >&2
  exit 1
fi

echo "=========================================="
echo "Kairo Deployment Completed Successfully!"
echo "Version: $(curl -s "${TARGET_URL}/health/version" 2>/dev/null || echo "N/A")"
echo "=========================================="
exit 0
