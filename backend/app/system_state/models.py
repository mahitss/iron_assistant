"""Domain models, state categories, epistemic classifications, and graph entities for Task 93.

Non-negotiable epistemic invariants:
- OBSERVED != DERIVED != INFERRED != PREDICTED != UNKNOWN
- UNKNOWN != FAILED
- PREDICTED_STATE != ACTUAL_STATE
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class StateCategory(str, Enum):
    """Operational state classification."""
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    FAILED = "FAILED"
    STARTING = "STARTING"
    STOPPING = "STOPPING"
    UNKNOWN = "UNKNOWN"
    STALE = "STALE"
    BLOCKED = "BLOCKED"
    SUSPENDED = "SUSPENDED"
    RECOVERING = "RECOVERING"
    SIMULATING = "SIMULATING"
    CANARY = "CANARY"
    ACTIVE = "ACTIVE"


class EpistemicStatus(str, Enum):
    """Rigid epistemological status of a state assertion."""
    OBSERVED = "OBSERVED"      # Direct measurement/heartbeat from authoritative component
    DERIVED = "DERIVED"        # Logically computed from verified observations
    INFERRED = "INFERRED"      # Probabilistic or heuristic attribution
    PREDICTED = "PREDICTED"    # Future/counterfactual state (Digital twin, forecasting)
    UNKNOWN = "UNKNOWN"        # Unmeasured or missing observation (NOT FAILED)


class StateType(str, Enum):
    """Entity domain in the operational state graph."""
    SYSTEM = "SYSTEM"
    COMPONENT = "COMPONENT"
    CAPABILITY = "CAPABILITY"
    RUNTIME = "RUNTIME"
    TASK = "TASK"
    WORKFLOW = "WORKFLOW"
    GOAL = "GOAL"
    RESOURCE = "RESOURCE"
    DEPENDENCY = "DEPENDENCY"
    INCIDENT = "INCIDENT"
    SECURITY = "SECURITY"
    GOVERNANCE = "GOVERNANCE"
    PROVIDER = "PROVIDER"
    KNOWLEDGE = "KNOWLEDGE"
    EXTERNAL_DEPENDENCY = "EXTERNAL_DEPENDENCY"


class EdgeType(str, Enum):
    """Operational relationships linking state entities."""
    GOAL_TASK = "SERVES"
    TASK_WORKFLOW = "EXECUTES_VIA"
    WORKFLOW_CAPABILITY = "REQUIRES_CAPABILITY"
    CAPABILITY_TOOL = "DISPATCHES_TO"
    TOOL_RUNTIME = "RUNS_ON"
    RUNTIME_RESOURCE = "CONSUMES"
    CAPABILITY_DEPENDENCY = "DEPENDS_ON"
    TASK_KNOWLEDGE = "PRODUCES"
    INCIDENT_COMPONENT = "AFFECTS"
    FAILURE_GOAL = "IMPACTS"
    RECOVERY_COMPONENT = "RESTORES"
    SECURITY_CAPABILITY = "CONSTRAINS"
    GOVERNANCE_ACTION = "CONSTRAINS"
    PROVIDER_CAPABILITY = "SUPPORTS"


class DeltaType(str, Enum):
    """Classification of state delta between snapshots."""
    ADDED = "ADDED"
    REMOVED = "REMOVED"
    CHANGED = "CHANGED"
    DEGRADED = "DEGRADED"
    RECOVERED = "RECOVERED"
    NEW_DEPENDENCY = "NEW_DEPENDENCY"
    LOST_DEPENDENCY = "LOST_DEPENDENCY"
    NEW_INCIDENT = "NEW_INCIDENT"
    RESOLVED_INCIDENT = "RESOLVED_INCIDENT"
    GOAL_IMPACT = "GOAL_IMPACT"
    RESOURCE_CHANGE = "RESOURCE_CHANGE"


class StateEntity(BaseModel):
    """Strongly-typed entity representing an operational component or process."""
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    id: str = Field(..., description="Stable unique identifier for the state entity")
    state_type: StateType
    status: StateCategory
    epistemic_status: EpistemicStatus = EpistemicStatus.OBSERVED
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source: str = Field(default="system", description="Authoritative source or reporter")
    provenance: str | None = Field(default=None, description="Audit trace or event reference")
    version: int = Field(default=1, ge=1)
    correlation_id: str | None = None
    observed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    ttl_seconds: float | None = Field(default=300.0, description="Freshness threshold in seconds")
    health_score: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def is_stale(self, now: datetime | None = None) -> bool:
        """Check if entity exceeds its TTL without observation."""
        if self.ttl_seconds is None:
            return False
        current_time = now or datetime.now(UTC)
        elapsed = (current_time - self.updated_at).total_seconds()
        return elapsed > self.ttl_seconds

    def with_update(
        self,
        status: StateCategory | None = None,
        epistemic_status: EpistemicStatus | None = None,
        confidence: float | None = None,
        health_score: float | None = None,
        metadata: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> StateEntity:
        """Return a new versioned copy with validated transitions."""
        now = datetime.now(UTC)
        new_meta = dict(self.metadata)
        if metadata:
            new_meta.update(metadata)

        return StateEntity(
            id=self.id,
            state_type=self.state_type,
            status=status or self.status,
            epistemic_status=epistemic_status or self.epistemic_status,
            confidence=confidence if confidence is not None else self.confidence,
            source=self.source,
            provenance=self.provenance,
            version=self.version + 1,
            correlation_id=correlation_id or self.correlation_id,
            observed_at=self.observed_at,
            updated_at=now,
            ttl_seconds=self.ttl_seconds,
            health_score=health_score if health_score is not None else self.health_score,
            metadata=new_meta,
        )


class StateEdge(BaseModel):
    """Directed dependency or operational relation in the state graph."""
    model_config = ConfigDict(frozen=True)

    source_id: str
    target_id: str
    edge_type: EdgeType
    epistemic_status: EpistemicStatus = EpistemicStatus.OBSERVED
    weight: float = Field(default=1.0, ge=0.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SystemStateSnapshot(BaseModel):
    """Immutable, point-in-time representation of Kairo's operational reality."""
    model_config = ConfigDict(frozen=True)

    snapshot_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    schema_version: str = "v1"
    system_version: str = "0.93.0"
    source_event_watermark: int = 0
    state_hash: str
    entities: dict[str, StateEntity]
    edges: list[StateEdge]
    metadata: dict[str, Any] = Field(default_factory=dict)


