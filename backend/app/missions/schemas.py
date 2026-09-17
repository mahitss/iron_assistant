"""Pydantic v2 domain schemas and data contracts for Kairo Autonomous Goal Management & Mission Control (Task 66 & Task 100)."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


# =====================================================================
# Domain Enums
# =====================================================================


class GoalOrigin(str, enum.Enum):
    """Explicit provenance of goal initiation (Spec 4).

    Invariant: AGENT_PROPOSAL != AUTHORIZED_GOAL.
    """

    USER = "USER"
    AUTHORIZED_SYSTEM = "AUTHORIZED_SYSTEM"
    APPROVED_WORKFLOW = "APPROVED_WORKFLOW"
    PLANNER = "PLANNER"
    INCIDENT_RESPONSE = "INCIDENT_RESPONSE"
    OPTIMIZATION = "OPTIMIZATION"
    SCHEDULED_TASK = "SCHEDULED_TASK"
    EXTERNAL_EVENT = "EXTERNAL_EVENT"
    AGENT_PROPOSAL = "AGENT_PROPOSAL"


class GoalAuthorityScope(str, enum.Enum):
    """Execution authority boundary for a goal or mission (Spec 6).

    Invariant: CAPABILITY != AUTHORIZATION.
    """

    READ_ONLY = "READ_ONLY"
    ANALYZE = "ANALYZE"
    RECOMMEND = "RECOMMEND"
    EXECUTE_LOW_RISK = "EXECUTE_LOW_RISK"
    EXECUTE_APPROVED = "EXECUTE_APPROVED"
    HIGH_IMPACT_REQUIRES_APPROVAL = "HIGH_IMPACT_REQUIRES_APPROVAL"


class GoalValidationStatus(str, enum.Enum):
    """Outcome of pre-execution goal validation (Spec 7, 8)."""

    VALID = "VALID"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    REJECTED = "REJECTED"
    INSUFFICIENT_AUTHORITY = "INSUFFICIENT_AUTHORITY"


class GoalFeasibilityStatus(str, enum.Enum):
    """Feasibility classification under current assumptions (Spec 23, 24).

    Invariant: FEASIBLE != GUARANTEE.
    """

    FEASIBLE = "FEASIBLE"
    LIKELY_FEASIBLE = "LIKELY_FEASIBLE"
    UNCERTAIN = "UNCERTAIN"
    BLOCKED = "BLOCKED"
    INFEASIBLE = "INFEASIBLE"


class MissionStatus(str, enum.Enum):
    """Comprehensive lifecycle states of an autonomous mission (Task 66 & Task 100).

    Enforces 18 operational states plus legacy backward compatibility aliases.
    """

    DRAFT = "DRAFT"
    READY = "READY"
    ACTIVE = "ACTIVE"
    RUNNING = "RUNNING"  # Legacy alias for ACTIVE
    VALIDATING = "VALIDATING"  # Legacy validation phase
    PLANNING = "PLANNING"  # Legacy planning phase
    WAITING_FOR_RESOURCES = "WAITING_FOR_RESOURCES"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"  # Legacy alias for AWAITING_APPROVAL
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    AWAITING_USER = "AWAITING_USER"
    EXECUTING = "EXECUTING"
    PAUSED = "PAUSED"
    BLOCKED = "BLOCKED"
    DEGRADED = "DEGRADED"
    AT_RISK = "AT_RISK"
    REPLANNING = "REPLANNING"
    VERIFYING = "VERIFYING"
    STABILIZING = "STABILIZING"
    COMPLETED = "COMPLETED"
    PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"
    FAILED = "FAILED"
    ABANDONED = "ABANDONED"
    CANCELLED = "CANCELLED"
    SUPERSEDED = "SUPERSEDED"
    ESCALATED = "ESCALATED"
    EXPIRED = "EXPIRED"
    REGRESSED = "REGRESSED"
    EMERGENCY_STOPPED = "EMERGENCY_STOPPED"
    RECOVERING = "RECOVERING"
    UNKNOWN = "UNKNOWN"

    @property
    def is_active(self) -> bool:
        return self in (
            MissionStatus.ACTIVE,
            MissionStatus.RUNNING,
            MissionStatus.EXECUTING,
            MissionStatus.VERIFYING,
            MissionStatus.STABILIZING,
            MissionStatus.REPLANNING,
        )

    @property
    def is_terminal(self) -> bool:
        return self in (
            MissionStatus.COMPLETED,
            MissionStatus.PARTIALLY_COMPLETED,
            MissionStatus.FAILED,
            MissionStatus.CANCELLED,
            MissionStatus.ABANDONED,
            MissionStatus.SUPERSEDED,
        )


class MilestoneStatus(str, enum.Enum):
    """Lifecycle states of persistent mission milestones (Task 100)."""

    PENDING = "PENDING"
    READY = "READY"
    ACTIVE = "ACTIVE"
    RUNNING = "ACTIVE"
    BLOCKED = "BLOCKED"
    AT_RISK = "AT_RISK"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    REGRESSED = "REGRESSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"


class AssumptionStatus(str, enum.Enum):
    """Validation states of explicit mission assumptions (Task 100)."""

    VALID = "VALID"
    VALIDATED = "VALIDATED"
    AT_RISK = "AT_RISK"
    INVALID = "INVALID"
    INVALIDATED = "INVALIDATED"
    UNVERIFIED = "UNVERIFIED"
    UNKNOWN = "UNKNOWN"


class DependencyType(str, enum.Enum):
    """Taxonomy of mission dependencies."""

    INTERNAL = "INTERNAL"
    EXTERNAL = "EXTERNAL"
    HUMAN = "HUMAN"
    CAPABILITY = "CAPABILITY"
    APPROVAL = "APPROVAL"
    RESOURCE = "RESOURCE"


class DependencyStatus(str, enum.Enum):
    """Operational availability status of a dependency."""

    AVAILABLE = "AVAILABLE"
    BLOCKED = "BLOCKED"
    DEGRADED = "DEGRADED"
    UNKNOWN = "UNKNOWN"
    FAILED = "FAILED"


class AutonomyLevel(str, enum.Enum):
    """Bounded autonomy operating modes for a mission."""

    OBSERVE_ONLY = "OBSERVE_ONLY"
    ASSISTED = "ASSISTED"
    PROPOSE = "PROPOSE"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    BOUNDED_AUTONOMY = "BOUNDED_AUTONOMY"


class ReviewType(str, enum.Enum):
    """Cadence or trigger category of a mission review."""

    SCHEDULED = "SCHEDULED"
    PERIODIC = "PERIODIC"
    TRIGGERED = "TRIGGERED"
    METACOGNITIVE = "METACOGNITIVE"
    EMERGENCY = "EMERGENCY"


class MissionHealth(str, enum.Enum):
    """Real-time operational health of an active mission (Spec 97 & Task 100)."""

    ON_TRACK = "ON_TRACK"
    HEALTHY = "ON_TRACK"
    AT_RISK = "AT_RISK"
    DEGRADED = "DEGRADED"
    BLOCKED = "BLOCKED"
    DRIFTING = "DRIFTING"
    STALE = "STALE"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"
    UNKNOWN = "UNKNOWN"


class GoalHierarchyLevel(str, enum.Enum):
    """Structural decomposition tier (Spec 12)."""

    MISSION = "MISSION"
    OBJECTIVE = "OBJECTIVE"
    SUB_GOAL = "SUB_GOAL"
    TASK = "TASK"
    ACTION = "ACTION"


class ReversibilityClass(str, enum.Enum):
    """Reversibility classification of mission actions (Spec 62)."""

    REVERSIBLE = "REVERSIBLE"
    PARTIALLY_REVERSIBLE = "PARTIALLY_REVERSIBLE"
    IRREVERSIBLE = "IRREVERSIBLE"


class BlockerStatus(str, enum.Enum):
    """Lifecycle state of an identified mission blocker (Spec 69)."""

    DETECTED = "DETECTED"
    INVESTIGATING = "INVESTIGATING"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
    WAIVED = "WAIVED"


class BlockerSeverity(str, enum.Enum):
    """Impact severity of a blocker on mission progress (Spec 70)."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# =====================================================================
