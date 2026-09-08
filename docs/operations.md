# Kairo Production Operations Runbook

This runbook provides actionable procedures for diagnosing, containing, and resolving production incidents and anomalies across Kairo's modular monolith and managed stateful services.

---

## Operational Incident Matrix

| Scenario | Severity | Initial Diagnostic | Primary Action |
|---|---|---|---|
| **1. API Down / Crash Loop** | Critical | `GET /health/live` fails (HTTP 502/503) | Check container logs, restart container |
| **2. Database Connection Exhaustion** | Critical | `GET /health/ready` fails (`database: failed`) | Inspect connection pool metrics, increase pool limit |
| **3. Redis Failover / Connection Loss** | High | `GET /health/ready` reports `redis: failed` | Verify Redis cluster status, check TLS certs |
| **4. OpenRouter Provider Outage** | High | Prometheus `kairo_circuit_breaker_trips_total > 0` | Switch to fallback model, monitor OpenRouter status |
| **5. GitHub API Rate Limit / Outage** | Medium | Tool errors during repository inspection | Rotate PAT, inspect rate limit reset headers |
| **6. High HTTP 5xx Error Rate Spike** | Critical | Prometheus `kairo_http_requests_total{status=~"5.."}` | Inspect error logs, trigger Emergency Stop if needed |
| **7. Workflow Failure Spike** | High | Spikes in failed `WorkflowRun` rows | Check worker logs, inspect external dependencies |
| **8. Stuck Multi-Agent Task** | Medium | Agent task status remains `RUNNING` past timeout | Invoke cancellation API: `POST /api/v1/agents/tasks/{id}/cancel` |
| **9. Stuck Human-in-the-Loop Approval** | Medium | Approval backlog increasing | Send reminder notification, auto-deny timed-out items |
| **10. Suspected Secret Compromise** | Critical | Unauthorized API token usage or exposed credentials | Rotate all secrets, flush Redis sessions, deploy update |
| **11. Unexpected Computer Control Behavior** | Critical | Rogue OS-level activity reported | **Activate Emergency Stop immediately**, disable capability |

---

## Detailed Runbook Procedures

### Scenario 1: API Down / Container Crash Loop
- **Symptom:** Ingress reverse proxy returns HTTP 502 Bad Gateway; `GET /health/live` times out or fails.
- **Diagnosis:**
  ```bash
  docker logs --tail 100 kairo-api
  ```
  Look for startup validation failures (`validate_environment()`), unhandled exceptions, or memory/OOM kills.
- **Safe Response:**
  1. If container was OOM-killed, temporarily increase container memory limit in `docker-compose.yml`.
  2. If a bad configuration was pushed, correct the environment variable in your secret manager.
  3. Restart container:
     ```bash
     docker compose restart api
     ```
- **Recovery Verification:** Verify `GET /health/live` returns HTTP 200.

---

### Scenario 2: Database Connection Exhaustion / DB Down
- **Symptom:** `GET /health/ready` returns HTTP 503 with `"database": "failed"`; API logs show `TimeoutError: QueuePool limit of size 20 overflow 10 reached`.
- **Diagnosis:**
  Check active database connections on PostgreSQL:
  ```sql
  SELECT count(*), state FROM pg_stat_activity WHERE datname = 'kairo_production' GROUP BY state;
  ```
- **Safe Response:**
  1. Identify long-running unindexed queries and terminate if blocking:
     ```sql
     SELECT pid, now() - query_start AS duration, query 
     FROM pg_stat_activity 
     WHERE state = 'active' AND (now() - query_start) > interval '30 seconds';
     ```
  2. Increase connection pool size via `KAIRO_DB_POOL_SIZE` and `KAIRO_DB_MAX_OVERFLOW` if load is legitimately high.
  3. Restart API workers to recycle connections.
- **Recovery Verification:** Confirm `GET /health/ready` returns `"status": "ready"`.

---

### Scenario 3: Redis Failover / Connection Loss
- **Symptom:** Session lookups fail; rate limiter logs connection warnings; `GET /health/ready` reports `"redis": "failed"`.
- **Diagnosis:**
  Test Redis connectivity directly:
  ```bash
  redis-cli -u $REDIS_URL ping
  ```
- **Safe Response:**
  1. Note that Kairo uses Redis strictly as ephemeral cache and short-term locks; **PostgreSQL remains intact**.
  2. If Redis service restarted, verify DNS or connection string credentials.
  3. Recreate/restart Redis instance if needed. Kairo will reconnect automatically via connection pre-ping.
- **Recovery Verification:** Confirm Redis ping returns `PONG`.

---

