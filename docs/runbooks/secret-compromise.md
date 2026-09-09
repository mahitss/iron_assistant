# Incident Runbook: Secret Compromise & Key Rotation

**Incident Type**: Security Compromise / Credential Exposure  
**Severity**: P0 / Critical  
**Target**: Secrets Manager, API Keys, JWT Secrets, Database Credentials  

---

## Symptoms
- Secrets discovered committed to Git repository, printed in application logs, or leaked in an external breach.
- Unauthorized API requests detected originating from unrecognized IPs using valid admin or provider credentials.
- Cloud provider automated alerting (e.g. GitHub Secret Scanning, AWS GuardDuty) reporting active leaked credentials.

---

## 9-Step Secret Incident Procedure

### Step 1: Emergency Stop Risky Capabilities (If Required)
If the compromised secret permits write or execution access (e.g., master API token, GitHub write token, or database superuser):
- Trigger Security Center Emergency Stop immediately:
  ```bash
  curl -X POST https://kairo.ai/api/v1/security/emergency-stop \
    -H "Authorization: Bearer $EMERGENCY_MASTER_KEY" \
    -d '{"scope": "all", "reason": "Potential credential compromise underway"}'
  ```

### Step 2: Revoke Compromised Secret
Immediately revoke the credential at the upstream issuer:
- **OpenRouter / LLM Providers**: Delete API key in provider console.
- **GitHub Personal Access Token**: Revoke token in GitHub Developer Settings.
- **JWT Secret**: Invalidate current signing key.
- **Database Password**: Alter user password in PostgreSQL admin console.

### Step 3: Rotate Secret
Generate a cryptographically secure replacement secret (min 32 bytes / 256 bits):
```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```
Store the new secret in AWS Secrets Manager, HashiCorp Vault, or GitHub Repository Secrets.  
**Strict Rule: Never commit replacement secrets to the Git repository.**

### Step 4: Revoke Affected Sessions
If user auth or JWT signing keys were compromised:
- Flush Redis session tokens and refresh tokens:
  ```bash
  redis-cli --scan --pattern "kairo:session:*" | xargs -r redis-cli del
  ```
- Force all users to re-authenticate.

### Step 5: Inspect Audit Logs
Review audit logs for all actions executed using the compromised credential:
```sql
SELECT timestamp, action, user_id, ip_address, details 
FROM audit_logs 
WHERE timestamp >= NOW() - INTERVAL '48 hours'
ORDER BY timestamp DESC;
```
Identify any unauthorized tool runs, workflow mutations, or permission escalations.

### Step 6: Inspect Access & Resource Integrity
- Check for newly created admin accounts or modified authorization roles.
- Verify file system and database integrity for unauthorized modifications.

### Step 7: Deploy Corrected Configuration
Update the production secrets store and trigger a rolling restart of the application:
```bash
# Update secret in Kubernetes:
kubectl set env deployment/kairo-api --from=secret/kairo-production-secrets

# Trigger rolling restart
kubectl rollout restart deployment/kairo-api
kubectl rollout status deployment/kairo-api --timeout=180s
```

### Step 8: Verify Systems
- Lift the Emergency Stop once verified:
  ```bash
  curl -X POST https://kairo.ai/api/v1/security/emergency-resume ...
  ```
- Run the smoke test suite to confirm operational readiness:
  ```bash
  python scripts/smoke_test.py --base-url "https://kairo.ai" --env production
  ```

### Step 9: Document Incident & Post-Mortem
- Record root cause (how the secret was exposed).
- Document blast radius, affected resources, rotation timeline, and preventive actions.
- File security report under tracked incident identifier.
