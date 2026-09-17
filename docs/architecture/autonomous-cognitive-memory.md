# KAIRO Autonomous Cognitive Memory, Experience Consolidation & Lifelong Learning Fabric (Task 103)

## 1. Executive Architectural Overview

The **Autonomous Cognitive Memory & Lifelong Learning Fabric** provides Kairo with an evidence-based, provenance-aware cognitive retention system that transforms operational experiences into durable structured knowledge.

Crucially, this system preserves clear boundaries between memory, live reality, and execution authority:

```
                                  MANDATORY INVARIANTS
  ┌────────────────────────────────────────────────────────────────────────────────────────┐
  │  MEMORY ≠ TRUTH          MEMORY ≠ CURRENT STATE       MEMORY ≠ AUTHORIZATION           │
  │  MEMORY ≠ POLICY         MEMORY ≠ GOAL                MEMORY ≠ DECISION                │
  │  MEMORY ≠ CAUSALITY      MEMORY ≠ REALITY             CURRENT WORLD-STATE WINS!        │
  └────────────────────────────────────────────────────────────────────────────────────────┘
```

A memory is historical evidence. Current operational reality must always come from live observation and the World-State Reconstruction Engine (Task 98).

```
   ┌──────────────┐      ┌───────────┐      ┌─────────────┐      ┌──────────────┐
   │  EXPERIENCE  │ ───► │  CAPTURE  │ ───► │  SANIDATE   │ ───► │  CANDIDATE   │
   │  (Raw Event) │      │ (Sanitize)│      │ (Trust Lvl) │      │ (Discounted) │
   └──────────────┘      └───────────┘      └─────────────┘      └──────┬───────┘
                                                                        │
        ┌───────────────────────────────────────────────────────────────┘
        ▼
   ┌──────────────┐      ┌───────────┐      ┌─────────────┐      ┌──────────────┐
   │ CORROBORATE  │ ───► │  PROMOTE  │ ───► │  RECONCILE  │ ───► │   RETRIEVE   │
   │ (≥2 Verified)│      │  (ACTIVE) │      │(World-State)│      │(Scope-Iso-Ctx│
   └──────────────┘      └───────────┘      └─────────────┘      └──────┬───────┘
                                                                        │
        ┌───────────────────────────────────────────────────────────────┘
        ▼
   ┌──────────────┐      ┌───────────┐      ┌─────────────┐      ┌──────────────┐
   │    APPLY     │ ───► │  EMPIRICAL│ ───► │ METACOGNITIVE│ ───► │ DETERMINISTIC│
   │ (Reasoning)  │      │  OUTCOME  │      │  FEEDBACK   │      │    REPLAY    │
   └──────────────┘      └───────────┘      └─────────────┘      └──────────────┘
```

---

## 2. Core Domain Contracts

### 2.1 The Experience Model (`Experience`)
Operational occurrences captured across Kairo with mandatory provenance:
- `experience_id`: Unique identifier (`exp_...`)
- `source_type`: Canonical classification (`OBSERVATION`, `ACTION`, `FAILURE`, `RECOVERY`, `USER_FEEDBACK`, `USER_CORRECTION`, etc.)
- `trust_classification`: Epistemological trust (`OBSERVED`, `USER_CONFIRMED`, `SYSTEM_VERIFIED`, `ACTION_VERIFIED`, `WORLD_STATE_VERIFIED`, `EXTERNAL_UNTRUSTED`, `INFERRED`, `UNKNOWN`)
- `summary`: Concise description with automatic regex redaction of API keys, bearer tokens, connection strings, and passwords
- `structured_facts`: Structured key-value data with recursive secret scrubbing
- `related_entities`: Entities linked in the Knowledge Graph

### 2.2 The Durable Memory Item (`CognitiveMemoryItem`)
- `memory_id`: Unique identifier (`mem_...`)
- `memory_type`: 15 canonical types (`EPISODIC`, `SEMANTIC`, `PROCEDURAL`, `PREFERENCE`, `ENVIRONMENTAL`, `CAPABILITY`, `MISSION`, `DECISION`, `FAILURE`, `RECOVERY`, `PATTERN`, `CONSTRAINT`, `FACTUAL`, `TEMPORAL`, `RELATIONAL`)
- `lifecycle_state`: Progression states (`CANDIDATE` -> `ACTIVE` -> `CONSOLIDATED` -> `STALE` -> `SUPERSEDED` -> `CONFLICTED` -> `RETIRED`)
- `freshness`: Temporal validity (`CURRENT`, `RECENT`, `STALE`, `EXPIRED`, `UNKNOWN`)
- `decay_rate_days`: Configurable decay (7 days for environment state, 90 days for verified procedures)
- `confidence`: Evidence-backed confidence score ($0.0 \dots 1.0$) with explicit evidence reasoning

