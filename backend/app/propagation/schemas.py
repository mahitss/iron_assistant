"""Pydantic v2 schemas and enums for Kairo Autonomous Risk Propagation & Cascade Engine (Task 75)."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


def generate_uuid() -> str:
    return str(uuid.uuid4())


# =====================================================================
# ENUMS
# =====================================================================

class PropagationScope(str, Enum):
    SERVICE = "SERVICE"
    INFRASTRUCTURE = "INFRASTRUCTURE"
    PROJECT = "PROJECT"
    WORKFLOW = "WORKFLOW"
    TASK = "TASK"
    RESOURCE = "RESOURCE"
    SCHEDULE = "SCHEDULE"
    KNOWLEDGE = "KNOWLEDGE"
    CONCEPTUAL = "CONCEPTUAL"


class TriggerType(str, Enum):
    STATE_CHANGE = "STATE_CHANGE"
    FAILURE = "FAILURE"
    PERFORMANCE_DEGRADATION = "PERFORMANCE_DEGRADATION"
    FORECAST = "FORECAST"
    INCIDENT = "INCIDENT"
    RESOURCE_DEPLETION = "RESOURCE_DEPLETION"
    EXTERNAL_EVENT = "EXTERNAL_EVENT"
    RECOVERY = "RECOVERY"


class EpistemicCategory(str, Enum):
    """Explicitly distinguish relationship and finding epistemic status (Spec 1)."""
    OBSERVED_RELATIONSHIP = "OBSERVED_RELATIONSHIP"
    CAUSAL_RELATIONSHIP = "CAUSAL_RELATIONSHIP"
    DEPENDENCY = "DEPENDENCY"
    CORRELATION = "CORRELATION"
    HYPOTHESIS = "HYPOTHESIS"
    SIMULATION_RESULT = "SIMULATION_RESULT"
    FORECAST = "FORECAST"
    ACTUAL_OUTCOME = "ACTUAL_OUTCOME"


class RelationshipType(str, Enum):
    """Explicit relationship semantics across technical, task, and conceptual domains (Spec 5)."""
    DEPENDS_ON = "DEPENDS_ON"
    CAUSES = "CAUSES"
    INFLUENCES = "INFLUENCES"
    ENABLES = "ENABLES"
    BLOCKS = "BLOCKS"
    AMPLIFIES = "AMPLIFIES"
    SUPPRESSES = "SUPPRESSES"
    CORRELATES_WITH = "CORRELATES_WITH"
    PRECEDES = "PRECEDES"
    TRIGGERS = "TRIGGERS"
    CONSTRAINS = "CONSTRAINS"
    REQUIRES = "REQUIRES"
    OPTIONALLY_REQUIRES = "OPTIONALLY_REQUIRES"
    SHARES_RESOURCE = "SHARES_RESOURCE"
    SHARES_FAILURE_DOMAIN = "SHARES_FAILURE_DOMAIN"


class RedundancyState(str, Enum):
    """Explicit redundancy classification (Spec 15)."""
    REDUNDANCY_UNKNOWN = "REDUNDANCY_UNKNOWN"
    NONE = "NONE"
    PARTIAL = "PARTIAL"
    FULL = "FULL"


class FeedbackType(str, Enum):
    """Cycle / loop classification (Spec 28)."""
    STABILIZING_FEEDBACK = "STABILIZING_FEEDBACK"
    AMPLIFYING_FEEDBACK = "AMPLIFYING_FEEDBACK"
    UNKNOWN_FEEDBACK = "UNKNOWN_FEEDBACK"


class CascadeType(str, Enum):
    """Conceptual cascade categories (Spec 12)."""
    DEPENDENCY_CASCADE = "DEPENDENCY_CASCADE"
    RESOURCE_CASCADE = "RESOURCE_CASCADE"
    FAILURE_CASCADE = "FAILURE_CASCADE"
    INFORMATION_CASCADE = "INFORMATION_CASCADE"
    SCHEDULE_CASCADE = "SCHEDULE_CASCADE"
    CAPACITY_CASCADE = "CAPACITY_CASCADE"
    SECURITY_CASCADE = "SECURITY_CASCADE"
    DECISION_CASCADE = "DECISION_CASCADE"
    FEEDBACK_CASCADE = "FEEDBACK_CASCADE"


class CascadeStatus(str, Enum):
    """10-state validated cascade lifecycle (Spec 58)."""
    DISCOVERED = "DISCOVERED"
    ANALYZING = "ANALYZING"
    PROJECTED = "PROJECTED"
    MONITORING = "MONITORING"
    CONFIRMED = "CONFIRMED"
    CONTAINED = "CONTAINED"
    RECOVERING = "RECOVERING"
    RESOLVED = "RESOLVED"
    INVALIDATED = "INVALIDATED"
    EXPIRED = "EXPIRED"


class CriticalityLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class BoundaryType(str, Enum):
    CIRCUIT_BREAKER = "CIRCUIT_BREAKER"
    ISOLATION_ZONE = "ISOLATION_ZONE"
    RESOURCE_POOL = "RESOURCE_POOL"
    WORKFLOW_GATE = "WORKFLOW_GATE"
    RATE_LIMIT = "RATE_LIMIT"
    HUMAN_APPROVAL = "HUMAN_APPROVAL"


class SubstitutabilityLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NONE = "NONE"


class ReversibilityLevel(str, Enum):
    EASY = "EASY"
    MODERATE = "MODERATE"
    DIFFICULT = "DIFFICULT"
    IRREVERSIBLE = "IRREVERSIBLE"


# =====================================================================
# CORE SCHEMAS
# =====================================================================

class ImpactDimensions(BaseModel):
    """Multi-dimensional systemic impact propagation (Spec 17, 18).
    
    Never collapse immediately into a single number.
    """
    model_config = ConfigDict(extra="ignore")

    operational_impact: float = Field(0.0, ge=0.0, le=1.0, description="Service or operational degradation severity")
    resource_impact: float = Field(0.0, ge=0.0, le=1.0, description="Resource depletion / saturation fraction")
    schedule_impact_seconds: float = Field(0.0, ge=0.0, description="Projected schedule delay in seconds")
    reliability_impact: float = Field(0.0, ge=0.0, le=1.0, description="System availability / MTBF impact")
    security_impact: float = Field(0.0, ge=0.0, le=1.0, description="Security boundary or isolation breach risk")
    financial_impact: Optional[float] = Field(None, ge=0.0, description="Empirical loss in currency, only if data exists")
    user_impact: float = Field(0.0, ge=0.0, le=1.0, description="End-user experience degradation")
    strategic_impact: float = Field(0.0, ge=0.0, le=1.0, description="Long-term goal / milestone impairment")

    def composite_severity(self) -> float:
        """Weighted non-financial severity index."""
        weights = [0.25, 0.15, 0.15, 0.15, 0.10, 0.10, 0.10]
        values = [
            self.operational_impact,
            self.resource_impact,
            min(1.0, self.schedule_impact_seconds / 86400.0),
            self.reliability_impact,
            self.security_impact,
            self.user_impact,
            self.strategic_impact,
        ]
        return round(sum(w * v for w, v in zip(weights, values)), 3)


class TemporalDelay(BaseModel):
    """Temporal characteristics of edge or cascade step (Spec 19)."""
    model_config = ConfigDict(extra="ignore")

    expected_delay_seconds: float = Field(0.0, ge=0.0)
    min_delay_seconds: float = Field(0.0, ge=0.0)
    max_delay_seconds: float = Field(0.0, ge=0.0)
    is_known: bool = Field(True)


class UncertaintyBreakdown(BaseModel):
    """Decomposed uncertainty for explainable propagation (Spec 27)."""
    model_config = ConfigDict(extra="ignore")

    epistemic_uncertainty: float = Field(0.1, ge=0.0, le=1.0, description="Graph or causal parameter uncertainty")
    aleatoric_uncertainty: float = Field(0.05, ge=0.0, le=1.0, description="Inherent system stochasticity")
    depth_penalty: float = Field(0.0, ge=0.0, le=1.0, description="Uncertainty accumulation over traversal depth")
    missing_edge_penalty: float = Field(0.0, ge=0.0, le=1.0, description="Penalty for unmonitored / incomplete graph")
    model_disagreement_variance: float = Field(0.0, ge=0.0, le=1.0, description="Variance across multiple forecasting models")
    composite_uncertainty: float = Field(0.15, ge=0.0, le=1.0)


class PropagationEdge(BaseModel):
    """Semantic graph edge with explicit evidence, provenance, and temporal validity (Spec 5, 49)."""
    model_config = ConfigDict(extra="ignore")

    edge_id: str = Field(default_factory=generate_uuid)
    source_entity: str
    target_entity: str
    relationship_type: RelationshipType
    epistemic_category: EpistemicCategory = EpistemicCategory.DEPENDENCY
    direction: str = "DIRECTED"
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    provenance: Dict[str, Any] = Field(default_factory=dict)
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    source: str = "knowledge_graph"
    discovery_method: str = "architectural_topology"
    redundancy_state: RedundancyState = RedundancyState.REDUNDANCY_UNKNOWN
    redundancy_alternatives: List[str] = Field(default_factory=list)
    temporal_delay: TemporalDelay = Field(default_factory=TemporalDelay)
    is_disputed: bool = False
    dispute_reason: Optional[str] = None


class GraphSnapshotReference(BaseModel):
    """Frozen graph version for auditability and zero-leakage backtesting (Spec 6, 62)."""
    model_config = ConfigDict(extra="ignore")

    snapshot_id: str = Field(default_factory=generate_uuid)
    graph_version: int = 1
    snapshot_timestamp: datetime = Field(default_factory=utc_now)
    node_count: int = 0
    edge_count: int = 0
    source_references: List[str] = Field(default_factory=list)


class DirectEffect(BaseModel):
    """Direct (Depth 1) effect from trigger entity (Spec 8)."""
    model_config = ConfigDict(extra="ignore")

    target_entity: str
    relationship_type: RelationshipType
    epistemic_category: EpistemicCategory
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    expected_direction: str = "DEGRADATION"
    expected_magnitude: Optional[float] = None
    impact: ImpactDimensions = Field(default_factory=ImpactDimensions)
    temporal_delay: TemporalDelay = Field(default_factory=TemporalDelay)
    uncertainty: float = Field(0.1, ge=0.0, le=1.0)
    evidence: List[Dict[str, Any]] = Field(default_factory=list)


class SecondOrderEffect(BaseModel):
    """Second-order (Depth 2) indirect effect (Spec 9)."""
    model_config = ConfigDict(extra="ignore")

    intermediate_entity: str
    target_entity: str
    path: List[str] = Field(default_factory=list)
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    explanation: str
    temporal_delay: TemporalDelay = Field(default_factory=TemporalDelay)
    uncertainty: float = Field(0.2, ge=0.0, le=1.0)


class CascadeChain(BaseModel):
    """Ordered chain of dependent consequences (Spec 11, 12)."""
    model_config = ConfigDict(extra="ignore")

    chain_id: str = Field(default_factory=generate_uuid)
    cascade_type: CascadeType
    nodes: List[str] = Field(default_factory=list)
    edges: List[Dict[str, Any]] = Field(default_factory=list)
    total_depth: int = 0
    cumulative_delay_seconds: float = 0.0
    amplification_detected: bool = False
    feedback_type: FeedbackType = FeedbackType.STABILIZING_FEEDBACK
    likelihood: float = Field(0.5, ge=0.0, le=1.0)
    impact: ImpactDimensions = Field(default_factory=ImpactDimensions)
    fingerprint: str = ""
    status: CascadeStatus = CascadeStatus.DISCOVERED


class BottleneckNode(BaseModel):
    """Disproportionately important node in system topology (Spec 13)."""
    model_config = ConfigDict(extra="ignore")

    entity_id: str
    name: str = ""
    downstream_reach: int = 0
    dependency_count: int = 0
    centrality_score: float = 0.0
    critical_path_participant: bool = False
    resource_contention_index: float = 0.0
    failure_propagation_potential: float = 0.0
    spof_criticality: CriticalityLevel = CriticalityLevel.LOW
    redundancy_state: RedundancyState = RedundancyState.REDUNDANCY_UNKNOWN
    substitutes: List[str] = Field(default_factory=list)


class SinglePointOfFailure(BaseModel):
    """Single Point of Failure assessment (Spec 14)."""
    model_config = ConfigDict(extra="ignore")

    entity_id: str
    criticality: CriticalityLevel = CriticalityLevel.MEDIUM
    dependent_count: int = 0
    downstream_nodes: List[str] = Field(default_factory=list)
    redundancy_state: RedundancyState = RedundancyState.NONE
    recovery_options: List[str] = Field(default_factory=list)
    substitutability: SubstitutabilityLevel = SubstitutabilityLevel.NONE
    reversibility: ReversibilityLevel = ReversibilityLevel.MODERATE


class ContainmentBoundary(BaseModel):
    """System barrier that can halt propagation (Spec 30)."""
    model_config = ConfigDict(extra="ignore")

    boundary_id: str = Field(default_factory=generate_uuid)
    entity_id: str
    boundary_type: BoundaryType
    effectiveness_estimate: float = Field(0.8, ge=0.0, le=1.0)
    is_active: bool = True
    description: str = ""


class MitigationRecommendation(BaseModel):
    """Advisory-only intervention candidate (Spec 31, 71)."""
    model_config = ConfigDict(extra="ignore")

    recommendation_id: str = Field(default_factory=generate_uuid)
    action_type: str
    target_entity: str
    description: str
    expected_risk_reduction: float = Field(0.5, ge=0.0, le=1.0)
    estimated_effort: str = "MEDIUM"
    requires_approval: bool = True
    is_advisory_only: bool = True


class ResilienceAssessment(BaseModel):
    """Systemic resilience model findings (Spec 16)."""
    model_config = ConfigDict(extra="ignore")

    systemic_resilience_score: float = Field(0.5, ge=0.0, le=1.0)
    redundancy_ratio: float = Field(0.0, ge=0.0, le=1.0)
    bottleneck_concentration: float = Field(0.0, ge=0.0, le=1.0)
    max_dependency_depth: int = 0
    coupling_density: float = Field(0.0, ge=0.0, le=1.0)
    containment_boundaries: List[ContainmentBoundary] = Field(default_factory=list)
    recovery_speed_estimate: str = "MODERATE"
    findings: List[str] = Field(default_factory=list)


class PropagationAnalysis(BaseModel):
    """Master domain model for systemic propagation analysis (Spec 4)."""
    model_config = ConfigDict(extra="ignore")

    propagation_id: str = Field(default_factory=generate_uuid)
    tenant_id: str = "default_tenant"
    scope: PropagationScope = PropagationScope.SERVICE
    trigger: str
    trigger_type: TriggerType = TriggerType.STATE_CHANGE
    origin_entity: str
    origin_state: Dict[str, Any] = Field(default_factory=dict)
    origin_event: Optional[Dict[str, Any]] = None
    origin_forecast: Optional[Dict[str, Any]] = None
    graph_snapshot: GraphSnapshotReference = Field(default_factory=GraphSnapshotReference)
    causal_model_reference: Optional[str] = None
    world_state_reference: Optional[str] = None
    analysis_time: datetime = Field(default_factory=utc_now)
    horizon: str = "MEDIUM"
    propagation_depth: int = 0
    confidence: float = Field(0.8, ge=0.0, le=1.0)
    uncertainty: UncertaintyBreakdown = Field(default_factory=UncertaintyBreakdown)
    assumptions: List[str] = Field(default_factory=list)
    status: CascadeStatus = CascadeStatus.DISCOVERED
    direct_effects: List[DirectEffect] = Field(default_factory=list)
    second_order_effects: List[SecondOrderEffect] = Field(default_factory=list)
    cascades: List[CascadeChain] = Field(default_factory=list)
    bottlenecks: List[BottleneckNode] = Field(default_factory=list)
    single_points_of_failure: List[SinglePointOfFailure] = Field(default_factory=list)
    resilience_assessment: ResilienceAssessment = Field(default_factory=ResilienceAssessment)
    containment_options: List[ContainmentBoundary] = Field(default_factory=list)
    mitigation_candidates: List[MitigationRecommendation] = Field(default_factory=list)
    fingerprint: str = ""
    provenance: Dict[str, Any] = Field(default_factory=dict)
    is_truncated: bool = False
    truncation_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


# =====================================================================
# EVALUATION & BACKTEST SCHEMAS
# =====================================================================

class CascadeEvaluation(BaseModel):
    """Post-window evaluation comparing predicted vs actual cascade (Spec 59, 60)."""
    model_config = ConfigDict(extra="ignore")

    evaluation_id: str = Field(default_factory=generate_uuid)
    propagation_id: str
    target_origin: str
    predicted_nodes: List[str] = Field(default_factory=list)
    actual_nodes: List[str] = Field(default_factory=list)
    missed_nodes: List[str] = Field(default_factory=list)
    false_nodes: List[str] = Field(default_factory=list)
    node_precision: float = 1.0
    node_recall: float = 1.0
    path_precision: float = 1.0
    path_recall: float = 1.0
    depth_error: int = 0
    timing_error_seconds: float = 0.0
    impact_estimation_error: float = 0.0
    warning_lead_time_seconds: float = 0.0
    false_positive: bool = False
    evaluated_at: datetime = Field(default_factory=utc_now)


class BacktestReport(BaseModel):
    """Zero-leakage historical backtesting report (Spec 61, 62)."""
    model_config = ConfigDict(extra="ignore")

    backtest_id: str = Field(default_factory=generate_uuid)
    start_timestamp: datetime
    end_timestamp: datetime
    historical_snapshot_id: str
    total_triggers_evaluated: int = 0
    mean_node_precision: float = 0.0
    mean_node_recall: float = 0.0
    mean_lead_time_seconds: float = 0.0
    false_positive_rate: float = 0.0
    zero_future_leakage_verified: bool = True
    evaluations: List[CascadeEvaluation] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