# Domain Data Models
# =====================================================================


class SuccessCriteria(BaseModel):
    """Empirical definition of when a mission or goal is achieved (Spec 10, 75).

    Invariant: PROGRESS != SUCCESS. TASK COMPLETION != GOAL COMPLETION.
    """

    model_config = ConfigDict(extra="ignore")

    criteria_id: str = Field(default_factory=lambda: f"crit_{uuid.uuid4().hex[:8]}")
    description: str
    criteria_type: str = "metric_threshold"  # metric_threshold, milestone_completion, verification_result, user_approval, test_pass, world_state
    target_metric: str | None = None
    target_value: float | str | bool | None = None
    comparison_operator: str = "eq"  # eq, lt, lte, gt, gte, between, in
    current_value: float | str | bool | None = None
    is_verified: bool = False
    verification_evidence: list[str] = Field(default_factory=list)
    verified_at: datetime | None = None


class FailureCondition(BaseModel):
    """Conditions under which continuation is unsafe or pointless (Spec 11)."""

    model_config = ConfigDict(extra="ignore")

    condition_id: str = Field(default_factory=lambda: f"fail_{uuid.uuid4().hex[:8]}")
    description: str
    metric: str | None = None
    threshold: float | str | None = None
    is_triggered: bool = False
    triggered_at: datetime | None = None
    action: str = "escalate"  # pause, escalate, fail, replan


