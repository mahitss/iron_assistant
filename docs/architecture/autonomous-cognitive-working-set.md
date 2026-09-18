# Kairo Autonomous Cognitive Working Set, Context Assembly & Context Lifecycle Engine (Task 110)

> **Status**: Production-Hardened Autonomous Cognitive Working Set Substrate  
> **Module**: `backend/app/context/`  
> **Database Migration**: `0078_autonomous_cognitive_working_set_and_context_lifecycle`  
> **Frontend View**: `frontend/components/context/cognitiveWorkingSetView.js`  
> **Verification Script**: `scripts/verify_cognitive_working_set_e2e.py`

---

## 1. Executive Summary & Problem Formulation

In complex autonomous AI agent architectures, reasoning performance degrades not from lack of information, but from **unbounded, unvetted, stale, conflicting, or unbudgeted context**.

The **Kairo Cognitive Working Set Engine** answers the authoritative operational question:
> **"What information should be presented to the next cognitive operation, in what form, with what provenance, with what freshness, and within what budget?"**

### The Core Architectural Tenet
```
RAW AVAILABLE INFORMATION (Attention, Intent, Belief, Memory, World State, Self Model, Decisions, Missions)
        ↓
Candidate Gathering (Multi-Subsystem Ingestion & Source Tagging)
        ↓
Freshness Evaluation (Exponential Volatility Decay: FRESH → STALE → EXPIRED)
        ↓
Security & Trust Filtering (Untrusted Web/Tool Text Quarantined to OPTIONAL)
        ↓
Bounded Dependency Expansion (Graph Traversal capped at Depth <= 3)
        ↓
Epistemic Conflict Surfacing (Preserves Competing Items Without False Consensus)
        ↓
Relevance Scoring (Multi-Component Transparent Breakdown: No Magic Numbers)
        ↓
Context Budgeting & Graceful Degradation (Tokens, Bytes, Latency, Items)
        ↓
Selective Compression (NONE, LIGHT, MODERATE, AGGRESSIVE, REFERENCE_ONLY)
        ↓
Working-Set Assembly & Section Packing (24 Canonical Structural Sections)
        ↓
Validity Lease Issuance (Short-Lived TTL, Event-Driven Invalidation)
        ↓
Immutable Audit Snapshot (Deterministic SHA-256 Fingerprint for Replay)
        ↓
Downstream Cognitive Operation (Planning, Decision Intelligence, Action Preflight)
        ↓
Empirical Usage Feedback & 13-Dimension Quality Assessment
```

---

## 2. Strict Core Invariants

The subsystem enforces 25 inviolable architectural invariants:

1. **`CONTEXT != MEMORY`**: Context is an ephemeral, bounded working set, not permanent storage.
2. **`CONTEXT != TRUTH`**: Inclusion in context does not validate factual correctness.
3. **`CONTEXT != ATTENTION`**: Attention decides focus; context packs the required information within budget.
4. **`CONTEXT != DECISION`**: The context engine does not make decisions; it supplies evidence to Task 94 Decision Intelligence.
5. **`CONTEXT != AUTHORIZATION`**: Inclusion in context never grants permission or authorization (SecurityCenter remains sole authority).
6. **`CONTEXT != POLICY`**: Context engine does not define or alter security policies.
7. **`CONTEXT != GOAL`**: Missions and goals are defined upstream in Task 100.
8. **`CONTEXT != WORLD STATE`**: Distinguishes observed reality from predicted or historical state.
9. **`CONTEXT != USER CONSENT`**: Cannot infer consent from context inclusion.
10. **`CONTEXT != EXECUTION`**: Zero execution primitives inside the context engine.
11. **`CONTEXT != COMPLETE REALITY`**: Absence from context does not equal absence from reality.
12. **`HIGH RELEVANCE != HIGH TRUTH`**: High relevance to a query does not make an item true.
13. **`RECENCY != CORRECTNESS`**: Freshness is tracked explicitly; recency does not imply accuracy.
14. **`MEMORY RETRIEVAL != CURRENT STATE`**: Stored memories cannot silently masquerade as live state.
15. **`BELIEF != FACT`**: Epistemic certainty is preserved and labeled.
16. **`SUMMARY != SOURCE`**: Lossy summarization retains source pointers; never claims equivalence.
17. **`COMPRESSION != LOSSLESS REPRESENTATION`**: Information loss is explicitly tracked (`NONE`, `MINOR`, `MODERATE`, `SEVERE`).
18. **`TOKEN SAVINGS != COGNITIVE QUALITY`**: Compression balances semantic fidelity against budget.
19. **`UNTRUSTED CONTENT NEVER GAINS AUTHORITY`**: Web, DOM, Git, and tool text remain untrusted data.
20. **`EMERGENCY STOP ALWAYS OVERRIDES`**: Immediately invalidates execution-related working sets fail-closed.
21. **`LEASES EXPIRE FAIL-CLOSED`**: Stale or expired leases prevent blind reuse.
22. **`REQUIRED SAFETY CONTEXT NEVER DROPPED`**: Safety context is non-negotiable even under severe budget pressure.
23. **`RESOURCE BUDGETS NEVER EXCEEDED SILENTLY`**: Budget exhaustion triggers graceful degradation ladders.
24. **`MULTI-AGENT ISOLATION`**: Agent A's private context never leaks to Agent B.
25. **`SNAPSHOTS REMAIN IMMUTABLE`**: Context snapshots are cryptographically reproducible audit records.

