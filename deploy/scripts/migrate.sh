#!/usr/bin/env bash
# ==========================================
# Kairo Production Database Migration Script
# Runs Alembic migrations explicitly with safe error handling
# ==========================================
set -euo pipefail

echo "=========================================="
echo "Kairo Database Migration Engine"
echo "=========================================="

# 1. Environment Validation
if [ -z "${DATABASE_URL:-}" ]; then
  echo "[-] ERROR: DATABASE_URL environment variable is not set." >&2
  exit 1
fi

# Sanitize database URL for logging (mask password)
MASKED_DB_URL=$(echo "$DATABASE_URL" | sed -E 's/:([^@]+)@/:****@/')
echo "[+] Target Database: ${MASKED_DB_URL}"

# 2. Check Alembic CLI availability
if ! command -v alembic &> /dev/null; then
  if command -v python &> /dev/null && python -m alembic --help &> /dev/null; then
    ALEMBIC_CMD="python -m alembic"
  else
    echo "[-] ERROR: Alembic is not installed or not found in PATH." >&2
    exit 1
  fi
else
  ALEMBIC_CMD="alembic"
fi

# 3. Verify Database Connectivity Before Migrating
echo "[+] Validating database connectivity..."
if command -v python &> /dev/null; then
  python - << 'EOF'
import os, sys
from sqlalchemy import create_engine, text
url = os.environ.get("DATABASE_URL", "")
# Strip async driver prefix if needed for sync check
sync_url = url.replace("postgresql+asyncpg://", "postgresql://").replace("sqlite+aiosqlite://", "sqlite://")
try:
    engine = create_engine(sync_url, pool_pre_ping=True, connect_args={"connect_timeout": 5} if "sqlite" not in sync_url else {})
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("[+] Database connectivity confirmed.")
except Exception as e:
    print(f"[-] Database connectivity check failed: {e}", file=sys.stderr)
    sys.exit(1)
EOF
fi

# 4. Execute Alembic Migration
echo "[+] Executing: ${ALEMBIC_CMD} upgrade head"
if $ALEMBIC_CMD upgrade head; then
  echo "[+] Database migrations applied successfully."
  exit 0
else
  echo "[-] ERROR: Database migration failed. Aborting deployment." >&2
  exit 1
fi
