# Incident Runbook: High Error Rate

**Incident Type**: Application Anomaly / Error Spike  
**Severity**: P1 / High (P0 if > 5%)  
**Target**: Kairo API Cluster  

---

## Symptoms
- Alert firing: `HighHttp5xxErrorRate` (Error rate > 1% over a 3-minute window).
- Operations Dashboard (`/health/operations`) shows `error_rate` exceeding acceptable thresholds (> 0.01).
- Spikes in client-side retry storms and user complaints.
- Audit logs capturing elevated incident records.

---

## Checks
1. **Assign Incident Identifier**:
   - Generate a tracked incident ID to correlate logs, metrics, and traces:
     ```bash
     # Format: INC-YYYYMMDDHHMM-<uuid>
     ```
2. **Correlate Error Distribution by Route**:
   - Query Grafana / Prometheus for `sum(rate(kairo_http_requests_total{status_code=~"5.."}[2m])) by (path, status_code)`.
   - Identify if errors are concentrated in a specific route (e.g. `/api/v1/chat/stream`, `/api/v1/auth/login`, or `/api/v1/projects`).
3. **Recent Deployment Check**:
   - Determine if the error spike coincided with a recent deployment within the 15-minute release health window:
     ```bash
     kubectl rollout history deployment/kairo-api
     ```
4. **Backend Log Stack Traces**:
   - Filter logs for unhandled 500 exceptions:
     ```bash
     kubectl logs -l app=kairo-api --tail=300 | grep -E "ERROR|Traceback"
     ```
   - Check if downstream services (DB, Redis, Model Provider) are triggering cascading failures.

---

## Safe Actions
- **Do Not** silence alerts without identifying root cause.
- **Do Not** commit quick hotfix code directly to production pods.
- If the error spike is caused by a recent bad release, proceed immediately to Rollback.

---

## Recovery
1. **If Caused by New Release**:
   - Follow `docs/runbooks/rollback.md` immediately. Revert to previous known-good artifact.
2. **If Caused by Database Saturation / Locking**:
   - Follow `docs/runbooks/database-down.md` to clear blocked locks or pool exhaustion.
3. **If Caused by Malformed Client Requests or Edge Cases**:
   - Enable feature flags or temporary rate-limiting on the affected route to protect core services.
4. **If Upstream Provider Failure**:
   - Follow `docs/runbooks/provider-outage.md`.

---

## Verification
- Monitor `/health/operations` to verify `error_rate` drops back below 0.001 (0.1%).
- Verify no new unhandled exceptions appear in application logs for 10 consecutive minutes.
- Close incident ticket with root cause analysis and correlated incident ID.