class Goal(BaseModel):
    """Formal Goal Representation adhering to Spec 3 with 22 required fields.

    Invariant: GOAL != INTENT != PLAN != TASK.
    """

    model_config = ConfigDict(extra="ignore")

    goal_id: str = Field(default_factory=lambda: f"goal_{uuid.uuid4().hex[:10]}")
    title: str
    description: str
    origin: GoalOrigin = GoalOrigin.USER
    owner: str = "user"
    stakeholders: list[str] = Field(default_factory=list)
    priority: int = 5  # 1 (lowest) to 10 (highest)
    importance: float = 0.5  # 0.0 to 1.0
    urgency: float = 0.5  # 0.0 to 1.0
    scope: dict[str, Any] = Field(default_factory=dict)
    constraints: list[str] = Field(default_factory=list)
    deadline: datetime | None = None
    success_criteria: list[SuccessCriteria] = Field(default_factory=list)
    failure_conditions: list[FailureCondition] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    resources: list[str] = Field(default_factory=list)
    risk_level: float = 0.2  # 0.0 (safe) to 1.0 (extreme)
    authority_scope: GoalAuthorityScope = GoalAuthorityScope.EXECUTE_LOW_RISK
    status: MissionStatus = MissionStatus.DRAFT
    created_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)
    version: int = 1
    provenance: dict[str, Any] = Field(default_factory=dict)
    tenant_id: str = "default"


class MissionCheckpoint(BaseModel):
    """Structured checkpoint along long-running mission execution (Spec 26 & Task 100)."""

    model_config = ConfigDict(extra="ignore")

    checkpoint_id: str = Field(default_factory=lambda: f"chk_{uuid.uuid4().hex[:8]}")
    mission_id: str
    state: MissionStatus
    progress_pct: float = 0.0
    active_plan_id: str | None = None
    active_milestones: list[str] = Field(default_factory=list)
    assumptions_snapshot: list[dict[str, Any]] = Field(default_factory=list)
    world_state_ref: dict[str, Any] = Field(default_factory=dict)
    evidence: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    verification: dict[str, Any] = Field(default_factory=dict)
    context_summary: str = ""
    handoff_manifest: dict[str, Any] | None = None
    timestamp: datetime = Field(default_factory=_now_utc)
    version: int = 1


