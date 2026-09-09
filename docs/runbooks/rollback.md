# Runbook: Emergency Production Rollback

**Target System**: Kairo Production Cluster (`https://kairo.ai`)  
**Severity**: P1 / Critical Incident  
**Ownership**: Site Reliability Engineering, Incident Commander  

---

## Rollback Principles
1. **Application Rollback First**: Immediately revert the container image to the previous known-good immutable artifact tag.
2. **Never Automatically Downgrade Database Schema**: Because Kairo uses expand/contract migrations, the active database schema contains additions that N-1 application code can safely ignore. Blindly running `alembic downgrade` destroys production data and table locks live systems.
3. **Speed & Decisiveness**: Rollback takes precedence over active in-production debugging when critical error thresholds are breached.

---

## Rollback Triggers & Thresholds
Initiate an immediate rollback if ANY of the following occur during or immediately after deployment:

| Trigger Condition | Threshold / Observation Window | Severity |
|---|---|---|
| **Sustained Error Rate** | HTTP 5xx errors > 1.0% over 3 consecutive minutes | Critical |
| **Authentication Regression** | Token verification or login failure rate > 5.0% | Critical |
| **Crash Loop BackOff** | Pod crash loop count > 3 restarts within 5 minutes | Critical |
| **Severe Latency Regression** | P99 API response latency > 3,000ms over 5 minutes | High |
| **Security / Authz Regression** | Tenant isolation failure or permission bypass detected | P0 Critical |
| **Workflow Duplication Bug** | Celery/Worker deduplication failure causing run storms | Critical |
| **Data Corruption Bug** | Integrity constraints failing on active writes | P0 Critical |

---

## Step-by-Step Rollback Execution

### Step 1: Identify Active Release & Previous Known-Good Artifact
Inspect the deployment history and artifact manifest to locate the previous stable tag:
```bash
# Example Kubernetes rollout history:
kubectl rollout history deployment/kairo-api

# Identify target revision (e.g. revision 42 with image tag sha-d3c4b5a6)
```
Record:
- Faulty Release Tag: `kairo-api:<FAILED_SHA>`
- Target Stable Tag: `kairo-api:<KNOWN_GOOD_SHA>` (e.g., `1.0.9` or prior Git SHA)

### Step 2: Confirm Database Compatibility
Check if any migrations applied in the failed release dropped or destructively altered columns:
```bash
# Verify no destructive alterations occurred:
git log -n 5 -- backend/app/db/migrations/versions/
```
*Because Kairo mandates expand/contract migrations, the prior application version MUST be able to query the current database schema without schema rollback.*

### Step 3: Deploy Previous Known-Good Artifact
Execute the rollback command immediately:
```bash
# Rollback using Kubernetes deployment undo:
kubectl rollout undo deployment/kairo-api

# Or explicitly pin to the previous known-good SHA:
kubectl set image deployment/kairo-api kairo-api=ghcr.io/kairo-ai/kairo-api:<KNOWN_GOOD_SHA> --record
kubectl rollout status deployment/kairo-api --timeout=180s
```

### Step 4: Verify Health & Readiness
Confirm healthy pods and endpoints:
```bash
curl -fsS https://kairo.ai/health/live
curl -fsS https://kairo.ai/health/ready
curl -fsS https://kairo.ai/health/version
```
Confirm the returned `git_sha` matches `<KNOWN_GOOD_SHA>`.

### Step 5: Run Automated Post-Rollback Smoke Suite
```bash
python scripts/smoke_test.py --base-url "https://kairo.ai" --env production
```
Verify:
- API status: `HEALTHY`
- Database & Redis connectivity: `HEALTHY`
- Auth tokens accept and validate properly: `HEALTHY`

### Step 6: Post-Rollback Monitoring & Incident Review
- Observe error rate drop below 0.05%.
- Assign an `incident_id` using `generate_incident_id("ROLLBACK")`.
- Notify stakeholders in internal incident channel.
- Open post-mortem investigation ticket with container logs from the failed deployment.
