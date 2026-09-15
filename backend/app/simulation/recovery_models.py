"""Pydantic v2 schemas and enums for Task 89 Autonomous Recovery Simulation & Digital Twin."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SimulationMode(str, Enum):
    """Execution modes for resilience recovery simulation."""

    ANALYTICAL = "ANALYTICAL"
    EVENT_REPLAY = "EVENT_REPLAY"
    DISCRETE_EVENT = "DISCRETE_EVENT"
    RESOURCE_SIMULATION = "RESOURCE_SIMULATION"
    FAULT_INJECTION = "FAULT_INJECTION"
    SANDBOXED_EXECUTION = "SANDBOXED_EXECUTION"


class ConsistencyLevel(str, Enum):
    """Consistency guarantees for operational snapshots."""

    STRONG = "STRONG"
    BOUNDED = "BOUNDED"
    EVENTUAL = "EVENTUAL"
    PARTIAL = "PARTIAL"


class UncertaintyLevel(str, Enum):
    """Qualitative uncertainty levels to prevent fake precision."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RecoveryCandidate(BaseModel):
    """Evaluated recovery strategy candidate with quantitative and qualitative projections."""

    model_config = ConfigDict(extra="ignore")

    candidate_id: str = Field(default_factory=lambda: f"cand_{uuid.uuid4().hex[:10]}")
    strategy: str  # RecoveryStrategyType string (e.g., RESTART_COMPONENT, RECONNECT, DEGRADE_CAPABILITY)
    target_subsystem: str
    description: str = ""
    expected_benefit: str
    expected_risk: str
    resource_cost: dict[str, Any] = Field(default_factory=dict)
    predicted_duration_seconds: float = 2.0
    duration_interval: str = "2–5s"
    blast_radius_score: float = 0.25
    affected_components: list[str] = Field(default_factory=list)
    reversibility: bool = True
    verification_difficulty: str = "LOW"  # LOW, MEDIUM, HIGH
    failure_probability: float = 0.1
    recovery_probability: float = 0.9
    confidence: float = 0.85
    uncertainty: UncertaintyLevel = UncertaintyLevel.LOW
    pareto_rank: int = 1
    is_recommended: bool = False
    rationale: str = ""


class RecoveryScenario(BaseModel):
    """Typed scenario representing a hypothetical fault, state, or recovery counterfactual."""

    model_config = ConfigDict(extra="ignore")

    scenario_id: str = Field(default_factory=lambda: f"scen_{uuid.uuid4().hex[:12]}")
    base_snapshot_id: str
    description: str
    hypothesis: str
    incident_id: str | None = None
    target_subsystem: str = "system"
    actions: list[dict[str, Any]] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    duration_seconds: float = 300.0
    resource_budget: dict[str, Any] = Field(default_factory=dict)
    simulation_mode: SimulationMode = SimulationMode.ANALYTICAL
    confidence: float = 0.85
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RecoverySimulationResult(BaseModel):
    """Complete output of a recovery simulation run across candidate strategies."""

    model_config = ConfigDict(extra="ignore")

    simulation_id: str = Field(default_factory=lambda: f"sim_{uuid.uuid4().hex[:12]}")
    scenario_id: str
    base_snapshot_id: str
    simulation_mode: SimulationMode = SimulationMode.ANALYTICAL
    environment_label: str = "SIMULATION_ONLY"
    predicted_final_state: dict[str, Any] = Field(default_factory=dict)
    predicted_events: list[dict[str, Any]] = Field(default_factory=list)
    predicted_resource_usage: dict[str, Any] = Field(default_factory=dict)
    predicted_risk: dict[str, Any] = Field(default_factory=dict)
    predicted_blast_radius: dict[str, Any] = Field(default_factory=dict)
    candidates: list[RecoveryCandidate] = Field(default_factory=list)
    recommended_candidate: RecoveryCandidate | None = None
    confidence: float = 0.85
    uncertainty: UncertaintyLevel = UncertaintyLevel.LOW
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    model_coverage: dict[str, str] = Field(
        default_factory=lambda: {
            "RUNTIME": "HIGH",
            "RESOURCE": "HIGH",
            "NETWORK": "MEDIUM",
            "EXTERNAL_SERVICE": "LOW",
            "USER_BEHAVIOR": "UNKNOWN",
        }
    )
    model_versions: dict[str, str] = Field(
        default_factory=lambda: {
            "causal_model": "1.2.0",
            "risk_model": "2.1.0",
            "forecast_model": "1.0.0",
            "resilience_engine": "1.0.0",
            "simulation_engine": "2.0.0",
        }
    )
    state_drift_detected: bool = False
    is_stale: bool = False
    duration_ms: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PredictionVsRealityRecord(BaseModel):
    """Forensic comparison record between simulation forecast and observed reality."""

    model_config = ConfigDict(extra="ignore")

    comparison_id: str = Field(default_factory=lambda: f"cmp_{uuid.uuid4().hex[:12]}")
    simulation_id: str
    recovery_id: str = ""
    strategy: str
    predicted_duration_seconds: float = 0.0
    actual_duration_seconds: float = 0.0
    duration_error: float = 0.0
    predicted_resource_cost: dict[str, Any] = Field(default_factory=dict)
    actual_resource_cost: dict[str, Any] = Field(default_factory=dict)
    resource_error: float = 0.0
    predicted_risk: float = 0.0
    actual_risk: float = 0.0
    risk_error: float = 0.0
    predicted_blast_radius: float = 0.0
    actual_blast_radius: float = 0.0
    blast_radius_error: float = 0.0
    verification_expected: bool = True
    verification_actual: bool = True
    verification_match: bool = True
    calibrated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RecoveryStrategyScorecard(BaseModel):
    """Historical performance scorecard for an autonomous recovery strategy."""

    model_config = ConfigDict(extra="ignore")

    strategy: str
    total_attempts: int = 0
    successful_recoveries: int = 0
    success_rate: float = 1.0
    failed_recoveries: int = 0
    failure_rate: float = 0.0
    median_duration_ms: float = 1500.0
    average_duration_ms: float = 1500.0
    verification_rate: float = 1.0
    average_resource_cost: dict[str, float] = Field(default_factory=dict)
    last_attempt_at: datetime | None = None
    status: str = "HEALTHY"  # HEALTHY, DEGRADED, UNSTABLE


class ResilienceBenchmark(BaseModel):
    """Empirical resilience benchmark measuring system-level MTTR, containment, and recovery."""

    model_config = ConfigDict(extra="ignore")

    benchmark_id: str = Field(default_factory=lambda: f"bmk_{uuid.uuid4().hex[:10]}")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    mttr_seconds: float = 3.2
    mtbf_hours: float = 168.0
    detection_latency_ms: float = 18.5
    selection_latency_ms: float = 24.0
    recovery_duration_seconds: float = 2.4
    verification_duration_seconds: float = 0.8
    resource_recovery_pct: float = 98.5
    average_blast_radius: float = 0.22
    failure_recurrence_rate: float = 0.02
    dimensions: dict[str, float] = Field(
        default_factory=lambda: {
            "detection": 0.95,
            "containment": 0.92,
            "recovery": 0.94,
            "verification": 0.98,
            "resource_stability": 0.91,
            "dependency_stability": 0.89,
            "recurrence": 0.96,
        }
    )
