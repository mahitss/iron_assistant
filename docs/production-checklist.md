# Kairo Production Deployment Checklist

> [!CRITICAL]
> **Production Readiness Notice:**
> Kairo is not production-ready until authentication, secret management, HTTPS, backups, monitoring, and security review are configured.

This checklist must be systematically completed and validated before any Kairo instance is deployed to public or corporate networks.

---

## 1. Environment & Configuration

- [ ] **`ENVIRONMENT=production` set**: Confirm that `ENVIRONMENT` is set to `production` in the production environment. Development fallbacks and mock configurations are automatically disabled.
- [ ] **Fail-Fast Validation**: Ensure `validate_environment()` executes on startup. The application will abort immediately if any critical production secret is missing, default, or insecure.
- [ ] **No `.env` in Production Images**: Ensure no `.env` files with production secrets are baked into container images (verified via `.dockerignore`).
- [ ] **App URL & Host Configuration**: Set `KAIRO_HOST=0.0.0.0`, `KAIRO_PORT=8000`, and `APP_URL=https://<your-domain>`.

---

## 2. Authentication & Secrets

- [ ] **`AUTH_SECRET_KEY` Generated**: Generate a cryptographically random secret with at least 32 bytes of entropy (`openssl rand -hex 32`). Must NOT use default values.
- [ ] **`OPENROUTER_API_KEY` Configured**: Real OpenRouter API key configured via a secret manager (AWS Secrets Manager, HashiCorp Vault, Kubernetes Secrets, or encrypted environment variables).
- [ ] **Default Admin Credentials Replaced**: Ensure any bootstrap administrative accounts have strong, unique passwords (PBKDF2-SHA256 hashed).
- [ ] **Session Expiry Configured**:
  - `SESSION_IDLE_TIMEOUT_SECONDS=1800` (30 minutes max inactivity)
  - `SESSION_ABSOLUTE_LIFETIME_SECONDS=86400` (24 hours max lifetime)
- [ ] **Logout Approval Revocation Verified**: Verify that logging out automatically revokes all pending human-in-the-loop approvals associated with that session.

---

## 3. Network & Transport Security (HTTPS)

- [ ] **TLS / HTTPS Termination**: Deploy behind a reverse proxy (e.g., Nginx, Caddy, Cloudflare, AWS ALB) with TLS 1.3 enforced.
- [ ] **HSTS Enforced**: Confirm `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload` is sent in response headers.
- [ ] **CORS Restricted**: Set `CORS_ORIGINS` to the exact trusted frontend origin(s) (e.g., `["https://app.kairo.ai"]`). Never use wildcard `*` in production.
- [ ] **OWASP Defensive Headers Active**:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Content-Security-Policy: default-src 'self'`
  - `Referrer-Policy: strict-origin-when-cross-origin`
- [ ] **Request Body Size Limit**: Verify reverse proxy and application limit payload size to `10 MB` max (`413 Payload Too Large`).

---

## 4. Rate Limiting & Abuse Prevention

- [ ] **Global Rate Limiter Active**: Verify sliding-window rate limiting is enabled (`RATE_LIMIT_REQUESTS_PER_MINUTE=120`).
- [ ] **Per-Endpoint Rate Limits**:
  - Authentication login endpoint restricted to 10 attempts/minute.
  - Chat streaming endpoints restricted to 30 requests/minute.
- [ ] **Emergency Stop & Health Exemption**: Confirm `/api/v1/security/emergency-stop` and `/health` endpoints are exempt from rate limiting to prevent denial-of-service on critical safety controls.

---

## 5. Central Security Center & Permissions

- [ ] **Controlled Computer Interaction**: Verify computer control capability toggle defaults to `OFF` (`COMPUTER_CONTROL_ENABLED=false`) unless explicitly enabled by an authorized administrator.
- [ ] **Approval Workflow Active**: High-risk tool calls (`execute_command`, `git_push`, `delete_file`, `write_file`) require explicit human approval.
- [ ] **Timeout on Approvals**: Pending approval requests must time out after 10 minutes and default to `DENIED`.
- [ ] **Emergency Stop Kill Switch Tested**: Verify that activating `/api/v1/security/emergency-stop` immediately aborts all running tools, agents, workflows, and blocks subsequent execution.

---

## 6. Database & Persistence Hardening

- [ ] **PostgreSQL 16+ with pgvector**: Verify PostgreSQL connection string (`postgresql+asyncpg://...`) uses SSL (`sslmode=require` or `verify-full`).
- [ ] **Connection Pooling Configured**:
  - `DB_POOL_SIZE=20`
  - `DB_MAX_OVERFLOW=10`
  - `DB_POOL_TIMEOUT=30`
  - `DB_POOL_RECYCLE=1800`
  - `DB_POOL_PRE_PING=true` (stale connection health checks)
