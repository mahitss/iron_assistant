# KAIRO Autonomous Cognitive Control Plane & Unified Operating Loop (Task 102)

## 1. Executive Architectural Overview

The **Autonomous Cognitive Control Plane** serves as Kairo's central supervisory coordination fabric. Rather than acting as a redundant reasoning authority or an unconstrained LLM loop, the Control Plane orchestrates the 16 existing specialized intelligence systems into one coherent, bounded, safe, and verifiable autonomous operating cycle.

```
                 ┌──────────────────────────────────────┐
                 │                USER                  │
                 └──────────────────┬───────────────────┘
                                    │ (Natural Intent / Policies)
                                    ▼
                 ┌──────────────────────────────────────┐
                 │            CONTROL PLANE             │
                 │      (Supervisory Orchestrator)      │
                 └──────────────────┬───────────────────┘
                                    │
       ┌────────────────────────────┴────────────────────────────┐
       ▼                                                         ▼
┌──────────────┐                                          ┌──────────────┐
│  WORLD-STATE │ (Task 98)                                │  SELF-MODEL  │ (Task 101)
│  (Reconciled │                                          │  (Capability │
│   Reality)   │                                          │   Readiness) │
└──────┬───────┘                                          └──────┬───────┘
       └────────────────────────────┬────────────────────────────┘
                                    ▼
                 ┌──────────────────────────────────────┐
                 │         SITUATION AWARENESS          │ (Task 99)
                 └──────────────────┬───────────────────┘
                                    ▼
                 ┌──────────────────────────────────────┐
                 │               ATTENTION              │ (Task 60)
                 └──────────────────┬───────────────────┘
                                    ▼
                 ┌──────────────────────────────────────┐
                 │           MISSIONS & GOALS           │ (Task 100)
                 └──────────────────┬───────────────────┘
                                    ▼
                 ┌──────────────────────────────────────┐
                 │               PLANNING               │ (Task 58)
                 └──────────────────┬───────────────────┘
                                    ▼
                 ┌──────────────────────────────────────┐
                 │        DECISION INTELLIGENCE         │ (Task 94/96)
                 └──────────────────┬───────────────────┘
                                    ▼
                 ┌──────────────────────────────────────┐
                 │    SECURITY / GOVERNANCE / APPROVAL  │ (Task 74)
                 └──────────────────┬───────────────────┘
                                    ▼
                 ┌──────────────────────────────────────┐
                 │           RESOURCE ECONOMY           │ (Task 77)
                 └──────────────────┬───────────────────┘
                                    ▼
                 ┌──────────────────────────────────────┐
                 │          ACTION TRANSACTION          │ (Task 95)
                 └──────────────────┬───────────────────┘
                                    ▼
                 ┌──────────────────────────────────────┐
                 │       TOOL / RUST EXECUTION          │
                 └──────────────────┬───────────────────┘
                                    ▼
                 ┌──────────────────────────────────────┐
                 │         OBSERVE & RECONCILE          │
                 └──────────────────┬───────────────────┘
                                    ▼
                 ┌──────────────────────────────────────┐
                 │       POST-ACTION VERIFICATION       │
                 └──────────────────┬───────────────────┘
                                    ▼
                 ┌──────────────────────────────────────┐
                 │       LEARNING / GRAPH / AUDIT       │
                 └──────────────────────────────────────┘
```

---

## 2. Fundamental Invariants & Authority Boundaries

The Control Plane strictly enforces the following non-negotiable architectural boundaries:

1. **The Control Plane is an Orchestrator, NOT an Authority**:
   - It cannot authorize itself or bypass `SecurityCenter`.
   - It cannot execute tools directly; all execution must flow through `ActionTransaction` with preflight validation and rollback guarantees.
   - It never replaces `PlanningService`, `DecisionIntelligenceService`, `SituationalAwarenessService`, `WorldStateReconciliationEngine`, or `SelfModelService`.
