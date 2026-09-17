"""Pydantic schemas and DTOs for Task 105:
Autonomous Adaptation, Experiment Orchestration & Governed Evolution Engine.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.adaptation.domain import (
    AssignmentStrategy,
    ComparisonVerdict,
    EvolutionProposalStatus,
    MetricDimension,
    ProgramStatus,
    ReviewStatus,
    RunStatus,
    SandboxEnvironment,
    ValidationStatus,
    VariantConfigType,
    VariantType,
)


# ==============================================================================
# 1. ADAPTATION PROGRAM SCHEMAS
# ==============================================================================

class AdaptationProgramCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    objective: str = Field(..., min_length=5)
    problem_statement: str = Field(..., min_length=5)
    originating_finding_id: Optional[str] = None
    affected_capability: str = Field(..., min_length=2)
    affected_mission_id: Optional[str] = None
    affected_situation_id: Optional[str] = None
    affected_decision_id: Optional[str] = None
    baseline_id: str = Field(default="latest_golden_baseline")
    hypothesis_id: Optional[str] = None
    constraints: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    expected_benefit: str = ""
    expected_cost: str = ""
    success_criteria: dict[str, Any] = Field(default_factory=dict)
    failure_criteria: dict[str, Any] = Field(default_factory=dict)
    safety_criteria: list[str] = Field(default_factory=list)
    resource_budget: dict[str, Any] = Field(default_factory=dict)
    time_budget_seconds: float = 3600.0
    rollback_strategy: str = "Revert to frozen baseline capability parameters"
    validation_strategy: str = "Multi-suite offline replay + simulation gate"
    provenance: dict[str, Any] = Field(default_factory=dict)


class AdaptationProgramUpdate(BaseModel):
    title: Optional[str] = None
    objective: Optional[str] = None
    problem_statement: Optional[str] = None
    constraints: Optional[list[str]] = None
    risks: Optional[list[str]] = None
    success_criteria: Optional[dict[str, Any]] = None
    failure_criteria: Optional[dict[str, Any]] = None
    status: Optional[ProgramStatus] = None


class AdaptationProgramResponse(BaseModel):
    id: str
    title: str
    objective: str
    problem_statement: str
    originating_finding_id: Optional[str] = None
    affected_capability: str
    affected_mission_id: Optional[str] = None
    affected_situation_id: Optional[str] = None
    affected_decision_id: Optional[str] = None
    baseline_id: str
    hypothesis_id: Optional[str] = None
    constraints: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    expected_benefit: str
    expected_cost: str
    success_criteria: dict[str, Any] = Field(default_factory=dict)
    failure_criteria: dict[str, Any] = Field(default_factory=dict)
    safety_criteria: list[str] = Field(default_factory=list)
    resource_budget: dict[str, Any] = Field(default_factory=dict)
    time_budget_seconds: float
    governance_requirements: list[str] = Field(default_factory=list)
    rollback_strategy: str
    validation_strategy: str
    owner_source: str
    version: str
    status: ProgramStatus
    created_at: datetime
    updated_at: datetime


# ==============================================================================
# 2. HYPOTHESIS SCHEMAS
# ==============================================================================

class AdaptationHypothesisCreate(BaseModel):
    condition_change: str = Field(..., min_length=8, description="IF condition/change")
    expected_outcome: str = Field(..., min_length=8, description="THEN expected outcome")
    evidence_reasoning: str = Field(..., min_length=8, description="BECAUSE rationale/evidence")
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    evidence_references: list[str] = Field(default_factory=list)
    counter_hypotheses: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    falsification_criteria: list[str] = Field(default_factory=list)
    measurable_outcomes: dict[str, float] = Field(default_factory=dict)
    originating_finding_id: Optional[str] = None


class AdaptationHypothesisResponse(BaseModel):
    id: str
    condition_change: str
    expected_outcome: str
    evidence_reasoning: str
    confidence: float
    evidence_references: list[str]
    counter_hypotheses: list[str]
    assumptions: list[str]
    falsification_criteria: list[str]
    measurable_outcomes: dict[str, float]
    originating_finding_id: Optional[str]
    created_at: datetime


# ==============================================================================
# 3. EXPERIMENT VARIANT & PLAN SCHEMAS
# ==============================================================================

class ExperimentVariantCreate(BaseModel):
    name: str
    variant_type: VariantType = VariantType.CANDIDATE
    config_type: VariantConfigType = VariantConfigType.CONFIGURATION
    target_artifact_id: str
    configuration_delta: dict[str, Any] = Field(default_factory=dict)
    is_control: bool = False


class ExperimentVariantResponse(BaseModel):
    id: str
    plan_id: str
    name: str
    variant_type: VariantType
    config_type: VariantConfigType
    target_artifact_id: str
    configuration_delta: dict[str, Any]
    fingerprint: str
    is_control: bool
    created_at: datetime


class ExperimentPlanCreate(BaseModel):
    program_id: str
    objective: str = Field(..., min_length=5)
    hypothesis_id: str
    variants: list[ExperimentVariantCreate] = Field(default_factory=list)
    dataset_id: str = "default_eval_dataset"
    evaluation_suite_id: str = "comprehensive_suite"
    target_metrics: list[str] = Field(default_factory=lambda: ["quality", "safety", "latency"])
    safety_gates: list[str] = Field(default_factory=lambda: ["SAFETY_GATE", "SECURITY_GATE", "EMERGENCY_STOP_GATE"])
    stop_conditions: list[str] = Field(default_factory=lambda: ["SAFETY_VIOLATION", "SECURITY_VIOLATION", "EMERGENCY_STOP"])
    resource_budget: dict[str, Any] = Field(default_factory=dict)
    time_limit_seconds: float = 1800.0
    min_sample_size: int = 20
    max_sample_size: int = 200
    rollback_condition: str = "Error rate > 5% or safety regression"
    sandbox_environment: SandboxEnvironment = SandboxEnvironment.SIMULATION


class ExperimentPlanResponse(BaseModel):
    id: str
    program_id: str
    objective: str
    hypothesis_id: str
    variants: list[ExperimentVariantResponse]
    dataset_id: str
    evaluation_suite_id: str
    target_metrics: list[str]
    safety_gates: list[str]
    stop_conditions: list[str]
    resource_budget: dict[str, Any]
    time_limit_seconds: float
    min_sample_size: int
    max_sample_size: int
    rollback_condition: str
    evidence_requirements: list[str]
    sandbox_environment: SandboxEnvironment
    created_at: datetime


# ==============================================================================
# 4. EXPERIMENT RUN & ACTION SCHEMAS
# ==============================================================================

class ExperimentRunCreate(BaseModel):
    plan_id: str
    program_id: str
    stage_number: int = 1
    environment: SandboxEnvironment = SandboxEnvironment.SIMULATION
    target_sample_count: int = 20


class ExperimentActionRequest(BaseModel):
    action: str = Field(..., pattern="^(start|stop|pause|resume)$")
    reason: Optional[str] = None


class ExperimentRunResponse(BaseModel):
    id: str
    plan_id: str
    program_id: str
    stage_number: int
    environment: SandboxEnvironment
    status: RunStatus
    current_sample_count: int
    target_sample_count: int
    stop_reason: Optional[str]
    passed_safety_gates: bool
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime


class ExperimentObservationResponse(BaseModel):
    id: str
    run_id: str
    variant_id: str
    scenario_id: str
    step_index: int
    input_summary: str
    execution_output: str
    latency_ms: float
    tokens_used: int
    cost_usd: float
    has_error: bool
    error_message: Optional[str]
    world_state_drift_detected: bool
    observed_at: datetime


class ExperimentComparisonResponse(BaseModel):
    id: str
    run_id: str
    baseline_variant_id: str
    candidate_variant_id: str
    no_action_variant_id: Optional[str]
    verdict: ComparisonVerdict
    dimension_scores: dict[str, dict[str, float]]
    absolute_differences: dict[str, float]
    relative_differences: dict[str, float]
    causal_attribution_verified: bool
    causal_explanation: str
    world_state_verified: bool
    world_state_drift_summary: str
    sample_size: int
    is_statistically_significant: bool
    rationale: str
    created_at: datetime


class ExperimentGateResponse(BaseModel):
    id: str
    run_id: str
    gate_name: str
    passed: bool
    is_critical_security: bool
    threshold: Optional[float]
    measured_value: Optional[float]
    reason: str
    evaluated_at: datetime


class ExperimentEvidenceResponse(BaseModel):
    id: str
    run_id: str
    program_id: str
    hypothesis_text: str
    baseline_summary: dict[str, Any]
    candidate_summary: dict[str, Any]
    comparison_summary: dict[str, Any]
    observations_count: int
    safety_gates_passed: bool
    world_state_reconciled: bool
    resource_consumed: dict[str, Any]
    immutable_hash: str
    created_at: datetime


# ==============================================================================
# 5. EVOLUTION PROPOSAL & CHANGESET SCHEMAS
# ==============================================================================

class EvolutionProposalCreate(BaseModel):
    program_id: str
    evidence_id: str
    title: str = Field(..., min_length=3)
    affected_capability: str = Field(..., min_length=2)
    current_version: str = "1.0.0"
    target_version: str = "1.1.0"
    baseline_id: str
    candidate_variant_id: str
    evidence_summary: str
    rollback_plan: str
    deployment_scope: str = "CANARY_10_PERCENT"
    confidence: float = Field(0.85, ge=0.0, le=1.0)
    required_approval: bool = True


class EvolutionReviewRequest(BaseModel):
    reviewer: str = Field(..., min_length=2)
    status: ReviewStatus
    rationale: str = Field(..., min_length=5)
    approval_reference_id: Optional[str] = None


class EvolutionProposalResponse(BaseModel):
    id: str
    program_id: str
    evidence_id: str
    title: str
    affected_capability: str
    current_version: str
    target_version: str
    baseline_id: str
    candidate_variant_id: str
    evidence_summary: str
    metrics_summary: dict[str, Any]
    regression_results: dict[str, Any]
    safety_results: dict[str, Any]
    security_results: dict[str, Any]
    reliability_results: dict[str, Any]
    resource_impact: dict[str, Any]
    known_limitations: list[str]
    rollback_plan: str
    deployment_scope: str
    required_governance: list[str]
    required_approval: bool
    confidence: float
    generation: int
    parent_proposal_id: Optional[str]
    status: EvolutionProposalStatus
    created_at: datetime
    updated_at: datetime


class EvolutionReviewResponse(BaseModel):
    id: str
    proposal_id: str
    reviewer: str
    status: ReviewStatus
    rationale: str
    approval_reference_id: Optional[str]
    reviewed_at: Optional[datetime]
    created_at: datetime


class EvolutionChangeSetResponse(BaseModel):
    id: str
    proposal_id: str
    capability_id: str
    current_version: str
    candidate_version: str
    configuration_delta: dict[str, Any]
    dependencies: list[str]
    compatibility_report: dict[str, Any]
    migration_requirements: list[str]
    rollback_instructions: dict[str, Any]
    content_hash: str
    created_at: datetime


class EvolutionValidationRequest(BaseModel):
    proposal_id: str
    changeset_id: str
    include_holdout: bool = True


class EvolutionValidationResponse(BaseModel):
    id: str
    changeset_id: str
    proposal_id: str
    suite_results: dict[str, str]
    holdout_passed: bool
    overall_status: ValidationStatus
    failure_details: list[str]
    validated_at: Optional[datetime]
    created_at: datetime


# ==============================================================================
# 6. DASHBOARD SCHEMAS
# ==============================================================================

class AdaptationDashboardResponse(BaseModel):
    active_experiments: int = 0
    blocked_count: int = 0
    failed_count: int = 0
    inconclusive_count: int = 0
    improving_count: int = 0
    regressing_count: int = 0
    awaiting_review_count: int = 0
    awaiting_approval_count: int = 0
    validating_count: int = 0
    emergency_stop_active: bool = False
    recent_programs: list[AdaptationProgramResponse] = Field(default_factory=list)
    recent_experiments: list[ExperimentRunResponse] = Field(default_factory=list)
    recent_proposals: list[EvolutionProposalResponse] = Field(default_factory=list)
