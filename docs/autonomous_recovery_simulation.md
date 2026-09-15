# Kairo Autonomous Recovery Simulation, Digital Twin & Resilience Validation (Task 89)

## 1. Architectural Overview & Boundaries

Task 89 establishes the **Autonomous Recovery Simulation & Digital Twin Subsystem** in Kairo. It enables Kairo to simulate recovery strategies against a sanitized digital twin before committing mutations to the live runtime or host environment.

```
+-----------------------------------------------------------------------------------+
|                            PYTHON ORCHESTRATION LAYER                             |
|  - Digital Twin State Ingestion: captures live subsystem health, metrics, tokens   |
|  - Multi-pattern Secret Sanitization: redacts auth keys, passwords, sensitive env  |
|  - Consequence Simulation: generates candidate actions & Pareto trade-off ranking |
|  - Stale Simulation Drift Detection: rejects stale/expired snapshots fail-closed   |
|  - Chaos Scenario Library: 14 canonical system failure perturbation drills        |
|  - Metacognitive Calibration: compares predicted consequences against reality     |
|  - Strategy Scorecards & Resilience Benchmarks: 7-dimension resilience grading    |
+------------------------------------------^----------------------------------------+
                                           | Length-Prefixed IPC Framing
                                           | SimulationContext (is_simulation=true)
+------------------------------------------v----------------------------------------+
|                          NATIVE RUST SUBSTRATE (kairo-runtime)                    |
|  - sys.snapshot / sys.twin: returns lightweight atomic daemon snapshot             |
|  - Simulation Firewall: blocks live mutating side effects (sys.stop, native.input, |
|    clipboard write, network requests, sandbox execute) when simulation flag is set|
|  - Read-Only Inspection Allowed: ping, telemetry, and non-mutating metric reads    |
+-----------------------------------------------------------------------------------+
```

---

## 2. Core Invariants & Safety Ladders

1. **Deterministic Simulation Firewall (`SimulationContext`):**
   - Every simulated request sent across IPC carries a typed `SimulationContext`.
   - The native Rust dispatcher (`kairo-runtime/src/dispatcher.rs`) evaluates `sim_ctx.is_simulation` and blocks any operation with side effects (e.g. `sys.stop`, `sys.emergency_stop`, `native.input.*`, `native.clipboard.write`, `native.net.request`, `sandbox.execute`) with error `SIMULATION_MUTATION_BLOCKED`.
2. **Zero Live Credential Ingestion:**
   - The digital twin snapshot generator recursively redacts sensitive tokens, credentials, API keys, and passwords before constructing the immutable `RuntimeSnapshot`.
   - Snapshots are tagged with `environment_label="SIMULATION_ONLY"` and cryptographically fingerprinted using SHA-256.
3. **Stale Simulation Drift Rejection:**
   - If the runtime instance restarts, the capability fingerprint drifts, or the snapshot exceeds maximum allowed age (default: 60s), the `StaleSimulationDetector` rejects the simulation as stale, preventing outdated plans from being evaluated.
4. **Pareto-Optimal Candidate Ranking:**
   - Candidate strategies are evaluated across estimated duration, resource delta, blast radius, recovery probability, and qualitative uncertainty levels (`CERTAIN`, `HIGH`, `MEDIUM`, `SPECULATIVE`).
5. **Prediction vs. Reality Metacognitive Calibration:**
   - Post-recovery executions record actual duration, resource cost, and blast radius to calibrate future simulation models and detect strategy degradation or regression below 80% success thresholds.

---

## 3. Subsystem Components

### 3.1 Digital Twin (`digital_twin.py`)
- `RuntimeDigitalTwin`: Asynchronously ingests current operational status from the native runtime daemon, Python event bus, resource economy, and reliability registry.
- Enforces immutability, SHA-256 hashing, and secret redaction.

### 3.2 Recovery Simulator (`recovery_engine.py`)
- `RecoverySimulator`: Generates recovery candidates based on target subsystem failure.
- Computes Pareto rank, risk scores, duration intervals, and documents explicit simulation assumptions and limitations.

### 3.3 Drift Detector (`drift_detector.py`)
- `StaleSimulationDetector`: Evaluates drift between the simulation baseline and current live state.
- Immediately halts if Emergency Stop was engaged between snapshot capture and plan selection.

### 3.4 Chaos Scenario Library (`chaos_library.py`)
- Contains 14 canonical system failure scenarios:
  1. `chaos_crash_native_daemon`
  2. `chaos_ipc_socket_disconnect`
  3. `chaos_memory_leak_pressure`
  4. `chaos_cpu_exhaustion_spin`
  5. `chaos_corrupt_sandbox`
  6. `chaos_stale_connection_pool`
  7. `chaos_network_packet_loss`
  8. `chaos_database_contention`
  9. `chaos_zombie_process_accumulation`
  10. `chaos_emergency_stop_trip`
  11. `chaos_workflow_step_failure`
  12. `chaos_authorization_expiry`
  13. `chaos_toctou_mutation`
  14. `chaos_cascading_subsystem_outage`

### 3.5 Scorecards & Resilience Benchmarks (`scorecards.py`)
- `ScorecardManager`: Tracks per-strategy execution counts, success rates, failure rates, and health statuses (`HEALTHY`, `DEGRADED`, `CRITICAL`).
- `ResilienceBenchmarkEngine`: Evaluates system resilience across 7 dimensions: detection, containment, recovery, verification, stability, calibration, and autonomy.
- `RecoveryRegressionDetector`: Flags strategies that fall below reliability thresholds.

---

## 4. REST API Reference

All endpoints are mounted under `/api/v1/simulation`:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/simulation/snapshot` | Capture sanitized operational digital twin snapshot |
| `GET` | `/api/v1/simulation/snapshot/latest` | Inspect most recent captured snapshot |
| `GET` | `/api/v1/simulation/snapshot/{snapshot_id}` | Retrieve specific snapshot by ID |
| `POST` | `/api/v1/simulation/run` | Run consequence simulation for candidate strategies |
| `GET` | `/api/v1/simulation/list` | List recent simulation runs and Pareto rankings |
| `GET` | `/api/v1/simulation/{simulation_id}` | Retrieve full simulation result and Pareto candidates |
| `GET` | `/api/v1/simulation/chaos/scenarios` | List 14 canonical chaos drill scenarios |
| `POST` | `/api/v1/simulation/chaos/drill` | Trigger synthetic chaos drill scenario |
| `POST` | `/api/v1/simulation/calibrate` | Ingest real-world outcome to calibrate predictions |
| `GET` | `/api/v1/simulation/scorecards` | Retrieve strategy reliability scorecards |
| `GET` | `/api/v1/simulation/benchmarks` | Retrieve 7-dimension resilience benchmark report |
| `GET` | `/api/v1/simulation/regressions` | Identify degraded or regressing recovery strategies |
| `GET` | `/api/v1/simulation/comparisons` | List prediction-vs-reality calibration records |
