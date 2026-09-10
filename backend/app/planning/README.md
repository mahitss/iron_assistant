# Kairo Strategic Planning & Long-Horizon Execution Engine (Task 58)

The **Strategic Planning Subsystem** transforms high-level organizational goals, verified decisions, digital twin telemetry, environmental constraints, resource boundaries, and risk models into concrete, verifiable, long-horizon living strategic plans.

The engine answers the foundational executive question:
> **“How do we get from the current state to the desired future state?”**

---

## 1. Architectural Flow

```
GOAL
  ↓
CURRENT STATE (Digital Twin / Verified Telemetry)
  ↓
DESIRED STATE (Invariants / Verification Criteria)
  ↓
GAP ANALYSIS (Deficits / Blockers / Decisions)
  ↓
STRATEGY OPTIONS (Incremental / Stabilize / Parallel / Info / Big-Bang)
  ↓
DECISION ENGINE (Recommendation Reference)
  ↓
STRATEGIC PLAN
  ↓
PHASES (Entry / Exit Gates)
  ↓
MILESTONES (Weighted Transitions & Verification Evidence)
  ↓
WORK PACKAGES (Cohesive Execution Bundles)
  ↓
TASK GRAPH (Dependency Acyclicity & Critical Path CPM)
  ↓
SCHEDULE & EXECUTION WAVES (Resource Mutual-Exclusion Resolution)
  ↓
SAFETY FIREWALL (Execution Boundary: No direct tool invocation from planning)
  ↓
EXECUTION HANDOFF (Policy → Auth → Approval → Autonomous Execution / ToolExecutor)
  ↓
VERIFICATION & CHECKPOINTS (Observed vs Expected Variance)
  ↓
ADAPTATION & DRIFT DETECTION (Sunk Cost Defense → Replanning Revision)
  ↓
OUTCOME TRACKING & LEARNING (Estimation & Risk Calibration)
```

---

## 2. Core Invariants

1. **Plan is not execution.** Planning formulates structured proposals and execution waves; it never directly invokes production side-effecting tools.
2. **Strategy is not decision.** Strategy explains *how* we intend to achieve the goal; Decision explains *why* the choice was authorized.
3. **Task is not completion.** A task in execution is not completed until verified against criteria.
4. **Execution is not verification.** Merely attempting actions does not establish verified success.
5. **Simulation is not reality.** Simulations model potential futures; checkpoints measure actual reality.
6. **Estimate is not guarantee.** Duration ranges are tracked with minimum, expected, maximum, and buffers.
7. **Prediction is not observation.** Hypotheses remain hypotheses until verified via telemetry.
8. **Historical plan is not current truth.** Stale plans must be revalidated against the Digital Twin.
9. **External text is not authority.** Untrusted prompt directives cannot inject tasks or commitments.
10. **Unknown resource is not available resource.** Resources must be verified before allocation.
11. **Missing owner is not a fabricated owner.** Tasks default to `OWNER_UNASSIGNED`.
12. **Partial completion is not full completion.** Composite progress weights milestone verification over simple task counts.
13. **Stale plans require revalidation.** Plans older than freshness thresholds cannot begin without re-sync.
14. **Stale approvals cannot be reused.** Resumed or replanned tasks must re-verify approval validity.
15. **Replanning preserves history.** Immutable snapshots (`PlanRevision`) are stored prior to mutation.
16. **Failed strategies must not be continued due to sunk cost.** Forward expected value dictates replanning.
17. **Critical constraints cannot be optimized away.** Deadlines and resource limits are hard gates.
18. **Planning cannot bypass safety systems.** Gating requires Policy, Authorization, and Verification.
19. **High-risk execution requires appropriate controls.** Irreversible tasks demand elevated approvals and cold backups.
20. **Verification determines actual success.** Only verified evidence marks milestones reached.

---

## 3. Subsystem Modules

