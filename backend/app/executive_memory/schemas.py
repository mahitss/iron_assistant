"""Pydantic schemas and enums for Kairo Executive Memory & Long-Horizon Context Engine (Task 53)."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field


class ExecutiveStateScope(str, Enum):
    """INVARIANT 3: Scopes for executive state aggregation."""
    SESSION = "SESSION"
    TASK = "TASK"
    PROJECT = "PROJECT"
    USER = "USER"
    ORGANIZATION = "ORGANIZATION"


class ProjectLifecycleState(str, Enum):
    """INVARIANT 8: Formal project lifecycle states."""
    IDEA = "IDEA"
    PLANNING = "PLANNING"
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"
    CANCELLED = "CANCELLED"


class TimelineEventType(str, Enum):
    """INVARIANT 11: Authoritative timeline event types."""
    CREATED = "CREATED"
    STARTED = "STARTED"
    DECIDED = "DECIDED"
    CHANGED = "CHANGED"
    BLOCKED = "BLOCKED"
    UNBLOCKED = "UNBLOCKED"
    TASK_CREATED = "TASK_CREATED"
    TASK_COMPLETED = "TASK_COMPLETED"
    DEPLOYED = "DEPLOYED"
    FAILED = "FAILED"
    RECOVERED = "RECOVERED"
    MEETING = "MEETING"
    DOCUMENTED = "DOCUMENTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PAUSED = "PAUSED"
    RESUMED = "RESUMED"
    COMPLETED = "COMPLETED"


class OpenLoopStatus(str, Enum):
    """INVARIANT 28: Status of open loops and unfinished work."""
    OPEN = "OPEN"
    WAITING = "WAITING"
    BLOCKED = "BLOCKED"
    STALE = "STALE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"


class BlockerStatus(str, Enum):
    """INVARIANT 39: Blocker operational status."""
    ACTIVE = "ACTIVE"
    RESOLVED = "RESOLVED"
    UNKNOWN = "UNKNOWN"


class MilestoneStatus(str, Enum):
    """INVARIANT 43: Milestone progression status."""
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    ACHIEVED = "ACHIEVED"
    MISSED = "MISSED"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"


class QualitativeProgress(str, Enum):
    """INVARIANT 48: Qualitative progress representation avoiding fake percentages."""
    NOT_STARTED = "NOT_STARTED"
    EARLY = "EARLY"
    IN_PROGRESS = "IN_PROGRESS"
    NEAR_COMPLETE = "NEAR_COMPLETE"
    COMPLETE = "COMPLETE"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


class RiskState(str, Enum):
    """INVARIANT 172: Historical and active risk states."""
    OPEN = "OPEN"
    MITIGATED = "MITIGATED"
    REALIZED = "REALIZED"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"


class UncertaintyLevel(str, Enum):
    """INVARIANT 201: Grounded uncertainty representation."""
    KNOWN = "KNOWN"
    SUPPORTED = "SUPPORTED"
    INFERRED = "INFERRED"
    UNKNOWN = "UNKNOWN"


class NextActionStatus(str, Enum):
    """Operational status of recommended next actions."""
    RECOMMENDED = "RECOMMENDED"
    ACCEPTED = "ACCEPTED"
    DISMISSED = "DISMISSED"
    EXECUTED = "EXECUTED"


class TimelineEventSchema(BaseModel):
    """INVARIANT 10: Authoritative timeline event item."""
    model_config = ConfigDict(use_enum_values=True)

    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    event_type: TimelineEventType = TimelineEventType.CHANGED
    source: str = "SYSTEM"
    project_id: str | None = None
    actor: str = "kairo"
    description_reference: str
    impact: str = "MEDIUM"
    provenance: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class OpenLoopSchema(BaseModel):
    """INVARIANT 27: Unfinished work and pending state tracking."""
    model_config = ConfigDict(use_enum_values=True)

    loop_id: str = Field(default_factory=lambda: f"loop_{uuid.uuid4().hex[:12]}")
    description: str
    owner: str = "user"
    source: str = "TASK"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_activity: datetime = Field(default_factory=lambda: datetime.now(UTC))
    due_at: datetime | None = None
    priority: float | str = 1.0
    status: OpenLoopStatus = OpenLoopStatus.OPEN
    dependencies: list[str] = Field(default_factory=list)
    scope: ExecutiveStateScope = ExecutiveStateScope.PROJECT
    scope_id: str | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    age_days: int = 0


class BlockerSchema(BaseModel):
    """INVARIANT 38: Blocker with evidence and affected tasks."""
    model_config = ConfigDict(use_enum_values=True)

    blocker_id: str = Field(default_factory=lambda: f"blk_{uuid.uuid4().hex[:12]}")
    description: str
    affected_tasks: list[str] = Field(default_factory=list)
    source: str = "ENVIRONMENT"
    severity: str = "HIGH"
    owner: str = "team"
    detected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    resolved_at: datetime | None = None
    status: BlockerStatus = BlockerStatus.ACTIVE
    causality_evidence: str | dict[str, Any] = Field(default_factory=dict)
    project_id: str | None = None


class MilestoneSchema(BaseModel):
    """INVARIANT 42: Project milestone with criteria and evidence."""
    model_config = ConfigDict(use_enum_values=True)

    milestone_id: str = Field(default_factory=lambda: f"mls_{uuid.uuid4().hex[:12]}")
    project_id: str
    goal_id: str | None = None
    title: str = ""
    criteria: list[str] | str = Field(default_factory=list)
    due_at: datetime | None = None
    status: MilestoneStatus = MilestoneStatus.PLANNED
    evidence: dict[str, Any] | str = Field(default_factory=dict)
    achieved_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class NextActionSchema(BaseModel):
    """INVARIANT 74: Recommended next action derived from open loops."""
    model_config = ConfigDict(use_enum_values=True)

    action_id: str = Field(default_factory=lambda: f"act_{uuid.uuid4().hex[:12]}")
    objective: str
    rationale: str
    dependencies: list[str] = Field(default_factory=list)
    authorization_status: str = "REQUIRED"
    confidence: float = 0.8
    status: NextActionStatus = NextActionStatus.RECOMMENDED
    project_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ExecutiveBriefSchema(BaseModel):
    """INVARIANT 147 & 148: Compact, structured executive project briefing."""
    model_config = ConfigDict(use_enum_values=True)

    summary_id: str = Field(default_factory=lambda: f"brf_{uuid.uuid4().hex[:12]}")
    project_id: str
    current_status: str
    recent_progress: list[dict[str, Any]] = Field(default_factory=list)
    open_work: list[dict[str, Any]] = Field(default_factory=list)
    blockers: list[dict[str, Any]] = Field(default_factory=list)
    decisions: list[dict[str, Any]] = Field(default_factory=list)
    risks: list[dict[str, Any]] = Field(default_factory=list)
    next_actions: list[dict[str, Any]] = Field(default_factory=list)
    as_of: datetime = Field(default_factory=lambda: datetime.now(UTC))
    staleness_hash: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CheckpointSchema(BaseModel):
    """INVARIANT 157: Long-running workflow checkpoint for resumption."""
    model_config = ConfigDict(use_enum_values=True)

    checkpoint_id: str = Field(default_factory=lambda: f"chk_{uuid.uuid4().hex[:12]}")
    workflow_id: str
    goal_id: str | None = None
    goal: str | None = None
    state_payload: dict[str, Any] = Field(default_factory=dict)
    state: dict[str, Any] = Field(default_factory=dict)
    progress: str = "IN_PROGRESS"
    dependencies: list[str] = Field(default_factory=list)
    authorization: dict[str, Any] = Field(default_factory=dict)
    next_step: Any = Field(default_factory=dict)
    valid: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ExecutiveStateSchema(BaseModel):
    """INVARIANT 2: Synthesized executive state from authoritative sources."""
    model_config = ConfigDict(use_enum_values=True)

    state_id: str = Field(default_factory=lambda: f"exs_{uuid.uuid4().hex[:12]}")
    scope: ExecutiveStateScope = ExecutiveStateScope.PROJECT
    scope_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    active_projects: list[dict[str, Any]] = Field(default_factory=list)
    active_goals: list[dict[str, Any]] = Field(default_factory=list)
    active_tasks: list[dict[str, Any]] = Field(default_factory=list)
    blockers: list[BlockerSchema] = Field(default_factory=list)
    open_loops: list[OpenLoopSchema] = Field(default_factory=list)
    recent_decisions: list[dict[str, Any]] = Field(default_factory=list)
    recent_outcomes: list[dict[str, Any]] = Field(default_factory=list)
    upcoming_deadlines: list[dict[str, Any]] = Field(default_factory=list)
    pending_commitments: list[dict[str, Any]] = Field(default_factory=list)
    next_actions: list[NextActionSchema] = Field(default_factory=list)
    risks: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float = 1.0
    provenance: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ContinuityQueryRequest(BaseModel):
    """Request model for continuity inquiries."""
    question_type: str = Field(
        ...,
        description="WHAT_WERE_WE_DOING, WHY_DID_WE_DO_IT, WHERE_DID_WE_STOP, WHAT_CHANGED, "
                    "WHAT_IS_HAPPENING, WHAT_REMAINS, WHAT_NEXT, WHAT_WAS_TRUE",
    )
    project_id: str | None = None
    as_of: datetime | None = None
    target_id: str | None = None
    explicit_user_intent: str | None = None


class ContinuityQueryResponse(BaseModel):
    """Answer with evidence and authoritative provenance."""
    model_config = ConfigDict(use_enum_values=True)

    question: str
    answer: str
    last_meaningful_state: dict[str, Any] | None = None
    recent_progress: list[dict[str, Any]] = Field(default_factory=list)
    open_loops: list[dict[str, Any]] = Field(default_factory=list)
    blockers: list[dict[str, Any]] = Field(default_factory=list)
    next_actions: list[dict[str, Any]] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    uncertainty: UncertaintyLevel = UncertaintyLevel.KNOWN
    confidence_level: UncertaintyLevel | str = UncertaintyLevel.KNOWN
    authoritative_sources: list[str] = Field(default_factory=list)


class ReconciliationReportSchema(BaseModel):
    """INVARIANT 124 & 205: Reconciliation report between executive state and source systems."""
    model_config = ConfigDict(use_enum_values=True)

    reconciliation_id: str = Field(default_factory=lambda: f"rec_{uuid.uuid4().hex[:12]}")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    drift_detected: bool = False
    drift_items: list[dict[str, Any]] = Field(default_factory=list)
    discrepancies: list[str] = Field(default_factory=list)
    corrected_items: list[dict[str, Any]] = Field(default_factory=list)
    reconciled_state: dict[str, Any] = Field(default_factory=dict)
    source_authoritative_overrides: int = 0


class ExecutiveMemoryMetricsSchema(BaseModel):
    """INVARIANT 223: Multi-dimensional executive memory operational metrics."""
    reconstruction_accuracy: float = 1.0
    summary_accuracy: float = 1.0
    open_loop_precision: float = 1.0
    stale_loop_rate: float = 0.0
    timeline_integrity: float = 1.0
    context_retrieval_latency_ms: float = 0.0
    false_continuity_rate: float = 0.0
    user_correction_rate: float = 0.0
    total_events: int = 0
    active_loops: int = 0
    active_blockers: int = 0
