# Kairo v1.0.0 End-to-End Demonstration Script

This document provides a reproducible, step-by-step demonstration of Kairo v1 capabilities, security controls, multi-agent orchestration, and safety mechanisms.

> [!NOTE]
> All actions in this demonstration run safely against local test environments or mocked external interfaces without side effects on production accounts.

---

## 1. Normal Conversation
**User Prompt:**
> "Hello Kairo! What can you help me with today?"

**Expected Behavior:**
- Fast response routed via `ModelCapability.GENERAL`.
- Concise introductory status message highlighting capabilities: research, developer tools, automation, and multi-agent coordination.
- No unnecessary agent decomposition or external tool invocations.

---

## 2. Research Question with Live Verification
**User Prompt:**
> "What are the latest features introduced in Python 3.13?"

**Expected Behavior:**
- Kairo recognizes that real-time release details are required.
- Invokes `web_search` and `web_fetch` through `ToolExecutor`.
- Returns structured answer with bracketed citations (e.g. `[1]`) referencing verified documentation.
- Clearly distinguishes between factual statements and inferred compatibility notes.

---

## 3. Local Repository Inspection
**User Prompt:**
> "Inspect the current Git repository status and recent commits on this branch."

**Expected Behavior:**
- Invokes read-only developer tools: `git_status` and `git_log`.
- `SecurityCenter` evaluates permission level as `PermissionLevel.READ` and auto-authorizes.
- Displays clean branch summary, working directory state, and latest commit hashes.

---

## 4. Multi-Agent Orchestration
**User Prompt:**
> "Research the Python 3.13 free-threaded mode, inspect our dependencies, and analyze whether upgrading will cause any issues."

**Expected Behavior:**
- `SupervisorAgent` detects query complexity and creates a decomposition plan.
- Dispatches tasks in parallel to `ResearcherAgent` (web docs) and `DeveloperAgent` (dependencies).
- Coordinates results through `AnalystAgent` for synthesis.
- Outputs structured evidence table categorized strictly as:
  - **OBSERVED**: Direct facts verified via tools.
  - **INFERRED**: Logical hypotheses based on observations.
  - **UNKNOWN**: Open questions requiring runtime verification.

---

## 5. Workflow Automation
**User Prompt:**
> "Create a scheduled workflow to monitor our CI checks every morning at 09:00 UTC."

**Expected Behavior:**
- Creates a workflow record with cron trigger `0 9 * * *`.
- Registers deterministic idempotency key generator (`sched_{workflow_id}_{timestamp}`).
- Workflow state persisted in PostgreSQL with zero authoritative state in Redis.

---

## 6. Simulated Provider Failure & Circuit Breaking
**Action:**
- Simulate temporary provider HTTP 503 errors on the OpenRouter gateway.

**Expected Behavior:**
- `CircuitBreaker` records consecutive failures without crashing the application.
- Trips to `OPEN` state after configured threshold.
- Subsequent calls fail-fast with user-friendly error:
  > *"The AI provider is temporarily unavailable. Circuit breaker active. Please try again shortly."*
- Proactively enters `HALF_OPEN` state to test recovery when timeout expires.

---

## 7. Proactive Intelligence Notification
**Action:**
- Background monitor detects a failing CI run on the main branch.

**Expected Behavior:**
- `CandidateInsight` generated with SHA-256 event fingerprint.
- `InsightDeduplicator` validates no duplicate insight was dispatched in the last 24 hours.
- Notification appears in UI notification center and surfaces concisely to the user.

---

## 8. Trigger a Risky / Destructive Action
**User Prompt:**
> "Execute test runner with clean environment: pytest backend/tests/test_v1_prompt_injection.py"

**Expected Behavior:**
- Action evaluated by `SecurityCenter`.
- Classified as `PermissionLevel.EXECUTE` / `RiskLevel.HIGH`.
- Tool execution pauses immediately; returns status `approval_required`.

---

## 9. Approval Screen in Security Center
**UI State:**
- Frontend displays pending approval card in the Security Center.
- Details: tool name (`test_runner`), exact argument payload, expiration timestamp, and risk level.
- Single-use cryptographic action fingerprint displayed.

---

## 10. Deny the Action
**Action:**
- User clicks **"Deny"** and provides optional reason: *"Not ready to run tests right now."*

**Expected Behavior:**
- Approval status transitions to `DENIED`.
- `ToolExecutor` immediately discards execution without calling subprocess.
- Clean user response: *"Action 'test_runner' was denied by user."*

---

## 11. Review Immutable Audit Log
**Action:**
- Navigate to **Security Center -> Audit Log** (`GET /api/v1/security/audit`).

**Expected Behavior:**
- Displays append-only audit records for:
  - Tool execution request
  - Security authorization check
  - Approval request creation
  - User denial event with timestamp and actor ID
- All records tamper-evident and permanently recorded.

---

## 12. Emergency Stop Kill Switch
**Action:**
- Click **"Emergency Stop"** button in top bar or POST `/api/v1/security/emergency-stop`.

**Expected Behavior:**
- Emergency stop status transitions to `ACTIVE` across all sessions.
- System banner: *"EMERGENCY STOP ACTIVE - All side-effecting tools and agents halted."*
- Any attempt to invoke write, execute, or external tools immediately raises `EmergencyStopActiveError`.

---

## 13. Capability Controls
**Action:**
- Inspect **Capability Toggles** in Security Center.
- Confirm `computer_control` is disabled by default.
- Toggle individual capabilities (Web Research, Developer Tools, Voice, Vision).
- Audit log records `capability.changed` event.

---

## 14. Session Summary
**User Prompt:**
> "Kairo, summarize what actions and security events occurred in this session."

**Expected Behavior:**
- Kairo queries the conversation memory and audit events.
- Produces a concise, factual summary:
  - Researched Python 3.13 features.
  - Multi-agent investigation completed.
  - Automated workflow created.
  - One test execution requested, paused for approval, and denied.
  - Emergency Stop demonstrated and reset.
- No hidden chain-of-thought or internal system instructions exposed.
