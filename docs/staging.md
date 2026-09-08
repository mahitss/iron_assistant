# Kairo Staging Environment Architecture & Operations

The Staging environment provides an exact, production-like replica for verifying database migrations, API changes, UI workflows, and security policies before releasing to production.

> [!CRITICAL]
> **Data Isolation Mandate:**
> Staging MUST NEVER connect to production PostgreSQL or production Redis.
> Staging must use isolated credentials, separate encryption keys, and dedicated domains.

---

## 1. Staging Environment Architecture

| Attribute | Production | Staging |
|---|---|---|
| **Domain** | `https://api.example.com` | `https://staging-api.example.com` |
| **Frontend** | `https://app.example.com` | `https://staging-app.example.com` |
| **PostgreSQL DB** | `kairo_production` (SSL enforced) | `kairo_staging` (SSL enforced) |
| **Redis Cache** | `prod-redis.example.internal:6379/0` (TLS) | `staging-redis.example.internal:6379/1` (TLS) |
| **Auth Secrets** | Production Secret Key (32+ bytes) | Dedicated Staging Secret Key |
| **OpenRouter Quota** | Production Tier | Scoped Staging Testing Quota |
| **Computer Control**| `false` (Disabled) | `false` (Disabled) |

---

## 2. Deploying to Staging

Staging deployments are automated upon successful merge of pull requests to the `main` branch or release candidate tags.

### Manual Staging Deployment Command:
```bash
# Export staging environment configuration
set -a
source deploy/environments/staging.env
set +a

# 1. Run migrations against staging database
bash deploy/scripts/migrate.sh

# 2. Deploy staging containers
docker compose -f docker-compose.yml -p kairo-staging up -d --build

# 3. Verify health & readiness
bash deploy/scripts/healthcheck.sh https://staging-api.example.com
```

---

## 3. Pre-Production Staging Smoke Test Protocol

Before approving any release to production, the automated smoke test suite must pass against the staging environment:

```bash
bash deploy/scripts/smoke-test.sh https://staging-api.example.com
```

### Manual Verification Checklist in Staging:
- [ ] **Health & Readiness**: `/health/live` and `/health/ready` return HTTP 200 with all components connected.
- [ ] **Version Metadata**: `/health/version` confirms the deployed Git commit SHA.
- [ ] **Authentication Flow**: User registration/login returns valid bearer token; invalid credentials return 401.
- [ ] **Chat & AI Streaming**: Multi-turn conversation works; `/api/v1/chat/stream` streams tokens progressively without buffering.
- [ ] **Memory System**: Context retrieval and long-term memory extraction operate cleanly against staging pgvector.
- [ ] **Multi-Agent Orchestration**: Complex supervisor plan completes; evidence taxonomy distinguishes `OBSERVED`, `INFERRED`, and `UNKNOWN`.
- [ ] **Security Center**: Pending approval requests require user confirmation; emergency stop successfully halts tasks.
- [ ] **Audit Trail**: Audit events are recorded in `audit_events` table with accurate timestamps and user scoping.

---

## 4. Staging Data Management & Sanitization

- **No Production PII in Staging**: Never clone production user conversations, personal memories, or credentials into staging.
- **Synthetic Test Datasets**: Seed staging using automated seed fixtures representing edge-case workflows, multi-step approvals, and memory entities.
- **Periodic Reset**: Staging database can be safely dropped, recreated, and migrated via `alembic upgrade head` on a weekly schedule.
