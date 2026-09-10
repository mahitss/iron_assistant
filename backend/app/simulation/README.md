# Kairo Simulation & Counterfactual Planning Engine (Task 56)

The Kairo Simulation Engine enables safe exploration of hypothetical interventions before executing changes in production environments.

## Core Invariant Pipeline

```
OBSERVED REAL STATE
        ↓
VERIFIED DIGITAL TWIN
        ↓
SIMULATION SNAPSHOT
        ↓
HYPOTHETICAL CHANGE
        ↓
PROPAGATE EFFECTS
        ↓
SIMULATE FUTURE STATE
        ↓
MEASURE CONSEQUENCES
        ↓
COMPARE SCENARIOS
        ↓
RECOMMEND PLAN
        ↓
REAL AUTHORIZED EXECUTION
        ↓
VERIFY
        ↓
COMPARE REALITY WITH SIMULATION
        ↓
LEARN
```

## Key Safety Guarantees

1. **Zero Real-World Side Effects**: Simulation APIs strictly mutate only in-memory hypothetical state. Any call to production `ToolExecutor` tools is intercepted by the firewall (`SimulationSideEffectError`).
2. **Hard Separation**: A passing simulation recommendation does not constitute approval or authorization (`simulated_pass_is_not_approval`).
3. **Verified Real-World Transition**: Real execution requires passing the `ExecutionGate`. If the real-world state hash diverged from the baseline snapshot since the simulation was run, the gate is marked `STALE` or `INVALIDATED` and transition is blocked (`StaleSimulationError`).
4. **Epistemic Marking**: All outputs are explicitly tagged `SIMULATED`, `HYPOTHETICAL`, `PREDICTED` with `is_hypothetical=True` and `environment_label="SIMULATION_ONLY"`.
5. **Epistemic Honesty**: No false precision in cost, latency, or risk calculations; unmapped dependencies reduce confidence and generate uncertainty profiles.
