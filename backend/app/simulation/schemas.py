"""Pydantic v2 schemas and enums for Kairo Simulation & Counterfactual Planning Engine (Task 56)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SimulationStatus(str, Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    STALE = "STALE"
    INVALIDATED = "INVALIDATED"


class ScenarioType(str, Enum):
    NO_CHANGE = "NO_CHANGE"
    SINGLE_CHANGE = "SINGLE_CHANGE"
    MULTI_CHANGE = "MULTI_CHANGE"
    FAILURE = "FAILURE"
    RECOVERY = "RECOVERY"
    ROLLBACK = "ROLLBACK"
    SCALE_UP = "SCALE_UP"
    SCALE_DOWN = "SCALE_DOWN"
    MIGRATION = "MIGRATION"
    DEPLOYMENT = "DEPLOYMENT"
    CONFIGURATION = "CONFIGURATION"
    RESOURCE = "RESOURCE"
    NETWORK = "NETWORK"
    DEPENDENCY = "DEPENDENCY"
    CUSTOM = "CUSTOM"


class EffectType(str, Enum):
    HEALTH = "HEALTH"
    LATENCY = "LATENCY"
    THROUGHPUT = "THROUGHPUT"
    ERROR_RATE = "ERROR_RATE"
    CAPACITY = "CAPACITY"
    COST = "COST"
    AVAILABILITY = "AVAILABILITY"
    DEPENDENCY = "DEPENDENCY"
    SECURITY = "SECURITY"
    RESOURCE = "RESOURCE"
    STATE = "STATE"


class ObjectiveType(str, Enum):
    MINIMIZE_COST = "MINIMIZE_COST"
    MINIMIZE_LATENCY = "MINIMIZE_LATENCY"
    MINIMIZE_RISK = "MINIMIZE_RISK"
    MAXIMIZE_AVAILABILITY = "MAXIMIZE_AVAILABILITY"
    MAXIMIZE_THROUGHPUT = "MAXIMIZE_THROUGHPUT"
    MINIMIZE_DOWNTIME = "MINIMIZE_DOWNTIME"
    MAXIMIZE_RELIABILITY = "MAXIMIZE_RELIABILITY"


class RiskCategory(str, Enum):
    AVAILABILITY = "AVAILABILITY"
    SECURITY = "SECURITY"
    DATA = "DATA"
    COST = "COST"
    PERFORMANCE = "PERFORMANCE"
    DEPENDENCY = "DEPENDENCY"
    OPERATIONS = "OPERATIONS"
    COMPLIANCE = "COMPLIANCE"


class AssumptionType(str, Enum):
    STATIC = "STATIC"
    ESTIMATED = "ESTIMATED"
    INFERRED = "INFERRED"
    UNKNOWN = "UNKNOWN"


class AssumptionImpact(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ExecutionGateStatus(str, Enum):
    BLOCKED = "BLOCKED"
    READY = "READY"
    NEEDS_APPROVAL = "NEEDS_APPROVAL"
    NEEDS_AUTHORIZATION = "NEEDS_AUTHORIZATION"
    STALE = "STALE"
    INVALIDATED = "INVALIDATED"


# Schemas
class SimulationSnapshot(BaseModel):
    model_config = ConfigDict(extra="ignore")

    snapshot_id: str
    source_entity: str = "digital_twin"
    scope: str = "SYSTEM"
    scope_id: str | None = None
    world_state: dict[str, Any] = Field(default_factory=dict)
    digital_twin_state: dict[str, Any] = Field(default_factory=dict)
    telemetry_state: dict[str, Any] = Field(default_factory=dict)
    state_payload: dict[str, Any] = Field(default_factory=dict)
    topology_graph: dict[str, Any] = Field(default_factory=dict)
    version: int = 1
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    baseline_hash: str = ""
    hash_sha256: str = ""
    is_stale: bool = False
    staleness_reason: str | None = None
    is_immutable: bool = True
    environment_label: str = "SIMULATION_ONLY"
    provenance: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SimulatedIntervention(BaseModel):
    model_config = ConfigDict(extra="ignore")

    intervention_id: str
    target: str
    operation: str
    before: Any = Field(default_factory=dict)
    hypothetical_after: Any = Field(default_factory=dict)
    expected_effect: dict[str, Any] = Field(default_factory=dict)
    constraints: list[str] = Field(default_factory=list)
    is_hypothetical: bool = True
    environment_label: str = "SIMULATION_ONLY"


class SimulatedEffect(BaseModel):
    model_config = ConfigDict(extra="ignore")

    effect_id: str
    source: str
    target: str
    effect_type: EffectType
    magnitude: float = 0.0
    confidence: float = 1.0
    evidence: list[str] = Field(default_factory=list)
    mechanism: str = ""
    is_hypothetical: bool = True


class SimulationObjective(BaseModel):
    model_config = ConfigDict(extra="ignore")

    objective_id: str
    objective_type: ObjectiveType = ObjectiveType.MINIMIZE_COST
    metric: str
    direction: str = "MINIMIZE"  # "MINIMIZE" or "MAXIMIZE"
    target: float | None = None
    target_value: float | None = None
    constraints: dict[str, Any] = Field(default_factory=dict)
    priority: int = 1  # 1 = highest


class SimulationRisk(BaseModel):
    model_config = ConfigDict(extra="ignore")

    risk_id: str
    scenario_id: str
    category: RiskCategory
    probability: Any = 0.5  # float or str
    impact: str = "LOW"
    confidence: float = 0.8
    evidence: list[str] = Field(default_factory=list)
    mitigation: str = ""


class ScenarioAssumption(BaseModel):
    model_config = ConfigDict(extra="ignore")

    assumption_id: str
    name: str = ""
    statement: str = ""
    assumption_type: AssumptionType = AssumptionType.STATIC
    impact: AssumptionImpact = AssumptionImpact.MEDIUM
    confidence: float = 0.8
    description: str = ""
    is_critical: bool = False


class Scenario(BaseModel):
    model_config = ConfigDict(extra="ignore")

    scenario_id: str
    name: str
    scenario_type: ScenarioType = ScenarioType.CUSTOM
    baseline_snapshot_id: str
    interventions: list[SimulatedIntervention] = Field(default_factory=list)
    assumptions: list[ScenarioAssumption] = Field(default_factory=list)
    constraints: Any = Field(default_factory=list)
    objectives: list[SimulationObjective] = Field(default_factory=list)
    horizon: str = "SHORT_TERM"
    horizon_seconds: int = 3600
    status: str = "CREATED"
    version: int = 1
    is_hypothetical: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Simulation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    simulation_id: str
    source_snapshot_id: str = ""
    scenario_id: str = ""
    source_snapshot: Any = None
    scenario: Any = None
    initial_state: dict[str, Any] = Field(default_factory=dict)
    future_state: dict[str, Any] = Field(default_factory=dict)
    predicted_future_state: dict[str, Any] = Field(default_factory=dict)
    diff: dict[str, Any] = Field(default_factory=dict)
    effects: list[SimulatedEffect] = Field(default_factory=list)
    risks: list[SimulationRisk] = Field(default_factory=list)
    assumptions: list[ScenarioAssumption] = Field(default_factory=list)
    model_version: str = "1.0.0"
    status: SimulationStatus = SimulationStatus.CREATED
    confidence: float = 0.8
    environment_label: str = "SIMULATION_ONLY"
    is_hypothetical: bool = True
    outputs: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None


class ExecutionGate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    gate_id: str
    simulation_id: str = ""
    scenario_id: str = ""
    plan_id: str | None = None
    status: ExecutionGateStatus = ExecutionGateStatus.BLOCKED
    gate_status: ExecutionGateStatus = ExecutionGateStatus.BLOCKED
    baseline_snapshot_id: str = ""
    baseline_hash: str = ""
    baseline_hash_at_sim: str = ""
    current_hash: str | None = None
    current_real_hash: str = ""
    drift_detected: bool = False
    drift_details: Any = Field(default_factory=dict)
    approval_required: bool = True
    approval_id: str | None = None
    authorization_required: bool = True
    authorized_by: str | None = None
    policy_compliant: bool = True
    revalidation_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    verification_plan: list[str] = Field(default_factory=list)
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ScenarioComparison(BaseModel):
    model_config = ConfigDict(extra="ignore")

    comparison_id: str = Field(default_factory=lambda: f"cmp_{uuid.uuid4().hex[:12]}")
    scenario_ids: list[str] = Field(default_factory=list)
    scenarios: list[str] = Field(default_factory=list)
    metrics_matrix: dict[str, dict[str, Any]] = Field(default_factory=dict)
    metrics_comparison: dict[str, dict[str, Any]] = Field(default_factory=dict)
    risk_summary: dict[str, list[str]] = Field(default_factory=dict)
    trade_offs: Any = Field(default_factory=list)
    pareto_optimal_scenarios: list[str] = Field(default_factory=list)
    recommended_scenario_id: str | None = None
    recommended_scenario: str | None = None
    recommendation_rationale: str = ""
    is_hypothetical: bool = True


class CalibrationMetric(BaseModel):
    model_config = ConfigDict(extra="ignore")

    calibration_id: str
    simulation_id: str
    metric_name: str = ""
    predicted_value: float = 0.0
    actual_value: float = 0.0
    predicted_metrics: dict[str, float] = Field(default_factory=dict)
    actual_metrics: dict[str, float] = Field(default_factory=dict)
    error: float = 0.0
    bias: float = 0.0
    absolute_errors: dict[str, float] = Field(default_factory=dict)
    mean_absolute_error: float = 0.0
    accuracy: float = 1.0
    drift_detected: bool = False
    calibrated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
