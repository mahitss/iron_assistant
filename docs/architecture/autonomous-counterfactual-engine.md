# Kairo Autonomous Counterfactual, Intervention Analysis, What-If Simulation & Causal Experiment Planning Engine (Task 113)

## 1. Architectural Overview

The **Autonomous Counterfactual Engine** provides Kairo with rigorous what-if simulation, intervention reasoning, side-by-side comparison, active causal experiment design, and prediction-vs-reality calibration.

Crucially, the engine enforces strict cognitive and safety boundaries:
```
CURRENT / HISTORICAL STATE
        ↓
CAUSAL MODEL (DAG / Precedence)
        ↓
TARGET VARIABLE
        ↓
INTERVENTION CANDIDATES
        ↓
BASELINE / NO-ACTION (First-Class)
        ↓
COUNTERFACTUAL SCENARIOS
        ↓
SIMULATION / REPLAY / SANDBOX
        ↓
OUTCOME DISTRIBUTION (13 Dimensions)
        ↓
RISK / RESOURCE / GOVERNANCE CHECK
        ↓
COMPARISON & TRADEOFF SUMMARY
        ↓
DECISION SUPPORT (Task 94)
        ↓
OPTIONAL AUTHORIZED ACTION (Tasks 95 & Security)
        ↓
OBSERVE TELEMETRY
        ↓
VERIFY (Prediction vs Reality)
        ↓
LEARNING / CALIBRATION
```

---

## 2. Core Invariants & Cognitive Separation

1. **`COUNTERFACTUAL != HISTORY`**: Hypothetical outcomes never overwrite or masquerade as historical events.
2. **`SIMULATION != REALITY`**: Every simulated state carries `is_hypothetical=True` and `environment_label="SIMULATION_ONLY"`.
3. **`PREDICTION != OBSERVATION`**: Model predictions and empirical observations are stored in distinct fields.
4. **`INTERVENTION != AUTHORIZATION`**: An intervention plan confers zero execution permission.
5. **`EXPERIMENT != PERMISSION`**: Active experiment designs require explicit human/governance approval before execution.
6. **`WHAT-IF != ACTION`**: Running a scenario does not mutate any production state.
7. **`CAUSAL MODEL != TRUTH`**: Causal DAG reachability is a candidate hypothesis, not ground truth.
8. **`MODEL OUTPUT != EVIDENCE`**: Model inferences do not count as empirical evidence.
9. **`FORECAST != GUARANTEE`**: Projected metrics carry explicit uncertainty intervals.
10. **`CORRELATION != CAUSATION`**: Correlation links are discounted to low mechanism fit.
11. **`NO-ACTION IS A REAL BASELINE`**: Action is never assumed inherently better. NO_ACTION is evaluated on equal footing.

---

## 3. Subsystem Extensions (Zero Duplication)

The engine directly orchestrates across existing Kairo foundations:
- **Causal Graph & Precedence (Task 55/73)**: Reuses `app.causal.service.CausalService` and `TemporalCausalityEngine` for bounded subgraphs and causal mechanism inference.
- **Simulation & Digital Twin (Task 89)**: Reuses `app.simulation.service.SimulationService` and `SimulationEngine` for sandboxed deterministic/stochastic scenario executions.
- **Continuous Evaluation & Experimentation (Task 104/105)**: Reuses `app.adaptation.experiment_engine.ExperimentFirewall` for experiment gate checks.
- **Temporal Intelligence (Task 111)**: Reuses `TemporalIntelligenceService.reconstruct_state_as_of` for historical baseline reconstruction.
- **Causal Explanation & Root-Cause (Task 112)**: Reuses root cause contributors and competing alternatives to construct targeted counterfactuals.
- **EmergencyStop & Governance**: Reuses fail-closed emergency stop primitives.

---

## 4. Multi-Dimensional Comparison (13 Dimensions)

Candidate interventions and NO_ACTION are compared across:
1. `mission_success_delta`: Impact on active mission objectives.
2. `goal_progress_delta`: Progress toward inferred goals.
3. `system_health_delta`: System operational status change.
4. `reliability_delta`: Failure rate and MTBF trajectory.
5. `risk_score`: Propagated risk score via Task 75.
6. `resource_usage`: CPU, memory, and token cost estimates.
7. `latency_delta_ms`: Projected p95/p99 latency difference.
8. `cost_estimate_units`: Financial and economic cost.
9. `safety_score`: Invariant compliance score.
10. `reversibility_score`: Ease of rollback/reversion.
11. `capability_impact`: Impact on autonomous capabilities.
12. `user_impact`: User experience impact.
13. `external_impact`: External dependencies and blast radius.

The comparison engine does **not** unilaterally declare a "winner"; it supplies structured evidence and trade-off summaries for Task 94 Decision Intelligence.

---

## 5. Sensitivity & Robustness Analysis

- **Sensitivity**: Computes parameter elasticities across external perturbations ($\pm 20\%$) to identify critical influential factors.
- **Robustness Classification**:
  - `ROBUST`: Conclusion holds across wide parameter and assumption variations.
  - `SENSITIVE`: Minor parameter variations materially alter predicted trajectory.
  - `FRAGILE`: Relies on multiple unverified assumptions or narrow stability bounds.
  - `UNKNOWN`: Insufficient variance telemetry.

---

## 6. Staleness & Invalidation Model

A counterfactual analysis automatically transitions to `STALE` and is blocked from silent reuse when:
1. **Causal Model Changes**: Retrained or updated graph versions invalidate prior assumptions.
2. **World-State Divergence**: Material status mutations occur between simulation time and decision time.
3. **Dependency Degradation**: External upstream dependencies degrade or change protocol.
4. **Horizon Expiration**: Analysis age exceeds validity horizon (default 3600s).

---

## 7. Prediction-vs-Reality Learning

Following real-world execution of an authorized intervention:
1. The engine observes subsequent telemetry.
2. Compares observed state against the counterfactual prediction.
3. Classifies outcome (`VERIFIED`, `CONTRADICTED`, `DEVIATED`, `UNRESOLVED`).
4. Computes state deviation scores and records discrepancies.
5. Emits calibration feedback to Evaluation (Task 104), Reliability (Task 90), and Cognitive Memory (Task 103).
6. **Hard Invariant**: The original counterfactual prediction is preserved immutably and never overwritten.