- [ ] **Database Backups**:
  - Automated daily snapshots (`pg_dump` or WAL-G/Barman continuous archiving).
  - Point-in-time recovery (PITR) enabled.
  - Periodic backup restore drills tested.
- [ ] **Database Migrations Tested**: Run `alembic upgrade head` cleanly against a staging database before deploying to production.

---

## 7. Redis Cache & Ephemeral State

- [ ] **Password / TLS Configured**: Redis must require authentication (`AUTH`) and use TLS (`rediss://...`) if accessible over the network.
- [ ] **Persistence Policy**: Redis configured with `appendonly yes` or RDB snapshots if used for persistent job queues, or memory limits with `volatile-lru` eviction policy.
- [ ] **Ephemeral Safety**: Confirm system recovers cleanly even if Redis is completely flushed (PostgreSQL is the source of truth).

---

## 8. Resilience & LLM Failover

- [ ] **Circuit Breaker Active**: Verify circuit breaker triggers on consecutive failures (threshold: 5 failures, reset timeout: 60s).
- [ ] **Exponential Backoff & Jitter**: Confirm retry policy backs off with jitter on transient 5xx / 429 / network errors.
- [ ] **Non-Retriable Errors**: Confirm `AuthenticationError` and `SecurityError` fail immediately without retrying or tripping breaker.
- [ ] **Model Fallback**: Ensure fallback models are configured in `ModelRouter` if the primary model is unavailable.

---

## 9. Observability & Monitoring

- [ ] **Structured JSON Logging**: Ensure logs output structured JSON with timestamps, log levels, request IDs, and caller context.
- [ ] **Secret Redaction**: Confirm `StructuredJsonFormatter` redacts API keys, tokens, passwords, and authorization headers from logs.
- [ ] **Health Probes Wired to Orchestrator**:
  - Liveness probe: `GET /health/live` (checks process heartbeat)
  - Readiness probe: `GET /health/ready` (checks DB, Redis, and model connectivity)
  - Prometheus metrics: `GET /metrics` scraped by Prometheus/VictoriaMetrics.
- [ ] **Alerting Thresholds Defined**:
  - HTTP 5xx error rate > 1% over 5 minutes.
  - Database pool saturation > 85%.
  - Circuit breaker trips (`kairo_circuit_breaker_trips_total > 0`).
  - Emergency stop activated (`kairo_emergency_stop_events_total > 0`).
  - Stale workflow / agent recovery events detected.

---

## 10. Container & Deployment Safety

- [ ] **Non-Root Container User**: Ensure containers run as `kairo:kairo` (`uid: 1000`, `gid: 1000`).
- [ ] **Read-Only Root Filesystem**: Mount container root filesystem as read-only where feasible, with `/tmp` as `tmpfs`.
- [ ] **Resource Limits**: CPU (`cpus: 2.0`) and Memory (`memory: 2048M`) limits defined in deployment configurations.
- [ ] **Graceful Shutdown**: Container orchestrator sends `SIGTERM` with at least 30 seconds grace period to allow ongoing requests and agent tasks to safely cancel.
- [ ] **Startup Recovery**: Confirm `recover_stale_tasks_on_startup()` cleans up any orphaned tasks from previous crashed runs.
