"""Pydantic v2 domain schemas and data contracts for Kairo Autonomous Goal Management & Self-Directed Mission Engine (Task 66)."""

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
    """16 canonical lifecycle states of a self-directed mission (Spec 25)."""

    DRAFT = "DRAFT"
    VALIDATING = "VALIDATING"
    READY = "READY"
    PLANNING = "PLANNING"
    WAITING_FOR_RESOURCES = "WAITING_FOR_RESOURCES"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    BLOCKED = "BLOCKED"
    REPLANNING = "REPLANNING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    ESCALATED = "ESCALATED"
    EXPIRED = "EXPIRED"


class MissionHealth(str, enum.Enum):
    """Real-time operational health of an active mission (Spec 97)."""

    ON_TRACK = "ON_TRACK"
    HEALTHY = "ON_TRACK"
    AT_RISK = "AT_RISK"
    BLOCKED = "BLOCKED"
    DRIFTING = "DRIFTING"
    STALE = "STALE"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"


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
    criteria_type: str = "metric_threshold"  # metric_threshold, milestone_completion, verification_result, user_approval, test_pass
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
    """Structured checkpoint along long-running mission execution (Spec 26)."""

    model_config = ConfigDict(extra="ignore")

    checkpoint_id: str = Field(default_factory=lambda: f"chk_{uuid.uuid4().hex[:8]}")
    mission_id: str
    state: MissionStatus
    progress_pct: float = 0.0
    evidence: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    verification: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=_now_utc)


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


class Mission(BaseModel):
    """Top-level self-directed autonomous mission entity (Spec 2, 25, 37).

    Invariant: PLAN != MISSION. A mission persists across multiple replanning cycles.
    """

    model_config = ConfigDict(extra="ignore")

    mission_id: str = Field(default_factory=lambda: f"msn_{uuid.uuid4().hex[:10]}")
    title: str
    description: str = ""
    goal_id: str = Field(default_factory=lambda: f"goal_{uuid.uuid4().hex[:10]}")
    authority_scope: GoalAuthorityScope = GoalAuthorityScope.EXECUTE_LOW_RISK
    status: MissionStatus = MissionStatus.DRAFT
    health: MissionHealth = MissionHealth.ON_TRACK
    active_plan_id: str | None = None
    plan_versions: list[str] = Field(default_factory=list)
    progress_pct: float = 0.0
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
    expires_at: datetime | None = None
    checkpoints: list[MissionCheckpoint] = Field(default_factory=list)
    blockers: list[Blocker] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)
    version: int = 1
    provenance: dict[str, Any] = Field(default_factory=dict)
    tenant_id: str = "default"


class MissionOverview(BaseModel):
    """Aggregated dashboard telemetry for the Mission Control Center."""

    model_config = ConfigDict(extra="ignore")

    total_missions: int = 0
    active_missions: int = 0
    healthy_count: int = 0
    blocked_missions: int = 0
    completed_missions: int = 0
    failed_missions: int = 0
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
    origin: GoalOrigin = GoalOrigin.USER
    authority_scope: GoalAuthorityScope = GoalAuthorityScope.EXECUTE_LOW_RISK
    priority: int = 5
    importance: float = 0.5
    urgency: float = 0.5
    constraints: list[str] | None = None
    success_criteria_descriptions: list[str] | None = None
    deadline: datetime | None = None
    budget_limit: float | None = None
    budget_limits: dict[str, float] | None = None
    tenant_id: str = "default"


class GoalClarificationResponse(BaseModel):
    """Response returned when an initial goal is ambiguous (Spec 8)."""

    status: GoalValidationStatus = GoalValidationStatus.NEEDS_CLARIFICATION
    ambiguity_reason: str
    candidate_interpretations: list[dict[str, Any]]
    suggested_defaults: dict[str, Any]
