"""Pydantic schemas and DTOs for Kairo Strategy Engine API (Task 106)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.strategy.domain import (
    ApplicabilityStatus,
    ConditionOperator,
    ConflictType,
    ContraindicationSeverity,
    EvidenceSourceType,
    ProposalStatus,
    ReviewDecision,
    StrategyCategory,
    StrategyStatus,
)


class StrategyConditionCreate(BaseModel):
    condition_type: str
    operator: ConditionOperator = ConditionOperator.EQUALS
    field_path: str
    target_value: Any
    is_mandatory: bool = True


class StrategyPreconditionCreate(BaseModel):
    precondition_type: str
    requirement_description: str
    verification_key: str
    expected_state: Any = True
    is_hard_requirement: bool = True


class StrategyContraindicationCreate(BaseModel):
    contraindication_type: str
    severity: ContraindicationSeverity = ContraindicationSeverity.PROHIBITIVE
    trigger_condition: Dict[str, Any] = Field(default_factory=dict)
    rationale: str


class StrategyOutcomeCreate(BaseModel):
    dimension: str
    expected_delta: float
    variance: float = 0.0
    success_criteria: str
    measurement_unit: str = "percentage"


class StrategyFailureModeCreate(BaseModel):
    failure_class: str
    symptom: str
    known_cause: str
    frequency: float = 0.0
    mitigation_strategy_id: Optional[str] = None


class StrategyCreateRequest(BaseModel):
    name: str
    category: StrategyCategory = StrategyCategory.PLANNING
    objective: str
    recommended_approach: str
    domain_scope: str = "SYSTEM"
    tested_domain: str = ""
    supported_domain: str = ""
    unknown_domain: str = ""
    validity_window_seconds: int = 604800
    is_safety_critical: bool = False
    provenance_type: str = "MANUAL_DESIGN"
    provenance_id: str = ""
    conditions: List[StrategyConditionCreate] = Field(default_factory=list)
    preconditions: List[StrategyPreconditionCreate] = Field(default_factory=list)
    contraindications: List[StrategyContraindicationCreate] = Field(default_factory=list)
    outcomes: List[StrategyOutcomeCreate] = Field(default_factory=list)
    failure_modes: List[StrategyFailureModeCreate] = Field(default_factory=list)


class StrategyUpdateRequest(BaseModel):
    name: Optional[str] = None
    objective: Optional[str] = None
    recommended_approach: Optional[str] = None
    lifecycle_status: Optional[StrategyStatus] = None
    validity_window_seconds: Optional[int] = None
    is_safety_critical: Optional[bool] = None


class StrategyVersionCreateRequest(BaseModel):
    change_reason: str
    change_description: str = ""
    parameters: Dict[str, Any] = Field(default_factory=dict)
    rules: List[Dict[str, Any]] = Field(default_factory=list)


class StrategyEvidenceCreateRequest(BaseModel):
    source_type: EvidenceSourceType
    source_id: str
    is_counterexample: bool = False
    claim: str
    observed_metrics: Dict[str, Any] = Field(default_factory=dict)
    environmental_context: Dict[str, Any] = Field(default_factory=dict)
    capability_version: str = "1.0.0"
    confidence_weight: float = 1.0


class StrategyApplicabilityCheckRequest(BaseModel):
    strategy_id: Optional[str] = None
    category: Optional[StrategyCategory] = None
    context: Dict[str, Any] = Field(default_factory=dict)


class StrategyApplicabilityResponse(BaseModel):
    strategy_id: str
    strategy_name: str
    applicability_status: ApplicabilityStatus
    applicability_score: float
    blocking_reasons: List[str]
    uncertainty_reasons: List[str]
    conditions_met: int
    total_conditions: int


class StrategyFeedbackRequest(BaseModel):
    decision_id: Optional[str] = None
    action_id: Optional[str] = None
    outcome_status: str = "SUCCESS"  # SUCCESS, FAILURE, PARTIAL, UNKNOWN
    actual_metrics: Dict[str, Any] = Field(default_factory=dict)
    observed_failure_mode: Optional[str] = None
    resource_cost: float = 0.0
    user_intervention: bool = False


class StrategyProposalCreateRequest(BaseModel):
    proposal_title: str
    strategy_id: Optional[str] = None
    target_version: int = 1
    rationale: str
    mined_patterns_summary: Dict[str, Any] = Field(default_factory=dict)


class StrategyProposalReviewRequest(BaseModel):
    reviewer: str = "kairo_governance"
    decision: ReviewDecision = ReviewDecision.APPROVED
    comments: str = ""
    governance_approval_id: Optional[str] = None


class StrategySearchRequest(BaseModel):
    query: Optional[str] = None
    category: Optional[StrategyCategory] = None
    status: Optional[StrategyStatus] = None
    domain_scope: Optional[str] = None
    is_stale: Optional[bool] = None
    limit: int = 50


class StrategyCandidateContract(BaseModel):
    """Typed candidate contract presented to Task 94 Decision Intelligence."""

    strategy_id: str
    strategy_version: int
    name: str
    category: StrategyCategory
    objective: str
    recommended_approach: str
    applicability_status: ApplicabilityStatus
    applicability_score: float
    confidence: float
    uncertainty: float
    evidence_count: int
    counterexample_count: int
    expected_outcomes: List[Dict[str, Any]]
    known_failure_modes: List[Dict[str, Any]]
    preconditions: List[Dict[str, Any]]
    contraindications: List[Dict[str, Any]]
    tested_domain: str
    supported_domain: str
    unknown_domain: str
    freshness: str
    provenance: str


class StrategyDashboardResponse(BaseModel):
    total_strategies: int
    available_count: int
    candidate_count: int
    validating_count: int
    stale_count: int
    suspended_count: int
    conflicted_count: int
    revalidation_queue_count: int
    proposals_pending_count: int
    emergency_stop_active: bool
    coverage_by_category: Dict[str, int]
    recent_strategies: List[Dict[str, Any]]
    active_conflicts: List[Dict[str, Any]]