---

## 3. Subsystem Architecture

### 3.1 Freshness Engine (`freshness_engine.py`)
Calculates staleness using domain-specific half-life curves:
- **Static Documentation / Code**: 30-day half-life.
- **User Preferences / Beliefs**: 7-day half-life.
- **Standard Operational State**: 24-hour half-life.
- **Dynamic Attention / Situation**: 1-hour half-life.
- **Live Telemetry**: 60-second half-life.

Items are classified into:
- `FRESH`: Recent and fully actionable.
- `RECENT`: High confidence.
- `AGING`: Usable, but approaching expiry.
- `STALE`: Outdated; preserved for historical comparison, prohibited from masquerading as current state.
- `EXPIRED`: Past explicit deadline; rejected for current deliberation.

### 3.2 Provenance & Cryptographic Lineage (`provenance_engine.py`)
Every item maintains an unbroken audit path:
```
external_observation → parser → world_state → belief_arbitration → context_transform → working_set
```
Lineage signatures are hashed with SHA-256 to ensure authenticity. Content is strictly classified into trust tiers:
- `OBSERVED`: Ground-truth telemetry or sensory inputs.
- `USER_AUTHORED`: Direct user prompts.
- `SYSTEM_DERIVED`: Internal deterministically computed state.
- `MODEL_DERIVED`: Inferred or generated by LLMs.
- `AGENT_DERIVED`: Produced by autonomous subagents.
- `EXTERNAL_UNTRUSTED`: Ingested from external APIs, web scrapers, or repositories.

### 3.3 Context Budgeting & Degradation Ladder (`budget_engine.py`)
When candidate tokens exceed the allocated budget from Task 77 Resource Economy, the engine executes a strict priority ladder:
1. **Preserves REQUIRED items** (system safety, user pins, active intent).
2. **Preserves user/system pinned items**.
3. **Preserves active task state and contradiction evidence**.
4. **Compresses lower-priority items** (LIGHT → MODERATE → AGGRESSIVE).
5. **Drops optional items** and records explicit `ContextExclusion` records.
6. **Logs explicit `ContextGap` records** whenever high-relevance items cannot fit.

### 3.4 Validity Leases & Targeted Revalidation (`lease_and_lifecycle_engine.py`)
- Working sets receive short-lived leases (default 60s TTL).
- Leases transition through: `VALID` → `AGING` → `EXPIRED` / `INVALIDATED`.
- When upstream state drifts, only affected sections are refreshed, incrementing the working set version without rebuilding unaffected sections.

---

## 4. REST API Reference

| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/api/context/assemble` | Assembles a bounded Cognitive Working Set. |
| `GET` | `/api/context/working-sets` | Lists active working sets for the authenticated user/tenant. |
| `GET` | `/api/context/working-sets/{id}` | Retrieves working set details and section breakdown. |
| `GET` | `/api/context/working-sets/{id}/items` | Lists all context items with scores and inclusion status. |
| `GET` | `/api/context/working-sets/{id}/provenance` | Inspects cryptographic lineage paths for all items. |
| `GET` | `/api/context/working-sets/{id}/conflicts` | Lists preserved epistemic conflicts. |
| `GET` | `/api/context/working-sets/{id}/gaps` | Lists identified missing context gaps. |
| `GET` | `/api/context/working-sets/{id}/snapshot` | Retrieves immutable audit snapshot and SHA-256 fingerprint. |
| `POST` | `/api/context/working-sets/{id}/refresh` | Incrementally refreshes working set to a new version. |
| `POST` | `/api/context/working-sets/{id}/invalidate`| Invalidates working set fail-closed. |
| `POST` | `/api/context/working-sets/{id}/pin` | Pins an item to guarantee presence. |
| `POST` | `/api/context/working-sets/{id}/unpin` | Unpins a previously pinned item. |
| `POST` | `/api/context/working-sets/{id}/feedback` | Submits post-deliberation empirical feedback. |
| `GET` | `/api/context/working-sets/{id}/quality` | Retrieves 13-dimension quality assessment scorecard. |
| `GET` | `/api/context/working-sets/{id}/timeline`| Retrieves audit event timeline. |

---

## 5. Verification & Testing

The engine is verified by two test harnesses:
1. **Pytest Suite**:
   ```bash
   pytest backend/tests/test_cognitive_working_set_and_context_lifecycle.py -v
   ```
2. **Frontend Unit Tests**:
   ```bash
   node --test frontend/tests/cognitive_working_set.test.js
   ```
3. **10-Phase End-to-End Verification Drill**:
   ```bash
   python scripts/verify_cognitive_working_set_e2e.py
   ```
