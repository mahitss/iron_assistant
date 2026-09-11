"""Domain schemas, data models, and epistemic enums for Autonomous World Model & Long-Horizon Foresight Engine (Task 65)."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


# =====================================================================
# Epistemic & Domain Enums
# =====================================================================


class WorldScope(str, enum.Enum):
    """Scope boundaries represented by a world model instance."""

    SYSTEM = "SYSTEM"
    ORGANIZATION = "ORGANIZATION"
    INFRASTRUCTURE = "INFRASTRUCTURE"
    PROJECT = "PROJECT"
    ENVIRONMENT = "ENVIRONMENT"
    MARKET = "MARKET"
    STRATEGIC = "STRATEGIC"
    SIMULATION = "SIMULATION"


class ForesightHorizon(str, enum.Enum):
    """Temporal forecast horizons across past, present, near, and long future."""

    PAST = "PAST"  # T-30d, T-7d
    NOW = "NOW"  # Real-time present state
    NEAR_FUTURE_1H = "NEAR_FUTURE_1H"  # T+1 hour
    NEAR_FUTURE_1D = "NEAR_FUTURE_1D"  # T+1 day
    MID_FUTURE_1W = "MID_FUTURE_1W"  # T+1 week
    MID_FUTURE_1M = "MID_FUTURE_1M"  # T+1 month
    LONG_FUTURE_1Y = "LONG_FUTURE_1Y"  # T+1 year


class UncertaintyGrade(str, enum.Enum):
    """Epistemic classification of belief certainty (Invariant: UNKNOWN != SAFE)."""

    KNOWN = "KNOWN"
    LIKELY = "LIKELY"
    UNCERTAIN = "UNCERTAIN"
    DISPUTED = "DISPUTED"
    ASSUMED = "ASSUMED"
    UNKNOWN = "UNKNOWN"


class StateAuthority(str, enum.Enum):
    """Source authority and provenance tier for world assertions."""

    OBSERVED = "OBSERVED"  # Directly witnessed from verified telemetry or source
    REPORTED = "REPORTED"  # Reported by external user or third-party actor
    INFERRED = "INFERRED"  # Derived logically from associated signals
    SIMULATED = "SIMULATED"  # Counterfactual sandbox output (strictly read-only)
    PREDICTED = "PREDICTED"  # Foresight engine output
    VERIFIED = "VERIFIED"  # Passed Truth & Verification barrier


class RelationshipType(str, enum.Enum):
    """Semantic and causal relationships connecting entities."""

    DEPENDS_ON = "DEPENDS_ON"
    USES = "USES"
    OWNS = "OWNS"
    CONTROLS = "CONTROLS"
    AFFECTS = "AFFECTS"
    LOCATED_IN = "LOCATED_IN"
    PART_OF = "PART_OF"
    CONNECTED_TO = "CONNECTED_TO"
    PRODUCES = "PRODUCES"
    CONSUMES = "CONSUMES"
    BLOCKS = "BLOCKS"
    ENABLES = "ENABLES"
    CAUSES = "CAUSES"
    CORRELATES_WITH = "CORRELATES_WITH"
    SIMILAR_TO = "SIMILAR_TO"
    REPLACED_BY = "REPLACED_BY"
    PRECEDES = "PRECEDES"
    FOLLOWS = "FOLLOWS"


class TrendDirection(str, enum.Enum):
    """Temporal trend trajectory classifications (Invariant: TREND != CAUSE)."""

    INCREASING = "INCREASING"
    DECREASING = "DECREASING"
    STABLE = "STABLE"
    VOLATILE = "VOLATILE"
    ACCELERATING = "ACCELERATING"
    DECELERATING = "DECELERATING"
    STRUCTURAL_SHIFT = "STRUCTURAL_SHIFT"


class ScenarioType(str, enum.Enum):
    """Scenario archetype taxonomy for future branching."""

    BASELINE = "BASELINE"
    OPTIMISTIC = "OPTIMISTIC"
    PESSIMISTIC = "PESSIMISTIC"
    ADVERSE = "ADVERSE"
    RECOVERY = "RECOVERY"
    DISRUPTION = "DISRUPTION"
    TRANSFORMATION = "TRANSFORMATION"
    CUSTOM = "CUSTOM"


class ReversibilityClass(str, enum.Enum):
    """Reversibility tier for decision actions in the world model."""

    REVERSIBLE = "REVERSIBLE"
    PARTIALLY_REVERSIBLE = "PARTIALLY_REVERSIBLE"
    IRREVERSIBLE = "IRREVERSIBLE"


class EarlyWarningSeverity(str, enum.Enum):
    """Severity tier for leading indicators and emerging risk signals."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class InconsistencyType(str, enum.Enum):
    """Taxonomy of world model self-check integrity violations."""

    CONTRADICTORY_STATE = "CONTRADICTORY_STATE"
    CIRCULAR_CAUSALITY = "CIRCULAR_CAUSALITY"
    STALE_DEPENDENCY = "STALE_DEPENDENCY"
    ORPHANED_ENTITY = "ORPHANED_ENTITY"
    INVALID_TEMPORAL = "INVALID_TEMPORAL"
    CONFIDENCE_ANOMALY = "CONFIDENCE_ANOMALY"


