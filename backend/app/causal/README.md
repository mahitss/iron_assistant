# Kairo Causal Reasoning & Causal Graph Engine (Task 55)

The Causal Reasoning & Causal Graph Engine enables Kairo to rigorously distinguish between:

$$\text{OBSERVATION} \ne \text{CORRELATION} \ne \text{DEPENDENCY} \ne \text{CAUSAL HYPOTHESIS} \ne \text{VERIFIED CAUSAL RELATION}$$

## Core Principle

$$\text{OBSERVE} \longrightarrow \text{ORDER} \longrightarrow \text{CORRELATE} \longrightarrow \text{MODEL DEPENDENCIES} \longrightarrow \text{GENERATE HYPOTHESES} \longrightarrow \text{COMPARE ALTERNATIVES} \longrightarrow \text{TEST / INTERVENE} \longrightarrow \text{VERIFY} \longrightarrow \text{UPDATE CAUSAL GRAPH}$$

## Key Invariants & Safety Guarantees

1. **Temporal Precedence $\ne$ Causation**: Merely occurring before an incident does not establish causality (post hoc fallacy rejection).
2. **Topological Dependency $\ne$ Direct Causation**: Reachability in a service graph defines candidates (`DEPENDS_ON`), not direct mechanisms (`CAUSES`).
3. **Model Output is NOT Evidence**: LLM-generated explanations are hypotheses, never empirical evidence (`ModelOutputAsEvidenceError`).
4. **No Direct Production Mutation**: Interventions cannot execute on production without operator approval and policy authorization (`UnauthorizedInterventionError`).
5. **No Forced Root Cause**: If empirical evidence is insufficient, root cause status remains `UNKNOWN`. Never invent causes (`UnverifiedRootCauseError`).
6. **Explicit Counterfactuals**: All what-if scenarios and simulations are tagged `is_hypothetical=True` and separated from physical reality.

## 5-Stage Root Cause Chain

$$\text{Underlying Condition} \longrightarrow \text{Trigger} \longrightarrow \text{Mechanism} \longrightarrow \text{Symptom} \longrightarrow \text{Impact}$$

## Architecture

- `graph.py` & `nodes.py` & `edges.py`: Directed causal graph with cycle detection and weakest-link path confidence.
- `evidence.py`: Evidence classification (`CRITICAL`, `STRONG`, `MODERATE`, `WEAK`) with source independence discounting.
- `hypotheses.py` & `alternatives.py`: Competing hypothesis generation and evidence-based elimination.
- `root_cause.py`: Root cause analysis engine modeling primary vs contributing factors.
- `interventions.py`: Authorized intervention modeling, expected vs actual effect evaluation, and safety stops.
- `counterfactuals.py` & `simulation.py`: What-if counterfactual modeling with Digital Twin integration.
- `experiments.py`: Controlled A/B causal testing with contamination checks.
- `verification.py`: Multi-source empirical threshold verification.
- `explanations.py`: Structured 6-part explanations and natural language Q&A.
- `evaluation.py`: Cognitive and statistical fallacy detection (`POST_HOC`, `COMMON_CAUSE`, `SELECTION_BIAS`, `CONFOUNDING`, `REVERSE_CAUSALITY`, `COLLIDER_BIAS`, `OVERFITTING`).
- `privacy.py`: Secret scrubbing, data minimization, and prompt injection guards.
