"""Pydantic schemas for Task 115:
Kairo Autonomous Hypothesis Management, Competing Explanations, Evidence Update, Falsification & Uncertainty Resolution Engine.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.hypothesis.domain import (
    EvidenceIndependence,
    EvidenceType,
    HypothesisRelationshipType,
    SupportVerdict,
)


class HypothesisClaimSchema(BaseModel):
    claim_id: Optional[str] = None
    subject: str = ""
    predicate: str = ""
    object_value: Any = None
    qualifier: str = ""
    target_metric: Optional[str] = None
    expected_direction: Optional[str] = None


class HypothesisScopeSchema(BaseModel):
    entity_ids: List[str] = Field(default_factory=list)
    subsystems: List[str] = Field(default_factory=list)
    time_window_start: Optional[datetime] = None
    time_window_end: Optional[datetime] = None
    environment: str = "production"
    context_keys: Dict[str, Any] = Field(default_factory=dict)


class HypothesisFalsificationConditionSchema(BaseModel):
    condition_id: Optional[str] = None
    description: str
    required_observations: List[str] = Field(default_factory=list)
    metric_thresholds: Dict[str, Any] = Field(default_factory=dict)
    contradiction_signals: List[str] = Field(default_factory=list)
    is_falsified: bool = False
    falsification_evidence_ids: List[str] = Field(default_factory=list)
    falsification_reasoning: Optional[str] = None


class HypothesisPredictionSchema(BaseModel):
    prediction_id: Optional[str] = None
    predicted_event: str
    predicted_state: Dict[str, Any] = Field(default_factory=dict)
    expected_metric: Optional[str] = None
    expected_value_range: Optional[List[float]] = None
    expected_timing_seconds: float = 0.0
    validity_window_start: Optional[datetime] = None
    validity_window_end: Optional[datetime] = None
    uncertainty_range: float = 0.1
    source_model: str = "causal_model"
    observed_outcome: Optional[Any] = None
    outcome_status: str = "PENDING"
    failure_notes: Optional[str] = None


class HypothesisEvidenceItemSchema(BaseModel):
    evidence_id: Optional[str] = None
    source: str
    source_type: str = "system"
    source_agent_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    observation_time: Optional[datetime] = None
    scope: Optional[HypothesisScopeSchema] = None
    provenance: str = ""
    parent_evidence_ids: List[str] = Field(default_factory=list)
    independence: EvidenceIndependence = EvidenceIndependence.INDEPENDENT
    freshness_seconds: float = 0.0
    reliability_score: float = 1.0
    direct_status: bool = True
    evidence_type: EvidenceType = EvidenceType.OBSERVATION
    payload: Dict[str, Any] = Field(default_factory=dict)
    is_simulation: bool = False
    is_counterfactual: bool = False


class HypothesisEvidenceAssessmentSchema(BaseModel):
    assessment_id: Optional[str] = None
    hypothesis_id: str
    evidence_id: str
    verdict: SupportVerdict = SupportVerdict.NEUTRAL
    reasoning_basis: str
    confidence: float = 0.5
    temporal_fit: float = 0.5
    causal_fit: float = 0.5
    independence: EvidenceIndependence = EvidenceIndependence.INDEPENDENT
    model_version: str = "v1.0"
    assessed_at: Optional[datetime] = None


class HypothesisConfidenceProfileSchema(BaseModel):
    evidence_strength: float = 0.0
    evidence_independence: float = 0.0
    temporal_consistency: float = 0.5
    mechanism_plausibility: float = 0.5
    causal_support: float = 0.5
    predictive_success: float = 0.5
    counterfactual_support: float = 0.0
    contradiction_score: float = 0.0
    source_reliability: float = 0.8
    completeness: float = 0.3
    uncertainty: float = 0.7
    historical_consistency: float = 0.5
    viability_score: float = 0.5


class HypothesisDiscriminatorSchema(BaseModel):
    discriminator_id: Optional[str] = None
    target_metric_or_signal: str
    hypothesis_predictions: Dict[str, str] = Field(default_factory=dict)
    observation_channel: str = ""
    information_value: float = 0.5
    estimated_cost: float = 0.1
    latency_seconds: float = 1.0
    risk_level: str = "LOW"
    rationale: str = ""
    task_114_observation_id: Optional[str] = None


class HypothesisRelationshipSchema(BaseModel):
    relationship_id: Optional[str] = None
    source_hypothesis_id: str
    target_hypothesis_id: str
    relationship_type: HypothesisRelationshipType = HypothesisRelationshipType.ALTERNATIVE_TO
    rationale: str = ""
    confidence: float = 0.7


class HypothesisConflictSchema(BaseModel):
    conflict_id: Optional[str] = None
    hypothesis_a_id: str
    hypothesis_b_id: str
    conflicting_property: str
    evidence_ids: List[str] = Field(default_factory=list)
    detected_at: Optional[datetime] = None
    resolution_state: str = "UNRESOLVED"
    notes: Optional[str] = None


class HypothesisResponseSchema(BaseModel):
    hypothesis_id: str
    set_id: str
    version: int
    statement: str
    claim: HypothesisClaimSchema
    scope: HypothesisScopeSchema
    status: str
    provenance: str
    proposer_agent_id: Optional[str] = None
    is_unknown_hypothesis: bool
    mechanism_summary: str
    causal_node_refs: List[str]
    assumptions: List[str]
    falsification_conditions: List[HypothesisFalsificationConditionSchema]
    predictions: List[HypothesisPredictionSchema]
    confidence_profile: HypothesisConfidenceProfileSchema
    assessments: List[HypothesisEvidenceAssessmentSchema]
    supporting_evidence_ids: List[str]
    contradicting_evidence_ids: List[str]
    falsifying_evidence_ids: List[str]
    parent_hypothesis_ids: List[str]
    child_hypothesis_ids: List[str]
    superseded_by_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    stale_at: Optional[str] = None
    staleness_reason: Optional[str] = None
    contradiction_search_performed: bool
    bias_guard_triggers: List[str]


class HypothesisSetResponseSchema(BaseModel):
    set_id: str
    version: int
    target_description: str
    target_incident_id: Optional[str] = None
    scope: HypothesisScopeSchema
    active_hypothesis_ids: List[str]
    rejected_hypothesis_ids: List[str]
    unknown_hypothesis_id: Optional[str] = None
    unresolved_conflicts: List[HypothesisConflictSchema]
    relationships: List[HypothesisRelationshipSchema]
    discriminators: List[HypothesisDiscriminatorSchema]
    information_gaps: List[str]
    is_resolved: bool
    resolution_summary: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class CreateHypothesisSetRequest(BaseModel):
    target_description: str
    target_incident_id: Optional[str] = None
    scope: Optional[HypothesisScopeSchema] = None
    candidate_explanations: Optional[List[Dict[str, Any]]] = None


class CreateHypothesisRequest(BaseModel):
    set_id: str
    statement: str
    claim: Optional[HypothesisClaimSchema] = None
    provenance: str = "AGENT_PROVIDED"
    proposer_agent_id: Optional[str] = None
    mechanism_summary: str = ""
    causal_node_refs: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    falsification_conditions: List[HypothesisFalsificationConditionSchema] = Field(default_factory=list)
    predictions: List[HypothesisPredictionSchema] = Field(default_factory=list)


class AttachEvidenceRequest(BaseModel):
    source: str
    source_type: str = "system"
    source_agent_id: Optional[str] = None
    evidence_type: str = "OBSERVATION"
    parent_evidence_ids: List[str] = Field(default_factory=list)
    payload: Dict[str, Any]
    reliability_score: float = 1.0
    direct_status: bool = True
    is_simulation: bool = False
    is_counterfactual: bool = False


class SplitHypothesisRequest(BaseModel):
    parent_hypothesis_id: str
    child_specs: List[Dict[str, Any]]


class MergeHypothesesRequest(BaseModel):
    source_hypothesis_ids: List[str]
    consolidated_statement: str


class HypothesisFeedbackRequest(BaseModel):
    evaluator: str = "user"
    comment: str
    suggested_status: Optional[str] = None