class ForecastStatus(str, enum.Enum):
    """Lifecycle status of a temporal forecast."""

    ACTIVE = "ACTIVE"
    STALE = "STALE"
    INVALIDATED = "INVALIDATED"
    FULFILLED = "FULFILLED"
    CONTRADICTED = "CONTRADICTED"


# =====================================================================
# Domain Data Models
# =====================================================================


class ForesightEntity(BaseModel):
    """Entity representation in the Autonomous World Model."""

    model_config = ConfigDict(extra="ignore")

    entity_id: str = Field(default_factory=lambda: f"ent_{uuid.uuid4().hex[:8]}")
    type: str  # service, resource, plan, goal, agent, tool, database, etc.
    name: str
    attributes: dict[str, Any] = Field(default_factory=dict)
    state: str = "UNKNOWN"
    scope: WorldScope = WorldScope.SYSTEM
    valid_from: datetime = Field(default_factory=_now_utc)
    valid_until: datetime | None = None
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    uncertainty: UncertaintyGrade = UncertaintyGrade.LIKELY
    authority: StateAuthority = StateAuthority.OBSERVED
    provenance: dict[str, Any] = Field(default_factory=dict)
    version: int = 1
    is_stale: bool = False
    tenant_id: str = "default"


class ForesightRelationship(BaseModel):
    """Directed edge connecting two entities with semantic or causal semantics."""

    model_config = ConfigDict(extra="ignore")

    rel_id: str = Field(default_factory=lambda: f"rel_{uuid.uuid4().hex[:8]}")
    source_entity_id: str
    target_entity_id: str
    relationship_type: RelationshipType = RelationshipType.DEPENDS_ON
    causal_strength: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    conditions: list[str] = Field(default_factory=list)
    scope: WorldScope = WorldScope.SYSTEM
    is_critical: bool = False
    provenance: dict[str, Any] = Field(default_factory=dict)


class StateVersionRecord(BaseModel):
    """Immutable point-in-time state observation record for historical reconstruction."""

    model_config = ConfigDict(extra="ignore")

    record_id: str = Field(default_factory=lambda: f"svr_{uuid.uuid4().hex[:8]}")
    entity_id: str
    state_version: int
    state: str
    observed_at: datetime = Field(default_factory=_now_utc)
    received_at: datetime = Field(default_factory=_now_utc)
    valid_from: datetime = Field(default_factory=_now_utc)
    valid_until: datetime | None = None
    source: str = "system"
    confidence: float = 0.8
    authority: StateAuthority = StateAuthority.OBSERVED
    metadata: dict[str, Any] = Field(default_factory=dict)


