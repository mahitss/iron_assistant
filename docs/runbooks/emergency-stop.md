# Incident Runbook: Emergency Stop & Capability Kill Switches

**Incident Type**: Security Intervention / System Halting  
**Severity**: P0 / Critical  
**Target**: Kairo Security Center & Autonomous Capability Engine  

---

## Symptoms
- Autonomous agent performing unintended or destructive actions (e.g. unexpected computer control movements, rogue browser form submissions, unauthorized GitHub repository mutations).
- Security breach or operator command requiring instant cessation of all autonomous execution.
- Alert firing: `SecurityViolationTriggered` or `EmergencyStopEngaged`.

---

## Checks
1. **Security Center Status**:
   - Check current Security Center status via API or dashboard:
     ```bash
     curl -fsS https://kairo.ai/api/v1/security/status \
       -H "Authorization: Bearer $SECURITY_ADMIN_TOKEN"
     ```
2. **Active Tasks and Sockets**:
   - Verify if computer control or browser automation sessions are actively running.
   - Inspect active worker queue lengths.

---

## Safe Actions & Kill Switch Options
The Security Center remains the single authoritative source of truth for capability governance. Do not bypass the Security Center.

### Level 1: Granular Capability Kill Switches
Disable specific risky capabilities instantly without taking the entire API down:

1. **Disable Computer Control**:
   ```bash
   curl -X POST https://kairo.ai/api/v1/security/kill-switch \
     -H "Authorization: Bearer $SECURITY_ADMIN_TOKEN" \
     -d '{"capability": "computer_control", "enabled": false, "reason": "Operator intervention"}'
   ```
2. **Disable Browser External Actions (Form Submissions / Clicks)**:
   ```bash
   curl -X POST https://kairo.ai/api/v1/security/kill-switch \
     -H "Authorization: Bearer $SECURITY_ADMIN_TOKEN" \
     -d '{"capability": "browser_external_actions", "enabled": false}'
   ```
3. **Disable GitHub Writes (PR creation / comment posts)**:
   ```bash
   curl -X POST https://kairo.ai/api/v1/security/kill-switch \
     -H "Authorization: Bearer $SECURITY_ADMIN_TOKEN" \
     -d '{"capability": "github_writes", "enabled": false}'
   ```
4. **Disable Automation Writes & Proactive Execution**:
   ```bash
   curl -X POST https://kairo.ai/api/v1/security/kill-switch \
     -H "Authorization: Bearer $SECURITY_ADMIN_TOKEN" \
     -d '{"capability": "automation_execution", "enabled": false}'
   ```

### Level 2: Full System Emergency Stop
Halt all running workflows, agent executions, and tool calls immediately:
```bash
curl -X POST https://kairo.ai/api/v1/security/emergency-stop \
  -H "Authorization: Bearer $SECURITY_ADMIN_TOKEN" \
  -d '{"scope": "all", "reason": "Critical containment required"}'
```

---

## Recovery & Resumption
1. **Investigate Offending Operation**:
   - Inspect audit trail: `SELECT * FROM audit_logs WHERE timestamp >= NOW() - INTERVAL '30 minutes';`
   - Identify prompt, tool call, or workflow that prompted the emergency intervention.
2. **Apply Policy Patch or Constraints**:
   - Update permission policies, approval requirements, or tool execution restrictions.
3. **Resume Capabilities**:
   - Lift emergency stop and selectively re-enable capabilities:
     ```bash
     curl -X POST https://kairo.ai/api/v1/security/emergency-resume \
       -H "Authorization: Bearer $SECURITY_ADMIN_TOKEN"
     ```

---

## Verification
- Verify Security Center status endpoint reports capabilities restored to desired state:
  ```bash
  curl -fsS https://kairo.ai/api/v1/security/status -H "Authorization: Bearer $SECURITY_ADMIN_TOKEN"
  ```
- Confirm audit log captures emergency stop activation and resumption events.
- Operations Dashboard reflects `security: "HEALTHY"`.
