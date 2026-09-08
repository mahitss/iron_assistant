# Kairo Rollback, Recovery & Schema Evolution Strategy

This document establishes the official rollback protocol and schema management guidelines for Kairo production deployments.

> [!CRITICAL]
> **Database Safety Notice:**
> Application container rollback is fast and safe. Database migration downgrades are inherently dangerous and MUST NOT be executed automatically. Automatically executing `alembic downgrade` in production risks irrecoverable data loss.
> Kairo mandates backward-compatible **expand/contract schema evolution**.

---

## 1. Fast Application Rollback Protocol

When a production defect or fatal regression is detected, roll back the application container image immediately to the last known stable Git SHA or image tag.

### Step 1: Execute Container Rollback
```bash
# Invoke the emergency rollback script with the target previous image tag or Git SHA
bash deploy/scripts/rollback.sh sha-9a3b8c7
```

### Step 2: Verify Health
The rollback script automatically validates:
- `GET /health/live` returns HTTP 200 (`{"status":"alive"}`)
- `GET /health/ready` returns HTTP 200 (`{"status":"ready"}`)
- `GET /health/version` confirms the restored application version and Git SHA

### Step 3: Run Post-Rollback Smoke Tests
```bash
bash deploy/scripts/smoke-test.sh https://api.example.com
```

---

## 2. Safe Database Evolution: The Expand / Contract Pattern

To ensure that any application version can be rolled back safely without database breakage, all schema changes must follow the two-phase **Expand / Contract pattern**:

```text
Phase 1: EXPAND (Deploy first)
   ├── Add new optional / nullable columns
   ├── Add new tables or non-blocking indexes
   └── Both old and new application code function seamlessly

Phase 2: CODE MIGRATION (Deploy next)
   ├── Roll out application code reading/writing new columns
   └── Application can be safely rolled back at any time

Phase 3: CONTRACT (Deploy in a later release)
   ├── Remove obsolete columns or backfilled deprecated tables
   └── Performed only after new code is stable in production
```

### Prohibited Actions During Normal Deployments:
- ❌ **Dropping a column** in the same release where code stops using it.
- ❌ **Renaming a column** in a single migration step (instead: add new column, dual-write, backfill, deprecate old column).
- ❌ **Adding a `NOT NULL` constraint** to an existing column without a default value.
- ❌ **Running `alembic downgrade`** automatically on application error.

---

## 3. Database Recovery & Restore Procedures

If a database corruption or catastrophic data anomaly occurs, use formal backup restoration rather than schema rollback.

### 3.1 Point-in-Time Recovery (PITR)
For managed PostgreSQL (e.g. AWS RDS, GCP Cloud SQL, Supabase, Azure Database):
1. Navigate to your cloud provider's database management console.
2. Select **Restore to Point in Time**.
3. Choose the exact timestamp immediately preceding the incident.
4. Launch the restored instance as a staging replica to verify data consistency before updating `DATABASE_URL`.

### 3.2 Manual Snapshot Restoration
To restore a manual SQL snapshot:
```bash
# 1. Stop application traffic to prevent inconsistent writes
docker compose stop api worker

# 2. Restore PostgreSQL database snapshot
export PGPASSWORD="$PROD_DB_PASSWORD"
pg_restore -h prod-db.example.internal -U kairo_prod_user -d kairo_production \
  --clean --if-exists --no-owner --no-privileges kairo_backup_2026-09-08.dump

# 3. Restart application and verify health
docker compose start api worker
bash deploy/scripts/healthcheck.sh https://api.example.com
```

---

## 4. Post-Rollback Incident Resolution

1. **Keep Rollback Post-Mortem Logs**: Document the exact failure symptom, the offending Git SHA, and the rollback completion timestamp.
2. **Reproduce in Staging**: Check out the offending commit locally or in staging to isolate the bug and construct a regression test case.
3. **Draft a Forward Fix**: Implement the fix on a new branch, add automated test coverage, and deploy forward through the standard staging pipeline.
