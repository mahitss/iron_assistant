# Kairo Autonomous Reliability Intelligence & Predictive Failure Prevention Engine (Task 90)

## 1. Architectural Overview & Boundaries

Task 90 establishes Kairo's **Autonomous Reliability Intelligence & Predictive Failure Prevention Engine**. It shifts Kairo from *reactively repairing failures* after outages occur to *detecting early precursors, forecasting time-to-threshold, identifying causal drivers, simulating interventions against a mandatory NO_ACTION counterfactual baseline, selecting minimum-intervention actions, authorizing through governance, executing safely, and deterministically verifying health without LLM involvement*.

Crucially, Task 90 **does not reinvent or duplicate** existing engines. Instead, it serves as the master intelligence orchestrator delegating across 10 specialized foundational engines:

```
+----------------------------------------------------------------------------------------------------+
|                         KAIRO RELIABILITY INTELLIGENCE & PREVENTION LAYER                          |
|                                                                                                    |
|   +-------------------+    +--------------------+    +-------------------+    +----------------+   |
|   | Dynamic Baselines | -> | Rate-of-Change     | -> | State Machine     | -> | Deduplication  |   |
|   | & Trend Detection |    | & Time-to-Thresh   |    | (Anti-Flapping)   |    | Correlator     |   |
|   +-------------------+    +--------------------+    +-------------------+    +----------------+   |
+-------------|------------------------|------------------------|-----------------------|------------+
              |                        |                        |                       |
              v                        v                        v                       v
     [Task 74 Forecasting]    [Task 73 Causal DAG]   [Task 75 Risk Traversal]  [Task 89 Simulation]
     Multi-horizon failure    Trigger, condition &   Blast radius & affected   Counterfactual models
     probability & window     mechanism diagnosis    downstream workflows      & NO_ACTION baseline
              |                        |                        |                       |
              +------------------------+------------------------+-----------------------+
                                       |
                                       v
                     +-----------------------------------+
                     | Minimum Intervention Selection    |
                     | Highest reversibility & net value |
                     +-----------------+-----------------+
                                       |
              +------------------------+------------------------+
              v                                                 v
     [Task 78 Governance & SecurityCenter]            [Task 77 Resource Economy]
     EmergencyStop kill-switch primacy,               Cognitive budget reservation,
     autonomy adaptation & approval gating            active user work protection
              |                                                 |
              +------------------------+------------------------+
                                       |
                                       v
                     +-----------------------------------+
                     | Deterministic Execution Verifier  |
                     | Non-LLM synthetic health probes & |
                     | Task 86 Observability Event Bus   |
                     +-----------------+-----------------+
                                       |
                                       v
                     +-----------------------------------+
                     | Metacognitive Calibration Engine  |
                     | Prediction-vs-reality tracking,   |
                     | blind spots & strategy scorecards |
                     +-----------------------------------+
```

---

## 2. Core Safety Invariants

1. **Mandatory `NO_ACTION` Counterfactual Baseline:**
   - Every prevention candidate is evaluated against the counterfactual scenario of doing nothing.
   - If `NO_ACTION` produces equal or better expected outcome, or if no intervention achieves a positive net prevention value (`avoided_loss - cost - risk + reversibility_bonus`), `NO_ACTION` is explicitly selected and logged.
2. **Minimum Intervention Principle:**
   - When multiple actions can prevent the failure, Kairo selects the lowest-impact, smallest-scope, highest-reversibility action (e.g. `RELEASE_RESOURCE` or `REFRESH_POOL` before considering `DEGRADE_COMPONENT` or `RESTART_COMPONENT`).
3. **Zero Security Bypass & Emergency Stop Primacy:**
   - Predictions cannot self-authorize.
   - If the global `EmergencyStop` is active, all proactive mutating actions are rejected immediately fail-closed with status `EMERGENCY_STOP_ACTIVE`. Autonomy is forced to `STOPPED`.
   - Actions with side-effects or high blast radius require human governance approval.
4. **Zero LLM Verification:**
   - Health verification post-intervention uses deterministic synthetic probes, metric delta checks, and active ping tests.
   - No subjective LLM reasoning is permitted in deciding whether an intervention succeeded or failed.
5. **Active Work Protection:**
   - Preventive actions cannot disrupt active, high-priority user workflows.
   - Interventions must acquire a cognitive and system budget from Task 77 Resource Economy before proceeding.
6. **Anti-Flapping State Machine & Hysteresis:**
   - State escalations (`NORMAL` -> `WATCH` -> `ELEVATED` -> `HIGH` -> `CRITICAL` -> `IMMINENT`) occur promptly.
   - De-escalations strictly require 3 consecutive readings below threshold to eliminate oscillation and alert flapping.
7. **Structured Decision Transparency:**
   - All operator-facing explanations follow the rigid 9-element structure:
     `PROBLEM`, `EVIDENCE`, `EXPECTED IMPACT`, `OPTIONS`, `SELECTED ACTION`, `WHY`, `CONFIDENCE`, `UNCERTAINTY`, `VERIFICATION`.
   - Zero raw internal prompt chains are leaked.

---

