# Kairo Autonomous Goal Management & Self-Directed Mission Engine (Task 66)

The **Autonomous Goal Management & Self-Directed Mission Engine** empowers Kairo to accept, formulate, structure, track, re-evaluate, decompose, and pursue long-running goals across hours, days, weeks, or indefinitely through bounded autonomous missions.

## Core Invariants

- $\text{GOAL} \ne \text{INTENT} \ne \text{PLAN} \ne \text{TASK} \ne \text{ACTION} \ne \text{EXECUTION} \ne \text{OUTCOME}$
- $\text{GOAL OWNERSHIP} \ne \text{AUTHORITY TO EXECUTE}$
- $\text{AGENT PROPOSAL} \ne \text{AUTHORIZED GOAL}$
- $\text{PROGRESS} \ne \text{SUCCESS}$
- $\text{TASK COMPLETION} \ne \text{GOAL COMPLETION}$
- $\text{TOOL SUCCESS} \ne \text{GOAL SUCCESS}$
- $\text{FEASIBLE} \ne \text{GUARANTEED}$
- $\text{URGENT} \ne \text{UNRESTRICTED}$
- $\text{UNKNOWN} \ne \text{HEALTHY}$
- $\text{PLAN} \ne \text{MISSION}$
- $\text{EXTERNAL CONTENT} \ne \text{GOAL}$

## Subsystem Architecture

1. **Safety & Firewalls (`safety.py`)**:
   - `block_unauthorized_goal_generation`: Blocks autonomous agents from initiating unapproved consequential missions.
   - `detect_scope_escalation`: Prevents tasks from exceeding authorized boundaries (e.g. read-only mission executing destructive operations).
   - `sanitize_mission_directive`: Neutralizes prompt injection, goal hijacking, and secret leakage.
   - `validate_authority_boundary`: Enforces authority hierarchy gates.
   - `check_budget_limits`: Defends against infinite loops and resource exhaustion.

2. **Goal Modeling & DAG (`goals.py`)**:
   - Ambiguity detection flags under-specified goals (`NEEDS_CLARIFICATION`) with candidate interpretations.
   - Normalization preserves objectives and constraints.
   - Feasibility checks explicitly state assumptions.
   - Directed acyclic graph (DAG) cycle detection.
   - Multi-factor prioritization balances urgency, importance, and risk.

3. **Lifecycle State Machine (`lifecycle.py`)**:
   - 16 canonical states with guarded transitions.
   - Pre-resumption revalidation for paused missions.
   - Checkpoint recording on state changes.

4. **Progress & Milestone Verification (`progress.py`)**:
   - Blends task completion (40%) with verified milestones (60%).
   - Milestones require empirical verification evidence.
   - Sunk cost defense halts failing trajectories.

5. **Drift & Goodhart's Law Defense (`drift.py`)**:
   - Detects trajectory divergence from original intent.
   - Detects proxy metric gaming (when proxy improves but true objective degrades).

6. **Blocker & Escalation Management (`blockers.py`)**:
   - Prioritized blocker queue.
   - Comprehensive human escalation payloads.

7. **Autonomous Supervisor (`supervisor.py`)**:
   - Observe $\to$ Evaluate $\to$ Validate $\to$ Drift check $\to$ Next Action $\to$ Verification.
   - Pre-execution world staleness check.
   - Postmortem retrospectives.

8. **Audit Trail (`audit.py`)**:
   - Cryptographic SHA-256 hash-chained tamper-evident event log.