class Blocker(BaseModel):
    """Operational blocker halting mission progress (Spec 68-70)."""

    model_config = ConfigDict(extra="ignore")

    blocker_id: str = Field(default_factory=lambda: f"blk_{uuid.uuid4().hex[:8]}")
    mission_id: str
    blocker_type: str  # dependency, approval, resource, policy, external
    description: str
    severity: BlockerSeverity = BlockerSeverity.HIGH
    impact_score: float = 0.7  # 0.0 to 1.0
    detected_at: datetime = Field(default_factory=_now_utc)
    owner: str = "system"
    resolution: str | None = None
    status: BlockerStatus = BlockerStatus.DETECTED
    resolved_at: datetime | None = None


class GoalConflict(BaseModel):
    """Detected conflict between concurrent or hierarchical goals (Spec 15)."""

    model_config = ConfigDict(extra="ignore")

    conflict_id: str = Field(default_factory=lambda: f"cnf_{uuid.uuid4().hex[:8]}")
    conflicting_goal_ids: list[str]
    conflicting_objectives: list[str]
    tradeoffs: list[str]
    affected_resources: list[str] = Field(default_factory=list)
    decision_required: str
    detected_at: datetime = Field(default_factory=_now_utc)


class GoalDriftAlert(BaseModel):
    """Alert issued when active mission trajectory diverges from original intent (Spec 19, 20)."""

    model_config = ConfigDict(extra="ignore")

    alert_id: str = Field(default_factory=lambda: f"drf_{uuid.uuid4().hex[:8]}")
    mission_id: str
    goal_id: str
    original_objective: str
    current_trajectory: str
    divergence_score: float = 0.0  # 0.0 to 1.0
    is_objective_drift: bool = False  # Goodhart's law proxy metric manipulation
    trigger_reassessment: bool = True
    detected_at: datetime = Field(default_factory=_now_utc)


class MissionPostmortem(BaseModel):
    """Structured retrospective recorded upon mission closure (Spec 78)."""

    model_config = ConfigDict(extra="ignore")

    postmortem_id: str = Field(default_factory=lambda: f"pm_{uuid.uuid4().hex[:8]}")
    mission_id: str
    final_status: MissionStatus
    what_worked: list[str] = Field(default_factory=list)
    what_failed: list[str] = Field(default_factory=list)
    unexpected_events: list[str] = Field(default_factory=list)
    planning_errors: list[str] = Field(default_factory=list)
    resource_problems: list[str] = Field(default_factory=list)
    agent_performance: dict[str, Any] = Field(default_factory=dict)
    lessons: list[str] = Field(default_factory=list)
    duration_seconds: float = 0.0
    completed_at: datetime = Field(default_factory=_now_utc)


# =====================================================================
# Task 100 Enhanced Operational Entities
# =====================================================================


class MissionHealthDimensions(BaseModel):
    """Structured multi-dimensional operational health evaluation (Task 100)."""

    model_config = ConfigDict(extra="ignore")

    progress: float = 0.0  # 0.0 to 1.0
    risk: float = 0.0  # 0.0 (safe) to 1.0 (extreme)
    blockers: int = 0  # Count of open blockers
    uncertainty: float = 0.0  # 0.0 to 1.0
    dependency_health: float = 1.0  # 0.0 to 1.0
    resource_health: float = 1.0  # 0.0 to 1.0
    reliability: float = 1.0  # 0.0 to 1.0
    deadline_pressure: float = 0.0  # 0.0 to 1.0
    situation_pressure: float = 0.0  # 0.0 to 1.0
    capability_readiness: float = 1.0  # 0.0 to 1.0
    summary_explanation: str = "Initial baseline assessment"


class MissionObjective(BaseModel):
    """Hierarchical objective tier tracking high-level intent decomposition (Task 100)."""

    model_config = ConfigDict(extra="ignore")

    objective_id: str = Field(default_factory=lambda: f"obj_{uuid.uuid4().hex[:8]}")
    mission_id: str
    parent_objective_id: str | None = None
    title: str
    description: str = ""
    status: str = "PENDING"  # PENDING, ACTIVE, COMPLETED, BLOCKED
    ordering: int = 0
    success_criteria: list[SuccessCriteria] = Field(default_factory=list)
    progress_pct: float = 0.0
    created_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)