### Scenario 4: OpenRouter / LLM Provider Outage or 429 Throttling
- **Symptom:** LLM responses time out; `CircuitBreaker` trips to `OPEN`; metric `kairo_circuit_breaker_trips_total` increments.
- **Diagnosis:**
  Inspect status of upstream provider (e.g. `status.openrouter.ai`) or check API quota.
- **Safe Response:**
  1. Circuit breaker automatically prevents cascading exhaustion by failing fast with descriptive errors.
  2. Update `KAIRO_MODEL` in environment variables to a fallback model or secondary provider endpoint.
  3. Restart API instances with zero downtime:
     ```bash
     docker compose up -d --no-deps api
     ```
- **Recovery Verification:** Test simple chat completion via `POST /api/v1/chat`.

---

### Scenario 5: High HTTP 5xx Error Rate Spike
- **Symptom:** Prometheus alert fires for HTTP 5xx rate > 1% over 5 minutes.
- **Diagnosis:**
  Inspect structured JSON error logs filtering by level:
  ```bash
  docker logs kairo-api --since 15m | grep '"level":"ERROR"'
  ```
  Check correlation `request_id` values to isolate offending routes or payloads.
- **Safe Response:**
  1. If errors stem from a bad deployment, initiate immediate container rollback:
     ```bash
     bash deploy/scripts/rollback.sh <PREVIOUS_STABLE_SHA>
     ```
  2. If errors stem from an ongoing exploit or resource exhaustion, activate Emergency Stop.
- **Recovery Verification:** Error rate drops below 0.1%.

---

### Scenario 6: Stuck Multi-Agent Task or Runaway Workflow
- **Symptom:** Multi-agent task or scheduled workflow execution remains in `RUNNING` past configured timeout.
- **Diagnosis:**
  Inspect task status via API:
  ```bash
  curl -s -H "Authorization: Bearer $ADMIN_TOKEN" "https://api.example.com/api/v1/agents/tasks/{task_id}"
  ```
- **Safe Response:**
  1. Cancel the stuck task immediately using the cancellation endpoint:
     ```bash
     curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" "https://api.example.com/api/v1/agents/tasks/{task_id}/cancel"
     ```
  2. If worker process is unresponsive, restart worker container:
     ```bash
     docker compose restart worker
     ```
     Kairo's startup recovery routine (`recover_stale_tasks_on_startup`) will automatically transition orphaned tasks to `FAILED`.
- **Recovery Verification:** Task status reflects `CANCELLED` or `FAILED`.

---

### Scenario 7: Suspected Secret or Token Compromise
- **Symptom:** Anomalous API activity detected from unknown IP addresses, or credentials leaked in external commits.
- **Diagnosis:**
  Inspect recent audit logs:
  ```sql
  SELECT timestamp, user_id, action, status, ip_address 
  FROM audit_events 
  WHERE timestamp >= NOW() - INTERVAL '4 hours' 
  ORDER BY timestamp DESC LIMIT 50;
  ```
- **Safe Response:**
  1. Invalidate all active user sessions by rotating `AUTH_SECRET_KEY` and restarting API containers:
     ```bash
     export AUTH_SECRET_KEY=$(openssl rand -hex 32)
     docker compose up -d --force-recreate api worker
     ```
  2. Flush Redis cache to immediately drop cached bearer tokens:
     ```bash
     redis-cli -u $REDIS_URL FLUSHDB
     ```
  3. Rotate external provider keys (`OPENROUTER_API_KEY`, `KAIRO_GITHUB_TOKEN`, PostgreSQL and Redis passwords).
- **Recovery Verification:** Confirm old tokens receive HTTP 401 Unauthorized.

---

### Scenario 8: Unexpected Computer Control Behavior
- **Symptom:** User reports unauthorized local window movement, unexpected typing, or runaway cursor activity.
- **Diagnosis:**
  Check capability status: verify if `KAIRO_COMPUTER_ENABLED` was inadvertently enabled.
- **Safe Response:**
  1. **TRIGGER EMERGENCY STOP IMMEDIATELY:**
     ```bash
     curl -X POST "https://api.example.com/api/v1/security/emergency-stop" \
       -H "Authorization: Bearer $ADMIN_TOKEN" \
       -H "Content-Type: application/json" \
       -d '{"reason": "Immediate containment: unexpected computer control behavior reported"}'
     ```
  2. Verify that Emergency Stop sets the atomic global halt flag and cancels all active tools.
  3. Ensure `KAIRO_COMPUTER_ENABLED=false` is set in configuration and redeploy.
- **Recovery Verification:** Confirm SecurityCenter reports `emergency_stop: true` and `computer_control: false`.
