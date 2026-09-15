# Autonomous Runtime Reliability, Fault Injection & Deterministic Self-Healing

## 1. Architectural Boundary & Core Philosophy

Kairo enforces an uncompromising division of responsibility across the intelligence and execution boundary:
- **Python (The Brain)**: Reasoning, policy, intent classification, causal graphs, blast-radius estimation, bounded recovery selection, governance gating, cognitive budget reservations, metacognitive learning, and operator approvals.
- **Rust (The Body)**: Native process execution, sandboxing, low-level error signaling, telemetry propagation, raw pipe communication, and emergency-stop execution.

### Fundamental Self-Healing Invariants

1. **Non-LLM Deterministic Recovery & Verification**: LLMs are never permitted to generate or arbitrate low-level recovery actions or decide whether a system has recovered. Recovery strategy selection is strictly governed by deterministic rule matrices, and post-recovery health is validated via synthetic health probes.
2. **Emergency Stop Absolute Priority**: If an operator or system emergency stop is triggered, all autonomous recovery attempts are immediately halted (`EMERGENCY_STOP_ACTIVE`). No self-healing routine may override an active kill-switch.
3. **Crash Loop Circuit Breaking**: If a component encounters repeated crashes exceeding the configured restart ceiling (default: 3 restarts within 60s), automatic process restarts are terminated immediately. The system shifts to graceful capability degradation or human escalation.
4. **Zero Secret Leakage**: All raw error messages, traces, and metadata payloads are sanitized through multi-pattern regex redaction prior to logging, event emission, or persistence.
5. **Bounded Cognitive & Resource Economy Budgeting**: Every recovery attempt must reserve resources via Task 77 Resource Economy prior to execution and release them upon completion. Runaway recovery loops that consume infinite CPU/memory are architecturally impossible.

---

## 2. Failure Detection, Taxonomy & Sanitization

Failures from the native runtime daemon, IPC transport, child sandboxes, network layer, or Python async workers are ingested by the `FailureClassifier` and normalized into canonical `FailureRecord`s.

### Typed Failure Taxonomy

| FailureType | Canonical Description | Default Severity | Recoverability | Retryability |
| :--- | :--- | :--- | :--- | :--- |
| `PROCESS_FAILURE` | Native runtime worker exit, SIGSEGV, SIGKILL, fatal crash | P1 | True | False |
| `IPC_FAILURE` | Pipe disconnected, connection refused/reset, broken pipe | P2 | True | True |
| `PROTOCOL_FAILURE`| Malformed envelope, version mismatch, invalid handshake | P2 | True | False |
| `SANDBOX_FAILURE` | MMU violation, job object termination, path traversal | P1 | True | False |
| `RESOURCE_FAILURE`| Memory, CPU, or disk quota exceeded | P2 | True | False |
| `MEMORY_PRESSURE` | Cgroup/process memory ceiling hit | P1 | True | False |
| `TIMEOUT` | Async/sync operation exceeded duration threshold | P3 | True | True |
| `DEADLINE_EXCEEDED`| Request deadline exceeded client expiration | P2 | True | False |
| `NETWORK_FAILURE` | Connection reset, TLS handshake failure, DNS failure | P2 | True | True |
| `TOOL_FAILURE` | Native tool returned non-zero or crashed | P2 | True | Dynamic |
| `CORRUPTION` | Data checksum mismatch or storage corruption | P0 | False | False |
| `UNKNOWN_FAILURE` | Unclassified generic exception | P2 | True | False |

### Sensitive Data Redaction Patterns

The `sanitize_message` and `sanitize_payload` engines inspect and redact:
- Authorization Bearer tokens: `Bearer [REDACTED_TOKEN]`
- OpenAI / Third-party API keys: `sk-...` -> `[REDACTED_API_KEY]`
- Passwords and secrets in connection strings or JSON objects -> `[REDACTED]`
- Database connection strings (`postgres://...`, `redis://...`) -> `[REDACTED_DATABASE_URL]`
- Private cryptographic keys (`BEGIN ... PRIVATE KEY`) -> `[REDACTED_PRIVATE_KEY]`

---

## 3. Fingerprinting, Storms & Crash Loops

### Deterministic Deduplication Fingerprints

Each failure generates a 16-character SHA-256 fingerprint:
$$\text{Fingerprint} = \text{SHA256}(\text{component} \parallel \text{failure\_type} \parallel \text{operation} \parallel \text{normalized\_msg})[:16]$$

This allows deduplication of identical failure cascades across sliding time windows (`dedup_window_seconds = 5.0s`).

### Storm Detection

If more than 5 identical failure fingerprints arrive within a sliding window of 10 seconds, `detect_storm()` flags the incident as a failure storm, suppressing redundant downstream recovery workflows and triggering aggregated incident reporting.

### Crash Loop Circuit Breaker

`FailureDetector` maintains a sliding restart history per component.
- If $\ge 3$ restarts occur within 60 seconds, `is_in_crash_loop(component)` transitions to `True`.
- `RecoveryEngine` immediately rejects `RESTART_PROCESS` or `RESTART_COMPONENT` actions.
- The system automatically selects `DEGRADE_CAPABILITY` (disabling non-critical native features while keeping core services alive) or `ESCALATE` (notifying the operator).

