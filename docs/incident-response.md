# Kairo Security Incident Response Playbook

This document provides a battle-tested, 10-step incident response protocol for responding to security anomalies, unauthorized access, runaway automation, or service compromises in a production Kairo deployment.

---

## Severity Levels (Triaging Matrix)

| Severity | Definition | Response Target | Escalation & Notification |
|---|---|---|---|
| **P0 - Critical** | Active data breach, compromised API key, runaway unauthorized code execution, bypass of SecurityCenter. | Immediate (< 15 mins) | Security Lead, Infrastructure On-Call, Executive Team |
| **P1 - High** | Emergency stop triggered due to rogue agent behavior, elevated authentication failure spikes, SSRF attempt detected. | < 30 mins | Security On-Call, Engineering Leads |
| **P2 - Medium** | Circuit breaker permanently tripped, rate-limit exhaustion impacting normal users, degraded database connection pool. | < 2 hours | Core Engineering Team |
| **P3 - Low** | Isolated non-exploitable error, minor logging anomaly, non-critical scheduled job failure. | < 24 hours | Standard Issue Backlog |

---

## 10-Step Incident Response Protocol

### Step 1: Detection & Alert Triaging
- **Action:** Ingest and verify alerts from Prometheus, Grafana, AWS CloudWatch, Datadog, or user reports.
- **Key Indicators:**
  - `kairo_emergency_stop_events_total > 0`
  - Spike in `kairo_http_requests_total{status=~"401|403|500"}`
  - Consecutive `kairo_circuit_breaker_trips_total`
  - Abnormal spike in tool calls (`execute_command`, `git_push`)
- **Triage:** Confirm whether the alert indicates an active attack, system instability, or a false positive.

### Step 2: Severity Assessment
- Categorize the incident as **P0, P1, P2, or P3** using the Triaging Matrix above.
- Designate an **Incident Commander (IC)** and record the timestamp of triage.
- Open a dedicated secure communication channel (e.g., private incident Slack/Discord channel).

### Step 3: Emergency Containment (Kill Switch Activation)
- **If arbitrary code execution, runaway automation, or credential leakage is suspected:**
  - **Execute Emergency Stop immediately:**
    ```bash
    curl -X POST "https://<kairo-host>/api/v1/security/emergency-stop" \
      -H "Authorization: Bearer <ADMIN_TOKEN>" \
      -H "Content-Type: application/json" \
      -d '{"reason": "Active incident containment: suspicious tool execution pattern"}'
    ```
  - **Verify Emergency State:** Confirm that all running tools, agents, workflows, and computer interaction routines have been aborted.

### Step 4: Token & Credential Revocation
- If unauthorized access or token leakage is suspected:
  - Invalidate all active user sessions:
    ```bash
    # Rotate AUTH_SECRET_KEY in secret manager and restart service, or flush Redis session store
    redis-cli -u $REDIS_URL FLUSHDB
    ```
  - Rotate upstream API keys immediately:
    - Rotate `OPENROUTER_API_KEY` in OpenRouter console.
    - Revoke and regenerate all GitHub Personal Access Tokens (PATs).
    - Rotate PostgreSQL and Redis service passwords.

### Step 5: Network & Ingress Isolation
- If an ongoing DDoS or external exploit is active:
  - Block offending IP addresses or CIDR blocks at the reverse proxy / edge firewall (Cloudflare / AWS WAF / Nginx).
  - Temporarily restrict API ingress strictly to internal VPN or administrative bastion IPs.
  - Disable public `/api/v1/chat` or registration routes if targeted.

### Step 6: Diagnostic Log & Trace Investigation
- Extract structured JSON logs for the incident timeframe:
  ```bash
  # Filter logs for request_id or error anomalies
  docker logs kairo-backend --since 1h | grep -E '"level":"(ERROR|CRITICAL)"' > incident_logs.json
  ```
- Correlate `request_id` across ingress, API middleware, SecurityCenter, and tool executor.
- Query PostgreSQL immutable audit logs:
  ```sql
  SELECT timestamp, event_type, user_id, action, status, metadata 
  FROM audit_events 
  WHERE timestamp >= NOW() - INTERVAL '2 hours' 
  ORDER BY timestamp DESC;
  ```
- Identify exact root causes: prompt injection payloads, suspicious tool requests, or malformed payloads.

### Step 7: Eradication & Hotfix Deployment
- Fix identified vulnerabilities:
  - If prompt injection bypassed constraints, update tool schemas or add prompt boundary defenses.
  - If a tool validation flaw was exploited, patch tool argument validators.
  - If a dependency vulnerability was identified, update packages in `requirements.txt`.
- Run automated validation:
  ```bash
  python -m ruff check backend
  python -m pytest backend/tests -ra -q
  ```
- Build and deploy updated container image via CI/CD pipeline.

### Step 8: System Recovery & State Verification
- Restart Kairo services in staging first, then deploy rolling update to production.
- Monitor startup recovery logs:
  - Verify `recover_stale_tasks_on_startup()` successfully cleans up any interrupted workflows or tasks.
  - Confirm computer control defaults to `OFF`.
- Verify health checks:
  ```bash
  curl -i https://<kairo-host>/health/ready
  ```
- If emergency stop was active, clear it under administrative supervision:
  ```bash
  curl -X POST "https://<kairo-host>/api/v1/security/emergency-stop/clear" \
    -H "Authorization: Bearer <ADMIN_TOKEN>"
  ```

### Step 9: Post-Incident Review (RCA)
- Convene a blameless Post-Incident Review within 48 hours.
- Document in a formal Root Cause Analysis (RCA) report:
  - **Timeline of events** (Detection, containment, eradication, recovery).
  - **Root cause** (What broke and why).
  - **Impact assessment** (Users affected, data exposed, system downtime).
  - **What went well** (Fast containment, logs available).
  - **Where we got lucky / What went wrong**.

### Step 10: Security Controls Enhancement & Audit Archival
- Create preventative action items and assign ticket owners.
- Add regression test cases in `backend/tests/` reproducing the incident attack vector.
- Export and cryptographically archive all relevant audit logs, database snapshots, and metric graphs for compliance and legal retention (minimum 90 days).
