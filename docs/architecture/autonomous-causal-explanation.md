# Kairo Autonomous Causal Explanation, Event Chain Reconstruction & "Why Did This Happen?" Engine

## 1. Overview & Conceptual Pipeline

Kairo Autonomous Causal Explanation (Task 112) provides a unified, auditable, evidence-backed engine that explains complex incidents, state divergences, failures, and regressions **without fabricating causality**.

```
                           TEMPORAL EVENTS (Task 111)
                                      │
                                      ▼
                         STATE TRANSITIONS (Task 111)
                                      │
                                      ▼
                            CHANGE SETS (Task 111)
                                      │
                                      ▼
                         DEPENDENCIES (Tasks 55 & 73)
                                      │
                                      ▼
                        EXISTING CAUSAL MODEL (Task 55)
                                      │
                                      ▼
                      EVENT CHAIN RECONSTRUCTION (Task 112)
                                      │
                                      ▼
                    EVIDENCE ARBITRATION (Task 107 Belief)
                                      │
                                      ▼
                      TEMPORAL PRECEDENCE VALIDATION
                 (validate_temporal_precedence from Task 73)
                                      │
                                      ▼
                       ALTERNATIVE HYPOTHESIS ENGINE
                      (Discriminating Observations)
                                      │
                                      ▼
                        COUNTERFACTUAL VERIFICATION
                       (is_hypothetical=True isolated)
                                      │
                                      ▼
                      MULTI-DIMENSIONAL CONFIDENCE
                   (Temporal, Mechanism, Evidence, Gaps)
                                      │
                                      ▼
                         STRUCTURED EXPLANATION
                (6-Part Narrative + Deep Causal Graph)
                                      │
                                      ▼
                      POST-INCIDENT VERIFICATION
             (Confirmed -> VERIFIED, Contradicted -> CONTRADICTED)
```

---

## 2. Core Principles & Safety Invariants

Kairo strictly enforces:

$$\text{CAUSATION} \ne \text{CORRELATION}$$
$$\text{TEMPORAL ORDER} \ne \text{CAUSATION}$$
$$\text{GRAPH PATH} \ne \text{CAUSATION}$$
$$\text{DEPENDENCY} \ne \text{CAUSATION}$$
$$\text{CONTRIBUTION} \ne \text{SOLE CAUSE}$$
$$\text{OBSERVATION} \ne \text{EXPLANATION}$$
$$\text{EXPLANATION} \ne \text{TRUTH}$$
$$\text{SIMULATION} \ne \text{REALITY}$$
$$\text{FORECAST} \ne \text{OUTCOME}$$
$$\text{ABSENCE OF EVIDENCE} \ne \text{EVIDENCE OF ABSENCE}$$

### Why Kairo Says "Cause Unknown"
A core safety property of Kairo is the ability to decline to speculate. If telemetry is absent, transitions are uninstrumented, or observations are contradictory, Kairo explicitly outputs:
```json
{
  "why_it_happened": "CAUSE UNKNOWN: Insufficient empirical evidence exists to establish causality.",
  "root_cause_category": "UNKNOWN",
  "is_cause_unknown": true,
  "confidence": {
    "composite_confidence": 0.0,
    "uncertainty_score": 1.0
  },
  "unresolved_gaps": [
    {
      "subsystem": "target_entity",
      "description": "Zero telemetry or event transitions recorded preceding symptom",
      "why_it_matters": "Cannot infer causal mechanisms without empirical observations"
    }
  ]
}
```
Kairo will never invent a single root cause merely because a user or dashboard expects one.

---

## 3. Explanation Lifecycle

Explanations transition through a formal state machine:
1. `REQUESTED`: Target entity and incident identified.
2. `ASSEMBLING`: Preceding temporal events and transitions retrieved.
3. `HYPOTHESIS_GENERATED`: Mechanistic candidate links formed.
4. `EVIDENCE_PENDING`: Arbitrated empirical evidence attached.
5. `TEMPORALLY_VALIDATED`: Strict cause-before-effect precedence verified.
6. `CAUSALLY_ASSESSED`: Weakest-link confidence and contributors scored.
7. `ALTERNATIVES_ASSESSED`: Competing hypotheses and discriminating tests formulated.
8. `PROVISIONAL`: Candidate explanation ready for human/operator inspection.
9. `SUPPORTED`: Backed by high-confidence empirical evidence.
10. `CONTESTED`: Conflicting telemetry or agent reports observed.
11. `CONTRADICTED`: Subsequent observation disproves the predicted outcome.
12. `VERIFIED`: Follow-up observation explicitly confirms the mechanistic prediction.
13. `SUPERSEDED`: Replaced by a newer version with late-arriving telemetry.
14. `STALE`: Historical validity window expired.
15. `UNKNOWN`: Cause cannot be established with available observations.