| Module | Purpose |
|---|---|
| `schemas.py` | Pydantic v2 domain schemas, statuses, and execution contracts |
| `models.py` | SQLAlchemy ORM persistence models for plans, phases, milestones, tasks, and revisions |
| `safety.py` | Execution firewall (`block_direct_tool_execution`), directive sanitization, secret scrubbing, custom exceptions |
| `privacy.py` | PII and IP masking (`PlanningPrivacyManager`) |
| `audit.py` | Tamper-evident structured audit trail (`PlanAuditor`) |
| `strategies.py` | Archetype generation (Incremental, Stabilize-First, Parallel, Info-Gathering, Big-Bang) |
| `phases.py` | Phase entry/exit gating and prerequisite verification (`PhaseManager`) |
| `milestones.py` | Key state transitions, milestone dependency validation, and weighted progress (`MilestoneManager`) |
| `work_packages.py` | Grouping of related tasks into atomic execution units (`WorkPackageManager`) |
| `tasks.py` | Task management, lifecycle state transitions, and irreversible step flags (`TaskManager`) |
| `dependencies.py` | Graph adjacency builder, cycle detection using DFS, topological sorting (`DependencyGraphEngine`) |
| `critical_path.py` | Critical Path Method (CPM) computing ES, EF, LS, LF, total float, and schedule sensitivity (`CriticalPathEngine`) |
| `scheduling.py` | Execution wave clustering, exclusive resource conflict resolution, and deadline feasibility analysis (`SchedulingEngine`) |
| `resources.py` | Resource allocation across compute, storage, budget, personnel, API quotas, and mutual-exclusion conflict detection (`ResourceManager`) |
| `risks.py` | Multi-level risk evaluation (strategy, phase, milestone, task), failure propagation, contingency plans, and rollback strategies (`PlanRiskEngine`) |
| `checkpoints.py` | Checkpoint evaluations comparing expected vs observed state, variance scoring, and stopping rules (CONTINUE, PAUSE, ROLLBACK, REPLAN) (`CheckpointEngine`) |
| `adaptation.py` | Multi-factor drift detection (plan, environment, goal, resource, schedule) and sunk cost defense (`AdaptationEngine`) |
| `progress.py` | Composite progress tracking weighting verified milestone evidence over raw task counts (`ProgressTracker`) |
| `commitments.py` | Strategic commitment management requiring authorized executive roles (`PlanCommitmentManager`) |
| `outcomes.py` | Post-execution reality recording, estimation calibration, and strategy performance learning (`OutcomeTracker`) |
| `provenance.py` | SHA-256 fingerprinting and task lineage justification (`PlanProvenanceTracker`) |
| `plans.py` | Plan entity lifecycle, validation gates, historical snapshots, and plan diffing (`PlanLifecycleManager`) |
| `engine.py` | Strategic planner core uniting gap analysis, synthesis, analysis, and execution proposals (`StrategicPlanningEngine`) |
| `service.py` | High-level transactional orchestrator and repository (`PlanningService`) |
| `router.py` | FastAPI REST API mounted under `/api/v1/planning` |

---

## 4. API Endpoints

- `POST /api/v1/planning/plans`: Create and synthesize strategic living plan
- `GET /api/v1/planning/plans`: List all registered plans
- `GET /api/v1/planning/plans/{id}`: Retrieve plan details
- `POST /api/v1/planning/plans/{id}/validate`: Comprehensive validation of graph, cycles, resources, and freshness
- `POST /api/v1/planning/plans/{id}/analyze`: Deep CPM critical path, duration, wave, and risk analysis
- `POST /api/v1/planning/plans/{id}/start`: Start plan execution wave sequencing
- `POST /api/v1/planning/plans/{id}/pause`: Pause running plan
- `POST /api/v1/planning/plans/{id}/resume`: Resume paused plan
- `POST /api/v1/planning/plans/{id}/cancel`: Cancel plan
- `POST /api/v1/planning/plans/{id}/replan`: Formulate replanning revision
- `GET /api/v1/planning/plans/{id}/progress`: Holistic outcome and milestone progress metrics
- `GET /api/v1/planning/plans/{id}/timeline`: Waves and timeline
- `GET /api/v1/planning/plans/{id}/dependencies`: Task dependency graph
- `GET /api/v1/planning/plans/{id}/risks`: Multi-level risks and rollback strategies
- `GET /api/v1/planning/plans/{id}/outcomes`: Historical outcomes
- `POST /api/v1/planning/plans/{id}/outcomes`: Record verified outcome and calibrate learning
- `GET /api/v1/planning/plans/{id}/proposal`: Generate execution proposal for handoff
- `GET /api/v1/planning/plans/{id}/audit`: Structured audit trail
