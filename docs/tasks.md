# Kairo Autonomous Task Engine

The **Kairo Autonomous Task Engine** enables Kairo to accept high-level user objectives and execute them through a bounded, verifiable, security-first autonomous loop.

---

## 1. Goal and Execution Philosophy

Kairo can accept a complex objective, decompose it into a directed acyclic graph (DAG) of steps, validate dependencies, enforce security policies, execute steps (parallelizing read-only queries and serializing mutations), observe results, take checkpoints, replan if needed, verify outcomes against objective criteria, and report a grounded result summary.

```
OBJECTIVE
    ↓
UNDERSTAND & CONTEXT
    ↓
PLAN (Versioned DAG)
    ↓
SECURITY CHECK (SecurityCenter evaluates each step independently)
    ↓
EXECUTE (Parallel reads, serialized writes, idempotency keys)
    ↓
OBSERVE (Result, evidence, duration; no hidden reasoning)
    ↓
CHECKPOINT (Sanitized state snapshot for crash recovery)
    ↓
REPLAN IF NECESSARY (Retry transient failures, alternative steps, versioned replan)
    ↓
VERIFY (Deterministic test/file checks, bounded LLM synthesis)
    ↓
RESULT SUMMARY
```

---

## 2. Core Principle of Autonomy

> **Autonomy means:**
> Kairo can continue executing an authorized objective without requiring a new user message for every individual step.
>
> **Autonomy does NOT mean:**
> - Unlimited tool access or execution duration.
> - Bypassing approvals or SecurityCenter.
> - Self-modifying production code or security policies.
> - Autonomous destructive actions without explicit user approval.
> - Ignoring user cancellation or Emergency Stop.

Security boundaries remain absolute.

---

## 3. Tasks vs. Workflows

| Characteristic | Autonomous Task | Workflow |
| :--- | :--- | :--- |
| **Concept** | One objective-oriented execution | Reusable, scheduled automation |
| **Planning** | Dynamic DAG generated and adapted to the objective | Predefined, static or parameterized graph |
| **Lifecycle** | Runs until objective verified or stopped | Triggered periodically (e.g. cron) or by events |
| **Replanning** | Dynamically adapts and replans on unexpected failure | Fails or retries based on static config |
| **Example** | *"Investigate why CI is failing, find root cause, and report fix"* | *"Run CI check every day at 09:00"* |

A workflow may spawn tasks, but the dynamic execution of an autonomous objective remains strictly modeled as a **Task**.

---

## 4. Autonomy Levels

1. **`ASSISTED`**: User explicitly confirms each major plan step before execution.
2. **`SUPERVISED` (Default)**: Low-risk `READ` steps execute automatically; mutating `WRITE` steps require human approval.
3. **`AUTONOMOUS_READ`**: Strictly read-only research and analysis tasks execute automatically without prompting. Writes are prohibited.
4. **`AUTONOMOUS_BOUNDED`**: Authorized low/medium-risk workflows execute within strict budgets. Destructive actions still require explicit human approval.

Emergency Stop overrides all autonomy levels unconditionally.

---

## 5. Security & Authorization Invariants

- **Step-by-Step Authorization**: Every step independently passes authorization through `SecurityCenter`. A task is never granted blanket authorization upfront.
- **Immutable Original Objective**: The user's original objective is stored separately and can never be overwritten by model output, web documents, or prompt injection.
- **Anti-Goal Drift**: If a generated plan materially diverges from the initial objective (e.g. an investigative task attempting destructive actions), execution is immediately blocked.
- **Anti-Scope Creep**: When unrelated issues are discovered during execution, they are surfaced as informational findings rather than automatically acted upon.
- **Anti-Prompt Injection**: External content (repository READMEs, web text, OCR text) is treated as untrusted user data. It cannot issue instructions to cancel tasks, approve actions, or elevate permissions.
- **Write Serialization & Resource Locking**: Mutating steps acquire expiring resource locks (`task_locks`) on repositories, files, and devices, strictly preventing concurrent conflicting writes.

---

## 6. Verification Contracts

Tasks complete only when their objective is verified:
- **Test Execution**: Exit code must match expected value (e.g. 0).
- **File Operations**: Target file existence and schema validation.
- **Content Assertions**: Verifies key findings or evidence strings exist in output.
- **Subjective LLM Evaluator**: Strictly reserved for assessing research synthesis and summary quality; strictly prohibited from judging security, authorizations, file presence, or test exit codes.

---

## 7. Checkpoints & Crash Recovery

- After each completed step, a sanitized state snapshot is saved to `task_checkpoints`.
- Idempotency keys (`task_id:step_id:attempt`) prevent duplicate external mutations upon restart.
- Stale plans are invalidated if external environment (e.g. git commit hash) changed during downtime.

---

## 8. REST API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/tasks` | Create and initiate an autonomous task |
| `GET` | `/api/v1/tasks` | List tasks with status and project filters |
| `GET` | `/api/v1/tasks/{id}` | Retrieve task detail, step DAG, and progress |
| `POST` | `/api/v1/tasks/{id}/pause` | Pause active task |
| `POST` | `/api/v1/tasks/{id}/resume` | Resume paused task after re-validation |
| `POST` | `/api/v1/tasks/{id}/cancel` | Cooperatively cancel task execution |
| `POST` | `/api/v1/tasks/{id}/retry` | Safely retry a failed task |
| `POST` | `/api/v1/tasks/{id}/approve` | Approve or reject a step waiting for human authorization |
| `POST` | `/api/v1/tasks/{id}/respond` | Submit user clarification when in `WAITING_USER` state |
| `GET` | `/api/v1/tasks/{id}/activity` | Fetch milestone activity trail |
| `GET` | `/api/v1/tasks/{id}/plan` | Retrieve plan versions and DAG structure |