class MissionMilestone(BaseModel):
    """Persistent, evidence-backed operational milestone (Task 100)."""

    model_config = ConfigDict(extra="ignore")

    milestone_id: str = Field(default_factory=lambda: f"mls_{uuid.uuid4().hex[:8]}")
    mission_id: str
    objective_id: str | None = None
    title: str
    description: str = ""
    status: MilestoneStatus = MilestoneStatus.PENDING
    ordering: int = 0
    dependencies: list[str] = Field(default_factory=list)
    goal_linkage: str | None = None
    success_criteria: list[SuccessCriteria] = Field(default_factory=list)
    verification_criteria: list[str] = Field(default_factory=list)
    progress_pct: float = 0.0
    confidence: float = 1.0
    deadline: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    blocked_reason: str | None = None
    current_situation: str | None = None
    current_decision: str | None = None
    current_action: str | None = None
    verification_evidence: list[str] = Field(default_factory=list)
    version: int = 1
    created_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)


class MissionAssumption(BaseModel):
    """First-class explicit mission assumption (Task 100)."""

    model_config = ConfigDict(extra="ignore")

    assumption_id: str = Field(default_factory=lambda: f"asm_{uuid.uuid4().hex[:8]}")
    mission_id: str
    statement: str
    evidence: list[str] = Field(default_factory=list)
    confidence: float = 1.0
    status: AssumptionStatus = AssumptionStatus.VALID
    dependent_milestones: list[str] = Field(default_factory=list)
    dependent_plan_versions: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now_utc)
    last_verified_at: datetime | None = None
    invalidation_reason: str | None = None


class MissionDependency(BaseModel):
    """Internal, external, human, capability, or resource dependency (Task 100)."""

    model_config = ConfigDict(extra="ignore")

    dependency_id: str = Field(default_factory=lambda: f"dep_{uuid.uuid4().hex[:8]}")
    mission_id: str
    name: str
    dependency_type: DependencyType = DependencyType.INTERNAL
    status: DependencyStatus = DependencyStatus.AVAILABLE
    details: dict[str, Any] = Field(default_factory=dict)
    blocking_reason: str | None = None
    escalation_ref: str | None = None
    created_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)


class MissionPlanVersion(BaseModel):
    """Immutable versioned plan snapshot linking decisions and milestones (Task 100)."""

    model_config = ConfigDict(extra="ignore")

    version_id: str = Field(default_factory=lambda: f"pln_{uuid.uuid4().hex[:8]}")
    mission_id: str
    plan_id: str
    version_number: int = 1
    reason: str = ""
    triggering_situation_id: str | None = None
    changed_assumptions: list[str] = Field(default_factory=list)
    changed_milestones: list[str] = Field(default_factory=list)
    superseded_plan_id: str | None = None
    decisions_linked: list[str] = Field(default_factory=list)
    plan_spec: dict[str, Any] = Field(default_factory=dict)
    status: str = "ACTIVE"  # DRAFT, ACTIVE, SUPERSEDED, INVALIDATED
    created_at: datetime = Field(default_factory=_now_utc)


class MissionReview(BaseModel):
    """Periodic or event-triggered structured evaluation of mission status (Task 100)."""

    model_config = ConfigDict(extra="ignore")

    review_id: str = Field(default_factory=lambda: f"rev_{uuid.uuid4().hex[:8]}")
    mission_id: str
    reviewer: str = "system"
    review_type: ReviewType = ReviewType.SCHEDULED
    evaluation_score: float = 1.0
    health_dimensions: MissionHealthDimensions = Field(default_factory=MissionHealthDimensions)
    findings: list[str] = Field(default_factory=list)
    observations: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    actions_taken: list[str] = Field(default_factory=list)
    reviewed_at: datetime = Field(default_factory=_now_utc)


