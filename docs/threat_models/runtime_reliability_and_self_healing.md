# Threat Model: Autonomous Runtime Reliability, Fault Injection & Self-Healing

## 1. Overview & Scope

The Kairo Self-Healing Subsystem monitors runtime execution, detects failures, correlates root causes, reserves recovery resources, applies bounded recovery strategies, verifies system health, and conducts controlled chaos drills.

Because self-healing mechanisms have the power to restart processes, manipulate connections, and allocate system resources, the recovery engine itself is a high-value target for adversaries seeking denial of service, privilege escalation, or resource exhaustion.

---

## 2. Threat Analysis Matrix (STRIDE)

| Threat ID | Category | Threat Scenario | Impact | Severity | Mitigation Strategy |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TH-REL-01** | Denial of Service | **Crash Loop Amplification**: Adversary repeatedly triggers a deterministic panic in a native worker, causing the recovery engine to enter an endless restart loop that starves the CPU/OS. | System unresponsiveness, host thread starvation | **High** | `FailureDetector` crash loop circuit breaker limits restarts to 3 per 60s window, transitioning immediately to `DEGRADE_CAPABILITY` or `ESCALATE`. |
| **TH-REL-02** | Denial of Service | **Recovery Budget Exhaustion**: Rapid influx of artificial failures exhausts cognitive budgets, memory, and task execution slots. | DoS for legitimate agent workflows | **High** | Every recovery action must reserve a bounded budget via Task 77 Resource Economy before execution. Requests exceeding the recovery budget are escalated rather than retried. |
| **TH-REL-03** | Information Disclosure | **Secret Leakage in Forensic Logs**: Sensitive user passwords, API keys, or JWT tokens embedded in error traces are written to unencrypted audit records or telemetry streams. | Credential theft, unauthorized account access | **High** | Multi-pattern regex redactor (`sanitize_message`, `sanitize_payload`) scrubs Bearer tokens, private keys, API keys, and connection strings prior to persistence or event emission. |
| **TH-REL-04** | Tampering / Spoofing | **Phantom Verification Spoofing**: An attacker simulates a healthy recovery signal or suppresses errors during the stability window to trick the engine into prematurely marking a corrupted service `RESOLVED`. | Undetected corruption, silent state drift | **Medium** | Verification never relies on simple return codes or LLM judgment; `RecoveryVerifier` issues active synthetic probes (e.g. `sandbox.hash`, IPC ping) and monitors a mandatory 15-second stability window. |
| **TH-REL-05** | Elevation of Privilege | **Unauthorized Fault Injection**: Malicious user or unauthenticated workflow invokes `/api/v1/reliability/faults/inject` to inject synthetic crashes or drop network connections. | Host disruption, unauthorized denial of service | **Critical** | Chaos injection is globally disabled by default. Enabling requires explicit admin configuration, and triggering requires an authenticated caller identity in `("admin", "test_runner", "chaos_controller")`. |
| **TH-REL-06** | Bypassing Security | **Emergency Stop Circumvention**: Autonomous self-healing attempts to restart a quarantined process or re-enable network sockets after a human operator has triggered Emergency Stop. | Violation of human operator authority, rogue agent activity | **Critical** | `RecoveryEngine.authorize_recovery()` unconditionally checks `is_emergency_stopped()`. If active, all recoveries are denied with `EMERGENCY_STOP_ACTIVE`. |
| **TH-REL-07** | Tampering | **Cascading Root Cause Masking**: Downstream victim failures overwhelm the system, causing the engine to misattribute root causes and apply incorrect recovery strategies. | Prolonged outage, wasted recovery cycles | **Medium** | `RootCauseCorrelator` analyzes topological dependency precedence (`SYSTEM_DEPENDENCY_EDGES`), ensuring upstream failures (DB, Rust daemon) always take precedence over downstream tool failures. |

---

## 3. Detailed Threat Mitigations & Invariants

### 3.1 Unconditional Emergency Stop Gating
```python
if self.is_emergency_stopped(user_id):
    logger.critical("Recovery DENIED: EmergencyStop is ACTIVE for user %s", user_id)
    return False, "EMERGENCY_STOP_ACTIVE", None
```
Under no circumstances may an automated recovery routine restart a process, reopen a network socket, or reconnect a database while an Emergency Stop condition is active.

### 3.2 Anti-Crash Loop Guarantee
```python
if is_crash_loop:
    logger.warning("Crash loop active for %s: selecting DEGRADE_CAPABILITY or ESCALATE", comp)
    if ftype in (FailureType.PROCESS_FAILURE, FailureType.RUNTIME_FAILURE, FailureType.SANDBOX_FAILURE):
        return self._create_strategy(RecoveryStrategyType.DEGRADE_CAPABILITY, comp)
    return self._create_strategy(RecoveryStrategyType.ESCALATE, comp)
```
Blind restarts are strictly bounded. The engine will degrade the subsystem (disabling native acceleration in favor of safer fallback mechanisms) rather than allow an infinite restart cycle.

### 3.3 Zero-Trust Secret Redaction
All incoming exceptions and metadata are processed through deterministic sanitization:
```python
def sanitize_message(msg: str | None) -> str:
    if not msg:
        return ""
    sanitized = str(msg)
    for pattern, replacement in _REDACTION_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized
```
Tokens are replaced with `[REDACTED_TOKEN]` or `[REDACTED_API_KEY]`, preventing credential leakage into logs, telemetry, or UI views.

---

## 4. Verification & Testing Matrix

| Threat Vector | Test Function | Test File | Status |
| :--- | :--- | :--- | :--- |
| **TH-REL-01** (Crash Loop) | `test_crash_loop_circuit_breaker` | `tests/test_reliability_and_self_healing.py` | **PASS** |
| **TH-REL-02** (Budget Exhaustion) | `test_recovery_resource_budget_lifecycle` | `tests/test_reliability_and_self_healing.py` | **PASS** |
| **TH-REL-03** (Secret Leakage) | `test_sensitive_data_sanitization` | `tests/test_reliability_and_self_healing.py` | **PASS** |
| **TH-REL-04** (Phantom Verification) | `test_deterministic_non_llm_verification` | `tests/test_reliability_and_self_healing.py` | **PASS** |
| **TH-REL-05** (Unauthorized Faults) | `test_fault_injection_guardrail_blocking` | `tests/test_reliability_and_self_healing.py` | **PASS** |
| **TH-REL-06** (E-Stop Circumvention) | `test_emergency_stop_halts_recovery` | `tests/test_reliability_and_self_healing.py` | **PASS** |
| **TH-REL-07** (Causal Misattribution) | `test_root_cause_correlation_across_subsystems` | `tests/test_reliability_and_self_healing.py` | **PASS** |