## 3. Subsystem Architecture

### 3.1 Dynamic Baselines & Trend Engine (`baselines.py`)
- Maintains rolling, bounded-window metric histories (`deque(maxlen=N)`).
- Computes mean, variance, standard deviation, and freshness confidence penalties.
- Empirically determines metric trend: `INCREASING`, `DECREASING`, `STABLE`, `OSCILLATING`, `VOLATILE`, `UNKNOWN`.
- Computes linear regression rate-of-change ($\frac{\Delta}{\text{min}}$) and projects time-to-threshold with explicit uncertainty intervals (e.g. `4.2–7.0 min`).

### 3.2 Signal State Machine & Deduplication (`signals.py`)
- `SignalStateMachine`: Implements hysteresis gating across 6 discrete states.
- `SignalCorrelator`: Deduplicates multi-source telemetry spikes into a unified incident cluster within correlation time windows (default 60s), suppressing alert storms.

### 3.3 Integration Bridges (`*_bridge.py`)
- `ForecastingBridge`: Interfaces with Task 74 (`default_prediction_service`) to synthesize failure probability across horizons (`IMMEDIATE`, `SHORT`, `MEDIUM`, `LONG`).
- `CausalBridge`: Interfaces with Task 73 causal root-cause models to isolate primary triggers, underlying conditions, mechanisms, and contributing factors.
- `RiskBridge`: Interfaces with Task 75 risk propagation graphs to evaluate blast radius, affected dependencies, and downstream workflows.
- `SimulationBridge`: Interfaces with Task 89 digital twin simulation kernels to evaluate candidates against `NO_ACTION` and compute net prevention value.
- `GovernanceBridge`: Interfaces with Task 78 governance and `EmergencyStopService`. Dynamically adapts operational autonomy:
  - `NORMAL` -> `FULL`
  - `WATCH` -> `CAUTIOUS`
  - `ELEVATED` -> `CAUTIOUS`
  - `HIGH` -> `RESTRICTED`
  - `CRITICAL` / `IMMINENT` -> `RESTRICTED`
  - `EMERGENCY_STOP` -> `STOPPED`
- `EconomyBridge`: Interfaces with Task 77 cognitive budget manager to reserve compute allowances and protect active tasks.

### 3.4 Deterministic Execution Verifier (`execution_verifier.py`)
- Coordinates preventive remediation through Task 88 `SubsystemRecoveryAdapter`.
- Runs deterministic post-action synthetic health checks (`ping`, `memory_pressure_check`, `circuit_breaker_status`).
- Emits structured telemetry events to Task 86 Native Observability Fabric (`kairo.reliability.*`).

### 3.5 Metacognitive Calibration Engine (`calibration.py`)
- Compares failure predictions against actual ground-truth outcomes.
- Tracks False Positives (over-alerting / wasted compute) and False Negatives (missed failures / model blind spots).
- Maintains per-strategy effectiveness scorecards.
- Flags degraded strategies whose rolling success rate drops below the 80% SLA.

### 3.6 Master Service Coordinator (`service.py`)
- Single entry-point coordinating telemetry ingestion, correlation, forecasting, causal analysis, simulation, authorization, execution, verification, and calibration.
- Supports proactive background polling (`run_periodic_evaluation`) and manual on-demand triggers.

---

## 4. REST API Reference

All endpoints are mounted under `/api/v1/reliability-intelligence`:

| Method | Path | Description |
|---|---|---|
| `GET` | `/status` | Subsystem status, active signals, current autonomy level, and degradation state. |
| `POST` | `/evaluate` | Ingests a raw telemetry reading and executes the complete prevention loop if elevated. |
| `GET` | `/signals` | Retrieves currently active precursor signals with correlation IDs. |
| `GET` | `/incidents` | Retrieves historical predictive incidents with structured decision explanations. |
| `GET` | `/baselines` | Retrieves learned baseline statistics and rates of change for all components. |
| `GET` | `/calibration` | Retrieves calibration metrics, scorecards, false positive/negative counts, and degraded strategies. |
| `POST` | `/incidents/{id}/approve` | Grants operator approval for pending high-risk prevention candidates. |
| `POST` | `/calibration/ground-truth` | Records actual operational outcome for prediction-vs-reality calibration. |

---

## 5. UI Operator Surface

Integrated into the **Kairo Resource Center** (`frontend/components/orchestration/resourceCenterView.js`) under Subtab 15 (`intelligence`):
- **KPI Summary Grid**: Operational Autonomy Badge, Active Signals Count, Prevention Rate %, Degradation Alert Badge.
- **Active Predictive Incidents Feed**: Displays live early warnings, failure horizons, blast radius scores, and non-LLM verification badges.
- **Structured 9-Element Decision Explanations**: Expandable cards revealing `PROBLEM`, `EVIDENCE`, `OPTIONS`, `WHY`, and `VERIFICATION`.
- **Strategy Scorecard Table**: Per-strategy success rates, attempt counters, and degradation warnings (< 80% SLA).
- **Interactive Evaluation Trigger**: `#btn-evaluate-telemetry` for immediate on-demand telemetry analysis drills.
