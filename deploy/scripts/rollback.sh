#!/usr/bin/env bash
# ==========================================
# Kairo Emergency Rollback Script
# Rolls back application container safely without destructive DB downgrades
# ==========================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

TARGET_TAG="${1:-${PREVIOUS_IMAGE_TAG:-}}"

echo "=========================================="
echo "Kairo Emergency Application Rollback"
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "=========================================="

# Critical Safety Notice
cat << 'WARN'
> [!WARNING]
> CRITICAL DATABASE SAFETY NOTICE:
> This rollback script restores previous application container code.
> It DOES NOT automatically downgrade database migrations.
> Automatically downgrading database schemas in production risks catastrophic data loss.
> Kairo adheres to backward-compatible expand/contract database migration patterns.
WARN

if [ -z "$TARGET_TAG" ]; then
  echo "[-] Usage: $0 <PREVIOUS_IMAGE_TAG_OR_GIT_SHA>" >&2
  echo "    Example: $0 v0.4.9" >&2
  echo "    Example: $0 sha-9a3b8c7" >&2
  exit 1
fi

echo "[+] Rollback target image/tag: ${TARGET_TAG}"

# 1. Rollback Container Services
if command -v docker &> /dev/null; then
  echo "[+] Re-pointing service image to: ${TARGET_TAG}..."
  export KAIRO_IMAGE_TAG="${TARGET_TAG}"
  if [ -f "${ROOT_DIR}/docker-compose.yml" ]; then
    docker compose -f "${ROOT_DIR}/docker-compose.yml" up -d --remove-orphans api worker
  fi
else
  echo "[-] Docker command not found. Please redeploy target tag '${TARGET_TAG}' via your container orchestrator." >&2
fi

# 2. Verify Health of Rolled Back Application
echo "[+] Verifying rolled back service health..."
TARGET_URL="${KAIRO_HOST_URL:-http://localhost:8000}"
sleep 3

if bash "${SCRIPT_DIR}/healthcheck.sh" "${TARGET_URL}"; then
  echo "=========================================="
  echo "[+] Rollback completed successfully!"
  echo "    Current version: $(curl -s "${TARGET_URL}/health/version" 2>/dev/null || echo "N/A")"
  echo "=========================================="
  exit 0
else
  echo "[-] Rollback verification FAILED. Check container logs immediately." >&2
  exit 1
fi
