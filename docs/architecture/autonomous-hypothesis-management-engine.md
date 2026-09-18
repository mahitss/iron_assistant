# Autonomous Hypothesis Management, Competing Explanations & Uncertainty Resolution Engine (Task 115)

## 1. Objective & Philosophy

The **Kairo Autonomous Hypothesis Management Engine** provides a disciplined, auditable epistemological layer for formulating, evaluating, falsifying, and refining competing explanations for incidents and observations over time.

In complex autonomous systems, the primary danger is not lack of data, but **premature collapse of uncertainty**—jumping to a single plausible narrative (anchoring/confirmation bias) and treating it as proven fact. Task 115 ensures Kairo holds competing hypotheses in parallel, tracks testable falsification conditions, monitors evidence independence, guards against cognitive biases, and explicitly respects `UNRESOLVED / CAUSE_UNKNOWN` when evidence does not warrant certainty.

```
OBSERVATION / TARGET INCIDENT
            ↓
HYPOTHESIS GENERATION (+ Mandatory UNKNOWN)
            ↓
EVIDENCE INGESTION & LINEAGE TRACKING
            ↓
EVIDENCE INDEPENDENCE EVALUATION
            ↓
TEMPORAL & CAUSAL COMPATIBILITY
            ↓
FALSIFICATION & PREDICTION CHECKS
            ↓
COGNITIVE BIAS SAFEGUARDS (Contradiction Search / Premature Closure)
            ↓
DISCRIMINATING OBSERVATIONS (Task 114 VoI)
            ↓
STATUS: SUPPORTED / CONTESTED / WEAKENED / FALSIFIED / UNRESOLVED
            ↓
DOWNSTREAM DECISION INTELLIGENCE (Advisory, Non-Executive)
```

---

## 2. Hard Invariants

1. **`HYPOTHESIS ≠ BELIEF`**: Hypotheses are candidate explanations under test. Beliefs (Task 107) are arbitrated degrees of epistemic commitment.
2. **`HYPOTHESIS ≠ FACT / TRUTH`**: Hypotheses remain tentative models of reality.
3. **`HYPOTHESIS ≠ DECISION / ACTION / AUTHORIZATION`**: Hypotheses cannot execute tools, alter policies, or grant authority. Action selection is reserved for Task 94 Decision Intelligence; authorization belongs to SecurityCenter & Governance.
4. **`EVIDENCE ≠ TRUTH`**: Evidence items have measurable reliability, freshness, and potential corruption.
5. **`CORRELATION ≠ CAUSATION` & `TEMPORAL ORDER ≠ CAUSATION`**: Temporal sequence does not imply a causal link without a verified physical or architectural mechanism.
6. **`SIMULATION ≠ REALITY` & `COUNTERFACTUAL ≠ HISTORY`**: Simulated twin models and counterfactual interventions are strictly tagged as `SIMULATED` and discounted relative to physical measurements.
7. **`AGENT CLAIM ≠ INDEPENDENT EVIDENCE`**: Multiple agents repeating identical telemetry or citing a shared ancestor are categorized as `DERIVED` or `DUPLICATE`, preventing echo-chamber inflation.
8. **`ABSENCE OF EVIDENCE ≠ EVIDENCE OF ABSENCE`**: Missing telemetry is an information gap, NOT negative evidence.
9. **`UNKNOWN REMAINS FIRST-CLASS`**: Every hypothesis set must include `UNKNOWN / OTHER CAUSE` to prevent forced convergence.
10. **`NO ARBITRARY WINNER SELECTION`**: Comparison interfaces expose multidimensional evidence transparently without declaring a "winner".

---

## 3. Core Components

