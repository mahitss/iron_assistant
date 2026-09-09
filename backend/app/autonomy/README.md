# Kairo Autonomous Execution, Long-Horizon Agency, Persistent Task Control, and Goal Completion Engine (Task 45)

## Overview

The **Kairo Autonomous Execution & Long-Horizon Agency Engine** empowers Kairo to formulate, pursue, verify, and complete long-horizon goals across multiple iterative cycles, while preserving:
- Goal boundary & strict anti-drift guarantees
- Explicit scope locks and tenant isolation (user/project)
- Cryptographic checkpoints and crash recovery without blind resumption
- Independent empirical verification (no false completion)
- Multi-factor resource quotas (models, tools, cost, compute) and deadline propagation
- Safe human interruption (pause, resume, cancel, emergency stop cascade)
- Fail-closed governance and anti-self-modification protections

---

## Core Principles

```
GOAL
 ↓
UNDERSTAND (Session context & long-horizon memory)
 ↓
PLAN (Cognitive DAG with dependency ordering)
 ↓
VALIDATE (Preconditions, policy, authorization, approval)
 ↓
EXECUTE (ToolExecutor with idempotency & resource locks)
 ↓
OBSERVE (Empirical outputs & world-state telemetry)
 ↓
VERIFY (Independent verification criteria)
 ↓
UPDATE STATE (Progress tracking & journal appending)
 ↓
CHECKPOINT (Atomic SHA-256 hashed state snapshot)
 ↓
CONTINUE
      │
      └── if reality changed → REPLAN (Structural diff & versioning)
```

The autonomous engine owns orchestration. It does NOT own:
- Policy
- Authorization
- Security
- Tool implementation
- Verification rules
- Governance

---

## Architecture

The engine is modularized within `backend/app/autonomy/`:

| Module | Responsibility |
|---|---|
| `engine.py` | Master `AutonomousExecutionEngine` coordinator orchestrating goals, runs, steps, and completion records |
| `controller.py` | Canonical 12-stage `RunController` executing preconditions, safety gating, execution, verification, and checkpoints |
| `execution.py` | `AutonomousExecutionLoop`, `ExecutionResourceManager` (reader-writer locks), idempotency store, and unknown outcome recovery |
| `lifecycle.py` | `RunLifecycleManager` governing transitions across 14 states and durable wait conditions |
| `goals.py` | `GoalManager`, persistent `AutonomousGoal`, and anti-drift validation |
| `sessions.py` | `AutonomousSession`, `AutonomousScope` enforcement, cross-tenant isolation, and context compaction |
| `checkpoints.py` | `CheckpointManager`, `AutonomousCheckpoint` with SHA-256 integrity hash, and corruption fallback |
| `recovery.py` | `RecoveryEngine` auditing state freshness, plan validity, and authorization before resumption |
| `replanning.py` | `ReplanningManager`, `PlanDiff` calculation, and approval invalidation |
| `scheduler.py` | `AutonomousScheduler`, DAG step readiness resolution, and event correlation deduplication |
| `policies.py` | `AutonomyPolicyEngine`, fail-closed defaults, and domain-specific workflow validations |
| `safety.py` | `AutonomySafetyGuard`, autonomy levels, and anti-self-modification defenses |
| `budgets.py` | `AutonomousBudget` multi-quota tracking and bounded child budget propagation |
| `deadlines.py` | `DeadlineTracker` global SLA enforcement and sub-task timeout calculation |
| `leases.py` | `ExecutionLeaseManager` preventing split-brain execution across multiple workers |
| `heartbeat.py` | `HeartbeatTracker` recording worker liveness |
| `watchdog.py` | `AutonomyWatchdog` diagnosing stuck, expired, unresponsive, or orphaned runs |
| `progress.py` | `ProgressTracker` verifying empirical completion and detecting no-progress loops |
| `escalation.py` | `EscalationManager` handling targeted human-in-the-loop interventions without needless queries |
| `interruption.py` | `InterruptionHandler` managing pause, cancel, and emergency stop cascades |
| `persistence.py` | `AutonomyPersistenceManager` integrating SQLAlchemy models and append-only journals |
| `models.py` | SQLAlchemy database models (`AutonomousGoalModel`, `AutonomousRunModel`, `AutonomousCheckpointModel`, etc.) |
| `schemas.py` | Pydantic request and response schemas |
| `router.py` | FastAPI REST API endpoints mounted under `/api/v1/autonomy` |