class Mission(BaseModel):
    """Top-level self-directed autonomous mission entity (Task 66 & Task 100).

    Invariants:
    - PLAN != MISSION: A mission persists across multiple replanning cycles.
    - GOAL != MISSION: A goal defines desired outcome; a mission coordinates long-horizon attainment.
    - WORK DONE != GOAL ACHIEVED: 100% task execution != mission success until empirically verified.
    """

    model_config = ConfigDict(extra="ignore")

    mission_id: str = Field(default_factory=lambda: f"msn_{uuid.uuid4().hex[:10]}")
    title: str
    description: str = ""
    objective: str = ""
    scope: str = "SYSTEM"
    goal_id: str = Field(default_factory=lambda: f"goal_{uuid.uuid4().hex[:10]}")
    goal_version: int = 1
    authority_scope: GoalAuthorityScope = GoalAuthorityScope.EXECUTE_LOW_RISK
    autonomy_level: AutonomyLevel = AutonomyLevel.BOUNDED_AUTONOMY
    status: MissionStatus = MissionStatus.DRAFT
    health: MissionHealth = MissionHealth.ON_TRACK
    health_dimensions: MissionHealthDimensions = Field(default_factory=MissionHealthDimensions)
    priority: int = 5
    strategic_importance: float = 0.5
    active_plan_id: str | None = None
    plan_versions: list[str] = Field(default_factory=list)
    progress_pct: float = 0.0
    progress_confidence: float = 1.0
    uncertainty: float = 0.0
    risk_summary: dict[str, Any] = Field(default_factory=dict)
    active_situations: list[str] = Field(default_factory=list)
    active_decisions: list[str] = Field(default_factory=list)
    active_actions: list[str] = Field(default_factory=list)
    active_workflows: list[str] = Field(default_factory=list)
    active_agents: list[str] = Field(default_factory=list)
    blocked_items: list[str] = Field(default_factory=list)
    objectives: list[MissionObjective] = Field(default_factory=list)
    milestones: list[MissionMilestone] = Field(default_factory=list)
    assumptions: list[MissionAssumption] = Field(default_factory=list)
    dependencies: list[MissionDependency] = Field(default_factory=list)
    plan_records: list[MissionPlanVersion] = Field(default_factory=list)
    reviews: list[MissionReview] = Field(default_factory=list)
    milestone_count: int = 0
    completed_milestones: int = 0
    failed_milestones: int = 0
    budget_limits: dict[str, float] = Field(
        default_factory=lambda: {
            "max_duration_hours": 72.0,
            "max_tool_calls": 500.0,
            "max_cost_usd": 50.0,
            "max_agent_spawns": 10.0,
        }
    )
    budget_consumed: dict[str, float] = Field(
        default_factory=lambda: {
            "duration_hours": 0.0,
            "tool_calls": 0.0,
            "cost_usd": 0.0,
            "agent_spawns": 0.0,
        }
    )
    deadline: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    expires_at: datetime | None = None
    last_review_at: datetime | None = None
    next_review_at: datetime | None = None
    current_context_id: str | None = None
    current_state_summary: str = ""
    checkpoints: list[MissionCheckpoint] = Field(default_factory=list)
    blockers: list[Blocker] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)
    version: int = 1
    provenance: dict[str, Any] = Field(default_factory=dict)
    tenant_id: str = "default"

    # Backward compatibility properties
    @property
    def id(self) -> str:
        return self.mission_id

    @property
    def progress(self) -> float:
        return self.progress_pct

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


class MissionOverview(BaseModel):
    """Aggregated dashboard telemetry for the Mission Control Center."""

    model_config = ConfigDict(extra="ignore")

    total_missions: int = 0
    active_missions: int = 0
    healthy_count: int = 0
    blocked_missions: int = 0
    at_risk_missions: int = 0
    awaiting_user_missions: int = 0
    awaiting_approval_missions: int = 0
    completed_missions: int = 0
    failed_missions: int = 0
    unknown_missions: int = 0
    open_blockers: int = 0
    active_drifts: int = 0
    audit_chain_intact: bool = True
    missions: list[Mission] = Field(default_factory=list)


# =====================================================================
# Request / Response DTOs
# =====================================================================


