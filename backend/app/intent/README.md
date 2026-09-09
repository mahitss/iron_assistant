# Kairo Unified Command, Intent, Goal & Motivation Engine (Task 35 & Task 48)

The **Unified Intent & Motivation Engine** (`backend/app/intent/`) safely converts human natural language input into verifiable, structured, and bounded representations of user goals, objectives, constraints, preferences, urgency, scope, and assumptions.

---

## 1. Core Principle & Architectural Invariant

> **Never silently transform an uncertain inference into user intent.**

The system preserves absolute distinction between:
- **WHAT THE USER SAID** (`raw_input`)
- **WHAT THE USER EXPLICITLY REQUESTED** (`explicit_action`)
- **WHAT KAIRO INFERRED** (`inferred_intent`)
- **WHAT KAIRO ASSUMED** (`assumptions` with transparency & impact scores)
- **WHAT KAIRO KNOWS** (`explicitly grounded entities & context`)
- **WHAT KAIRO DOES NOT KNOW** (`ambiguity candidates & missing parameters`)

### Pipeline

```
INPUT
  ↓
PARSE & TYPO NORMALIZATION
  ↓
UNDERSTAND & MULTI-INTENT SPLIT
  ↓
EXTRACT (Entities, Temporal, Constraints, Objectives, Scope, Urgency, Motivations)
  ↓
SEPARATE FACT FROM INFERENCE
  ↓
CHECK AMBIGUITY (Consequence-Aware Gating)
  ↓
CHECK AUTHORITY & ISOLATION
  ↓
RESOLVE IF SAFE (Else create ClarificationRequest)
  ↓
CREATE GOAL (Desired outcome != Execution task)
  ↓
PLAN (Graph DAG)
```

---

## 2. Core Concepts

### Goal vs Task Separation
- **Goal**: The desired end-state outcome (e.g., "Deploy v1.2 with zero downtime").
- **Task**: The specific tactical execution steps planned to reach that state (e.g., "Run unit tests", "Push container image").

### Constraint Discovery & Hierarchy
Constraints are ranked and resolved strictly:
1. **Safety**
2. **Policy & Compliance**
3. **Authorization**
4. **Explicit user constraints** (Hard constraints)
5. **Project constraints**
6. **Preferences** (Soft constraints, overridable)
7. **Defaults** (Reversible low-risk defaults)

Conflicts are detected immediately. Explicit instructions always override memory preferences.

### Consequence-Aware Ambiguity & Clarification
- Destructive operations (`DELETE`, `CANCEL`, `DROP`) or high-impact actions strictly block execution upon any entity/target ambiguity.
- Safe defaults are only allowed for reversible, low-impact actions.
- Clarifications ask the minimal targeted question without defensive interrogation.

### Safe Functional Motivation Engine
Motivations categorize safe, functional utility drivers without psychological profiling:
- `EFFICIENCY`, `LEARNING`, `COMPLETION`, `QUALITY`, `SAFETY`, `CONVENIENCE`, `TIME_SAVING`, `EXPLORATION`, `CREATION`.
- Surface explicit tradeoffs when goals compete (cost vs. speed, quality vs. latency).

### Non-Defensive User Correction Loop
When the user states *"That's not what I meant"*:
1. Record error signal and recalibrate confidence estimator.
2. Formulate revised intent without arguing or being defensive.
3. Update active dialogue session and propagate goal changes.

---

## 3. REST API Endpoints

### Intent Engine Endpoints (`/api/v1/intent`)
- `POST /api/v1/intent/parse`: Parses, understands, extracts goals/constraints, evaluates ambiguity, and registers intent.
- `GET /api/v1/intent/intents`: Lists all understood intents.
- `GET /api/v1/intent/intents/{intent_id}`: Retrieves single intent record with objectives and assumptions.
- `POST /api/v1/intent/goals`: Creates explicit goal record separate from execution tasks.
- `GET /api/v1/intent/goals`: Queries goals by status and owner.
- `POST /api/v1/intent/clarify`: Submits answer to a pending clarification request.
- `POST /api/v1/intent/correct`: Processes user correction ("That's not what I meant") non-defensively.
- `POST /api/v1/intent/revoke`: Revokes an active intent and propagates cancellation to child goals and plans.
- `GET /api/v1/intent/graph/{intent_id}`: Retrieves DAG graph representation (`Intent -> Goal -> Objectives -> Constraints -> Tasks -> Outcomes`).
- `POST /api/v1/intent/tradeoffs`: Evaluates tradeoffs between conflicting goals.
- `GET /api/v1/intent/health`: Returns health metrics, calibration ratio, active goals, and pending clarifications.

### Command Endpoints (`/api/v1/commands`)
- `POST /api/v1/commands`: Submits command for immediate deterministic/model execution routing.
- `POST /api/v1/commands/resolve`: Read-only resolve without executing.
- `GET /api/v1/commands/{command_id}`: Retrieves command details.
