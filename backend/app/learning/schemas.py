"""Pydantic schemas for Kairo Adaptive Learning & Strategy Optimization (Task 43)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field

from app.learning.experiences import ExperienceType
from app.learning.experimentation import ExperimentStatus
from app.learning.signals import SignalSource, SignalType
from app.learning.strategies import StrategyStatus


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
