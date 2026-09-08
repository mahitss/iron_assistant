# Kairo Production Cloud Deployment Guide

> [!CRITICAL]
> **Core Architectural Principles:**
> 1. *"Kairo is deployed as a modular monolith with managed stateful infrastructure."*
> 2. *"Desktop computer control is a local/trusted capability and is not exposed directly from the public cloud API."*
> 3. *"Kairo is not production-ready until authentication, secret management, HTTPS, backups, monitoring, and security review are configured."*

---

## 1. Architectural Topology

Kairo employs a clean, modular monolith architecture backed by managed stateful cloud primitives:

```text
                                INTERNET
                                   │
                                 HTTPS
                                   │
                           ┌───────▼───────┐
                           │ Reverse Proxy │ (Nginx / Cloudflare / AWS ALB)
                           │ TLS & Headers │ (Port 443 -> Port 8000)
                           └───────┬───────┘
                                   │
               ┌───────────────────┴───────────────────┐
               ▼                                       ▼
        ┌──────────────┐                        ┌──────────────┐
        │  Kairo API   │                        │ Kairo Worker │
        │  (Instance 1)│                        │ (Scheduler)  │
        └──────┬───────┘                        └──────┬───────┘
               │                                       │
               └───────────────────┬───────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
            ┌──────────────┐ ┌───────────┐ ┌──────────────┐
            │  PostgreSQL  │ │   Redis   │ │External APIs │
            │  + pgvector  │ │ (Managed) │ │(OpenRouter,  │
            │  (Managed)   │ │  TLS/Auth │ │ GitHub, Web) │
            └──────────────┘ └───────────┘ └──────────────┘
```

### Architectural Guardrails
- **No Kubernetes or Service Mesh**: Deployment runs on standard virtual machines or container hosts using Docker and Docker Compose.
- **No Celery or Kafka**: Asynchronous workflows utilize PostgreSQL row-level locks (`FOR UPDATE SKIP LOCKED`) and Redis distributed locks for guaranteed single-claim scheduling.
- **Single Authoritative Data Store**: PostgreSQL contains all durable business facts, conversations, audit logs, and memories; Redis remains strictly ephemeral.

---

## 2. Infrastructure Prerequisites

1. **Compute**:
   - Host: Linux VPS (Ubuntu 22.04+ or Debian 12+) or Container as a Service (e.g. AWS ECS, GCP Cloud Run, DigitalOcean App Platform).
   - Resources: Minimum 2 vCPUs, 4 GB RAM, 20 GB SSD storage.
2. **Managed Database**:
   - PostgreSQL 16+ with `vector` extension enabled.
   - SSL/TLS connection enforcement (`sslmode=require` or `sslmode=verify-full`).
3. **Managed Cache**:
   - Redis 7+ with TLS encryption (`rediss://`) and password authentication.
4. **Networking & Ingress**:
   - Domain DNS records: `api.example.com` (pointing to proxy/load balancer) and `app.example.com`.
   - Ingress Firewall: Only port `443` (HTTPS) and port `80` (HTTP-to-HTTPS redirect) publicly exposed.
   - Database (5432) and Redis (6379) must remain in private subnets with strictly no public ingress.

---

## 3. Database Setup & Connection Pool Sizing

### 3.1 Initial Database Provisioning
Connect to your managed PostgreSQL database as administrator:
```sql
CREATE DATABASE kairo_production;
\c kairo_production
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
```

### 3.2 Connection Pool Calculation
The database connection pool must never exceed PostgreSQL's `max_connections`:
$$\text{Total Connections} = (N_{\text{API}} \times (\text{pool\_size} + \text{max\_overflow})) + (N_{\text{Worker}} \times (\text{pool\_size} + \text{max\_overflow})) + N_{\text{Reserved}}$$

**Production Sizing Example:**
- 2 API Instances: $2 \times (20 + 10) = 60$ connections
- 1 Worker Instance: $1 \times (10 + 5) = 15$ connections
- Reserved Administrator Connections: 10 connections
- **Minimum Required PostgreSQL `max_connections`:** $60 + 15 + 10 = 85$ connections (Recommend configuring `max_connections = 100`+).

---

## 4. Secret Management & Environment Injection

Secrets must NEVER be baked into container images or committed to Git. Inject them securely via environment variables:

```bash
# Generate high-entropy secrets:
export AUTH_SECRET_KEY=$(openssl rand -hex 32)
export SECRET_KEY=$(openssl rand -hex 32)
```

Configure your environment using the template at `deploy/environments/production.env.example`.

---

## 5. Reverse Proxy Configuration (HTTPS & Streaming)

Deploy Nginx using the battle-tested configuration at [`deploy/nginx/nginx.conf`](file:///c:/Users/pc/OneDrive/Desktop/Kairo_Ai%20assistant/deploy/nginx/nginx.conf):
- Enforces HTTP to HTTPS redirection (301).
- Terminates TLS with modern TLS 1.2/1.3 ciphers.
- Injects OWASP defensive headers (`HSTS`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`).
- Implements WebSocket upgrade mapping for real-time voice and notification connections.
- **Disables proxy buffering (`proxy_buffering off;`)** on `/api/v1/chat/stream` and `/api/v1/voice` so token streams and audio chunks arrive in real time.
- Enforces `client_max_body_size 10M;` to prevent memory exhaustion from oversized payloads.

---

## 6. Step-by-Step Production Deployment Flow

```text
Developer Push
     ↓
CI Checks & SAST (GitHub Actions)
     ↓
Build Image tagged with Git SHA (kairo-api:sha-xxxx)
     ↓
Deploy Staging & Run Automated Smoke Tests
     ↓
Manual Approval Gate
     ↓
Run Explicit Migration (bash deploy/scripts/migrate.sh)
     ↓
Rollout Production Container (bash deploy/scripts/deploy.sh)
     ↓
Verify Health (GET /health/ready & GET /health/version)
     ↓
Run Smoke Tests (bash deploy/scripts/smoke-test.sh)
```

### Execution Commands:
```bash
# 1. Run database migrations explicitly before launching new application version
bash deploy/scripts/migrate.sh

# 2. Deploy container services
bash deploy/scripts/deploy.sh

# 3. Verify health and operational readiness
bash deploy/scripts/healthcheck.sh https://api.example.com
bash deploy/scripts/smoke-test.sh https://api.example.com
```

---

## 7. Desktop Computer Control & Wake-Word Separation

> [!CAUTION]
> **Cloud Safety Constraint:**
> Desktop computer interaction and voice wake-word listening MUST NOT be executed within cloud containers.

- **Desktop Computer Control**: Requires local display access, keyboard/mouse hooks, and trusted host control. In cloud deployments, `KAIRO_COMPUTER_ENABLED=false` is enforced. A local agent client must be installed on the user's desktop to broker controlled commands securely over an authenticated channel.
- **Wake-Word Processing**: Wake-word models (e.g. OpenWakeWord) run locally on client hardware. Audio is never continuously streamed to the cloud; only explicitly activated voice sessions connect to `/api/v1/voice`.

---

## 8. Zero-Downtime Rolling Update Considerations

1. **Backward-Compatible Migrations**: Apply expand/contract schema migrations before deploying code. The database must remain compatible with both old and new application versions during the rollout.
2. **Graceful Shutdown**: Containers intercept `SIGTERM` with a 30-second drain window, completing in-flight HTTP requests and workflow steps before process exit.
3. **Readiness Verification**: Traffic shifts to the new container only after `GET /health/ready` returns HTTP 200.