class ForecastInterval(BaseModel):
    """Bounded numerical or categorical range interval (Invariant: NO FALSE PRECISION)."""

    metric_name: str
    lower_bound: float
    point_estimate: float
    upper_bound: float
    unit: str = ""
    confidence_level: float = 0.90


class ForecastRecord(BaseModel):
    """Long-horizon forecast specification (Invariant: FORECAST != FACT)."""

    model_config = ConfigDict(extra="ignore")

    forecast_id: str = Field(default_factory=lambda: f"fct_{uuid.uuid4().hex[:8]}")
    topic: str
    horizon: ForesightHorizon = ForesightHorizon.NEAR_FUTURE_1D
    intervals: list[ForecastInterval] = Field(default_factory=list)
    prediction_summary: str
    assumptions: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    competing_hypotheses: list[str] = Field(default_factory=list)
    model_name: str = "ensemble"
    confidence: float = Field(default=0.75, ge=0.0, le=1.0)
    status: ForecastStatus = ForecastStatus.ACTIVE
    actual_outcome: str | None = None
    calibration_score: float | None = None
    created_at: datetime = Field(default_factory=_now_utc)
    tenant_id: str = "default"


class ScenarioBranch(BaseModel):
    """Isolated scenario branch sandbox (Invariant: SIMULATION != REALITY)."""

    model_config = ConfigDict(extra="ignore")

    scenario_id: str = Field(default_factory=lambda: f"scn_{uuid.uuid4().hex[:8]}")
    name: str
    type: ScenarioType = ScenarioType.BASELINE
    horizon: ForesightHorizon = ForesightHorizon.MID_FUTURE_1M
    initial_state_summary: str
    assumptions: list[str] = Field(default_factory=list)
    interventions: list[str] = Field(default_factory=list)
    expected_changes: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    confidence: float = 0.70
    is_stale: bool = False
    is_robust: bool = False
    sensitivity_score: float = 0.5
    tenant_id: str = "default"
    created_at: datetime = Field(default_factory=_now_utc)


class EarlyWarningSignal(BaseModel):
    """Leading indicator or emerging risk signal (Invariant: EARLY WARNING != INCIDENT)."""

    model_config = ConfigDict(extra="ignore")

    signal_id: str = Field(default_factory=lambda: f"ew_{uuid.uuid4().hex[:8]}")
    title: str
    description: str
    severity: EarlyWarningSeverity = EarlyWarningSeverity.MEDIUM
    trend: TrendDirection = TrendDirection.ACCELERATING
    affected_entities: list[str] = Field(default_factory=list)
    trigger_condition: str
    leading_indicators: list[str] = Field(default_factory=list)
    blast_radius: list[str] = Field(default_factory=list)
    recommended_action: str = ""
    is_active: bool = True
    created_at: datetime = Field(default_factory=_now_utc)


class StrategicRisk(BaseModel):
    """Persistent entry in the Strategic Risk Register."""

    model_config = ConfigDict(extra="ignore")

    risk_id: str = Field(default_factory=lambda: f"rsk_{uuid.uuid4().hex[:8]}")
    title: str
    description: str
    probability: float = Field(default=0.5, ge=0.0, le=1.0)
    impact: float = Field(default=0.7, ge=0.0, le=1.0)
    time_horizon: ForesightHorizon = ForesightHorizon.MID_FUTURE_1M
    dependencies: list[str] = Field(default_factory=list)
    mitigations: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    confidence: float = 0.8
    status: str = "OPEN"  # OPEN, MITIGATED, ACCEPTED, RETIRED


