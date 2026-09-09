# Kairo Truth, Verification & Self-Correction Engine (Task 42)

The **Truth, Verification, Self-Correction, Contradiction Detection, Fact Validation, and Confidence Calibration Engine** provides robust verification of system claims, preventing hallucinated completions, false successes, stale state assumptions, and blind retries.

## Core Architectural Principle

```
CLAIM
  ↓
EVIDENCE
  ↓
VERIFICATION
  ↓
TRUTH STATUS
  ↓
STATE UPDATE
```

Never: `CLAIM → ASSUME TRUE`.

## Components

1. **Claims Lifecycle (`claims.py`)**:
   - Manages 9 claim types: `FACT`, `STATE`, `PREDICTION`, `PLAN_EXPECTATION`, `MODEL_ASSERTION`, `TOOL_REPORT`, `USER_ASSERTION`, `INFERENCE`, `HYPOTHESIS`.
   - 8 truth statuses: `VERIFIED`, `SUPPORTED`, `UNVERIFIED`, `CONTRADICTED`, `UNKNOWN`, `STALE`, `INVALID`, `REJECTED`.
   - Anti-Self-Attestation (Spec 19, 75): Model assertions such as "done" or "fixed" do not self-verify.

2. **Evidence Model & Provenance (`evidence.py`, `provenance.py`)**:
   - 15 evidence types: `DIRECT_OBSERVATION`, `TOOL_RESULT`, `DATABASE_STATE`, `API_RESPONSE`, `TEST_RESULT`, `FILE_CONTENT`, `GIT_STATE`, `DEPLOYMENT_STATE`, `HEALTH_CHECK`, `USER_INPUT`, `DOCUMENT`, `WEB_SOURCE`, `MEMORY_REFERENCE`, `WORLD_MODEL`, `MODEL_INFERENCE`.
   - Lineage preservation and same-source duplicate prevention.
   - Integrated with enterprise secret redaction (`app.security.redaction.ArgumentSanitizer`).

3. **Invariants & Domain Validators (`invariants.py`, `validators.py`)**:
   - Invariants evaluate state rules (e.g. task completed cannot hold active lease, unapproved high-risk actions cannot proceed).
   - Domain validators verify side effects: Deployment (API + health check + version check), Code change (tests + lint + typecheck), File write (existence + sha256 hash), Database migration (migration output + table inspection).

4. **Contradictions & Source Triangulation (`contradictions.py`, `triangulation.py`)**:
   - Detects 6 contradiction types: `DIRECT_CONFLICT`, `TEMPORAL_CONFLICT`, `SCOPE_CONFLICT`, `VERSION_CONFLICT`, `SOURCE_CONFLICT`, `STATE_CONFLICT`.
   - Authority hierarchy: Authoritative state > Direct observation > Trusted external evidence > Derived state > Inference > Model claim.
   - Triangulates multi-source facts, requiring independent sources and divergence detection.

5. **Freshness & Calibrated Confidence (`freshness.py`, `confidence.py`)**:
   - Tracks observation age against TTL windows (e.g., server health 60s, telemetry 120s). Automatically degrades expired claims to `STALE`.
   - Structured confidence (`LOW`, `MEDIUM`, `HIGH`) and uncertainty states (`KNOWN`, `LIKELY`, `UNCERTAIN`, `UNKNOWN`, `CONTRADICTORY`).
   - Rejects fake pseudo-exact percentages in favor of calibrated multi-factor scores.

6. **Self-Correction & Oscillation Guard (`self_correction.py`, `reconciliation.py`)**:
   - Executes canonical loop: `CLAIM → VERIFY → FAIL → DIAGNOSE → CORRECT → REVERIFY`.
   - Protects against oscillation loops (`A → B → A → B`) and bounds attempts.
   - Generates transparent admissions: *"I was wrong about X. Verification shows Y."*
   - Strictly enforces safety boundary: cannot alter security, policy, or audit records.

7. **Evaluators & Strategies (`evaluators.py`, `strategies.py`)**:
   - Validates citations against real sources and excerpts, detecting hallucinated citations.
   - Evaluates test rigor, rejecting empty or always-pass tautologies (`assert True`).
   - Implements 10 read-only verification strategies (`DIRECT_CHECK`, `STATE_QUERY`, `HEALTH_CHECK`, `TEST_EXECUTION`, `HASH_COMPARISON`, `DIFF_COMPARISON`, `SOURCE_COMPARISON`, `INVARIANT_CHECK`, `RECONCILIATION`, `USER_CONFIRMATION`).

8. **Service & REST API (`service.py`, `router.py`, `schemas.py`)**:
   - FastAPI endpoints mounted at `/api/v1/verification`.