2. **EmergencyStop Primacy**:
   - EmergencyStop is absolute and overrides all ongoing or queued control cycles immediately into `BLOCKED` state (`EMERGENCY_STOP_FAIL_CLOSED`).
   - Post-clearing requires mandatory supervisory revalidation.
3. **Execution Success $\neq$ Verified Success**:
   - Even if a tool reports exit code 0 or execution success, if empirical world-state observations show post-condition mismatches or continuing service degradation, the cycle status is strictly `VERIFICATION_FAILURE`.
4. **Unknown Must Remain Unknown**:
   - Unresolved action outcomes cannot be assumed as successes or blind retries. They are recorded as `UNKNOWN` or `WAITING_FOR_VERIFICATION`, triggering non-destructive world-state reconciliation.
5. **Anti-Thrashing Loop Guard**:
   - Circuit breakers monitor decision lineages, repetitive tool signatures, and consecutive failure counts to make infinite autonomous loops impossible.
6. **Deterministic Read-Only Replay**:
   - Historic cycles can be fully reconstructed and inspected through deterministic event logs and snapshots with guaranteed zero side-effects.

---

## 3. The 16-Stage Unified Operating Loop

Each bounded control cycle advances through canonical stages:

| Stage | Name | Description | Authoritative System |
| :--- | :--- | :--- | :--- |
| 1 | `OBSERVE` | Captures immutable multi-subsystem `ControlSnapshot`. | Control Snapshot Engine |
| 2 | `RECONCILE_WORLD` | Synchronizes external environment, services, and drift. | `WorldStateReconciliationEngine` (Task 98) |
| 3 | `RECONCILE_SELF` | Gathers capability readiness, resource saturation, and self-limitations. | `SelfModelService` (Task 101) |
| 4 | `FORM_SITUATIONS` | Identifies active situations and causal correlations. | `SituationalAwarenessService` (Task 99) |
| 5 | `UPDATE_ATTENTION` | Evaluates priority and salient focus items. | Attention Engine |
| 6 | `UPDATE_MISSIONS` | Aligns ongoing long-horizon missions and milestones. | `MissionService` (Task 100) |
| 7 | `CHECK_FORECASTS` | Inspects counterfactual risk forecasts and reliability telemetry. | Reliability & Forecasting |
| 8 | `BUILD_CONTEXT` | Constructs minimal, trust-labeled context bundle. | `ControlContextAssembler` |
| 9 | `REQUEST_PLAN` | Obtains candidate plans, assumptions, and dependencies. | `PlanningService` (Task 58) |
| 10 | `REQUEST_DECISION`| Evaluates options, costs, and tradeoffs. | `DecisionIntelligenceService` (Task 94) |
| 11 | `AUTHORIZE` | Enforces fail-closed security and approvals. | `SecurityCenter` & `ApprovalRegistry` |
| 12 | `ALLOCATE` | Deducts bounded budgets from resource economy. | `ResourceEconomyEngine` (Task 77) |
| 13 | `EXECUTE` | Dispatches transactional action via sandbox / Rust worker. | `ActionTransaction` (Task 95) |
| 14 | `OBSERVE` | Measures real-world external delta post-execution. | Telemetry & Environment Probes |
| 15 | `VERIFY` | Reconciles expected postconditions against empirical truth. | Post-Action Verification Engine |
| 16 | `LEARN` | Commits findings, updates knowledge graph, and schedules next step. | Knowledge Graph & Metacognition |

---

## 4. ControlCycle State Lifecycle

A `ControlCycle` transitions through 19 explicit lifecycle states:

```
               CREATED
                  │
                  ▼
              OBSERVING
                  │
                  ▼
             RECONCILING
                  │
                  ▼
              ASSESSING
                  │
                  ▼
          CONTEXT_BUILDING
                  │
                  ▼
         PLANNING_REQUESTED
                  │
                  ▼
         DECISION_REQUESTED ──────► NO_ACTION (Structured Reason)
                  │
                  ▼
               WAITING (Approval / Dependency / Resource)
                  │
                  ▼
             AUTHORIZED ──────────► BLOCKED (E-Stop / Policy / LoopGuard)
                  │
                  ▼
             EXECUTING
                  │
                  ▼
             VERIFYING ───────────► FAILED (Verification / Execution Failure)
                  │
                  ▼
              LEARNING
                  │
                  ▼
             COMPLETED
```