class StrategicOpportunity(BaseModel):
    """Persistent entry in the Strategic Opportunity Register."""

    model_config = ConfigDict(extra="ignore")

    opportunity_id: str = Field(default_factory=lambda: f"opp_{uuid.uuid4().hex[:8]}")
    title: str
    description: str
    potential_value: float = Field(default=0.7, ge=0.0, le=1.0)
    time_horizon: ForesightHorizon = ForesightHorizon.MID_FUTURE_1M
    dependencies: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    optionality_score: float = Field(default=0.8, ge=0.0, le=1.0)
    confidence: float = 0.75
    status: str = "IDENTIFIED"  # IDENTIFIED, ACTIVE, PURSUING, EXPIRED


class MonitoringPlan(BaseModel):
    """Bounded, signal-driven monitoring specification for risks and forecasts."""

    model_config = ConfigDict(extra="ignore")

    plan_id: str = Field(default_factory=lambda: f"mon_{uuid.uuid4().hex[:8]}")
    target_id: str
    target_type: str  # forecast, risk, scenario, entity
    signals: list[str] = Field(default_factory=list)
    thresholds: dict[str, float] = Field(default_factory=dict)
    frequency_seconds: int = 300
    expiry: datetime | None = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=_now_utc)


class WorldDiff(BaseModel):
    """Structural difference between two world model states or snapshots."""

    added_entities: list[str] = Field(default_factory=list)
    removed_entities: list[str] = Field(default_factory=list)
    changed_states: dict[str, dict[str, str]] = Field(default_factory=dict)
    new_dependencies: list[str] = Field(default_factory=list)
    removed_dependencies: list[str] = Field(default_factory=list)
    changed_relationships: list[str] = Field(default_factory=list)
    changed_assumptions: list[str] = Field(default_factory=list)
    new_risks: list[str] = Field(default_factory=list)
    new_opportunities: list[str] = Field(default_factory=list)


class WorldModelOverview(BaseModel):
    """High-level summary of the live world model and foresight state."""

    world_id: str
    scope: WorldScope
    version: int
    entity_count: int
    relationship_count: int
    active_forecasts_count: int
    active_scenarios_count: int
    open_risks_count: int
    open_opportunities_count: int
    early_warnings_count: int
    last_updated: datetime
    integrity_status: str = "HEALTHY"


# =====================================================================
# API Request & Response Schemas
# =====================================================================


class WorldModelQueryRequest(BaseModel):
    """Query request against the world model state."""

    query: str
    horizon: ForesightHorizon | None = None
    target_entities: list[str] = Field(default_factory=list)
    include_scenarios: bool = True
    include_risks: bool = True
    include_causal_path: bool = True


class WorldModelQueryResponse(BaseModel):
    """Response payload for a world model query."""

    answer: str
    confidence: float
    uncertainty: UncertaintyGrade
    relevant_entities: list[ForesightEntity] = Field(default_factory=list)
    causal_factors: list[str] = Field(default_factory=list)
    scenarios: list[ScenarioBranch] = Field(default_factory=list)
    early_warnings: list[EarlyWarningSignal] = Field(default_factory=list)
    explanation: str


class ForecastCreateRequest(BaseModel):
    """Payload to request or register a foresight forecast."""

    topic: str
    horizon: ForesightHorizon = ForesightHorizon.NEAR_FUTURE_1D
    target_metric: str | None = None
    assumptions: list[str] = Field(default_factory=list)
    tenant_id: str = "default"


class ScenarioCreateRequest(BaseModel):
    """Payload to generate an isolated counterfactual or future scenario branch."""

    name: str
    type: ScenarioType = ScenarioType.BASELINE
    horizon: ForesightHorizon = ForesightHorizon.MID_FUTURE_1M
    assumptions: list[str] = Field(default_factory=list)
    interventions: list[str] = Field(default_factory=list)
    tenant_id: str = "default"


class ReassessRequest(BaseModel):
    """Payload to trigger proactive world model reassessment."""

    changed_entity_id: str | None = None
    reason: str = "routine_reassessment"
    invalidate_stale_forecasts: bool = True