### 3.1 Domain Models (`app.hypothesis.domain`)
- **`Hypothesis`**: First-class candidate explanation with statement, causal node references, assumptions, falsification conditions, predictions, and multidimensional confidence profile.
- **`HypothesisSet`**: Cohesive competing explanations for a target incident, tracking active hypotheses, rejected hypotheses, information gaps, and discriminators.
- **`HypothesisFalsificationCondition`**: Explicit, testable, bounded criterion specifying what observations would conclusively prove the hypothesis wrong.
- **`HypothesisPrediction`**: Quantitative or qualitative forecast used to evaluate hypothesis calibration.
- **`HypothesisEvidenceItem`**: Immutable evidence record with strict provenance, parent IDs, and independence classification.
- **`HypothesisConfidenceProfile`**: 12-dimensional profile preserving:
  - `evidence_strength`
  - `evidence_independence`
  - `temporal_consistency`
  - `mechanism_plausibility`
  - `causal_support`
  - `predictive_success`
  - `counterfactual_support`
  - `contradiction_score`
  - `source_reliability`
  - `completeness`
  - `uncertainty`
  - `historical_consistency`

### 3.2 Evidence Evaluator & Independence (`app.hypothesis.evidence_evaluator`)
Ensures evidence lineage is audited. If Telemetry A creates derived signal B and Agent C reports B, the engine tags B and C as `DERIVED`, preventing confidence inflation from redundant sources.

### 3.3 Falsification Engine (`app.hypothesis.falsification_engine`)
Evaluates testable falsification conditions and prediction outcomes. When a falsification condition is met, the hypothesis immediately transitions to `FALSIFIED`, and is moved out of active candidates into rejected lists.

### 3.4 Cognitive Bias Guard Engine (`app.hypothesis.bias_guard_engine`)
- **Confirmation Bias Guard**: Requires an active contradiction search before advancing any hypothesis to `STRONGLY_SUPPORTED`. If unexamined contradictions exist, the hypothesis is capped at `SUPPORTED` or flagged as `CONTESTED`.
- **Premature Closure Guard**: Blocks declaring an incident set resolved if competing alternative hypotheses remain completely unexamined.
- **Single-Source Dominance**: Detects when >80% of supporting evidence stems from a single reporting node and caps confidence independence.
- **Majority-Agent Echo Guard**: Detects multiple agents echoing identical underlying observations and collapses them into a single derived evidence point.

### 3.5 Refinement Engine (`app.hypothesis.refinement_engine`)
- **Splitting**: Deconstructs overly broad hypotheses (e.g. "Network issue") into specialized variants ("Packet loss", "DNS failure", "TLS handshake latency") with explicit parent-child lineage.
- **Merging**: Unifies duplicate or equivalent hypotheses while strictly preserving historical evidence trails and provenance.

### 3.6 Discriminator Engine (`app.hypothesis.discriminator_engine`)
Identifies observations that produce diverging expected outcomes across competing hypotheses, calculates expected Value-of-Information (Task 114 VoI), and exposes actionable information gaps.

---

## 4. Downstream Integrations & Safety

- **Task 94 (Decision Intelligence)**: Consumes bounded hypothesis landscapes, active candidates, and residual uncertainty. Does NOT delegate action decisions to the hypothesis engine.
- **Task 107 (Belief / Evidence Arbitration)**: Hands off evidence assessments without mutating beliefs directly (`HYPOTHESIS != BELIEF`).
- **Task 112 (Causal Explanation)**: Reuses causal graphs and chains without duplicating causal inference.
- **Task 113 (Counterfactuals)**: Evaluates what-if absence of hypothesized causes; outputs strictly tagged `SIMULATED`.
- **Task 114 (Active Observation)**: Translates discriminators into observation plans when uncertainty reduction justifies collection costs.
- **EmergencyStop & SecurityCenter**: Strict fail-closed authority preservation. If emergency stop is triggered, all hypothesis mutation is blocked.

---

## 5. Why "UNRESOLVED" is a Valid and Desirable Outcome

In high-stakes distributed systems, claiming premature certainty when evidence is ambiguous causes disastrous misdiagnoses and cascading failures. The Kairo Hypothesis Engine treats `CAUSE_UNKNOWN` and `UNRESOLVED` as successful, informative states.

When Kairo states:
> *"Several candidate explanations remain viable. Current evidence weakly supports H1 and H3, but neither is verified. Observation of upstream router dropped packets would discriminate between them. Until that observation is acquired, the cause remains unresolved."*

Kairo demonstrates calibrated epistemic humility—knowing exactly what it does NOT know.
