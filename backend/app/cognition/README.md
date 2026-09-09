# Kairo Cognitive Planning, Reasoning, and Adaptive Decision Engine (Task 41)

The **Cognitive Planning & Reasoning Engine** (`app.cognition`) transforms high-level user objectives into reliable, structured, observable, and verifiable execution DAGs.

---

## 1. Core Architectural Separation

```text
User Request
     ↓
     LLM                 (PROPOSES Candidate Steps)
     ↓
Cognitive Planner        (STRUCTURES into Validated DAG, Detects Cycles & Conflicts)
     ↓
Policy Engine            (AUTHORIZES Actions, Risk Tiers, and Approvals)
     ↓
Autonomous Task Engine   (EXECUTES via ToolExecutor — Planner never executes tools directly)
     ↓
Cognitive Verifier       (CHECKS Postconditions, Diffs, Health Probes, and Invariants)
     ↓
World Model / State      (UPDATES Current Authoritative State)
     ↓
Adaptive Replanner       (RE-PLANS when Reality Diverges from Assumptions)
```

### Invariants:
1. **Separation of Planning and Execution**: The planner does **NOT** directly execute tools or perform side-effects. Execution is delegated to the Task Engine and ToolExecutor.
2. **Anti Self-Attestation**: Model claims like `"done"` or `"I fixed it"` are **never** accepted as verification. Empirical postconditions, diffs, or health checks are required.
3. **Confidence is NOT Authority**: High model confidence cannot bypass policy, scope locks, or approvals.
4. **Monotonic Versioning**: Every major re-plan generates a new plan version ($v1 \to v2$); old plans become `SUPERSEDED` and history is preserved.
5. **No Scope Creep**: Re-planning preserves original goals and hard constraints without silent privilege escalation.
6. **Parallel Safety**: Independent read-only steps may execute in parallel; steps modifying the same resource or sharing mutable state are strictly serialized.

---

## 2. Seven Reasoning Modes

| Mode | Description | Primary Use Case |
| :--- | :--- | :--- |
| **DIRECT** | Minimal overhead single-step execution | Simple status inspections or queries |
| **DECOMPOSITION** | Multi-step DAG planning with dependency resolution | Complex operational or development objectives |
| **COMPARISON** | Evaluates tradeoffs among alternative approaches | Architectural decisions (Fast Path vs Low-Risk Hardened Path) |
| **DIAGNOSTIC** | Observe $\to$ Hypothesize $\to$ Lowest-Risk Test | Bug fixes, failing CI runs, service outages |
| **RESEARCH** | Evidence retrieval $\to$ Synthesis with citations | Fact-finding, documentation search, market analysis |
| **ITERATIVE** | Step-by-step adaptive loop: Act $\to$ Observe $\to$ Update | Dynamic environments with uncertain intermediates |
| **LONG_HORIZON** | Extended tasks with checkpointing & budget monitoring | Database migrations, large-scale codebase refactoring |

---

## 3. Database Schema

- `cognitive_goals`: Persistent goals with priority, deadline, constraints, and scope.
- `cognitive_plans`: Structured plan instances with monotonic versioning and status.
- `cognitive_steps`: Atomic plan steps with dependencies, expected output, and verification specs.
- `plan_assumptions`: Explicit tracked assumptions validated before step execution.
- `plan_alternatives`: Alternative strategies with deterministic composite scores.
- `plan_traces`: Append-only audit and observability trace of planning decisions.