---

## 4. Multi-Factor Root Cause Analysis

Incidents frequently arise from systemic interactions rather than a single broken line of code. Root Cause categories include:
- `IMMEDIATE_TRIGGER`: Final precipitating event (e.g. memory allocation threshold reached).
- `CONTRIBUTING_FACTOR`: Intermediate amplifier (e.g. request queue buffer backlog).
- `UPSTREAM_CAUSE`: Preceding root dependency failure (e.g. third-party API outage).
- `ENABLING_CONDITION`: Dormant vulnerability or high base load.
- `SYSTEMIC_FACTOR`: Structural retry loops or cascade propagation.
- `ENVIRONMENTAL_FACTOR`: Cloud regional degradation or noisy neighbor contention.
- `PROTECTIVE_FACTOR`: Circuit breaker or rate limiter that arrested further escalation.

---

## 5. Competing Alternatives & Discriminating Observations

For every primary explanation, Kairo synthesizes competing hypotheses. Crucially, each alternative defines a **discriminating observation**:
- *Primary*: Resource exhaustion on database worker.
- *Alternative*: External network gateway packet drop.
- *Discriminating Test*: `"Inspect TCP retransmit rate and gateway egress drop counters; if drops < 0.1%, local resource exhaustion is confirmed."`

---

## 6. Counterfactual Isolation

Counterfactual simulations are generated via the causal engine (`CounterfactualEngine`), but are strictly tagged:
```json
{
  "intervention_description": "What if memory allocation had been 8GB instead of 2GB?",
  "expected_difference": "Queue would not have backlogged and latency would have remained nominal.",
  "is_hypothetical": true
}
```
`is_hypothetical=True` ensures simulations are never presented or stored as empirical facts.

---

## 7. Downstream Bridges & Safety Governance

- **Task 110 Cognitive Working Set**: Receives bounded explanation context (top 3 contributors, top 2 alternatives, next verification step) without dumping the full graph into context.
- **Task 109 Attention**: Receives salience alerts for contradicted or high-uncertainty explanations without usurping priority authority.
- **EmergencyStop**: Temporal explanations cannot authorize actions or override EmergencyStop (`hasattr(service, "execute_action") == False`).

---

## 8. REST API & CLI Interface

### REST Endpoints
- `POST /api/v1/explanations`: Generate causal explanation.
- `GET /api/v1/explanations`: List recent explanations.
- `GET /api/v1/explanations/{id}`: Full explanation record.
- `GET /api/v1/explanations/{id}/timeline`: Chronological event chain.
- `GET /api/v1/explanations/{id}/chain`: Causal links and mechanisms.
- `GET /api/v1/explanations/{id}/hypotheses`: Primary and alternative hypotheses.
- `GET /api/v1/explanations/{id}/evidence`: Supporting and contradicting evidence.
- `GET /api/v1/explanations/{id}/alternatives`: Competing alternatives.
- `GET /api/v1/explanations/{id}/counterfactuals`: What-if scenarios.
- `GET /api/v1/explanations/{id}/gaps`: Unresolved telemetry gaps.
- `GET /api/v1/explanations/{id}/snapshot`: Point-in-time snapshot.
- `GET /api/v1/explanations/{id}/verification`: Verification history.
- `POST /api/v1/explanations/{id}/verify`: Record empirical observation.
- `POST /api/v1/explanations/{id}/feedback`: Ingest operator feedback.
- `POST /api/v1/explanations/{id}/refresh`: Re-evaluate with current telemetry.

### CLI Commands
```bash
# Generate explanation for entity
python -m app.causal.explanation.cli target cluster_prod --symptom timeout

# Inspect event chain timeline
python -m app.causal.explanation.cli timeline <explanation_id>

# Inspect causal link chain
python -m app.causal.explanation.cli chain <explanation_id>

# Inspect evidence panel
python -m app.causal.explanation.cli evidence <explanation_id>

# View alternative hypotheses and discriminating tests
python -m app.causal.explanation.cli alternatives <explanation_id>

# View unresolved gaps
python -m app.causal.explanation.cli gaps <explanation_id>

# Record empirical follow-up verification
python -m app.causal.explanation.cli verify <explanation_id> "Confirmed zero packet drops"

# Inspect immutable snapshot
python -m app.causal.explanation.cli snapshot <explanation_id>
```