---

## 5. Event Burst Coalescing & Lineage

To prevent event storms and rapid duplicate reasoning loops, the `ControlTriggerCoalescer`:
- Groups incoming triggers within a configurable time window (e.g., 50ms–500ms).
- Escalates priority to the highest severity trigger (`EMERGENCY` > `CRITICAL` > `HIGH` > `NORMAL` > `LOW`).
- Preserves full causal lineage across all merged triggers (`coalesced_triggers`).

---

## 6. Loop Guard Circuit Breaker & Resource Budgets

The `LoopGuardCircuitBreaker` protects Kairo against autonomous thrashing:
- **Consecutive Failures**: Trips if the identical failure fingerprint occurs $\ge 3$ consecutive times.
- **Repetitive Actions**: Detects cycles repeating identical tool actions or decisions.
- **Budget Envelope**: Enforces strict caps per cycle on duration (60s), model calls (5), tool calls (10), retries (3), and planning/decision attempts (2).
- **Circuit Trip Behavior**: Immediately halts autonomous execution, marks the cycle `BLOCKED` with reason `LOOP_GUARD_TRIGGERED`, and alerts operators.

---

## 7. Context Assembly & Trust Class Labeling

Context is bounded and strictly annotated with trust classes to prevent prompt injection and hallucinated authority:
- `OBSERVED`: Empirical telemetry from world-state and self-model sensors.
- `USER_AUTHORED`: Explicit directives and goals from the human operator.
- `SYSTEM_DERIVED`: Internal calculations, graph relations, and state snapshots.
- `MODEL_DERIVED`: LLM reasoning, proposals, and candidate strategies.
- `WEB_UNTRUSTED`: Scraped external data or public documentation.
- `TOOL_UNTRUSTED`: Unverified outputs from external commands.

---

## 8. REST API & CLI Interface

### REST Endpoints
- `GET  /api/v1/control/status`: Operational status, active mode, and loop guard health.
- `GET  /api/v1/control/mode`: Current derived autonomy mode.
- `GET  /api/v1/control/health`: Health status and circuit breaker state.
- `GET  /api/v1/control/cycles`: Paginated list of recent control cycles.
- `GET  /api/v1/control/cycles/{id}`: Detailed cycle snapshot and authoritative references.
- `GET  /api/v1/control/cycles/{id}/timeline`: Chronological stage-by-stage execution audit.
- `GET  /api/v1/control/cycles/{id}/replay`: Deterministic read-only replay reconstruction.
- `POST /api/v1/control/reassess`: Triggers an immediate supervisory reassessment pass.

### CLI Commands
- `kairo control status`: View high-level command center telemetry.
- `kairo control mode`: Inspect current autonomy mode.
- `kairo control health`: Check circuit breaker and subsystem connectivity.
- `kairo control cycles`: List recently executed cycles.
- `kairo control cycle <id>`: View full cycle metadata.
- `kairo control timeline <id>`: Display execution stage timeline.
- `kairo control reassess`: Trigger supervisory operational reassessment.

---

## 9. Verification & Test Coverage

- **Backend Unit Tests** (`backend/tests/test_control_plane.py`): 11 tests passing in ~4.77s.
- **Frontend Unit Tests** (`frontend/tests/control_plane.test.js`): 9 tests passing in ~0.25s.
- **Total Frontend Test Suite** (`frontend/tests/*.test.js`): 359 tests passing in ~4.27s.
- **E2E Operational Harness** (`scripts/verify_control_plane_e2e.py`): All 8 operational scenarios verified end-to-end.
- **Database Migration**: `0070_autonomous_cognitive_control_plane_and_unified_loop.py` registered and valid.