class MissionCreateRequest(BaseModel):
    """Payload to initiate a structured goal and mission."""

    title: str
    description: str = ""
    objective: str | None = None
    scope: str = "SYSTEM"
    origin: GoalOrigin = GoalOrigin.USER
    authority_scope: GoalAuthorityScope = GoalAuthorityScope.EXECUTE_LOW_RISK
    autonomy_level: AutonomyLevel = AutonomyLevel.BOUNDED_AUTONOMY
    priority: int = 5
    importance: float = 0.5
    urgency: float = 0.5
    constraints: list[str] | None = None
    success_criteria_descriptions: list[str] | None = None
    deadline: datetime | None = None
    budget_limit: float | None = None
    budget_limits: dict[str, float] | None = None
    tenant_id: str = "default"


class MissionUpdateRequest(BaseModel):
    """Payload to update an existing mission."""

    title: str | None = None
    description: str | None = None
    objective: str | None = None
    autonomy_level: AutonomyLevel | None = None
    priority: int | None = None
    deadline: datetime | None = None
    strategic_importance: float | None = None


class MilestoneCreateRequest(BaseModel):
    """Payload to append a milestone to a mission."""

    title: str
    description: str = ""
    objective_id: str | None = None
    ordering: int = 0
    dependencies: list[str] | None = None
    depends_on_milestones: list[str] | None = None
    goal_linkage: str | None = None
    success_criteria: list[dict[str, Any]] | None = None
    verification_criteria: list[str] | None = None
    required_evidence_types: list[str] | None = None
    progress_weight: float | None = 0.25
    is_critical_path: bool = False
    deadline: datetime | None = None


class MilestoneUpdateRequest(BaseModel):
    """Payload to update a milestone."""

    status: MilestoneStatus | None = None
    progress_pct: float | None = None
    blocked_reason: str | None = None
    confidence: float | None = None


class MilestoneVerifyRequest(BaseModel):
    """Payload to submit empirical evidence for milestone verification."""

    evidence: list[str] = Field(default_factory=list)
    world_state_entity_id: str | None = None
    postconditions_matched: bool | None = None


class AssumptionCreateRequest(BaseModel):
    """Payload to register an assumption."""

    model_config = ConfigDict(extra="ignore")

    statement: str
    source: str | None = None
    evidence: list[str] = Field(default_factory=list)
    confidence: float = 1.0
    dependent_milestones: list[str] = Field(default_factory=list)
    dependent_milestone_ids: list[str] = Field(default_factory=list)
    dependent_plan_versions: list[str] = Field(default_factory=list)


class AssumptionUpdateRequest(BaseModel):
    """Payload to update/invalidate an assumption."""

    status: AssumptionStatus | None = None
    confidence: float | None = None
    evidence: list[str] | None = None
    invalidation_reason: str | None = None


class DependencyCreateRequest(BaseModel):
    """Payload to register a dependency."""

    name: str
    dependency_type: DependencyType = DependencyType.INTERNAL
    status: DependencyStatus = DependencyStatus.AVAILABLE
    details: dict[str, Any] = Field(default_factory=dict)
    blocking_reason: str | None = None


class ObjectiveCreateRequest(BaseModel):
    """Payload to register an objective."""

    title: str
    description: str = ""
    parent_objective_id: str | None = None
    ordering: int = 0
    success_criteria: list[dict[str, Any]] | None = None


class MissionReviewRequest(BaseModel):
    """Payload to trigger a mission review."""

    model_config = ConfigDict(extra="ignore")

    review_type: ReviewType = ReviewType.TRIGGERED
    notes: str = ""
    evaluation_score: float | None = None
    observations: list[str] = Field(default_factory=list)


class CheckpointCreateRequest(BaseModel):
    """Payload to create a mission checkpoint."""

    model_config = ConfigDict(extra="ignore")

    label: str = ""
    context_summary: str = ""
    generate_handoff_manifest: bool = False
    world_state_ref: dict[str, Any] | None = None
    evidence: list[str] | None = None
    risks: list[str] | None = None


class GoalClarificationResponse(BaseModel):
    """Response returned when an initial goal is ambiguous (Spec 8)."""

    status: GoalValidationStatus = GoalValidationStatus.NEEDS_CLARIFICATION
    ambiguity_reason: str
    candidate_interpretations: list[dict[str, Any]]
    suggested_defaults: dict[str, Any]
