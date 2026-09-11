"""Pydantic v2 schemas and enums for Kairo Autonomous Causal Discovery & World-Model Learning Engine (Task 73).

Strict Epistemic Invariants:
1. CORRELATION != CAUSAL_ASSOCIATION != CAUSAL_HYPOTHESIS != SUPPORTED_CAUSAL_RELATIONSHIP != VERIFIED_CAUSAL_RELATIONSHIP.
2. OBSERVATION != INTERVENTION (DO(X)) != EXPERIMENT != SIMULATION != PREDICTION != COUNTERFACTUAL != CAUSAL_CLAIM.
3. No silent promotion: 10 explicit states with validated state transitions.
4. Temporal precedence: cause must precede effect in time; surfaces contradictions.
5. Environmental and version scope isolation (e.g. Staging != Production, v4 != v5).
6. Mechanisms must not be fabricated; explicit mechanism status tracking.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class CausalRelationshipState(str, Enum):
    """The 10 explicit causal relationship lifecycle states (Task 73, Spec 4)."""

    CANDIDATE = "CANDIDATE"
    HYPOTHESIZED = "HYPOTHESIZED"
    SUPPORTED = "SUPPORTED"
    STRONGLY_SUPPORTED = "STRONGLY_SUPPORTED"
    VERIFIED = "VERIFIED"
    CONTRADICTED = "CONTRADICTED"
    INVALIDATED = "INVALIDATED"
    SUPERSEDED = "SUPERSEDED"
    CONTEXTUAL = "CONTEXTUAL"
    UNKNOWN = "UNKNOWN"


class EdgeRelationshipType(str, Enum):
    """Explicit graph edge classification (Task 73, Spec 5)."""

    RELATIONSHIP = "RELATIONSHIP"
    CORRELATION = "CORRELATION"
    CAUSAL = "CAUSAL"
    FEEDBACK_LOOP = "FEEDBACK_LOOP"


class EffectDirection(str, Enum):
    """Direction and form of the causal effect (Task 73, Spec 21)."""

    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NONLINEAR = "NONLINEAR"
    THRESHOLD = "THRESHOLD"
    MIXED = "MIXED"
    UNKNOWN = "UNKNOWN"


class MechanismStatus(str, Enum):
    """Evidence status of the causal mechanism (Task 73, Spec 6)."""

    OBSERVED = "OBSERVED"
    HYPOTHESIZED = "HYPOTHESIZED"
    SUPPORTED = "SUPPORTED"
    UNKNOWN = "UNKNOWN"


class CausalStrength(str, Enum):
    """Qualitative causal strength (Task 73, Spec 20)."""

    NEGLIGIBLE = "NEGLIGIBLE"
    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"


class ThresholdSegment(BaseModel):
    """Segment definition for threshold effects (Task 73, Spec 22)."""

    model_config = ConfigDict(extra="ignore")

    lower_bound: float | None = None
    upper_bound: float | None = None
    behavior: str  # e.g. "normal_latency", "increasing_latency", "severe_outage"
    description: str = ""
    impact_multiplier: float = 1.0


class EffectSize(BaseModel):
    """Quantitative measurement of causal effect without invented precision (Task 73, Spec 20)."""

    model_config = ConfigDict(extra="ignore")

    measurement: float
    unit: str
    method: str
    confidence_interval_low: float | None = None
    confidence_interval_high: float | None = None
    p_value: float | None = None


class ConfounderItem(BaseModel):
    """Confounder variable analysis (Task 73, Spec 11)."""

    model_config = ConfigDict(extra="ignore")

    variable: str
    entity: str
    relationship_to_cause: str
    relationship_to_effect: str
    evidence: list[str] = Field(default_factory=list)
    confidence: float = 0.5


class ConfounderAnalysis(BaseModel):
    """Result of confounder and common cause analysis (Task 73, Spec 11)."""

    model_config = ConfigDict(extra="ignore")

    candidate_confounders: list[ConfounderItem] = Field(default_factory=list)
    common_causes: list[str] = Field(default_factory=list)
    is_confounded: bool = False
    confidence_penalty: float = 0.0
    adjusted_confidence: float = 0.5
    recommendation: str = ""


class MediatorAnalysis(BaseModel):
    """Analysis of mediating variables in causal chains (Task 73, Spec 12)."""

    model_config = ConfigDict(extra="ignore")

    mediator_variables: list[str] = Field(default_factory=list)
    indirect_paths: list[list[str]] = Field(default_factory=list)
    is_mediated: bool = False
    mechanism_narrative: str = ""


class ColliderAnalysis(BaseModel):
    """Awareness of collider conditioning bias (Task 73, Spec 13)."""

    model_config = ConfigDict(extra="ignore")

    collider_variable: str | None = None
    cause_a: str | None = None
    cause_b: str | None = None
    is_conditioned: bool = False
    warning: str | None = None


class TemporalValidationResult(BaseModel):
    """Temporal precedence check and causal lag evaluation (Task 73, Spec 14, 15)."""

    model_config = ConfigDict(extra="ignore")

    is_temporally_valid: bool
    cause_time: datetime | None = None
    effect_time: datetime | None = None
    lag_seconds: float | None = None
    duration_seconds: float | None = None
    contradiction_detected: bool = False
    contradiction_reason: str | None = None


class CausalRelationship(BaseModel):
    """Core abstraction representing a discovered or hypothesized causal relationship (Task 73, Spec 3)."""

    model_config = ConfigDict(extra="ignore")

    causal_relation_id: str = Field(default_factory=lambda: f"crel_{uuid.uuid4().hex[:12]}")
    cause_entity: str
    cause_variable: str
    effect_entity: str
    effect_variable: str

    relationship_type: EdgeRelationshipType = EdgeRelationshipType.RELATIONSHIP
    direction: EffectDirection = EffectDirection.UNKNOWN
    mechanism: str = "UNKNOWN"
    mechanism_status: MechanismStatus = MechanismStatus.UNKNOWN

    conditions: dict[str, Any] = Field(default_factory=dict)
    scope: str = "SYSTEM"
    environment: str = "STAGING"  # e.g. STAGING, PRODUCTION, TEST
    software_version: str | None = None
    time_window: dict[str, Any] | None = None

    strength: CausalStrength = CausalStrength.MODERATE
    effect_size: EffectSize | None = None
    thresholds: list[ThresholdSegment] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    evidence_refs: list[str] = Field(default_factory=list)
    experiment_refs: list[str] = Field(default_factory=list)
    observation_refs: list[str] = Field(default_factory=list)
    counterfactual_refs: list[str] = Field(default_factory=list)
    verification_refs: list[str] = Field(default_factory=list)
    contradiction_refs: list[str] = Field(default_factory=list)
    falsification_criteria: list[str] = Field(default_factory=list)

    status: CausalRelationshipState = CausalRelationshipState.CANDIDATE
    model_version: int = 1
    previous_version_id: str | None = None
    change_reason: str | None = None

    created_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)
    provenance: dict[str, Any] = Field(default_factory=dict)


class InterventionRecord(BaseModel):
    """Record of a deliberate intervention DO(X = v) (Task 73, Spec 7, 8)."""

    model_config = ConfigDict(extra="ignore")

    intervention_id: str = Field(default_factory=lambda: f"intv_{uuid.uuid4().hex[:12]}")
    target: str  # Entity or variable intervened on
    previous_state: dict[str, Any] = Field(default_factory=dict)
    new_state: dict[str, Any] = Field(default_factory=dict)
    operator: str = "SYSTEM"
    experiment_id: str | None = None  # Link to Task 72 ExperimentDesign
    timestamp: datetime = Field(default_factory=_now_utc)
    environment: str = "STAGING"
    authorization: dict[str, Any] = Field(default_factory=dict)
    rollback_plan: dict[str, Any] = Field(default_factory=dict)
    observations: list[dict[str, Any]] = Field(default_factory=list)
    outcome: dict[str, Any] = Field(default_factory=dict)
    status: str = "COMPLETED"  # PROPOSED, EXECUTING, COMPLETED, ROLLED_BACK, FAILED
    is_controlled: bool = True
    provenance: dict[str, Any] = Field(default_factory=dict)


class CausalDriftReport(BaseModel):
    """Detection of drift in causal or world-model relationships (Task 73, Spec 47, 48)."""

    model_config = ConfigDict(extra="ignore")

    report_id: str = Field(default_factory=lambda: f"drift_{uuid.uuid4().hex[:12]}")
    drift_type: str = "CAUSAL_DRIFT"  # CAUSAL_DRIFT or WORLD_MODEL_DRIFT
    relation_id: str
    environment: str
    software_version: str | None = None
    expected_behavior: dict[str, Any] = Field(default_factory=dict)
    observed_behavior: dict[str, Any] = Field(default_factory=dict)
    prediction_error: float = 0.0
    status: str = "DETECTED"  # DETECTED, REVIEWING, MITIGATED, SUPERSEDED
    recommended_action: str = ""
    timestamp: datetime = Field(default_factory=_now_utc)


class CausalCandidateProposal(BaseModel):
    """Initial observation correlation proposed for causal investigation."""

    model_config = ConfigDict(extra="ignore")

    cause_entity: str
    cause_variable: str
    effect_entity: str
    effect_variable: str
    observed_correlation: float = 0.5
    sample_size: int = 10
    environment: str = "STAGING"
    observations: list[dict[str, Any]] = Field(default_factory=list)
    software_version: str | None = None


class CausalQuestionType(str, Enum):
    """Supported causal question types (Task 73, Spec 34)."""

    WHAT_CAUSED_X = "WHAT_CAUSED_X"
    WHAT_AFFECTS_Y = "WHAT_AFFECTS_Y"
    WHAT_WOULD_HAPPEN_IF_X = "WHAT_WOULD_HAPPEN_IF_X"
    WHAT_FACTORS_MEDIATE_Y = "WHAT_FACTORS_MEDIATE_Y"
    WHAT_FACTORS_CONFOUND = "WHAT_FACTORS_CONFOUND"
    WHAT_SHOULD_WE_INTERVENE_ON = "WHAT_SHOULD_WE_INTERVENE_ON"
    WHICH_CAUSE_STRONGEST = "WHICH_CAUSE_STRONGEST"
    WHAT_WOULD_DISPROVE = "WHAT_WOULD_DISPROVE"


class CausalQuestionRequest(BaseModel):
    """Request structure for the Causal Question Engine (Task 73, Spec 34)."""

    model_config = ConfigDict(extra="ignore")

    question_type: CausalQuestionType
    entity: str
    variable: str | None = None
    target_value: Any | None = None
    comparison_entity: str | None = None
    comparison_variable: str | None = None
    environment: str = "STAGING"


class CausalQuestionResponse(BaseModel):
    """Structured response from the Causal Question Engine."""

    model_config = ConfigDict(extra="ignore")

    question_type: CausalQuestionType
    query: str
    answer: str
    candidate_causes: list[dict[str, Any]] = Field(default_factory=list)
    supporting_evidence: list[str] = Field(default_factory=list)
    confidence: float = 0.5
    falsification_criteria: list[str] = Field(default_factory=list)
    scope: str = "SYSTEM"
    environment: str = "STAGING"
    uncertainty: str = ""
    suggested_experiments: list[dict[str, Any]] = Field(default_factory=list)


class CausalQualityMetrics(BaseModel):
    """Quality and telemetry metrics for the causal world model (Task 73, Spec 50)."""

    model_config = ConfigDict(extra="ignore")

    causal_relationship_count: int = 0
    verified_relationships: int = 0
    hypothesized_relationships: int = 0
    invalidated_relationships: int = 0
    conflicted_relationships: int = 0
    replication_rate: float = 0.0
    prediction_accuracy: float = 0.0
    causal_drift_count: int = 0
    model_revision_rate: float = 0.0
    unexplained_outcomes: int = 0