class StateDelta(BaseModel):
    """Computed state differential between two snapshots."""
    model_config = ConfigDict(frozen=True)

    delta_id: str
    from_snapshot_id: str
    to_snapshot_id: str
    delta_type: DeltaType
    entity_id: str
    entity_type: StateType
    from_status: StateCategory | None = None
    to_status: StateCategory | None = None
    epistemic_status: EpistemicStatus = EpistemicStatus.OBSERVED
    affected_tasks: list[str] = Field(default_factory=list)
    affected_workflows: list[str] = Field(default_factory=list)
    affected_goals: list[str] = Field(default_factory=list)
    affected_dependencies: list[str] = Field(default_factory=list)
    detected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)


class SystemDiagnosis(BaseModel):
    """Structured self-diagnostic report of Kairo's health and constraints."""
    current_state: StateCategory
    health_score: float
    active_objectives: list[dict[str, Any]] = Field(default_factory=list)
    active_work: list[dict[str, Any]] = Field(default_factory=list)
    resource_pressure: dict[str, Any] = Field(default_factory=dict)
    dependency_issues: list[dict[str, Any]] = Field(default_factory=list)
    security_restrictions: list[dict[str, Any]] = Field(default_factory=list)
    governance_blockers: list[dict[str, Any]] = Field(default_factory=list)
    active_incidents: list[dict[str, Any]] = Field(default_factory=list)
    stale_knowledge: list[dict[str, Any]] = Field(default_factory=list)
    predicted_risks: list[dict[str, Any]] = Field(default_factory=list)
    recovery_actions: list[dict[str, Any]] = Field(default_factory=list)
    unknown_states: list[dict[str, Any]] = Field(default_factory=list)
    epistemic_breakdown: dict[str, int] = Field(default_factory=dict)
    diagnosed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SelfModelAnswers(BaseModel):
    """Structured responses to the 13 canonical operational self-model queries."""
    what_am_i_doing: list[dict[str, Any]]
    why_am_i_doing_it: list[dict[str, Any]]
    what_am_i_waiting_for: list[dict[str, Any]]
    what_is_broken: list[dict[str, Any]]
    what_depends_on_component: dict[str, list[str]]
    what_goals_are_blocked: list[dict[str, Any]]
    what_resources_are_constrained: dict[str, Any]
    what_changed_recently: list[dict[str, Any]]
    what_capabilities_are_degraded: list[dict[str, Any]]
    what_incidents_are_active: list[dict[str, Any]]
    what_do_i_not_know: list[dict[str, Any]]
    what_state_is_stale: list[dict[str, Any]]
    which_assumptions_are_inferred: list[dict[str, Any]]
    queried_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
