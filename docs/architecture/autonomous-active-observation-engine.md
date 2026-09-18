# KAIRO Autonomous Active Observation, Value-of-Information, Information Acquisition & Uncertainty Reduction Engine (Task 114)

## 1. Executive Summary & Core Principles
The **Autonomous Active Observation, Value-of-Information (VoI), and Uncertainty Reduction Engine** provides Kairo with epistemic self-awareness: the autonomous ability to recognize **"I do not currently know enough"**, determine what specific information would resolve that unknown, calculate whether acquiring that information is worth the cost and operational risk, prioritize existing internal evidence before initiating external retrieval, and decide whether to **ACT NOW**, **WAIT**, **OBSERVE**, or **ASK USER**.

### Hard Architectural Invariants
1. **UNKNOWN ≠ FALSE**: Missing information is never treated as a negative assertion or absence of state change.
2. **MISSING DATA ≠ NO CHANGE**: Absence of telemetry does not imply the target system is invariant.
3. **NO OBSERVATION ≠ NO EVENT**: Silence across monitoring channels does not prove an event did not occur.
4. **MORE DATA ≠ MORE KNOWLEDGE**: Redundant retrieval is recognized as saturation with zero or negligible marginal VoI.
5. **MORE KNOWLEDGE ≠ BETTER DECISION**: High-cost observation that cannot alter the downstream decision is rejected (`NO_OBSERVATION_NEEDED`).
6. **INFORMATION VALUE ≠ ACTION VALUE**: High information value never confers execution authority.
7. **OBSERVATION ≠ AUTHORIZATION & OBSERVATION ≠ EXECUTION**: Observation candidates must respect `SecurityCenter`, `Governance`, `ApprovalRegistry`, `ResourceEconomy`, and `EmergencyStop`.
8. **EVIDENCE ≠ TRUTH**: Observations are empirical facts with source provenance, freshness, and reliability weights, never absolute metaphysical truth.
9. **CORRELATION ≠ CAUSATION & MODEL CONFIDENCE ≠ REALITY**: Causal hypotheses are discriminated through bounded observations or experiments, not speculative extrapolation.
10. **EXISTING DATA FIRST**: Kairo queries context, memory, beliefs, world-state, graph, and temporal history before considering active observation.
11. **PROMPT-INJECTION DEFENSE**: Observation payloads and targets are sanitized and handled strictly as DATA; never evaluated as code, system instructions, or permission escalations.
12. **NO RAW CHAIN-OF-THOUGHT**: All planning and evaluations persist structured hypotheses, evidence items, uncertainty matrices, and VoI metrics without raw reasoning traces.

---

## 2. End-to-End Information Acquisition Pipeline

```
CURRENT UNCERTAINTY STATE
          ↓
EPISTEMIC UNCERTAINTY (15 Dimensions)
          ↓
DOWNSTREAM DECISION IMPACT
          ↓
INFORMATION GAPS IDENTIFICATION
          ↓
EXISTING DATA FIRST CHECK (Context, Memory, Graph, Beliefs, Temporal)
          ↓ (If resolved → NO_OBSERVATION_NEEDED)
CANDIDATE OBSERVATION GENERATION (PASSIVE, ACTIVE, CONTROLLED, USER, WAIT)
          ↓
EXPECTED VALUE-OF-INFORMATION (VoI) & MARGINAL GAIN
          ↓
COST, LATENCY & RISK TRADEOFF ANALYSIS
          ↓
SAFETY, GOVERNANCE & PROMPT-INJECTION FIREWALL
          ↓
STOPPING INTELLIGENCE (ACT NOW | WAIT | OBSERVE | ASK USER | NO FURTHER INFO)
          ↓
EMPIRICAL OBSERVATION EXECUTION
          ↓
CONFLICT DETECTION & ARBITRATION (No blind averaging)
          ↓
INTEGRITY & PROVENANCE VERIFICATION
          ↓
BELIEF ARBITRATION (Task 107) & WORLD-STATE RECONCILIATION (Task 98)
          ↓
UNCERTAINTY REDUCTION & DECISION RE-EVALUATION (Task 94)
```

---

## 3. Epistemic Uncertainty Model (15 Dimensions)
Epistemic uncertainty is assessed across 15 orthogonal dimensions:
1. `FACTUAL`: Empirical existence of attributes and parameters.
2. `TEMPORAL`: Timestamp accuracy, order precedence, and duration validity.
3. `CAUSAL`: Root causes and mechanisms versus mere statistical correlation.
4. `STATE`: Concrete runtime state of components and services.
5. `IDENTITY`: Authenticated identity of callers, nodes, and resources.
6. `INTENT`: Ambiguity between competing interpretations of goals or user instructions.
7. `CAPABILITY`: Functional readiness versus degraded execution limits.
8. `RESOURCE`: Budget reserves, token limits, and compute quotas.
9. `RELIABILITY`: Failure likelihood trajectories, recurrence, and recovery durations.
10. `FORECAST`: Predictive projection bounds and horizon horizons.
11. `DECISION`: Invariant sensitivity versus branch-changing alternatives.
12. `OUTCOME`: Predicted post-condition verification.
13. `PROVENANCE`: Source lineage, audit signatures, and tamper-free hashes.
14. `SCOPE`: Blast radius boundaries and entity containment.
15. `FRESHNESS`: Staleness decay relative to operational TTLs.

