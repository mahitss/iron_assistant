"""Pydantic v2 schemas, enums, and data contracts for Kairo Executive Decision Engine (Task 57)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class DecisionStatus(str, Enum):
    DRAFT = "DRAFT"
    ANALYZING = "ANALYZING"
    RECOMMENDED = "RECOMMENDED"
    AWAITING_DECISION = "AWAITING_DECISION"
    DECIDED = "DECIDED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    EXECUTING = "EXECUTING"
    EXECUTED = "EXECUTED"
    VERIFYING = "VERIFYING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"
    SUPERSEDED = "SUPERSEDED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class ReversibilityLevel(str, Enum):
    REVERSIBLE = "REVERSIBLE"
    PARTIALLY_REVERSIBLE = "PARTIALLY_REVERSIBLE"
    DIFFICULT_TO_REVERSE = "DIFFICULT_TO_REVERSE"
    IRREVERSIBLE = "IRREVERSIBLE"


class EvidenceStrength(str, Enum):
    VERIFIED = "VERIFIED"
    SUPPORTED = "SUPPORTED"
    INDICATIVE = "INDICATIVE"
    INFERRED = "INFERRED"
    SPECULATIVE = "SPECULATIVE"
    UNKNOWN = "UNKNOWN"


class DataTrustLevel(str, Enum):
    TRUSTED_SYSTEM_DATA = "TRUSTED_SYSTEM_DATA"
    VERIFIED_EXTERNAL_DATA = "VERIFIED_EXTERNAL_DATA"
    USER_PROVIDED_DATA = "USER_PROVIDED_DATA"
    UNVERIFIED_EXTERNAL_DATA = "UNVERIFIED_EXTERNAL_DATA"
    MODEL_GENERATED_DATA = "MODEL_GENERATED_DATA"
    SIMULATED_DATA = "SIMULATED_DATA"


class RiskCategory(str, Enum):
    OPERATIONAL = "OPERATIONAL"
    SECURITY = "SECURITY"
    RELIABILITY = "RELIABILITY"
    FINANCIAL = "FINANCIAL"
    COMPLIANCE = "COMPLIANCE"
    PRIVACY = "PRIVACY"
    DATA_LOSS = "DATA_LOSS"
    DEPENDENCY = "DEPENDENCY"
    DEPLOYMENT = "DEPLOYMENT"
    HUMAN_ERROR = "HUMAN_ERROR"
    REVERSIBILITY = "REVERSIBILITY"
    UNCERTAINTY = "UNCERTAINTY"


class ConstraintType(str, Enum):
    HARD = "HARD"
    SOFT = "SOFT"


class OptionType(str, Enum):
    CONSERVATIVE = "CONSERVATIVE"
    AGGRESSIVE = "AGGRESSIVE"
    REVERSIBLE = "REVERSIBLE"
    NO_ACTION = "NO_ACTION"
    INFO_GATHERING = "INFO_GATHERING"
    STANDARD = "STANDARD"


class GateEvaluationStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    BLOCKED = "BLOCKED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


# Domain Models
class Objective(BaseModel):
    model_config = ConfigDict(extra="ignore")

    objective_id: str = Field(default_factory=lambda: f"obj_{uuid.uuid4().hex[:8]}")
    name: str
    description: str = ""
    direction: str = "MINIMIZE"  # "MINIMIZE" or "MAXIMIZE"
    priority: int = 1  # 1 = highest
    weight: float = 1.0  # Normalized relative weight
    source: str = "user_request"
    confidence: float = 1.0
    measurement_unit: str = ""


class Constraint(BaseModel):
    model_config = ConfigDict(extra="ignore")

    constraint_id: str = Field(default_factory=lambda: f"con_{uuid.uuid4().hex[:8]}")
    name: str
    constraint_type: ConstraintType = ConstraintType.HARD
    target_field: str
    operator: str = "<="  # "<=", ">=", "==", "!=", "in"
    value: Any
    is_satisfied: bool = True
    violation_reason: str | None = None


class Preference(BaseModel):
    model_config = ConfigDict(extra="ignore")

    preference_id: str = Field(default_factory=lambda: f"pref_{uuid.uuid4().hex[:8]}")
    statement: str
    category: str = "general"
    strength: float = 0.5
    is_explicit: bool = True
    source: str = "user"


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    evidence_id: str = Field(default_factory=lambda: f"ev_{uuid.uuid4().hex[:8]}")
    evidence_type: str = "observed_fact"
    strength: EvidenceStrength = EvidenceStrength.SUPPORTED
    trust_level: DataTrustLevel = DataTrustLevel.TRUSTED_SYSTEM_DATA
    source: str
    timestamp: datetime = Field(default_factory=_now_utc)
    summary: str
    is_primary: bool = True
    confidence: float = 0.9
    verification_status: str = "VERIFIED"


class EvidenceSet(BaseModel):
    model_config = ConfigDict(extra="ignore")

    decision_id: str
    items: list[EvidenceItem] = Field(default_factory=list)
    overall_strength: EvidenceStrength = EvidenceStrength.SUPPORTED
    untrusted_data_count: int = 0


class RiskAssessment(BaseModel):
    model_config = ConfigDict(extra="ignore")

    risk_id: str = Field(default_factory=lambda: f"risk_{uuid.uuid4().hex[:8]}")
    category: RiskCategory = RiskCategory.OPERATIONAL
    probability: str = "LOW"  # Qualitative: LOW, MEDIUM, HIGH (no false precision)
    impact: str = "MEDIUM"  # LOW, MEDIUM, HIGH, CRITICAL
    exposure_score: float = 0.3
    reversibility: ReversibilityLevel = ReversibilityLevel.REVERSIBLE
    mitigation: str = ""
    is_acceptable: bool = True


class Tradeoff(BaseModel):
    model_config = ConfigDict(extra="ignore")

    tradeoff_id: str = Field(default_factory=lambda: f"to_{uuid.uuid4().hex[:8]}")
    dimension_a: str
    dimension_b: str
    explanation: str
    tension_level: str = "MEDIUM"  # LOW, MEDIUM, HIGH


class CandidateOption(BaseModel):
    model_config = ConfigDict(extra="ignore")

    option_id: str = Field(default_factory=lambda: f"opt_{uuid.uuid4().hex[:8]}")
    name: str
    description: str = ""
    option_type: OptionType = OptionType.STANDARD
    is_feasible: bool = True
    rejection_reason: str | None = None
    reversibility: ReversibilityLevel = ReversibilityLevel.REVERSIBLE
    metrics: dict[str, float] = Field(default_factory=dict)
    scores: dict[str, float] = Field(default_factory=dict)
    tradeoffs: list[Tradeoff] = Field(default_factory=list)
    risks: list[RiskAssessment] = Field(default_factory=list)
    hard_constraints_satisfied: bool = True


class OptionEvaluation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    option_id: str
    name: str
    raw_score: float = 0.0
    normalized_score: float = 0.0
    rank: int = 1
    benefit_score: float = 0.0
    risk_penalty: float = 0.0
    cost_penalty: float = 0.0
    complexity_penalty: float = 0.0
    reversibility_bonus: float = 0.0
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    explanation: str = ""


class DecisionGate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    gate_number: int
    name: str
    status: GateEvaluationStatus = GateEvaluationStatus.PASSED
    message: str = ""
    evaluated_at: datetime = Field(default_factory=_now_utc)


class UncertaintyAssessment(BaseModel):
    model_config = ConfigDict(extra="ignore")

    overall_uncertainty: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    confidence: float = 0.8
    missing_data: list[str] = Field(default_factory=list)
    stale_signals: list[str] = Field(default_factory=list)
    assumptions_count: int = 0
    safe_to_proceed: bool = True


class DecisionRanking(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ranking_id: str = Field(default_factory=lambda: f"rnk_{uuid.uuid4().hex[:8]}")
    ranked_options: list[OptionEvaluation] = Field(default_factory=list)
    recommended_option_id: str | None = None
    dominated_option_ids: list[str] = Field(default_factory=list)
    confidence: float = 0.8
    tradeoffs_summary: list[str] = Field(default_factory=list)
    sensitivity_analysis: dict[str, Any] = Field(default_factory=dict)


class DecisionRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    request_id: str = Field(default_factory=lambda: f"dreq_{uuid.uuid4().hex[:12]}")
    question: str
    intent: str | None = None
    context_scope: str = "PROJECT"
    scope_id: str | None = None
    authority: str = "user"
    deadline: datetime | None = None
    risk_tolerance: str = "MEDIUM"
    objectives: list[Objective] = Field(default_factory=list)
    constraints: list[Constraint] = Field(default_factory=list)
    preferences: list[Preference] = Field(default_factory=list)
    available_options: list[str] = Field(default_factory=list)
    forbidden_options: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now_utc)


class Recommendation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    recommendation_id: str = Field(default_factory=lambda: f"rec_{uuid.uuid4().hex[:12]}")
    decision_id: str
    recommended_option_id: str
    headline: str
    why_selected: str
    why_not_alternatives: list[str] = Field(default_factory=list)
    worst_case_downside: str = ""
    assumptions: list[str] = Field(default_factory=list)
    uncertainty_summary: str = ""
    sensitivity_thresholds: list[str] = Field(default_factory=list)
    approval_required: bool = False
    proposed_execution_plan: dict[str, Any] | None = None
    verification_criteria: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now_utc)


class DecisionRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    decision_id: str = Field(default_factory=lambda: f"dec_{uuid.uuid4().hex[:12]}")
    request_id: str
    status: DecisionStatus = DecisionStatus.RECOMMENDED
    recommendation: Recommendation | None = None
    selected_option_id: str | None = None
    selected_by: str | None = None
    user_override: bool = False
    confidence: float = 0.8
    ranking: DecisionRanking | None = None
    decision_gates: dict[str, DecisionGate] = Field(default_factory=dict)
    approval_required: bool = False
    approval_id: str | None = None
    execution_plan: dict[str, Any] | None = None
    verification_plan: list[str] = Field(default_factory=list)
    version: int = 1
    provenance: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)


class DecisionCommitment(BaseModel):
    model_config = ConfigDict(extra="ignore")

    commitment_id: str = Field(default_factory=lambda: f"com_{uuid.uuid4().hex[:12]}")
    decision_id: str
    owner: str
    title: str
    deadline: datetime | None = None
    status: str = "PROPOSED"
    authorized_by: str | None = None
    created_at: datetime = Field(default_factory=_now_utc)


class DecisionOutcome(BaseModel):
    model_config = ConfigDict(extra="ignore")

    outcome_id: str = Field(default_factory=lambda: f"out_{uuid.uuid4().hex[:12]}")
    decision_id: str
    actual_benefit: float = 0.0
    actual_cost: float = 0.0
    actual_duration: float = 0.0
    prediction_error: float = 0.0
    unexpected_side_effects: list[str] = Field(default_factory=list)
    success: bool = True
    recorded_at: datetime = Field(default_factory=_now_utc)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DecisionRevision(BaseModel):
    model_config = ConfigDict(extra="ignore")

    revision_id: str = Field(default_factory=lambda: f"rev_{uuid.uuid4().hex[:12]}")
    parent_decision_id: str
    revision_number: int = 1
    reason: str
    actor: str
    previous_snapshot: dict[str, Any] = Field(default_factory=dict)
    new_snapshot: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now_utc)
