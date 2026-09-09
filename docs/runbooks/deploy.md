# Runbook: Kairo Production Deployment

**Target System**: Kairo Production Cluster (`https://kairo.ai`)  
**Version**: 1.1.0  
**Ownership**: Release Engineering & Operations  

---

## Overview
This runbook defines the mandatory 10-step zero-downtime deployment process for Kairo. Production deployments run the **exact immutable image** tested and validated on staging. Rebuilding images between staging and production is strictly prohibited.

---

## Pre-Requisites
- GitHub access with `production` environment approval permissions.
- Access to staging verification metrics and smoke test results.
- Cloud access (AWS EKS / ECS / GCP Cloud Run / Kubernetes).

---

## 10-Step Deployment Procedure

### Step 1: Verify CI Pipeline
Confirm that the CI workflow for the commit tag/SHA has completed with 100% green status:
- Unit tests pass.
- Integration tests pass.
- Security scans (Bandit SAST, Gitleaks secrets, Trivy container) clean.
- Frontend build succeeds.

### Step 2: Verify Immutable Artifact
Verify the artifact was built and signed in GitHub Container Registry (GHCR):
```bash
# Check image tags exist
docker pull ghcr.io/kairo-ai/kairo-api:sha-<GIT_SHA>
docker pull ghcr.io/kairo-ai/kairo-api:1.1.0-rc.1
```
*Never deploy `latest` as an authoritative reference.*

### Step 3: Verify Database Migrations (Expand/Contract)
Review any pending Alembic migrations:
```bash
alembic current
alembic history --verbose
```
**Safety Check**:
- Migrations must strictly follow the expand/contract design pattern.
- No destructive drops of tables or columns in the same release.
- New columns must either be nullable or have safe defaults.

### Step 4: Verify Staging Smoke Tests
Confirm staging smoke test suite execution:
```bash
python scripts/smoke_test.py --base-url "https://staging.kairo.ai" --env staging
```
Ensure all 8 subsystems (Database, Redis, Model, Automations, Agents, Security, GitHub, Browser) report `HEALTHY`.

### Step 5: Approve Production in GitHub
1. Navigate to GitHub Actions -> **Kairo Production Release**.
2. Select **Review Deployments** for the `production` environment.
3. Review deployment SHA, changelog, and staging smoke test artifact.
4. Input confirmation text: `PROCEED_PRODUCTION` and grant explicit sign-off.

### Step 6: Deploy to Production
Execute rolling deployment with zero downtime:
```bash
# Kubernetes rolling update example:
kubectl set image deployment/kairo-api kairo-api=ghcr.io/kairo-ai/kairo-api:sha-<GIT_SHA> --record
kubectl rollout status deployment/kairo-api --timeout=300s
```

### Step 7: Verify Service Health & Readiness
Probe endpoints immediately:
```bash
curl -fsS https://kairo.ai/health/live
curl -fsS https://kairo.ai/health/ready
curl -fsS https://kairo.ai/health/version
```
Expected output: HTTP 200 with `status: "ready"`, `version: "1.1.0"`, and matching `git_sha`.

### Step 8: Run Post-Deploy Smoke Test Suite
Execute safe, non-destructive smoke testing:
```bash
python scripts/smoke_test.py --base-url "https://kairo.ai" --env production
```
Verify:
- Health, Readiness, and Version endpoints.
- Authenticated read probes.
- Operations dashboard: `GET /health/operations`.
- *Destructive external writes (GitHub edits, shell execution) are disabled during smoke tests.*

### Step 9: Monitor Release Health Window
Activate the 15-minute release observation window:
- Review Operations Dashboard (`GET /health/operations`).
- Monitor Prometheus Grafana alerts:
  - HTTP 5xx error rate < 0.1%
  - Average latency p99 < 500ms
  - Model provider 429/500 rate < 1.0%
  - Redis connection pool saturation < 60%
  - Zero unhandled circuit breaker trips

### Step 10: Close Release
- Post release notice in internal operations chat.
- Push annotated Git release tag:
  ```bash
  git tag -a v1.1.0 -m "Release v1.1.0 - Production Validated"
  git push origin v1.1.0
  ```
- Close release ticket with smoke test logs and deployment manifest.