Each dimension is assigned an epistemic status:
`KNOWN`, `LIKELY`, `UNCERTAIN`, `CONTESTED`, `UNKNOWN`, `STALE`.

---

## 4. Decision Sensitivity Analysis
An unknown is only meaningful to resolve if doing so has the potential to alter a downstream decision:
- **Decision-Sensitive**: Resolving the gap discriminates between competing options (e.g. `Action A` vs `Action B`, or `ACT NOW` vs `WAIT`).
- **Decision-Insensitive**: Regardless of what value the unknown takes, the downstream action remains invariant. Under decision insensitivity, the engine issues `NO_OBSERVATION_NEEDED` with `DECISION_INSENSITIVE` stop reason, eliminating wasteful polling.

---

## 5. Value-of-Information (VoI) & Marginal Gain
The expected information value of a candidate observation is estimated as:
$$\text{Net Value Score} = \text{Marginal Value} - (\text{Cost Penalty} + \text{Risk Penalty})$$

### Information Saturation Detection
When two or more independent outcomes already report consistent readings for a metric, additional observations yield diminishing marginal returns ($< 0.15$), triggering saturation dampening and stopping redundant queries.

---

## 6. Observation Methods
1. **`PASSIVE`**: Non-intrusive ingestion of telemetry, metrics streams, and event buses.
2. **`ACTIVE`**: Targeted read-only diagnostic queries, status probes, or database inspections.
3. **`CONTROLLED`**: Sandboxed replays or safe staging experiments (Task 105 integration).
4. **`USER`**: Minimal, targeted user clarifications when intent ambiguity carries material consequence.
5. **`WAIT`**: Passive temporal convergence when natural state transitions or pending operations are expected to yield verified evidence without active polling.

---

## 7. Multi-Source Conflict Arbitration
When independent sources return contradictory signals (e.g., Source A reports `HEALTHY` while Source B reports `DEGRADED`), the engine avoids blind averaging. Instead, both signals are preserved with timestamps, confidence scores, and provenance hashes, assigning an explicit arbitration strategy:
- `RECENCY`: Prefer fresher telemetry when confidence is equal.
- `PROVENANCE_WEIGHT`: Trust verified cryptographic or high-reliability sensors.
- `UNRESOLVED`: Escalate contested state to Belief Arbitration (Task 107) and Situation Awareness (Task 99).

---

## 8. Stopping Intelligence & Recommended Stances
Stopping criteria prevent infinite loops:
- `SUFFICIENT_INFORMATION`: Uncertainty confidence $\ge 0.85$ with zero critical unknowns.
- `DECISION_INSENSITIVE`: Downstream decision is unaffected by further data.
- `BUDGET_EXHAUSTED`: Resource economy quota consumed.
- `DEADLINE_REACHED`: Time limit expired.
- `NO_USEFUL_SOURCE`: Available sources are exhausted or unreachable.
- `NO_OBSERVATION_NEEDED`: Internal evidence already resolved all gaps.

Operational Stances:
- **`ACT NOW`**: Information is sufficient or budget/deadline reached; proceed with decision.
- **`WAIT`**: Natural event is imminent; do not burn budget on active polling.
- **`OBSERVE`**: High-value, safe, cost-effective candidate available.
- **`ASK USER`**: High-consequence intent ambiguity detected.
- **`NO FURTHER INFORMATION NEEDED`**: Epistemic state is adequate or insensitive.

---

## 9. API & CLI Interface

### REST API Endpoints (`/api/v1/observations`)
- `POST /plans`: Create new observation plan with uncertainty matrix and gap detection.
- `GET /plans`: List recent observation plans.
- `GET /plans/{id}`: Detailed plan view with gaps, candidates, outcomes, and verifications.
- `GET /plans/{id}/gaps`: Extracted information gaps with sensitivity badges.
- `GET /plans/{id}/candidates`: Generated observation options with VoI estimates.
- `GET /plans/{id}/value`: VoI calculations and marginal gain breakdown.
- `GET /plans/{id}/cost`: Compute, network, latency, and privacy cost metrics.
- `GET /plans/{id}/risk`: Security, mutation, and reversibility risk classifications.
- `GET /plans/{id}/uncertainty`: Pre- and post-observation uncertainty matrices.
- `POST /plans/{id}/execute`: Execute selected or top-VoI candidate.
- `POST /plans/{id}/cancel`: Invalidate or cancel in-flight observation.
- `POST /plans/{id}/refresh`: Refresh stale plan against current state.
- `GET /gaps`: List all open information gaps across system.
- `GET /uncertainty`: Inspect 15-dimension uncertainty for target entity.
- `GET /history`: Historical observation logs and stances.

### CLI Subcommands (`kairo observe`)
```bash
kairo observe gaps [--plan-id ID]
kairo observe plan <target> [--question Q] [--budget B]
kairo observe candidates <id>
kairo observe value <id>
kairo observe cost <id>
kairo observe risk <id>
kairo observe run <id> [--candidate-id CID]
kairo observe show <id>
kairo observe verify <id>
kairo observe uncertainty [--target T]
kairo observe history
```
