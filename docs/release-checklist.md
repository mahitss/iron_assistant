# Kairo Production Release Checklist

Every release must follow:
`CODE -> CI -> TEST -> SECURITY SCAN -> BUILD -> STAGING -> SMOKE TEST -> APPROVAL -> PRODUCTION -> HEALTH -> MONITOR -> ROLLBACK IF NECESSARY`

No manual mystery steps.

---

## Release Checklist

### CODE
- [ ] **review complete**: Pull request approved by required reviewers; no outstanding change requests.
- [ ] **tests pass**: Unit, integration, and frontend test suites pass with 100% green status.
- [ ] **security scan**: Static analysis (`bandit`) passes with zero unmitigated High/Critical findings.
- [ ] **dependency scan**: Software supply chain audit (`pip-audit` & `npm audit`) shows no known CVEs.

### BUILD
- [ ] **image built**: Production Docker container built once using immutable configuration.
- [ ] **image scanned**: Container vulnerability scan (`trivy`) verified clean of critical vulnerabilities.
- [ ] **artifact tagged**: Immutable tag created using `git SHA` and release candidate/version (e.g. `kairo-api:1.1.0` and `kairo-api:<git-sha>`). Never use `latest` as an authoritative reference.

### STAGING
- [ ] **deployed**: Exact production-built image deployed to staging environment.
- [ ] **smoke test**: Automated smoke test suite passes (`python scripts/smoke_test.py --env staging`).
- [ ] **E2E**: End-to-end integration workflows verified against staging database and Redis.

### DATABASE
- [ ] **migration reviewed**: Database migrations adhere to expand/contract pattern; backward-compatible with N-1 application instances.
- [ ] **backup verified**: Production database backup verified with test restoration and integrity check completed.

### PRODUCTION
- [ ] **approval**: Explicit authorization granted in GitHub environment protection gate; no arbitrary branch deploys.
- [ ] **deploy**: Exact staging-tested artifact deployed to production cluster with zero downtime.
- [ ] **health**: Readiness and liveness probes verified (`GET /health/live`, `GET /health/ready`, `GET /health/version`).
- [ ] **smoke test**: Non-destructive post-deploy smoke test suite executed against production.
- [ ] **monitoring**: Release health window active (15 minutes); monitoring 5xx error rate, latency p99, model provider errors, and circuit breaker status.

### ROLLBACK
- [ ] **previous artifact available**: Previous known-good image tag confirmed present in container registry.
- [ ] **rollback tested/documented**: Rollback runbook (`docs/runbooks/rollback.md`) reviewed and verified compatible with current database schema.

---

## Release Artifact Manifest Record
- **Release Version**: `1.1.0`
- **Git SHA**: `<sha>`
- **Build Timestamp**: `<iso8601-utc>`
- **Backend Image**: `ghcr.io/kairo-ai/kairo-api:1.1.0`
- **Frontend Artifact**: `dist/` (Node 20 build)
- **Migration Version**: `0006_personal_context_and_projects`
