# Kairo Adaptive Learning, Strategy Optimization & Experience Engine (Task 43)

The **Adaptive Learning, Strategy Optimization, Failure Learning, Tool Reliability, Plan Improvement, and Safe Continuous Improvement Engine** enables Kairo to improve over time from verified experience without permitting unreviewed, uncontrolled, or unsafe behavior modifications.

## Core Operational Principle

```
EXPERIENCE
  ↓
EVALUATION
  ↓
LEARNING SIGNAL
  ↓
CANDIDATE IMPROVEMENT
  ↓
VALIDATION
  ↓
POLICY
  ↓
CONTROLLED ADOPTION
  ↓
MEASURE
  ↓
ROLLBACK IF NECESSARY
```

**Never**: `EXPERIENCE → AUTOMATIC UNREVIEWED BEHAVIOR CHANGE`.

## Absolute Security Invariants

Learning **MUST NOT** modify:
1. Security policy or `SecurityCenter` controls
2. Authorization rules and permissions
3. Human approval requirements
4. Historical audit records
5. System identity
6. Safety boundaries

Learning proposes improvements; Governance decides whether those improvements are allowed.

## Subsystems

1. **Experiences & Quality Weights (`experiences.py`, `outcomes.py`)**:
   - 12 Experience types: `SUCCESS`, `PARTIAL_SUCCESS`, `FAILURE`, `UNKNOWN`, `RECOVERY_SUCCESS`, `RECOVERY_FAILURE`, `USER_CORRECTION`, `VERIFICATION_FAILURE`, `PLAN_FAILURE`, `TOOL_FAILURE`, `MODEL_FAILURE`, `RETRIEVAL_FAILURE`.
   - Quality weighting: Only verified outcomes receive strong learning weight. Unknown outcomes receive zero or weak positive signal.
   - Secret redaction: Sensitive tokens and credentials scrubbed via `ArgumentSanitizer`.

2. **Signals & Source Authority (`signals.py`, `feedback.py`)**:
   - 7 Signal types: `POSITIVE`, `NEGATIVE`, `NEUTRAL`, `CORRECTION`, `REGRESSION`, `IMPROVEMENT`, `DEGRADATION`.
   - Verified objective outcomes outrank subjective feedback.
   - Anti-poisoning defenses: Rate limits and injection checks on user feedback.

3. **Strategy Store & Deterministic Optimizer (`strategies.py`, `strategy_store.py`, `optimizer.py`)**:
   - 6 Lifecycle statuses: `CANDIDATE`, `EXPERIMENTAL`, `ACTIVE`, `DEPRECATED`, `BLOCKED`, `ROLLED_BACK`.
   - Multi-factor deterministic ranking: Verification Rate (35%), Success Rate (25%), Confidence (15%), Sample Size (10%), Latency (10%), Cost (5%). No opaque single-number scores.
   - Small sample warnings for strategies with fewer than 5 executions.

4. **Reliability & Provider Tracking (`reliability.py`)**:
   - Empirical tracking of tool and model provider reliability (successes, failures, timeouts, unknown outcome rates, average latency).
   - High unknown-outcome rates heavily penalize reliability scores.

5. **Failure Clustering & Pre-Flight Warnings (`patterns.py`, `failures.py`, `recovery.py`)**:
   - Normalizes error messages into cluster signatures.
   - Generates evidence-backed pre-flight warnings before risky workflows execute.
   - Learns safe remediation actions per failure signature without blind retry loops.

6. **Controlled Canary Experiments (`experimentation.py`)**:
   - A/B canary trials comparing baseline vs candidate strategies.
   - Statuses: `PLANNED`, `RUNNING`, `COMPLETED`, `STOPPED`, `FAILED`.

7. **Promotion, Rollback & Environmental Decay (`promotion.py`, `rollback.py`, `decay.py`)**:
   - Governed promotion criteria: Minimum sample size (10), minimum verification rate (80%), maximum failure rate (15%).
   - Automated rollback triggers: Drops in verification rate or failure rate spikes.
   - Environmental decay: Re-evaluates and flags strategies when underlying tools, models, or dependencies change.

8. **Personalization & Safety Boundaries (`personalization.py`, `safety.py`, `calibration.py`)**:
   - Scoped user and project preferences with strict cross-tenant isolation.
   - Anti-reward-hacking guards prevent optimizations that sacrifice verification coverage for speed.

9. **REST API & Operator UI (`router.py`, `schemas.py`)**:
   - Mounted under `/api/v1/learning`.
