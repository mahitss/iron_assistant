# Threat Model: Autonomous Recovery Simulation & Digital Twin (Task 89)

## 1. System Scope & Assets

This threat model addresses **Task 89: Autonomous Recovery Simulation, Digital Twin & Resilience Validation**.
Key assets protected:
- **Production Host State**: Filesystems, native processes, user windows, clipboard, and active network connections.
- **Sensitive Credentials**: API keys, bearer tokens, passwords, private keys in daemon memory or environment variables.
- **Simulation Integrity**: Trustworthiness of Pareto candidate rankings and resilience scorecards.
- **Emergency Stop Primacy**: Absolute preemption of simulation actions when EmergencyStop is engaged.

---

## 2. Threat Analysis & Mitigations

### 2.1 Threat: Simulation Escape / Accidental Mutation of Production Environment
- **Risk**: A simulation meant to evaluate recovery steps inadvertently executes destructive system operations (e.g. process kill, arbitrary shell command, or modifying production database).
- **Mitigation**:
  - Typed `SimulationContext` propagated across the IPC protocol.
  - Native Rust substrate enforces the **Simulation Firewall** in `RequestDispatcher::dispatch`:
    - Blocks mutating capabilities (`sys.stop`, `sys.emergency_stop`, `native.input.*`, `native.clipboard.write`, `native.net.request`, `sandbox.execute`) with error `SIMULATION_MUTATION_BLOCKED`.
  - Python layer marks all snapshots with `environment_label="SIMULATION_ONLY"`.

### 2.2 Threat: Secret & Token Leakage into Snapshots or Logs
- **Risk**: Operational digital twin snapshots capture live memory, environment variables, or request payloads containing secret credentials.
- **Mitigation**:
  - `RuntimeDigitalTwin::capture_current_state` applies recursive sanitization across all keys and string fields matching known credential regex patterns.
  - Plaintext secrets are replaced with `[REDACTED]`.
  - Unit tests specifically assert that private keys, tokens, and passwords never appear in serialized snapshot strings.

### 2.3 Threat: Stale Simulation Poisoning (TOCTOU between Simulation & Execution)
- **Risk**: A recovery plan simulated against an earlier system snapshot is enacted after the system state has fundamentally shifted (e.g. native daemon restarted, Emergency Stop engaged, or resource exhausted).
- **Mitigation**:
  - `StaleSimulationDetector` validates:
    - Snapshot age <= configured threshold (`max_snapshot_age_seconds`, default 60s).
    - `runtime_instance_id` matching between snapshot baseline and live substrate.
    - `capability_fingerprint` parity.
    - Emergency Stop status check: if EmergencyStop is active, all simulation runs and recovery actions are terminated immediately.

### 2.4 Threat: Chaos Fault Injection Runaway in Production
- **Risk**: Chaos drills intended for validation escape test boundaries and induce unrecoverable outages on live services.
- **Mitigation**:
  - Fault injection is strictly guarded by `fault_injection_enabled` configuration flag (default: False).
  - Chaos drills are executed against synthetic perturbations on `RuntimeSnapshot` clones in memory rather than perturbing physical processes, unless explicitly opted in within a sandboxed testbed.
  - Rate limiting and maximum restart caps apply to all chaos invocations.

---

## 3. Verification & Compliance Matrix

| Threat Category | Invariant | Verified By |
| :--- | :--- | :--- |
| Simulation Escape | Mutating capabilities blocked | `native/crates/kairo-runtime/tests/simulation_firewall_tests.rs` |
| Credential Leakage | Zero secret exposure in snapshots | `backend/tests/test_simulation_and_recovery.py` |
| Stale Drift | Expired or drifted snapshots rejected | `test_stale_simulation_drift_detector` |
| Emergency Stop Bypass | Emergency stop overrides simulation | `test_drift_detector_with_emergency_stop` |
| Chaos Containment | Chaos drills perturbation contained | `test_all_14_chaos_scenarios_perturbation_and_generation` |
