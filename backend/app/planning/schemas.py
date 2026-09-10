"""Pydantic v2 schemas and domain models for Kairo Strategic Planning Engine (Task 58)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class PlanStatus(str, Enum):
    DRAFT = "DRAFT"
    ANALYZING = "ANALYZING"
    VALIDATED = "VALIDATED"
    READY = "READY"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    BLOCKED = "BLOCKED"
    REPLANNING = "REPLANNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SUPERSEDED = "SUPERSEDED"


class PhaseStatus(str, Enum):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    SKIPPED = "SKIPPED"


class MilestoneStatus(str, Enum):
    PENDING = "PENDING"
    REACHED = "REACHED"
    MISSED = "MISSED"
    BLOCKED = "BLOCKED"
    WAIVED = "WAIVED"


class TaskStatus(str, Enum):
    DRAFT = "DRAFT"
    READY = "READY"
    BLOCKED = "BLOCKED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SKIPPED = "SKIPPED"
    SUPERSEDED = "SUPERSEDED"


class DependencyType(str, Enum):
    PREREQUISITE = "PREREQUISITE"
    DATA = "DATA"
    RESOURCE = "RESOURCE"
    APPROVAL = "APPROVAL"
    DECISION = "DECISION"
    ENVIRONMENT = "ENVIRONMENT"
    TEMPORAL = "TEMPORAL"


class StrategyType(str, Enum):
    BIG_BANG = "BIG_BANG"
    INCREMENTAL = "INCREMENTAL"
    PARALLEL = "PARALLEL"
    STABILIZE_FIRST = "STABILIZE_FIRST"
    INFO_GATHERING = "INFO_GATHERING"
    CUSTOM = "CUSTOM"


class ResourceType(str, Enum):
    COMPUTE = "COMPUTE"
    STORAGE = "STORAGE"
    MEMORY = "MEMORY"
    BUDGET = "BUDGET"
    PERSONNEL = "PERSONNEL"
    API_QUOTA = "API_QUOTA"
    ENVIRONMENT = "ENVIRONMENT"


class RiskSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class HealthStatus(str, Enum):
    ON_TRACK = "ON_TRACK"
    AT_RISK = "AT_RISK"
    BLOCKED = "BLOCKED"
    STALE = "STALE"
    REPLANNING_REQUIRED = "REPLANNING_REQUIRED"
    COMPLETED = "COMPLETED"


class StateCertainty(str, Enum):
    OBSERVED = "OBSERVED"
    VERIFIED = "VERIFIED"
    INFERRED = "INFERRED"
    EXPECTED = "EXPECTED"
    SIMULATED = "SIMULATED"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


# Domain Contracts
class CurrentStateAssessment(BaseModel):
    model_config = ConfigDict(extra="ignore")

    state_id: str = Field(default_factory=lambda: f"st_{uuid.uuid4().hex[:8]}")
    summary: str
    verified_aspects: list[str] = Field(default_factory=list)
    active_telemetry: dict[str, Any] = Field(default_factory=dict)
    certainty: StateCertainty = StateCertainty.VERIFIED
    confidence: float = 0.9
    is_stale: bool = False


class DesiredStateDefinition(BaseModel):
    model_config = ConfigDict(extra="ignore")

    summary: str
    target_metrics: dict[str, float] = Field(default_factory=dict)
    completion_invariants: list[str] = Field(default_factory=list)
    verification_criteria: list[str] = Field(default_factory=list)


class GapAnalysis(BaseModel):
    model_config = ConfigDict(extra="ignore")

    missing_capabilities: list[str] = Field(default_factory=list)
    missing_resources: list[str] = Field(default_factory=list)
    technical_gaps: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    required_decisions: list[str] = Field(default_factory=list)


class StrategyOption(BaseModel):
    model_config = ConfigDict(extra="ignore")

    strategy_id: str = Field(default_factory=lambda: f"strat_{uuid.uuid4().hex[:8]}")
    name: str
    strategy_type: StrategyType = StrategyType.INCREMENTAL
    description: str
    rationale: str
    estimated_complexity: str = "MEDIUM"
    expected_risk: RiskSeverity = RiskSeverity.MEDIUM
    reversibility: str = "REVERSIBLE"
    decision_reference: str | None = None
    is_selected: bool = False


class ResourceRequirement(BaseModel):
    model_config = ConfigDict(extra="ignore")

    resource_id: str = Field(default_factory=lambda: f"res_{uuid.uuid4().hex[:8]}")
    resource_type: ResourceType = ResourceType.COMPUTE
    name: str
    amount: float = 1.0
    unit: str = "units"
    is_exclusive: bool = True
    is_available: bool = True


class TaskDependency(BaseModel):
    model_config = ConfigDict(extra="ignore")

    source_task_id: str
    target_task_id: str
    dependency_type: DependencyType = DependencyType.PREREQUISITE
    is_satisfied: bool = False


class PlanTask(BaseModel):
    model_config = ConfigDict(extra="ignore")

    task_id: str = Field(default_factory=lambda: f"ptk_{uuid.uuid4().hex[:8]}")
    phase_id: str | None = None
    package_id: str | None = None
    title: str
    description: str = ""
    owner: str = "OWNER_UNASSIGNED"
    status: TaskStatus = TaskStatus.DRAFT
    dependencies: list[str] = Field(default_factory=list)
    resources: list[ResourceRequirement] = Field(default_factory=list)
    duration_min: float = 1.0
    duration_expected: float = 2.0
    duration_max: float = 4.0
    is_irreversible: bool = False
    risk_level: RiskSeverity = RiskSeverity.LOW
    execution_wave: int = 1
    verification_criteria: list[str] = Field(default_factory=list)
    output_artifacts: list[str] = Field(default_factory=list)


class WorkPackage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    package_id: str = Field(default_factory=lambda: f"pwp_{uuid.uuid4().hex[:8]}")
    phase_id: str | None = None
    name: str
    description: str = ""
    owner: str = "OWNER_UNASSIGNED"
    status: PhaseStatus = PhaseStatus.PLANNED
    task_ids: list[str] = Field(default_factory=list)


class PlanMilestone(BaseModel):
    model_config = ConfigDict(extra="ignore")

    milestone_id: str = Field(default_factory=lambda: f"pml_{uuid.uuid4().hex[:8]}")
    phase_id: str | None = None
    name: str
    description: str = ""
    weight: float = 1.0
    target_date: datetime | None = None
    status: MilestoneStatus = MilestoneStatus.PENDING
    dependencies: list[str] = Field(default_factory=list)
    verification_criteria: list[str] = Field(default_factory=list)
    is_verified: bool = False


class PlanPhase(BaseModel):
    model_config = ConfigDict(extra="ignore")

    phase_id: str = Field(default_factory=lambda: f"pph_{uuid.uuid4().hex[:8]}")
    name: str
    phase_order: int = 1
    status: PhaseStatus = PhaseStatus.PLANNED
    entry_criteria: list[str] = Field(default_factory=list)
    exit_criteria: list[str] = Field(default_factory=list)
    milestone_ids: list[str] = Field(default_factory=list)
    package_ids: list[str] = Field(default_factory=list)


class ExecutionWave(BaseModel):
    model_config = ConfigDict(extra="ignore")

    wave_number: int
    task_ids: list[str] = Field(default_factory=list)
    estimated_duration: float = 0.0
    prerequisites_verified: bool = False


class PlanCheckpoint(BaseModel):
    model_config = ConfigDict(extra="ignore")

    checkpoint_id: str = Field(default_factory=lambda: f"pck_{uuid.uuid4().hex[:8]}")
    trigger_milestone_id: str | None = None
    name: str
    expected_state: dict[str, Any] = Field(default_factory=dict)
    observed_state: dict[str, Any] = Field(default_factory=dict)
    variance_score: float = 0.0
    decision_action: str = "CONTINUE"  # CONTINUE, PAUSE, ROLLBACK, REPLAN
    evaluated_at: datetime = Field(default_factory=_now_utc)


class PlanRisk(BaseModel):
    model_config = ConfigDict(extra="ignore")

    risk_id: str = Field(default_factory=lambda: f"prsk_{uuid.uuid4().hex[:8]}")
    description: str
    severity: RiskSeverity = RiskSeverity.MEDIUM
    probability: str = "MEDIUM"
    mitigation: str = ""
    contingency_plan: str = ""
    is_active: bool = True


class PlanRevision(BaseModel):
    model_config = ConfigDict(extra="ignore")

    revision_id: str = Field(default_factory=lambda: f"prev_{uuid.uuid4().hex[:8]}")
    parent_plan_id: str
    revision_number: int = 1
    reason: str
    actor: str
    diff_summary: dict[str, Any] = Field(default_factory=dict)
    snapshot: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now_utc)


class PlanOutcome(BaseModel):
    model_config = ConfigDict(extra="ignore")

    outcome_id: str = Field(default_factory=lambda: f"pout_{uuid.uuid4().hex[:8]}")
    plan_id: str
    success: bool = True
    actual_duration: float = 0.0
    actual_cost: float = 0.0
    estimation_error: float = 0.0
    lessons_learned: list[str] = Field(default_factory=list)
    recorded_at: datetime = Field(default_factory=_now_utc)


class StrategicPlan(BaseModel):
    model_config = ConfigDict(extra="ignore")

    plan_id: str = Field(default_factory=lambda: f"plan_{uuid.uuid4().hex[:10]}")
    name: str
    purpose: str
    goal_id: str | None = None
    decision_id: str | None = None
    current_state: CurrentStateAssessment
    desired_state: DesiredStateDefinition
    gap_analysis: GapAnalysis = Field(default_factory=GapAnalysis)
    strategy: StrategyOption
    phases: list[PlanPhase] = Field(default_factory=list)
    milestones: list[PlanMilestone] = Field(default_factory=list)
    work_packages: list[WorkPackage] = Field(default_factory=list)
    tasks: list[PlanTask] = Field(default_factory=list)
    execution_waves: list[ExecutionWave] = Field(default_factory=list)
    checkpoints: list[PlanCheckpoint] = Field(default_factory=list)
    risks: list[PlanRisk] = Field(default_factory=list)
    health: HealthStatus = HealthStatus.ON_TRACK
    status: PlanStatus = PlanStatus.DRAFT
    confidence: float = 0.85
    owner: str = "OWNER_UNASSIGNED"
    deadline: datetime | None = None
    version: int = 1
    provenance: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)
