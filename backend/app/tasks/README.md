# Kairo Autonomous Task Engine (Task 31)

The **Kairo Autonomous Task Engine** enables Kairo to accept high-level user objectives and execute them through a bounded, verifiable, security-first autonomous loop.

---

## 1. Core Principle of Autonomy

> **Autonomy means:**
> Kairo can continue executing an authorized objective without requiring a new user message for every individual step.
>
> **Autonomy does NOT mean:**
> - Unlimited tool access or duration.
> - Bypassing approvals or SecurityCenter.
> - Self-modifying production code or security policies.
> - Autonomous destructive actions without explicit user approval.
> - Ignoring user cancellation or Emergency Stop.

Security boundaries remain absolute.

---

## 2. Task vs. Workflow Distinction (Spec 2)

| Concept | Purpose | Example |
| :--- | :--- | :--- |
| **TASK** | One objective-oriented execution DAG with dynamic planning, replanning, and verification. | *"Investigate why the Kairo deployment is failing, identify root cause, research a fix, and report changes."* |
| **WORKFLOW** | Reusable, scheduled, or trigger-based automation. | *"Check CI health every morning at 09:00."* |

A workflow may create tasks, but dynamic autonomous DAG plans remain strictly modeled as **Tasks**.

---

## 3. Execution Lifecycle Loop

```
OBJECTIVE
    ↓
UNDERSTAND & CONTEXT (Knowledge Fabric, project files, memory)
    ↓
PLAN (Decompose into versioned DAG TaskPlan)
    ↓
SECURITY CHECK (SecurityCenter evaluates each step independently)
    ↓
EXECUTE (Parallel reads up to limit, serialized writes)
    ↓
OBSERVE (Collect status, output, evidence, artifacts)
    ↓
CHECKPOINT (Persist sanitized state snapshot for crash resumption)
    ↓
REPLAN IF NECESSARY (Transient retries, alternative steps, versioned replan)
    ↓
VERIFY (Deterministic checks: test exit codes, files, schemas)
    ↓
RESULT SUMMARY
```

---

## 4. Invariants & Security Boundaries

1. **Step-by-Step Authorization**: Tasks are never authorized globally. Every single step independently passes authorization through `SecurityCenter`.
2. **Immutable Original Objective**: The user's original objective is stored separately and cannot be mutated by model output, web documents, or prompt injection.
3. **Anti-Goal Drift**: Generated plans that materially diverge from the initial objective (e.g. an investigation task attempting to delete files) are instantly `BLOCKED`.
4. **Anti-Scope Creep**: Discovered unrelated findings are surfaced as notes; the agent is barred from autonomously taking on out-of-scope work.
5. **Anti-Oscillation & Loop Detection**: Tracks plan hashes (`plan_hash`) to detect oscillating plans ($A \rightarrow B \rightarrow A$) and repetitive tool failures, safely halting with `LOOP_DETECTED`.
6. **Destructive Actions Safeguard**: Destructive actions (`delete`, `drop`, `purge`, `reset --hard`) **always** require explicit human approval, regardless of autonomy mode.
7. **Resource Locking**: Expiring resource locks (`task_locks`) prevent conflicting concurrent modifications to repositories, files, and devices.
8. **Crash Resumption**: Tasks resume from latest checkpoints without replaying completed writes, using deterministic idempotency keys (`task_id:step_id:attempt`).
