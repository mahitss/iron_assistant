# Kairo Metacognitive Control & Autonomous Self-Audit Engine (Task 67)

The **Metacognitive Control & Autonomous Self-Audit Engine** allows Kairo to continuously evaluate its own reasoning quality, decisions, predictions, plans, execution, confidence calibration, assumptions, failures, resource usage, goal alignment, safety compliance, and behavioral drift.

## Core Operational Cycle

```
OBSERVE
   ↓
RECONSTRUCT
   ↓
ASSESS
   ↓
QUESTION
   ↓
CHALLENGE (Adversarial Self-Review)
   ↓
COMPARE WITH EVIDENCE
   ↓
IDENTIFY ERROR / UNCERTAINTY
   ↓
GENERATE CORRECTION RECOMMENDATION
   ↓
VERIFY (Independent Verification)
   ↓
LEARN
   ↓
MONITOR
```

## Foundational Invariants

- $\text{SELF-REFLECTION} \ne \text{REALITY}$
- $\text{SELF-AUDIT} \ne \text{TRUTH}$
- $\text{SELF-CRITIQUE} \ne \text{EXTERNAL VERIFICATION}$
- $\text{CONFIDENCE} \ne \text{CERTAINTY}$
- $\text{BELIEF} \ne \text{FACT}$
- $\text{INFERENCE} \ne \text{OBSERVATION}$
- $\text{DETECTED ERROR} \ne \text{CORRECTED ERROR}$
- $\text{CORRECTION} \ne \text{VERIFICATION}$
- $\text{RECOMMENDATION} \ne \text{CHANGE}$
- $\text{CHANGE} \ne \text{EXECUTION}$
- $\text{EXECUTION} \ne \text{VERIFICATION}$
- $\text{SELF-AUDIT} \ne \text{AUTHORIZATION}$
- $\text{UNKNOWN} \ne \text{HEALTHY} \ne \text{SAFE}$

## Subsystems & Components

1. **Self-Model (`self_model.py`)**:
   - Capability awareness: `AVAILABLE`, `DEGRADED`, `UNAVAILABLE`, `UNKNOWN`.
   - Explicit limitation modeling (missing tools, low confidence, stale knowledge).
   - Knowledge classification: `KNOWN`, `OBSERVED`, `INFERRED`, `ESTIMATED`, `PREDICTED`, `ASSUMED`, `UNKNOWN`.

2. **Belief Modeling & Revision (`beliefs.py`)**:
   - Non-destructive belief revisions preserving historical lineage upon conflicting evidence.
   - Structured self-questioning (*"Why do I believe this?", "What evidence contradicts it?"*).

3. **Reasoning & Decision Auditing (`reasoning_audit.py`)**:
   - Audits reasoning for unsupported assumptions, causal overreach, false certainty, confirmation bias, and circular reasoning.
   - Preserves structured metadata only without leaking private chain-of-thought.

4. **Confidence Calibration (`calibration.py`)**:
   - Computes Brier scores across predicted vs actual outcomes.
   - Flags `SYSTEMATIC_OVERCONFIDENCE` and `SYSTEMATIC_UNDERCONFIDENCE`.

5. **Behavioral Baseline & Drift (`drift.py`)**:
   - Detects drift against operational baselines (verification drops, tool call spikes).
   - Audits goal alignment and detects proxy metric manipulation (Goodhart's Law).

6. **Error Taxonomy & Clustering (`errors.py`)**:
   - Standard 12-category operational error taxonomy.
   - Detects recurring error clusters and flags `RATIONALIZATION_PATTERN`.

7. **Governance Boundaries & Safety (`safety.py`)**:
   - Enforces immutable governance: self-audit cannot alter security, authorization, or policy rules.
   - Enforces no self-preservation objectives and neutralizes prompt injections.
   - Redacts credentials and API keys in audit outputs.
