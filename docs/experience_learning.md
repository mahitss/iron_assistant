# Kairo Long-Term Experience Learning, Feedback Loop, and Controlled Improvement

## 1. Overview and Core Philosophy

Kairo learns from explicit user corrections, successful tasks, failed tasks, rejected suggestions, approved actions, denied actions, evaluation results, project evolution, and repeated user preferences.

Crucially, this learning is:
- **EXPLICIT**: Originates from identifiable, authenticated sources.
- **BOUNDED**: Subject to strict context limits (`KAIRO_MAX_EXPERIENCE_CONTEXT = 10`).
- **TRACEABLE**: Full provenance linking events, tasks, decisions, and outcomes.
- **REVERSIBLE**: Records can be superseded, decayed to `STALE`, or deleted by the user.
- **SECURE**: Operates under strict immutability invariants.

Kairo **NEVER** autonomously rewrites its own production code, system prompts, routing weights, or security permissions based on experience.

---

## 2. Distinction: Memory vs. Experience vs. Preference vs. Knowledge vs. Evaluation

| Subsystem | Semantic Role | Backing Storage | Example |
|---|---|---|---|
| **Memory** | Explicit facts Kairo is instructed to remember | `memories` table | "User's timezone is America/New_York" |
| **Experience** | What happened during past execution | `experiences` table | "Kairo successfully ran pgvector migration for project X" |
| **Preference** | How user explicitly wishes Kairo to behave | `preferences` table | "Prefer Markdown tables for project reports" |
| **Knowledge Fabric** | Verified domain facts, code AST, documentation | Knowledge graph & vector index | "PostgreSQL 16 supports jsonb subscripting" |
| **Evaluation** | Controlled benchmarks measuring model/skill versions | Evaluation datasets & runner | Regression scenario `eval-scen-ci-fail-002` |

---

## 3. Experience Lifecycle State Machine

```
   [Event Occurs]
         │
         ▼
   ┌───────────┐
   │ CANDIDATE │ ◄──── Single inferred or unvalidated event
   └─────┬─────┘
         │ (Validation / Explicit Confirmation)
         ▼
   ┌───────────┐
   │ VALIDATED │
   └─────┬─────┘
         │ (Activation)
         ▼
   ┌───────────┐       (Project Evolution / Repo Change)
   │  ACTIVE   ├───────────────────────────────────────────────► ┌───────┐
   └─────┬─────┘                                                 │ STALE │
         │                                                       └───────┘
         ├───────────────► ┌────────────┐
         │ (New Scoped     │ SUPERSEDED │ (Preserves provenance)
         │  Correction)    └────────────┘
         │
         └───────────────► ┌─────────┐
           (User Deletes)  │ DELETED │ (Removed from retrieval)
                           └─────────┘
```

Only records in `ACTIVE` or `VALIDATED` states may influence normal context.

---

## 4. Security & Safety Invariance Verification (Section 90)

| Security Invariance Question | System Guarantee | Enforcement Mechanism |
|---|---|---|
| **Can the model create permanent memory without validation?** | **NO** | Model-inferred memories are created as `CANDIDATE` and require validation or user confirmation. |
| **Can external webpages create preferences?** | **NO** | Preferences require `USER_EXPLICIT` or verified `USER_FEEDBACK`. Web content triggers `PermissionError`. |
| **Can experience grant permissions?** | **NO** | Experience data is purely informational. `EventSecurityGuard` blocks non-trusted sources from emitting permission events. |
| **Can repeated approval remove future approval requirements?** | **NO** | Approval rules remain static in `ApprovalManager` and cannot be softened by high-frequency approvals. |
| **Can learning modify SecurityCenter?** | **NO** | Protected governance domains (`security_center`, `permissions`, `approvals`, `tool_allowlist`, etc.) raise `ExperienceSecurityViolation`. |
| **Can learning modify system prompts?** | **NO** | System prompts are immutable. Context Engine only injects bounded, labeled context (`USER PREFERENCE: ...`). |
| **Can learning modify tool allowlists?** | **NO** | Tool allowlists and execution policies are statically defined in code and configuration. |
| **Can User A see User B experience?** | **NO** | All queries enforce strict tenant filtering by `user_id`. Cross-user access returns `403 Forbidden` or `404 Not Found`. |
| **Can stale experience override current project knowledge?** | **NO** | Active project knowledge in the Knowledge Fabric takes precedence. Older experiences decay to `STALE` on repo changes. |
| **Can deleted experience remain retrievable?** | **NO** | Deleted experiences are marked `DELETED` and excluded from `ExperienceRetriever` and API listings. |
| **Can feedback leak private user content?** | **NO** | `sanitize_content` strips secrets and credential patterns before storage or event emission. |
| **Can evaluation datasets contain real secrets?** | **NO** | Evaluation scenarios use synthetic inputs and redacts sensitive credentials. |
| **Can Kairo autonomously modify its own production code?** | **NO** | Code changes strictly require the human engineering pipeline: Experience → Learning Candidate → Benchmark → Engineering Review → CI → Release. |

---

## 5. Improvement Pipeline

```
Real-World Experience / Failure
               │
               ▼
   Learning Candidate (PROPOSED)
               │
               ▼
   Evaluation Regression Benchmark
               │
               ▼
     Human / Engineering Review
               │
       ┌───────┴───────┐
       ▼               ▼
   [ACCEPTED]      [REJECTED]
       │
       ▼
   Engineering Code / Prompt Update
       │
       ▼
   CI / Regression Test Suite Passing
       │
       ▼
   Controlled Release
```