---

## 14 Authoritative Run States

1. `CREATED`: Run instantiated, waiting for initialization.
2. `QUEUED`: Enqueued in scheduler waiting for worker lease.
3. `INITIALIZING`: Pre-run validation, session setup, initial checkpointing.
4. `RUNNING`: Actively selecting and executing ready DAG steps.
5. `WAITING`: Paused on external condition (approval, user input, rate limit, resource).
6. `PAUSED`: User-requested pause between safe operation boundaries.
7. `REPLANNING`: Plan invalidated by drift, failure, or environment shift.
8. `BLOCKED`: Dependency, security check, or quota blocked.
9. `RECOVERING`: Post-crash revalidation and checkpoint restoration.
10. `COMPLETED`: Verified completion certificate generated with all success criteria satisfied.
11. `FAILED`: Run permanently stopped due to non-recoverable error.
12. `CANCELLED`: User safely terminated run, preserving partial work and evidence.
13. `EXPIRED`: Global SLA deadline exceeded.
14. `SUPERSEDED`: Replaced by a newer plan version or re-scoped goal.

---

## Autonomy Levels

| Level | Behavior |
|---|---|
| `ASSISTED` | User confirms all significant consequential actions (WRITE, DEPLOY, DELETE). |
| `SUPERVISED` | System executes approved plan, but pauses at configured checkpoints for high-impact actions. |
| `CONDITIONAL` | Pre-authorized actions execute within explicit conditions; PRIVILEGED/DELETE require verification. |
| `AUTONOMOUS` | Executes autonomously within explicit policy and contract boundaries; PRIVILEGED still requires security approval. |

---

## Security & Invariant Checklist (Spec 196)

- **Can autonomy bypass Policy?** NO. All consequential operations pass `AutonomyPolicyEngine`. Fail-closed if unavailable.
- **Can autonomy bypass Authorization?** NO. Revalidation on resume and step execution checks authorization.
- **Can autonomy bypass Approval?** NO. Required human approvals cannot be skipped or assumed.
- **Can autonomy execute tools directly?** NO. All tool invocations flow through `ToolExecutor`.
- **Can autonomy expand scope?** NO. Scope expansions require explicit user intent and re-approval.
- **Can a model change the goal?** NO. Root goals are immutable in persistent storage; `GoalDriftError` halts unauthorized shifts.
- **Can a child task gain more privilege?** NO. Children inherit strictly bounded sub-scopes and sub-budgets.
- **Can a failed side effect be blindly retried?** NO. Non-idempotent side effects require state inspection before retry (`SideEffectRetryViolationError`).
- **Can a network timeout be interpreted as failure?** NO. Marked as `UNKNOWN` until verified.
- **Can a network timeout be interpreted as success?** NO. Must be independently verified.
- **Can stale state drive execution?** NO. State freshness revalidation blocks stale plan execution.
- **Can an old approval authorize a new plan?** NO. Material plan changes invalidate prior approvals.
- **Can a crashed worker resume without validation?** NO. `RecoveryEngine` revalidates state, plan, and authorization.
- **Can two workers execute the same side effect?** NO. Distributed execution leases (`SplitBrainConflictError`) and resource locks prevent concurrent writes.
- **Can a plan loop forever?** NO. `ProgressTracker` halts stagnant or oscillating cycles (`NoProgressLoopError`).
- **Can budget be exceeded?** NO. Pre-check halts execution immediately (`BudgetExhaustedError`).
- **Can deadline be ignored?** NO. SLA expiration transitions run to `EXPIRED` (`DeadlineExhaustedError`).
- **Can autonomy claim completion without evidence?** NO. `CompletionRecord` requires verified proof for all success criteria (`FalseCompletionError`).
- **Can autonomy modify its own security or governance?** NO. `AutonomySafetyGuard` protects system paths and blocks self-privilege directives.
