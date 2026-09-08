# Kairo Production Release Engineering Checklist

This checklist must be systematically completed and verified by the Release Engineer and Security Lead before, during, and after every production release.

---

## Pre-Release Phase (CI & Staging)

- [ ] **1. CI Pipeline Green**: Automated linting (`ruff check`), formatting (`ruff format`), backend unit/integration tests (`pytest`), and frontend tests (`npm test`) passed 100% on the release branch.
- [ ] **2. Security Scan Green**: Static application security testing (`bandit`) and container vulnerability scanning (`trivy`) completed with zero unmitigated Critical or High severity findings.
- [ ] **3. Immutable Image Built & Tagged**: Container image built and tagged with immutable Git SHA (e.g. `kairo-api:sha-a1b2c3d4`). Verified non-root execution (`uid 1000`).
- [ ] **4. Staging Deployed**: Release candidate deployed to staging environment with isolated database and Redis.
- [ ] **5. Staging Smoke Tests Passed**: Automated smoke test suite (`bash deploy/scripts/smoke-test.sh https://staging-api.example.com`) executed with 100% pass rate.
- [ ] **6. Database Backup Verified**: Fresh, valid snapshot of production PostgreSQL confirmed available within the last 4 hours; point-in-time recovery (PITR) window validated.
- [ ] **7. Database Migration Reviewed**: Alembic migration scripts inspected for backward compatibility (expand/contract schema pattern). Confirmed no blocking table locks or destructive column drops.
- [ ] **8. Secrets & Environment Verified**: All required production environment variables verified in cloud secret manager (no default or hardcoded secrets).
- [ ] **9. Rollback Plan Ready**: Previous stable image tag / Git SHA identified and recorded; rollback command verified (`bash deploy/scripts/rollback.sh <PREVIOUS_TAG>`).
- [ ] **10. Production Authorization**: Formal release approval signed off by Engineering and Product leads.

---

## Release Execution Phase (Production Rollout)

- [ ] **11. Maintenance Window Notification**: Operations team and users notified of deployment window (if applicable).
- [ ] **12. Run Database Migration**: Explicitly execute migration script prior to traffic shift:
  ```bash
  bash deploy/scripts/migrate.sh
  ```
- [ ] **13. Rollout Application Containers**: Deploy new container image version:
  ```bash
  bash deploy/scripts/deploy.sh
  ```
- [ ] **14. Health & Readiness Verification**: Verify that the application passes all readiness checks:
  ```bash
  bash deploy/scripts/healthcheck.sh https://api.example.com
  ```
- [ ] **15. Automated Smoke Tests**: Execute post-deployment smoke test suite against production:
  ```bash
  bash deploy/scripts/smoke-test.sh https://api.example.com
  ```

---

## Post-Release Phase (Monitoring & Sign-off)

- [ ] **16. Telemetry & Metrics Monitoring**:
  - Monitor Prometheus HTTP request rates and latency (`kairo_http_request_duration_seconds`).
  - Verify HTTP 5xx error rate remains < 0.1%.
  - Verify database connection pool saturation remains < 70%.
  - Confirm `kairo_circuit_breaker_trips_total == 0`.
  - Confirm `kairo_emergency_stop_events_total == 0`.
- [ ] **17. AI Streaming Verification**: Verify `/api/v1/chat/stream` token generation streams smoothly without proxy buffering delay.
- [ ] **18. Worker / Scheduler Health**: Check Kairo Worker logs to confirm due workflow polling is claiming tasks without duplicate runs.
- [ ] **19. Git Release Tagging**: Tag release in Git repository:
  ```bash
  git tag -a v0.5.0 -m "Release v0.5.0 (Phase 18 Production Deployment)"
  git push origin v0.5.0
  ```
- [ ] **20. Release Closeout**: Notify stakeholders and update release changelog.
