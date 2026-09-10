"""Pydantic schemas for Kairo Adaptive Learning & Strategy Optimization (Task 43)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field

from enum import Enum
from app.learning.experiences import ExperienceType
from app.learning.experimentation import ExperimentStatus
from app.learning.signals import SignalSource, SignalType
from app.learning.strategies import StrategyStatus


# =============================================================================
# TASK 52 CONTINUOUS LEARNING ENUMS
# =============================================================================

class ExperienceStatus(str, Enum):
    RAW = "RAW"
    EVALUATED = "EVALUATED"
    VALIDATED = "VALIDATED"
    CONSOLIDATED = "CONSOLIDATED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class ExperienceSource(str, Enum):
    USER = "USER"
    SYSTEM = "SYSTEM"
    TOOL = "TOOL"
    AGENT = "AGENT"
    AUTOMATION = "AUTOMATION"
    PREDICTION = "PREDICTION"
    PERCEPTION = "PERCEPTION"
    VERIFICATION = "VERIFICATION"
    COMMUNICATION = "COMMUNICATION"
    PROJECT = "PROJECT"
    WORKFLOW = "WORKFLOW"


class LessonType(str, Enum):
    SUCCESS_PATTERN = "SUCCESS_PATTERN"
    FAILURE_PATTERN = "FAILURE_PATTERN"
    TOOL_PATTERN = "TOOL_PATTERN"
    PLANNING_PATTERN = "PLANNING_PATTERN"
    COMMUNICATION_PATTERN = "COMMUNICATION_PATTERN"
    PREFERENCE_PATTERN = "PREFERENCE_PATTERN"
    PREDICTION_PATTERN = "PREDICTION_PATTERN"
    INTENT_PATTERN = "INTENT_PATTERN"
    WORKFLOW_PATTERN = "WORKFLOW_PATTERN"
    ENVIRONMENT_PATTERN = "ENVIRONMENT_PATTERN"


class LessonStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    ACTIVE = "ACTIVE"
    WEAKENED = "WEAKENED"
    SUPERSEDED = "SUPERSEDED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class GeneralizationScope(str, Enum):
    TASK = "TASK"
    SESSION = "SESSION"
    PROJECT = "PROJECT"
    REPOSITORY = "REPOSITORY"
    ENVIRONMENT = "ENVIRONMENT"
    USER = "USER"
    GLOBAL = "GLOBAL"


class FeedbackType(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    EDIT = "EDIT"
    CORRECT = "CORRECT"
    IGNORE = "IGNORE"
    CONFIRM = "CONFIRM"


class AdaptationType(str, Enum):
    ROUTING = "ROUTING"
    RETRIEVAL_RANKING = "RETRIEVAL_RANKING"
    PLANNING_HEURISTIC = "PLANNING_HEURISTIC"
    DRAFT_STYLE = "DRAFT_STYLE"
    TOOL_SELECTION = "TOOL_SELECTION"


class ExperienceCreateRequest(BaseModel):
    strategy: str = Field(..., description="Strategy name or identifier")
    actions: list[Any] = Field(default_factory=list)
    observations: list[Any] = Field(default_factory=list)
    verification_result: dict[str, Any] = Field(default_factory=dict)
    outcome: ExperienceType = Field(default=ExperienceType.SUCCESS)
    task_id: str | None = None
    goal_type: str = "GENERAL"
    plan_type: str | None = None
    duration_ms: float = 0.0
    cost: float = 0.0
    retries: int = 0
    failures: list[Any] = Field(default_factory=list)
    scope: dict[str, Any] = Field(default_factory=dict)


class ExperienceResponse(BaseModel):
    experience_id: str
    task_id: str | None = None
    goal_type: str
    plan_type: str | None = None
    strategy: str
    outcome: str
    duration_ms: float
    cost: float
    retries: int
    learning_weight: float
    created_at: str


class StrategyCreateRequest(BaseModel):
    domain: str = Field(..., description="Domain: coding, deployment, research, etc.")
    description: str = Field(..., description="Strategy mechanics description")
    prerequisites: list[str] = Field(default_factory=list)
    expected_outcome: dict[str, Any] = Field(default_factory=dict)
    scope: dict[str, Any] = Field(default_factory=dict)
    status: StrategyStatus = Field(default=StrategyStatus.CANDIDATE)


class StrategyResponse(BaseModel):
    strategy_id: str
    domain: str
    description: str
    version: int
    success_rate: float
    failure_rate: float
    verification_rate: float
    latency_ms: float
    cost: float
    confidence: str
    status: str
    sample_size: int
    created_at: str
    updated_at: str


class RecommendationResponse(BaseModel):
    recommended_strategy: StrategyResponse | None = None
    rank_score: float = 0.0
    explanation: str = "No suitable strategy found"
    small_sample_warning: str | None = None


class UserFeedbackRequest(BaseModel):
    target_id: str = Field(..., description="Plan, task, or strategy ID")
    feedback_type: str = Field(..., description="positive, negative, correction, preference, rating")
    rating: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = None
    scope: dict[str, Any] = Field(default_factory=dict)


class ExperimentCreateRequest(BaseModel):
    name: str = Field(...)
    domain: str = Field(default="system")
    baseline_strategy_id: str = Field(...)
    candidate_strategy_id: str = Field(...)
    target_sample_size: int = Field(default=50)


class ExperimentResponse(BaseModel):
    experiment_id: str
    name: str
    domain: str
    status: str
    baseline_strategy_id: str
    candidate_strategy_id: str
    target_sample_size: int
    current_sample_size: int
    comparison: dict[str, Any]
    created_at: str


class PromotionRequest(BaseModel):
    strategy_id: str = Field(...)
    approved_by: str = Field(...)
    reason: str = Field(default="Empirical benchmarks and governance criteria satisfied")


class PromotionResponse(BaseModel):
    promotion_id: str
    strategy_id: str
    from_status: str
    to_status: str
    reason: str
    approved_by: str
    timestamp: str


class RollbackRequest(BaseModel):
    strategy_id: str = Field(...)
    rolled_back_by: str = Field(default="operator")
    reason: str = Field(default="Performance regression detected")


class RollbackResponse(BaseModel):
    rollback_id: str
    strategy_id: str
    prior_status: str
    trigger_reason: str
    rolled_back_by: str
    timestamp: str


class PreFlightWarningResponse(BaseModel):
    warning_id: str
    target_workflow: str
    pattern_signature: str
    frequency: int
    message: str
    recommended_mitigation: str
    confidence: str
    is_blocking: bool
    created_at: str


class FailurePatternResponse(BaseModel):
    pattern_id: str
    domain: str
    signature: str
    frequency: int
    affected_components: list[str]
    mitigation: str
    confidence: str
    created_at: str
    updated_at: str


class LearningStatsResponse(BaseModel):
    total_experiences: int
    total_signals: int
    total_strategies: int
    total_failure_patterns: int
    total_experiments: int
    tool_reliabilities: list[dict[str, Any]]
    provider_reliabilities: list[dict[str, Any]]


# =============================================================================
# TASK 52 CONTINUOUS LEARNING DATA SCHEMAS
# =============================================================================

from pydantic import ConfigDict
from datetime import UTC


class ExperienceSchema(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    experience_id: str
    task_id: str | None = None
    intent_id: str | None = None
    goal_id: str | None = None
    context_refs: list[str] = Field(default_factory=list)
    actions: list[dict[str, Any]] = Field(default_factory=list)
    outcome: str = "SUCCESS"
    verification: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    environment: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
    privacy_scope: str = "PROJECT"
    status: ExperienceStatus = ExperienceStatus.RAW
    source: ExperienceSource = ExperienceSource.SYSTEM


class LearningOutcomeSchema(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    outcome_id: str
    task_id: str | None = None
    expected: dict[str, Any] = Field(default_factory=dict)
    actual: dict[str, Any] = Field(default_factory=dict)
    deviation: float = 0.0
    deviation_details: dict[str, Any] = Field(default_factory=dict)
    verified: bool = False
    evidence_refs: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class LessonSchema(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    lesson_id: str
    statement: str
    lesson_type: LessonType = LessonType.SUCCESS_PATTERN
    source_experiences: list[str] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float = 0.8
    scope: GeneralizationScope = GeneralizationScope.PROJECT
    validity: dict[str, Any] = Field(default_factory=dict)
    status: LessonStatus = LessonStatus.CANDIDATE
    reinforcement_count: int = 1
    decay_score: float = 1.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class WorkflowPatternSchema(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    workflow_id: str
    name: str
    version: str = "1.0.0"
    preconditions: list[dict[str, Any]] = Field(default_factory=list)
    steps: list[dict[str, Any]] = Field(default_factory=list)
    expected_outcome: dict[str, Any] = Field(default_factory=dict)
    verification: dict[str, Any] = Field(default_factory=dict)
    failure_modes: list[str] = Field(default_factory=list)
    success_count: int = 0
    failure_count: int = 0
    status: str = "CANDIDATE"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class HeuristicSchema(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    heuristic_id: str
    condition: str
    recommendation: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float = 0.7
    scope: GeneralizationScope = GeneralizationScope.TASK
    status: str = "CANDIDATE"
    priority: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ReplayEvaluationSchema(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    replay_id: str
    experience_id: str
    simulated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    evaluation_result: dict[str, Any] = Field(default_factory=dict)
    temporal_cutoff: datetime
    leakage_detected: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class LearningPolicySchema(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    policy_id: str
    scope: str = "GLOBAL"
    allowed_adaptations: list[str] = Field(default_factory=lambda: [
        "ROUTING",
        "RETRIEVAL_RANKING",
        "PLANNING_HEURISTIC",
        "DRAFT_STYLE",
        "TOOL_SELECTION"
    ])
    approval_required: bool = True
    retention_days: int = 90
    rollback_policy: dict[str, Any] = Field(default_factory=lambda: {
        "auto_rollback_on_regression": True,
        "regression_threshold": 0.15,
    })


class ContinuousLearningMetricsSchema(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    accuracy: float = 1.0
    safety_violations: int = 0
    verification_rate: float = 1.0
    user_satisfaction: float = 1.0
    cost_savings: float = 0.0
    latency_ms: float = 0.0
    tool_reliability: float = 1.0
    total_experiences: int = 0
    total_lessons: int = 0
    promoted_workflows: int = 0
    active_heuristics: int = 0


class FeedbackRecordSchema(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    feedback_id: str
    target_id: str
    feedback_type: FeedbackType
    user_id: str
    edit_diff: dict[str, Any] | None = None
    comment: str | None = None
    explicit_override: bool = False
    weight: float = 1.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CorrectionRecordSchema(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    correction_id: str
    target_action: str
    user_directive: str
    scope: GeneralizationScope
    is_ambiguous: bool = False
    clarification_prompt: str | None = None
    applied: bool = True
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

