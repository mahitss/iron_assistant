# Incident Runbook: Database Down

**Incident Type**: Core Infrastructure Outage  
**Severity**: P0 / Critical  
**Target**: PostgreSQL + pgvector Database  

---

## Symptoms
- `/health/ready` returns HTTP 503 with `"database": "unhealthy"` or `"database": "down"`.
- Backend logs flooded with `psycopg2.OperationalError: could not connect to server: Connection refused` or `asyncpg.exceptions.CannotConnectNowError`.
- Operations Dashboard (`/health/operations`) shows `database: "UNAVAILABLE"`.
- Application writes and authentication fail across all endpoints.

---

## Checks
1. **Database Service Status**:
   ```bash
   # Check managed DB (AWS RDS / Cloud SQL) status in cloud console or CLI:
   aws rds describe-db-instances --db-instance-identifier kairo-prod-pg --query "DBInstances[0].DBInstanceStatus"
   # Or local/k8s postgres pod:
   kubectl get pods -l app=postgres
   ```
2. **Connection Pool Saturation**:
   ```sql
   -- Connect via administrative bastion:
   SELECT count(*), state FROM pg_stat_activity GROUP BY state;
   SELECT max_connections, current_setting('max_connections') FROM pg_settings;
   ```
   Determine if active client connections reached `max_connections` (e.g. 100/100).
3. **Storage & Disk Space**:
   ```bash
   # Check disk volume utilization:
   df -h /var/lib/postgresql/data
   ```
   Postgres halts writes if disk is 100% full.
4. **Locks & Long-Running Queries**:
   ```sql
   SELECT pid, now() - query_start AS duration, query, state 
   FROM pg_stat_activity 
   WHERE state != 'idle' 
   ORDER BY duration DESC LIMIT 5;
   ```

---

## Safe Actions
- **Do Not** terminate PostgreSQL with `kill -9`, which can corrupt transaction logs (WAL). Use `pg_ctl stop -m fast` or graceful pod restart.
- **Do Not** execute destructive `DROP` commands or purge tables manually.
- Terminate non-essential idle or blocked client connections:
  ```sql
  SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle in transaction' AND query_start < now() - interval '5 minutes';
  ```

---

## Recovery
1. **If Connection Exhaustion**:
   - Restart PgBouncer connection pooler or restart API replicas to drop leaked connection sockets.
   - Adjust `DATABASE_POOL_SIZE` in backend configuration if traffic has outgrown the current pool limit.
2. **If Disk Full**:
   - Expand database storage volume immediately via cloud provider.
   - Clean up archived WAL logs or temp files if safe.
3. **If Instance Failure / Hardware Crash**:
   - Initiate automated failover to the standby Multi-AZ read-replica.
   - Verify DNS endpoint updates to point to the new primary instance.
4. **If Catastrophic Corruption**:
   - Restore database from the most recent verified backup (PITR snapshot). Refer to Section 40: Backup Verification.

---

## Verification
- Probe `/health/ready`:
  ```bash
  curl -fsS https://kairo.ai/health/ready
  ```
  Confirm HTTP 200 with `"database": "healthy"`.
- Run query probe:
  ```bash
  python -c "import asyncio; from backend.app.db.session import engine; asyncio.run(engine.dispose())"
  ```
- Verify Operations Dashboard reflects `database: "HEALTHY"`.