---

## 4. Root-Cause Correlation & Blast Radius

### Causal Graph Analysis (`RootCauseCorrelator`)

When a failure occurs, the correlator evaluates active failures in the window using:
1. **Direct Causation (`causation_id`)**: If a failure explicitly references another failure's ID.
2. **Trace / Correlation ID Matching**: Grouping failures that share a distributed trace or execution correlation ID.
3. **Topological Dependency Precedence**:
   - `database` $\to$ `workflow`, `memory`, `auth`, `tasks`
   - `native_runtime` $\to$ `native_tool`, `sandbox`, `computer`, `network_fabric`
   - `network_fabric` $\to$ `web_research`, `http_fetch`, `external_api`

If the native runtime crashes, downstream tool failures are correctly attributed to the parent `native_runtime` outage rather than misdiagnosed as individual tool bugs.

### Blast-Radius Calculation (`BlastRadiusAnalyzer`)

Estimates the systemic ripple effect of an outage:
- **Systemic Impact Score**: Computed based on severity (P0 = 1.0, P1 = 0.75, P2 = 0.5, P3 = 0.25) and multiplied across dependency edges.
- **Affected Subsystems**: Downstream services impacted by the primary failure.
- **Precautionary Containment Flag**: Mandatory for all P0 and P1 incidents.

---

## 5. Bounded Recovery Ladder & Governance Gating

### Strategy Ladder

```
[Level 1: Safe Read Retry]   --> Idempotent retry with exponential backoff
[Level 2: Transport Reconnect] --> Re-establish IPC pipe or reconnect pool
[Level 3: Resource Reconcile]  --> Clean orphaned processes, release memory
[Level 4: Component Restart]   --> Bounded restart (blocked if in crash loop)
[Level 5: Degrade Capability]  --> Disable optional features, maintain core
[Level 6: Human Escalation]    --> Request operator approval or intervention
```

### Risk Gating (`SafeRecoveryClass`)

| Strategy | Risk Class | Requires Approval? | Max Attempts | Cooldown |
| :--- | :--- | :--- | :--- | :--- |
| `RETRY` | `LOW_RISK_RECOVERY` | No | 3 | 1.0s |
| `RECONNECT` | `LOW_RISK_RECOVERY` | No | 3 | 2.0s |
| `RECONCILE_RESOURCE` | `MODERATE_RECOVERY` | No | 2 | 5.0s |
| `RESTART_COMPONENT` | `MODERATE_RECOVERY` | No | 2 | 10.0s |
| `ROLLBACK_SAFE_STATE` | `HIGH_RISK_RECOVERY` | **Yes (Operator)** | 1 | 30.0s |
| `FAILOVER` | `HIGH_RISK_RECOVERY` | **Yes (Operator)** | 1 | 60.0s |
| `ESCALATE` | `READ_ONLY_DIAGNOSTIC` | No | 1 | 0.0s |

---

## 6. Non-LLM Verification & Stability Windows

Upon executing a recovery action, `RecoveryVerifier` executes deterministic health probes:
1. **Native Ping/Health Probe**: Direct IPC ping request with deadline $\le 2000\text{ms}$.
2. **Capability Attestation Probe**: Validates that capability fingerprints match expected runtime states.
3. **Synthetic Tool Execution**: Dispatches `sandbox.echo` or `sandbox.hash` to confirm round-trip execution integrity.

### Stability Window Monitoring

When verification passes, the incident transitions to `MONITORING`:
- A clean window (default: 15 seconds) is observed.
- If any correlated failure recurs during the stability window, the incident transitions back to `RECOVERING` and escalates along the strategy ladder.
- If no failures occur throughout the window, the incident transitions to `RESOLVED` and then `CLOSED`.

---

## 7. Metacognitive Calibration & Forensic Evidence

Every recovery attempt generates an immutable `RecoveryEvidenceRecord`:
- Exact timestamp and duration.
- Before-state vs After-state telemetry snapshots.
- Strategy applied, parameters, and reservation IDs.
- Deterministic verification probe result and latency.
- Cryptographic provenance and hash.

`ReliabilityLearner` consumes this evidence to update strategy confidence calibration scores, enabling autonomous optimization of future strategy rankings without mutating code or prompting an LLM.

---

## 8. Controlled Chaos & Fault Injection Guardrails

`FaultInjectionEngine` provides programmatic chaos testing with rigid safety bounds:
- **Disabled by Default**: Fault injection is permanently disabled in production.
- **Admin Authentication**: Only callers with validated admin identities (`admin`, `test_runner`, `chaos_controller`) can trigger faults.
- **Pre-Configured Scenarios Only**: Only registered scenarios (`rust_crash_after_dispatch`, `ipc_disconnect_before_result`, `memory_pressure_burst`, `ssrf_dns_poisoning`, `workflow_deadlock`) can be executed.
- **Audit Logging**: Every injected fault is immutably logged with caller identity, parameters, and timestamp.
