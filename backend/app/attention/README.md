# Kairo Autonomous Attention & Cognitive Resource Allocation Engine (Task 70)

The **Kairo Autonomous Attention & Cognitive Resource Allocation Engine** determines what deserves attention, what can wait, what can be delegated, what can be monitored, and what should be ignored. It prevents cognitive overload while ensuring critical safety events preempt ongoing background tasks.

## Core Architectural Pillars

### 1. Decoupled Dimensions (`Attention ≠ Priority ≠ Action`)
Kairo distinguishes:
- **Importance**: Consequence to missions, goals, system integrity, and security (decoupled from recency).
- **Urgency**: Time-to-impact, rate of change, deadline proximity, and escalation likelihood.
- **Risk**: Probability and blast radius of negative outcomes.
- **Novelty & Change Magnitude**: Statistical deviation from historical and environment baselines.
- **Goal Alignment**: Relevance to active strategic objectives.

### 2. 12-State Explicit Lifecycle
```
UNSEEN -> OBSERVED -> QUEUED -> ATTENDING -> RESOLVED
              |          |           |
              v          v           v
          MONITORING  DEFERRED     PAUSED
              |          |           |
              v          v           v
          DISMISSED   DELEGATED   BLOCKED
```
- Arbitrary transitions (such as `DISMISSED` -> `ATTENDING`) are rejected. Reopening terminal states requires an explicit new event signal.

### 3. Preemption & State Preservation
- When a critical production outage appears during a low-priority task, the interruption engine:
  1. Checks non-interruptible critical commit constraints.
  2. Creates an immutable context snapshot of the active task (Task 69).
  3. Pauses the active task and pushes it onto the LIFO preemption stack.
  4. Allocates active attention to the incoming incident.
  5. Upon resolution, pops and cleanly resumes the interrupted task with full provenance and context intact.

### 4. Cognitive Resource Model & Value Analysis
- **Resource Budgets**: Tracks reasoning capacity %, active tool calls, agent slots, compute budget, and context token budgets.
- **Expected Value of Attention (EVOA)**: `EVOA = expected_benefit - attention_cost`.
- **Value of Information (VOI)**: `VOI = (uncertainty * decision_consequence) - investigation_cost`. Ensures expensive investigations are only prioritized when they will meaningfully impact downstream decisions.

### 5. Fairness Aging & Hysteresis Dampening
- **Anti-Starvation Aging**: Deferred low-priority tasks gradually gain scheduling priority over time, preventing permanent neglect without compromising critical safety priorities.
- **Anti-Thrashing Hysteresis**: Score fluctuations around threshold boundaries (e.g. 79 <-> 81) are dampened using dual boundary margins to prevent alert oscillation.
