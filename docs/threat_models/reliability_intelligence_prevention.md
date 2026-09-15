# Threat Model: Autonomous Reliability Intelligence & Predictive Failure Prevention (Task 90)

## 1. System Scope & Assets Protected

This threat model analyzes the security, safety, and integrity boundaries of **Task 90: Kairo Autonomous Reliability Intelligence & Predictive Failure Prevention Engine**.

### Key Assets Protected:
- **Production System Stability**: Avoiding autonomous self-induced cascading outages or crash-loops.
- **Active User Workflows**: User tasks, interactive queries, editing sessions, and background jobs.
- **Security & Authorization Boundaries**: Strict prevention of unauthorized mutations, privileged process restarts, or sandbox escapes.
- **Emergency Stop Primacy**: Absolute preemption of all proactive actions when EmergencyStop is active.
- **Cognitive & System Resources**: Prevention of budget exhaustion from runaway preventative loops or alert storms.
- **Model Calibration Integrity**: Protection against poisoned feedback loops, uncalibrated confidence scores, and undetected blind spots.

---

## 2. Threat Analysis & Mitigations

### 2.1 Threat: Adversarial Telemetry Injection / Alert Storm Flapping
- **Attack Vector**: An attacker or rogue worker emits rapidly oscillating metric values (e.g. 10MB -> 99MB -> 10MB) to induce continuous state transitions, saturate orchestrator CPU, and trigger unnecessary preventative actions.
- **Mitigation**:
  - **Bounded Window Aggregation**: `BaselineTracker` limits in-memory samples (`deque(maxlen=200)`), computing true trend rather than single-sample spikes.
  - **Anti-Flapping Hysteresis**: `SignalStateMachine` strictly requires 3 consecutive de-escalation readings before downgrading early-warning states.
  - **Temporal Deduplication**: `SignalCorrelator` maps repeating signals within correlation windows (60s) into unified clusters, discarding duplicates.

### 2.2 Threat: Forcing Service Disruption via Spurious Preventive Actions (Denial of Service)
- **Attack Vector**: A malicious actor crafts a telemetry pattern to convince the forecasting model that failure is imminent, hoping Kairo will restart critical services or drop active connections.
- **Mitigation**:
  - **Mandatory `NO_ACTION` Counterfactual**: Every candidate intervention is benchmarked against doing nothing. If net prevention value is negative or lower than `NO_ACTION`, no mutation is permitted.
  - **Minimum Intervention Principle**: Kairo enforces a strict hierarchy preferring lowest-impact, non-disruptive actions (`RELEASE_RESOURCE`, `REFRESH_POOL`) over destructive actions (`DEGRADE_COMPONENT`, `RESTART_COMPONENT`).
  - **Human Approval Gating**: Mutating actions (`RESTART_COMPONENT`, `DEGRADE_COMPONENT`) are classified as `requires_approval=True` and cannot self-authorize under standard autonomy.

### 2.3 Threat: Bypass of SecurityCenter & Governance Primacy
- **Attack Vector**: Predictive intelligence attempts to bypass Task 78 governance by tagging an action as "emergency" or "preemptive".
- **Mitigation**:
  - **Hardcoded Bridge Interceptors**: `GovernanceBridge::evaluate_authorization` is called before every non-simulation candidate execution.
  - **Zero Self-Authorization**: The forecasting model has no authorization capabilities. All action execution routes through `SecurityContext` checks in `SubsystemRecoveryAdapter`.

### 2.4 Threat: Execution During Active Emergency Stop
- **Attack Vector**: A preventative action is queued or currently executing when an operator or watchdog activates the global emergency kill switch.
- **Mitigation**:
  - **Two-Phase Kill-Switch Gating**: Emergency Stop is checked at candidate authorization in `GovernanceBridge` AND checked immediately prior to invoking any handler in `PreventionExecutorVerifier::execute_prevention`.
  - **Fail-Closed Guarantee**: If `get_emergency_stop_service().is_stopped()` is True, execution returns `PreventionStatus.CANCELLED` with error `EMERGENCY_STOP_ACTIVE`. Autonomy is forced to `STOPPED`.

### 2.5 Threat: Disruption of Active High-Priority User Workflows
- **Attack Vector**: Preventive resource rebalancing abruptly kills active user sessions or drops network connections during an active prompt transaction.
- **Mitigation**:
  - **Task 77 Active Work Protection**: `EconomyBridge::allocate_prevention_budget` checks active user reservations and rejects interventions that would disrupt running user workloads.
  - **Explicit Resource Budgeting**: Every intervention requires an approved budget token from the Resource Economy before taking system locks.

### 2.6 Threat: LLM Hallucination / Subjective Verification Fraud
- **Attack Vector**: An LLM agent is used to "evaluate" whether a fix worked, hallucinating a successful recovery when the system remains damaged.
- **Mitigation**:
  - **Zero LLM Verification Policy**: All health probes in `PreventionExecutorVerifier` are 100% deterministic (synthetic ping probes, socket connect tests, memory RSS delta checks, and circuit breaker trip queries).

### 2.7 Threat: Silent Degradation & Telemetry Blind Spots
- **Attack Vector**: A recurring failure mode bypasses early warning detection because thresholds are misconfigured or models fail silently, creating an operational blind spot.
- **Mitigation**:
  - **False Negative Audit Log**: `CalibrationManager::record_false_negative` captures unpredicted failures, classifying root cause (`MODEL_BLIND_SPOT`, `MISSING_TELEMETRY`, `SUDDEN_EXTERNAL_SHOCK`).
  - **Degraded Strategy Quarantine**: Any prevention strategy whose rolling success drops below 80% is flagged with `is_degraded=True` and surfaced prominently on the operator dashboard.

---

## 3. Threat Mitigation Verification Matrix

| Threat Category | Invariant Enforced | Verification Test / Method |
| :--- | :--- | :--- |
| Telemetry Injection & Flapping | Hysteresis requires 3 consecutive de-escalation readings | `test_early_warning_state_machine_hysteresis` |
| Alert Storm Deduplication | Multi-source spikes deduplicated into single cluster | `test_signal_correlator_deduplication` |
| Disruption via Over-Intervention | Minimum intervention and NO_ACTION counterfactual | `test_simulation_bridge_candidates_and_minimum_intervention` |
| Governance Bypass | Side-effecting restarts require explicit approval | `test_governance_bridge_approval_requirements` |
| Emergency Stop Preemption | Kill switch immediately halts prevention fail-closed | `test_governance_bridge_emergency_stop_primacy` |
| Active Work Disruption | Economy reservation protects active user sessions | `test_economy_bridge_active_work_protection` |
| Verification Hallucination | 100% non-LLM synthetic verification probes | `test_prevention_executor_and_synthetic_verification` |
| Strategy Degradation | Rolling scorecards flag strategies < 80% SLA | `test_calibration_manager_scorecards_and_degradation` |
