"""Pydantic v2 schemas and enums for Kairo Causal Reasoning & Causal Graph Engine (Task 55)."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CausalScope(str, Enum):
    EVENT = "EVENT"
    TASK = "TASK"
    SERVICE = "SERVICE"
    PROJECT = "PROJECT"
    ENVIRONMENT = "ENVIRONMENT"
    SYSTEM = "SYSTEM"


class CausalRelationshipType(str, Enum):
    CAUSES = "CAUSES"
    CONTRIBUTES_TO = "CONTRIBUTES_TO"
    ENABLES = "ENABLES"
    PREVENTS = "PREVENTS"
    MEDIATES = "MEDIATES"
    MODERATES = "MODERATES"
    DEPENDS_ON = "DEPENDS_ON"
    CORRELATES_WITH = "CORRELATES_WITH"
    TEMPORALLY_PRECEDES = "TEMPORALLY_PRECEDES"
    UNKNOWN = "UNKNOWN"


class HypothesisStatus(str, Enum):
    PROPOSED = "PROPOSED"
    SUPPORTED = "SUPPORTED"
    WEAKLY_SUPPORTED = "WEAKLY_SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    UNKNOWN = "UNKNOWN"


class EvidenceType(str, Enum):
    OBSERVATION = "OBSERVATION"
    TELEMETRY = "TELEMETRY"
    LOG = "LOG"
    TRACE = "TRACE"
    CONFIGURATION = "CONFIGURATION"
    DEPENDENCY = "DEPENDENCY"
    EXPERIMENT = "EXPERIMENT"
    INTERVENTION = "INTERVENTION"
    HISTORICAL_PATTERN = "HISTORICAL_PATTERN"
    USER_REPORT = "USER_REPORT"
    VERIFICATION = "VERIFICATION"


class EvidenceStrength(str, Enum):
    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"
    CRITICAL = "CRITICAL"


class RootCauseStatus(str, Enum):
    INVESTIGATING = "INVESTIGATING"
    LIKELY = "LIKELY"
    SUPPORTED = "SUPPORTED"
    VERIFIED = "VERIFIED"
    UNKNOWN = "UNKNOWN"


class InterventionType(str, Enum):
    CONFIG_CHANGE = "CONFIG_CHANGE"
    TRAFFIC_CHANGE = "TRAFFIC_CHANGE"
    SERVICE_RESTART = "SERVICE_RESTART"
    ROLLBACK = "ROLLBACK"
    FEATURE_TOGGLE = "FEATURE_TOGGLE"
    RESOURCE_CHANGE = "RESOURCE_CHANGE"
    DEPENDENCY_CHANGE = "DEPENDENCY_CHANGE"
    OTHER_AUTHORIZED_ACTION = "OTHER_AUTHORIZED_ACTION"


class VerificationStatus(str, Enum):
    UNTESTED = "UNTESTED"
    PARTIALLY_TESTED = "PARTIALLY_TESTED"
    SUPPORTED = "SUPPORTED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class CausalEdgeStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    ACTIVE = "ACTIVE"
    WEAKENED = "WEAKENED"
    SUPERSEDED = "SUPERSEDED"
    REJECTED = "REJECTED"


class FallacyType(str, Enum):
    POST_HOC = "POST_HOC"
    COMMON_CAUSE = "COMMON_CAUSE"
    SELECTION_BIAS = "SELECTION_BIAS"
    CONFOUNDING = "CONFOUNDING"
    REVERSE_CAUSALITY = "REVERSE_CAUSALITY"
    COLLIDER_BIAS = "COLLIDER_BIAS"
    OVERFITTING = "OVERFITTING"


# Schemas
class CausalNode(BaseModel):
    model_config = ConfigDict(extra="ignore")

    node_id: str
    entity: str
    variable: str
    state: Any
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str
    confidence: float = 1.0


class CausalEdge(BaseModel):
    model_config = ConfigDict(extra="ignore")

    edge_id: str
    cause: str
    effect: str
    relationship: CausalRelationshipType = CausalRelationshipType.CAUSES
    confidence: float = 0.5
    evidence_refs: list[str] = Field(default_factory=list)
    scope: CausalScope = CausalScope.SYSTEM
    valid_from: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    valid_until: datetime | None = None
    status: CausalEdgeStatus = CausalEdgeStatus.CANDIDATE


class CausalEvidence(BaseModel):
    model_config = ConfigDict(extra="ignore")

    evidence_id: str
    type: EvidenceType
    source: str
    observation: dict[str, Any] = Field(default_factory=dict)
    strength: EvidenceStrength = EvidenceStrength.MODERATE
    independence: float = 1.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CausalHypothesis(BaseModel):
    model_config = ConfigDict(extra="ignore")

    hypothesis_id: str
    cause: str
    effect: str
    mechanism: str
    evidence: list[CausalEvidence] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)
    confidence: float = 0.5
    status: HypothesisStatus = HypothesisStatus.PROPOSED


class RootCauseChain(BaseModel):
    model_config = ConfigDict(extra="ignore")

    underlying_condition: str | None = None
    trigger: str | None = None
    mechanism: str | None = None
    intermediate_state: str | None = None
    symptom: str | None = None
    impact: str | None = None


class RootCauseAnalysis(BaseModel):
    model_config = ConfigDict(extra="ignore")

    analysis_id: str
    incident_id: str
    candidate_causes: list[str] = Field(default_factory=list)
    evidence: list[CausalEvidence] = Field(default_factory=list)
    eliminated_causes: list[dict[str, Any]] = Field(default_factory=list)
    surviving_causes: list[str] = Field(default_factory=list)
    root_cause: str | None = None
    contributing_factors: list[str] = Field(default_factory=list)
    causal_chain: RootCauseChain | None = None
    is_necessary: bool = False
    is_sufficient: bool = False
    confidence: float = 0.5
    status: RootCauseStatus = RootCauseStatus.INVESTIGATING


class Intervention(BaseModel):
    model_config = ConfigDict(extra="ignore")

    intervention_id: str
    target: str
    change: dict[str, Any] = Field(default_factory=dict)
    intervention_type: InterventionType = InterventionType.OTHER_AUTHORIZED_ACTION
    expected_effect: dict[str, Any] = Field(default_factory=dict)
    actual_effect: dict[str, Any] | None = None
    authorization: dict[str, Any] = Field(default_factory=dict)
    risk: str = "MEDIUM"
    verification_plan: list[str] = Field(default_factory=list)
    status: str = "PROPOSED"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CounterfactualScenario(BaseModel):
    model_config = ConfigDict(extra="ignore")

    scenario_id: str
    baseline: dict[str, Any] = Field(default_factory=dict)
    intervention: dict[str, Any] = Field(default_factory=dict)
    expected_difference: dict[str, Any] = Field(default_factory=dict)
    assumptions: list[str] = Field(default_factory=list)
    confidence: float = 0.5
    is_hypothetical: bool = True  # Prompt #65: Clearly label hypothetical conclusions
    status: str = "GENERATED"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CausalExperiment(BaseModel):
    model_config = ConfigDict(extra="ignore")

    experiment_id: str
    hypothesis_id: str
    treatment: dict[str, Any] = Field(default_factory=dict)
    control: dict[str, Any] = Field(default_factory=dict)
    metric: str
    duration_seconds: int = 300
    authorization: dict[str, Any] = Field(default_factory=dict)
    status: str = "PENDING_APPROVAL"
    result: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CausalExplanation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    incident: str
    what_happened: str
    why_it_likely_happened: str
    evidence_summary: list[str] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)
    uncertainty: str
    suggested_testing: list[str] = Field(default_factory=list)
    confidence: str = "MEDIUM"
    is_verified: bool = False


class FallacyDetectionResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    has_fallacy: bool = False
    fallacies: list[FallacyType] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    recommendation: str | None = None


class CausalGraph(BaseModel):
    model_config = ConfigDict(extra="ignore")

    graph_id: str
    scope: CausalScope = CausalScope.SYSTEM
    scope_id: str | None = None
    version: int = 1
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    nodes: dict[str, CausalNode] = Field(default_factory=dict)
    edges: dict[str, CausalEdge] = Field(default_factory=dict)
    confidence: float = 1.0
    provenance: dict[str, Any] = Field(default_factory=dict)
