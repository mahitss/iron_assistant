# Kairo Executive Decision Engine (Task 57)

The **Kairo Executive Decision Engine** answers:
> *"What should Kairo recommend we do?"*

It synthesizes verified digital twin state, explicit goals, user priorities, hard/soft constraints, policy governance, causal reasoning (Task 55), counterfactual simulations (Task 56), epistemic uncertainty, multi-objective trade-offs, and historical executive memory into **ranked, explainable, traceable recommendations**.

---

## 1. Core Invariants

1. **Fundamental Distinction**:
   $$\text{Recommendation} \ne \text{Decision} \ne \text{Approval} \ne \text{Execution} \ne \text{Verification}$$
2. **Decision Support Only**: The Decision Engine is strictly an advisory subsystem. It possesses **zero authority to execute tools directly** (`block_direct_tool_execution` enforces this boundary).
3. **Hard Constraint Supremacy**: Hard constraints are evaluated prior to ranking. Infeasible options receive a score of zero and are disqualified. High scores on soft objectives can never compensate for violating a hard constraint.
4. **No False Certainty**: Missing data is explicitly marked `UNKNOWN`, not zero, free, or safe. Unsupported probabilities are never fabricated.
5. **Immutable Revisions**: When a user selects an alternative or overrides a recommendation, both the engine's original recommendation and the user's decision are preserved with cryptographic provenance.
6. **Prompt Injection Defense**: Untrusted external documents or model-generated text can serve as candidate evidence, but can **never** silently inject objectives, constraints, or approvals.

---

## 2. Architecture & Data Flow

```text
Goal / Intent
      ↓
Decision Request
      ↓
Context Assembly (Digital Twin + Executive Memory)
      ↓
Constraints Validation (Hard vs. Soft Pre-filtering)
      ↓
Option Generation (Conservative, Aggressive, Reversible, Info-gathering, NO_ACTION)
      ↓
Evidence Synthesis (Primary vs. Model-derived Trust Grading)
      ↓
Causal Inference Integration (Task 55)
      ↓
Counterfactual Simulation Integration (Task 56)
      ↓
Risk Assessment (12 Categories + Worst-case Exposure)
      ↓
Explainable Scoring (Multi-factor Normalized Breakdown)
      ↓
Pareto Trade-off Analysis (Frontier + Dominance)
      ↓
Epistemic Uncertainty Quantification
      ↓
Structured Deliberation (No Raw CoT Storage)
      ↓
Deterministic Ranking & Sensitivity Analysis
      ↓
Decision Gates Evaluation (10 Formal Gates)
      ↓
Recommendation Generation & Faithful Explanations
      ↓
User Decision (Engine Recommendation vs. User Override Recorded)
      ↓
Policy & Governance Engine
      ↓
Authorization & Permissions
      ↓
Formal Approval (Required for Production / Irreversible / High Risk)
      ↓
Guarded Execution Hand-off (ToolExecutor)
      ↓
Post-Execution Verification
      ↓
Outcome Reality Tracking (Predicted vs. Actual)
      ↓
Calibration & Adaptive Learning Loop
```

---

## 3. Ten Decision Gates

1. **Gate 1: Context Valid** — Ensures well-formed question, scope, and request ID.
2. **Gate 2: Goals Valid** — Verifies presence of authorized, explicit objectives.
3. **Gate 3: Constraints Satisfied** — Validates that the candidate option satisfies all hard constraints.
4. **Gate 4: Evidence Sufficient** — Confirms that grounding is supported by non-speculative evidence.
5. **Gate 5: Risk Acceptable** — Checks that risk exposure does not exceed critical thresholds.
6. **Gate 6: Simulation Freshness** — Ensures simulations are not stale or invalidated by environmental drift.
7. **Gate 7: Authorization Valid** — Verifies that the decision requester holds requisite authority.
8. **Gate 8: Approval Requirement** — Flags mandatory human approval for production, irreversible, or high-risk actions.
9. **Gate 9: Execution Plan Valid** — Generates a staged, guarded execution proposal.
10. **Gate 10: Verification Plan Exists** — Defines telemetry and invariant checks proving success post-execution.

---

## 4. REST API Reference

All endpoints are mounted under `/api/v1/decision`:

- `POST /api/v1/decision/analyze`: Deliberates on a decision request and generates a traceable recommendation.
- `GET /api/v1/decision/{id}`: Retrieves a decision record.
- `GET /api/v1/decision`: Lists recent decision records.
- `POST /api/v1/decision/{id}/select`: Records an authorized actor's selection (tracks user overrides).
- `POST /api/v1/decision/{id}/approve`: Records formal human or policy approval.
- `POST /api/v1/decision/{id}/revalidate`: Re-evaluates decision against drifted state or updated policies.
- `POST /api/v1/decision/{id}/outcome`: Records verified post-execution outcome and computes prediction error.
- `GET /api/v1/decision/{id}/outcome`: Retrieves verified outcome data.
- `GET /api/v1/decision/{id}/explanation`: Queries structured explanations ("why this option?", "why not B?", "risks?").
- `GET /api/v1/decision/{id}/as-of`: Reconstructs historical decision snapshot as of evaluation time.
- `GET /api/v1/decision/analytics/calibration`: Reports acceptance rate, override rate, calibration error, and overconfidence assessments.
