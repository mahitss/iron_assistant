# Incident Runbook: Authentication & Authorization Incident

**Incident Type**: Security Anomaly / Auth Compromise  
**Severity**: P0 / Critical  
**Target**: JWT Auth Gateway, RBAC Permissions, & Security Center  

---

## Symptoms
- Alert firing: `AuthFailureSpike` (> 50 failed login attempts per minute) or `UnauthorizedAccessSpike`.
- Multiple HTTP 401 Unauthorized or HTTP 403 Forbidden errors across legitimate client sessions.
- Invalidation or unexpected expiration of valid JWT tokens.
- Operations Dashboard shows elevated security alerts or `security: "DEGRADED"`.

---

## Checks
1. **Assign Incident Identifier**:
   - Generate tracked incident ID: `generate_incident_id("AUTH")`.
2. **Audit Log Inspection**:
   - Query security audit trail:
     ```sql
     SELECT id, timestamp, action, user_id, ip_address, status, details 
     FROM audit_logs 
     WHERE action IN ('LOGIN_FAILED', 'PERMISSION_DENIED', 'TOKEN_INVALID') 
     ORDER BY timestamp DESC LIMIT 50;
     ```
   - Determine whether failures originate from a single IP address (brute force attack) or across all users (signing key mismatch / auth provider bug).
3. **JWT Signing Secret & Clock Skew**:
   - Verify server time synchronization across API pods:
     ```bash
     kubectl exec -it <pod-name> -- date -u
     ```
     NTP drift > 30 seconds can cause valid JWTs to be rejected as expired or not yet valid.
4. **Token Blacklist / Redis Session Store**:
   - Verify Redis connectivity where revoked JWT tokens or active user sessions are stored.

---

## Safe Actions
- **Do Not** disable authentication or permit anonymous fallback in production under any circumstance.
- **Do Not** print or log raw user passwords, cleartext tokens, or secret keys in incident chat or logs.
- Block offending IP addresses at the edge CDN / Web Application Firewall (WAF) if a brute-force or credential stuffing attack is detected.

---

## Recovery
1. **If Brute Force / Distributed Attack**:
   - Apply rate-limiting IP blocks at AWS WAF or Cloudflare edge rules.
   - Enforce account lockout thresholds after 5 consecutive failed attempts.
2. **If JWT Secret Key Compromise**:
   - Immediately follow `docs/runbooks/secret-compromise.md`.
   - Rotate JWT signing secret, immediately invalidating all active sessions and requiring re-login.
3. **If Clock Skew**:
   - Synchronize chrony/NTP daemons across Kubernetes cluster host nodes.
4. **If Redis Session Cache Failure**:
   - Follow `docs/runbooks/redis-down.md` to restore session validation cache.

---

## Verification
- Test user login and token generation:
  ```bash
  curl -fsS -X POST https://kairo.ai/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"ValidTestPassword123!"}'
  ```
- Probe authenticated endpoint with generated token to verify HTTP 200.
- Verify audit log records successful login event with user ID and timestamp.
- Confirm Operations Dashboard reflects `security: "HEALTHY"`.