### 2.3 Dialectic Contradiction (`MemoryConflict`)
Tracks competing claims across memories in the same scope without destructive overwriting.
- Invariant: Current World-State arbitration automatically overrules historical claims.

---

## 3. Defense Mechanisms & Invariants

### 3.1 Memory Poisoning Defense
Untrusted sources (`EXTERNAL_UNTRUSTED`, untrusted web scraped content) are strictly flagged:
- **Immunity Invariant**: Repetition alone can NEVER promote an untrusted experience into a verified or active memory.
- An untrusted candidate remains permanently in `CANDIDATE` or `RETIRED` state with `UNTRUSTED` evidence flags.

### 3.2 Multi-Tenant Scope Isolation
Every memory has an explicit `MemoryScope` (`GLOBAL`, `USER`, `PROJECT`, `MISSION`, `CAPABILITY`, `ENVIRONMENT`, `SESSION`, `TASK`, `WORKFLOW`) and an optional `scope_id`:
- **Isolation Invariant**: Memory from Project A is strictly filtered out from queries in Project B. Cross-project leakage is impossible.

### 3.3 World-State Primacy
When a historical memory claims `port=8000`, but live sensor observation records `port=8080`:
- Historical memory is marked `STALE` and `CONFLICTED`.
- Current World-State wins unconditionally for operational reasoning and decision intelligence.

### 3.4 Procedural Safety & Non-Execution
A procedural memory specifies candidate preconditions, steps, and verification criteria, but:
- It CANNOT directly execute tools or shell commands.
- Execution must flow through `Decision Intelligence` -> `Security / Governance` -> `ActionTransaction`.

---

## 4. Subsystem Integration & Unified Loop

1. **Context Engineering**: Receives bounded `MemoryContextPack` bundles with freshness distributions and conflict notices rather than raw unbounded memory dumps.
2. **Decision Intelligence**: Retrieves historical precedents as evidence, not mandates.
3. **Mission Control**: Reviews previous attempts, blockers, and exceptions for cross-mission learning without state leakage.
4. **Metacognition & Self-Audit**: Consumes memory error taxonomy (`STALE`, `INCORRECT`, `OVERGENERALIZED`, `POISONING_ATTEMPT`) to adjust reasoning parameters.

---

## 5. API Surface

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/memory/status` | Fabric metrics (experiences, active, stale, conflicts, patterns) |
| `GET` | `/api/v1/memory` | List memories with scope, state, and type filtering |
| `POST` | `/api/v1/memory/experiences` | Ingest operational experience with sanitization |
| `POST` | `/api/v1/memory/search` | Scope-isolated multi-criteria memory retrieval |
| `POST` | `/api/v1/memory/context-pack` | Assemble bounded context pack for reasoning |
| `GET` | `/api/v1/memory/conflicts` | List active dialectic memory contradictions |
| `GET` | `/api/v1/memory/patterns` | List recurring consolidated patterns |
| `POST` | `/api/v1/memory/{id}/revalidate` | Empirically revalidate stale memory to `CURRENT` |
| `POST` | `/api/v1/memory/{id}/invalidate` | Retire memory preserving audit trail |
| `POST` | `/api/v1/memory/{id}/supersede` | Apply user correction and create v+1 |
| `POST` | `/api/v1/memory/replay` | Deterministic simulation without side-effects |
| `POST` | `/api/v1/memory/snapshot` | Point-in-time immutable state snapshot |

---

## 6. Verification & Test Coverage

- **Automated Backend Pytest Suite**: `backend/tests/test_cognitive_memory.py` (12/12 passing in 0.25s)
- **Frontend Node.js Suite**: `frontend/tests/cognitive_memory.test.js` (6/6 passing)
- **Deterministic E2E Harness**: `scripts/verify_cognitive_memory_e2e.py` (8/8 scenarios verified)
