"""FastAPI REST API router for Kairo Adaptive Learning & Strategy Optimization (Task 43)."""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.learning.experiences import Experience, ExperienceType
from app.learning.experimentation import Experiment, ExperimentStatus
from app.learning.schemas import (
    ExperienceCreateRequest,
    ExperienceResponse,
    ExperimentCreateRequest,
    ExperimentResponse,
    FailurePatternResponse,
    LearningStatsResponse,
    PreFlightWarningResponse,
    PromotionRequest,
    PromotionResponse,
    RecommendationResponse,
    RollbackRequest,
    RollbackResponse,
    StrategyCreateRequest,
    StrategyResponse,
    UserFeedbackRequest,
)
from app.learning.service import LearningService
from app.learning.strategies import Strategy, StrategyStatus

logger = logging.getLogger("kairo.learning.router")

router = APIRouter(prefix="/learning", tags=["Adaptive Learning & Strategy Engine"])

_learning_service: LearningService | None = None


def get_learning_service() -> LearningService:
    """Dependency provider for LearningService singleton."""
    global _learning_service
    if _learning_service is None:
        _learning_service = LearningService()
    return _learning_service


def get_current_user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    """Extract authenticated user ID from request header."""
    if not x_user_id or not x_user_id.strip():
        return "default_user"
    return x_user_id.strip()


def _to_strat_response(s: Strategy) -> StrategyResponse:
    return StrategyResponse(
        strategy_id=s.strategy_id,
        domain=s.domain,
        description=s.description,
        version=s.version,
        success_rate=round(s.success_rate, 3),
        failure_rate=round(s.failure_rate, 3),
        verification_rate=round(s.verification_rate, 3),
        latency_ms=round(s.latency_ms, 2),
        cost=round(s.cost, 4),
        confidence=s.confidence,
        status=s.status.value if hasattr(s.status, "value") else str(s.status),
        sample_size=s.sample_size,
        created_at=s.created_at.isoformat(),
        updated_at=s.updated_at.isoformat(),
    )


def _to_exp_response(e: Experience) -> ExperienceResponse:
    return ExperienceResponse(
        experience_id=e.experience_id,
        task_id=e.task_id,
        goal_type=e.goal_type,
        plan_type=e.plan_type,
        strategy=e.strategy,
        outcome=e.outcome.value if hasattr(e.outcome, "value") else str(e.outcome),
        duration_ms=e.duration_ms,
        cost=e.cost,
        retries=e.retries,
        learning_weight=e.calculate_learning_weight(),
        created_at=e.created_at.isoformat(),
    )


# =============================================================================
# STRATEGIES & RECOMMENDATIONS (Spec 137, 138)
# =============================================================================

@router.get("/strategies", response_model=list[StrategyResponse])
def list_strategies(
    domain: str | None = Query(default=None),
    status_filter: StrategyStatus | None = Query(default=None, alias="status"),
    service: LearningService = Depends(get_learning_service),
) -> list[StrategyResponse]:
    strategies = service.list_strategies(domain=domain, status=status_filter)
    return [_to_strat_response(s) for s in strategies]


@router.get("/strategies/{strategy_id}", response_model=StrategyResponse)
def get_strategy(
    strategy_id: str,
    service: LearningService = Depends(get_learning_service),
) -> StrategyResponse:
    strat = service.get_strategy(strategy_id)
    if not strat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Strategy '{strategy_id}' not found")
    return _to_strat_response(strat)


@router.post("/strategies", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
def register_strategy(
    req: StrategyCreateRequest,
    service: LearningService = Depends(get_learning_service),
) -> StrategyResponse:
    strat, msg = service.register_strategy(
        domain=req.domain,
        description=req.description,
        prerequisites=req.prerequisites,
        expected_outcome=req.expected_outcome,
        scope=req.scope,
        status=req.status,
    )
    if strat.status == StrategyStatus.BLOCKED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return _to_strat_response(strat)


@router.get("/recommendations", response_model=RecommendationResponse)
def get_recommendation(
    domain: str = Query(...),
    project_id: str | None = Query(default=None),
    service: LearningService = Depends(get_learning_service),
    user_id: str = Depends(get_current_user_id),
) -> RecommendationResponse:
    """Return top recommended strategy with deterministic factors and warnings (Spec 138)."""
    ranked = service.recommend_strategy(domain=domain, user_id=user_id, project_id=project_id)
    if not ranked:
        return RecommendationResponse()

    return RecommendationResponse(
        recommended_strategy=_to_strat_response(ranked.strategy),
        rank_score=ranked.rank_score,
        explanation=ranked.explanation,
        small_sample_warning=ranked.small_sample_warning,
    )


# =============================================================================
# EXPERIENCES
# =============================================================================

@router.get("/experiences", response_model=list[ExperienceResponse])
def list_experiences(
    strategy: str | None = Query(default=None),
    outcome: ExperienceType | None = Query(default=None),
    service: LearningService = Depends(get_learning_service),
) -> list[ExperienceResponse]:
    experiences = service.list_experiences(strategy=strategy, outcome=outcome)
    return [_to_exp_response(e) for e in experiences]


@router.post("/experiences", response_model=ExperienceResponse, status_code=status.HTTP_201_CREATED)
def record_experience(
    req: ExperienceCreateRequest,
    service: LearningService = Depends(get_learning_service),
) -> ExperienceResponse:
    exp = service.record_experience(
        strategy=req.strategy,
        actions=req.actions,
        observations=req.observations,
        verification_result=req.verification_result,
        outcome=req.outcome,
        task_id=req.task_id,
        goal_type=req.goal_type,
        plan_type=req.plan_type,
        duration_ms=req.duration_ms,
        cost=req.cost,
        retries=req.retries,
        failures=req.failures,
        scope=req.scope,
    )
    return _to_exp_response(exp)


# =============================================================================
# FAILURES & PRE-FLIGHT WARNINGS
# =============================================================================

@router.get("/failures", response_model=list[FailurePatternResponse])
def list_failures(
    domain: str | None = Query(default=None),
    service: LearningService = Depends(get_learning_service),
) -> list[FailurePatternResponse]:
    patterns = service.list_failure_patterns(domain=domain)
    return [
        FailurePatternResponse(
            pattern_id=p.pattern_id,
            domain=p.domain,
            signature=p.signature,
            frequency=p.frequency,
            affected_components=p.affected_components,
            mitigation=p.mitigation,
            confidence=p.confidence,
            created_at=p.created_at.isoformat(),
            updated_at=p.updated_at.isoformat(),
        )
        for p in patterns
    ]


@router.get("/failures/pre-flight", response_model=PreFlightWarningResponse | None)
def check_pre_flight(
    workflow_name: str = Query(...),
    domain: str = Query(default="system"),
    service: LearningService = Depends(get_learning_service),
) -> PreFlightWarningResponse | None:
    warning = service.check_pre_flight_warning(workflow_name=workflow_name, domain=domain)
    if not warning:
        return None
    return PreFlightWarningResponse(
        warning_id=warning.warning_id,
        target_workflow=warning.target_workflow,
        pattern_signature=warning.pattern_signature,
        frequency=warning.frequency,
        message=warning.message,
        recommended_mitigation=warning.recommended_mitigation,
        confidence=warning.confidence,
        is_blocking=warning.is_blocking,
        created_at=warning.created_at.isoformat(),
    )


# =============================================================================
# EXPERIMENTS
# =============================================================================

@router.get("/experiments", response_model=list[ExperimentResponse])
def list_experiments(
    status_filter: ExperimentStatus | None = Query(default=None, alias="status"),
    service: LearningService = Depends(get_learning_service),
) -> list[ExperimentResponse]:
    experiments = service.list_experiments(status=status_filter)
    return [
        ExperimentResponse(
            experiment_id=e.experiment_id,
            name=e.name,
            domain=e.domain,
            status=e.status.value if hasattr(e.status, "value") else str(e.status),
            baseline_strategy_id=e.baseline_strategy_id,
            candidate_strategy_id=e.candidate_strategy_id,
            target_sample_size=e.target_sample_size,
            current_sample_size=e.current_sample_size,
            comparison=e.get_comparison(),
            created_at=e.created_at.isoformat(),
        )
        for e in experiments
    ]


@router.post("/experiments", response_model=ExperimentResponse, status_code=status.HTTP_201_CREATED)
def create_experiment(
    req: ExperimentCreateRequest,
    service: LearningService = Depends(get_learning_service),
) -> ExperimentResponse:
    exp = service.create_experiment(
        name=req.name,
        domain=req.domain,
        baseline_strategy_id=req.baseline_strategy_id,
        candidate_strategy_id=req.candidate_strategy_id,
        target_sample_size=req.target_sample_size,
    )
    return ExperimentResponse(
        experiment_id=exp.experiment_id,
        name=exp.name,
        domain=exp.domain,
        status=exp.status.value if hasattr(exp.status, "value") else str(exp.status),
        baseline_strategy_id=exp.baseline_strategy_id,
        candidate_strategy_id=exp.candidate_strategy_id,
        target_sample_size=exp.target_sample_size,
        current_sample_size=exp.current_sample_size,
        comparison=exp.get_comparison(),
        created_at=exp.created_at.isoformat(),
    )


# =============================================================================
# PROMOTION & ROLLBACK
# =============================================================================

@router.post("/promote", response_model=PromotionResponse)
def promote_strategy(
    req: PromotionRequest,
    service: LearningService = Depends(get_learning_service),
) -> PromotionResponse:
    success, msg, rec = service.promote_strategy(
        strategy_id=req.strategy_id,
        approved_by=req.approved_by,
        reason=req.reason,
    )
    if not success or not rec:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    return PromotionResponse(
        promotion_id=rec.promotion_id,
        strategy_id=rec.strategy_id,
        from_status=rec.from_status.value,
        to_status=rec.to_status.value,
        reason=rec.reason,
        approved_by=rec.approved_by,
        timestamp=rec.timestamp.isoformat(),
    )


@router.post("/rollback", response_model=RollbackResponse)
def rollback_strategy(
    req: RollbackRequest,
    service: LearningService = Depends(get_learning_service),
) -> RollbackResponse:
    success, msg, rec = service.rollback_strategy(
        strategy_id=req.strategy_id,
        rolled_back_by=req.rolled_back_by,
        reason=req.reason,
    )
    if not success or not rec:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    return RollbackResponse(
        rollback_id=rec.rollback_id,
        strategy_id=rec.strategy_id,
        prior_status=rec.prior_status.value,
        trigger_reason=rec.trigger_reason,
        rolled_back_by=rec.rolled_back_by,
        timestamp=rec.timestamp.isoformat(),
    )


# =============================================================================
# FEEDBACK
# =============================================================================

@router.post("/feedback", status_code=status.HTTP_201_CREATED)
def submit_feedback(
    req: UserFeedbackRequest,
    service: LearningService = Depends(get_learning_service),
    user_id: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    accepted, msg = service.submit_user_feedback(
        user_id=user_id,
        target_id=req.target_id,
        feedback_type=req.feedback_type,
        rating=req.rating,
        comment=req.comment,
        scope=req.scope,
    )
    if not accepted:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=msg)
    return {"status": "ok", "message": msg}


# =============================================================================
# STATS & RELIABILITY
# =============================================================================

@router.get("/stats", response_model=LearningStatsResponse)
def get_stats(
    service: LearningService = Depends(get_learning_service),
) -> LearningStatsResponse:
    stats = service.get_stats()
    return LearningStatsResponse(
        total_experiences=stats["total_experiences"],
        total_signals=stats["total_signals"],
        total_strategies=stats["total_strategies"],
        total_failure_patterns=stats["total_failure_patterns"],
        total_experiments=stats["total_experiments"],
        tool_reliabilities=stats["tool_reliabilities"],
        provider_reliabilities=stats["provider_reliabilities"],
    )


# =============================================================================
# TASK 52 CONTINUOUS LEARNING REST APIS
# =============================================================================

from pydantic import BaseModel, Field
from datetime import datetime
from app.learning.schemas import (
    ExperienceSchema,
    GeneralizationScope,
    HeuristicSchema,
    LearningOutcomeSchema,
    LessonSchema,
    LessonType,
    ReplayEvaluationSchema,
    WorkflowPatternSchema,
)


class ExtractLessonRequest(BaseModel):
    statement: str
    lesson_type: LessonType = LessonType.SUCCESS_PATTERN
    source_experiences: list[str] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float = 0.8
    scope: GeneralizationScope = GeneralizationScope.PROJECT
    is_explicit_user_directive: bool = False


class ConsolidateLessonsRequest(BaseModel):
    target_lesson_id: str
    candidate_lesson_id: str


class ReplayExperienceRequest(BaseModel):
    experience_id: str
    simulation_context: dict[str, Any] = Field(default_factory=dict)
    temporal_cutoff: datetime


class RegisterWorkflowRequest(BaseModel):
    name: str
    steps: list[dict[str, Any]]
    preconditions: list[dict[str, Any]] = Field(default_factory=list)
    expected_outcome: dict[str, Any] = Field(default_factory=dict)
    verification: dict[str, Any] = Field(default_factory=dict)
    failure_modes: list[str] = Field(default_factory=list)


class RegisterHeuristicRequest(BaseModel):
    condition: str
    recommendation: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float = 0.7
    scope: GeneralizationScope = GeneralizationScope.TASK
    priority: int = 1


class UserCorrectionRequest(BaseModel):
    target_action: str
    user_directive: str
    scope_hint: str | None = None


class EvaluateOutcomeRequest(BaseModel):
    expected: dict[str, Any]
    actual: dict[str, Any]
    verification_telemetry: dict[str, Any] | None = None
    task_id: str | None = None


@router.get("/continuous/metrics")
def get_continuous_metrics(
    service: LearningService = Depends(get_learning_service),
) -> dict[str, Any]:
    return service.get_continuous_metrics()


@router.post("/continuous/outcomes")
def evaluate_outcome(
    req: EvaluateOutcomeRequest,
    service: LearningService = Depends(get_learning_service),
) -> dict[str, Any]:
    outcome = service.evaluate_task_outcome(
        expected=req.expected,
        actual=req.actual,
        verification_telemetry=req.verification_telemetry,
        task_id=req.task_id,
    )
    return outcome.model_dump()


@router.post("/continuous/lessons")
def extract_lesson(
    req: ExtractLessonRequest,
    service: LearningService = Depends(get_learning_service),
) -> dict[str, Any]:
    try:
        lesson = service.extract_lesson(
            statement=req.statement,
            lesson_type=req.lesson_type,
            source_experiences=req.source_experiences,
            evidence=req.evidence,
            confidence=req.confidence,
            scope=req.scope,
            is_explicit_user_directive=req.is_explicit_user_directive,
        )
        return lesson.model_dump()
    except Exception as ex:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ex))


@router.get("/continuous/lessons")
def list_lessons(
    lesson_type: LessonType | None = Query(None),
    scope: GeneralizationScope | None = Query(None),
    service: LearningService = Depends(get_learning_service),
) -> list[dict[str, Any]]:
    lessons = service.lesson_extractor.list_lessons(lesson_type=lesson_type, scope=scope)
    return [l.model_dump() for l in lessons]


@router.post("/continuous/lessons/consolidate")
def consolidate_lessons(
    req: ConsolidateLessonsRequest,
    service: LearningService = Depends(get_learning_service),
) -> dict[str, Any]:
    try:
        res = service.consolidate_lessons(req.target_lesson_id, req.candidate_lesson_id)
        return res.model_dump()
    except Exception as ex:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ex))


@router.post("/continuous/replays")
def replay_experience(
    req: ReplayExperienceRequest,
    service: LearningService = Depends(get_learning_service),
) -> dict[str, Any]:
    try:
        replay = service.replay_experience(
            experience_id=req.experience_id,
            simulation_context=req.simulation_context,
            temporal_cutoff=req.temporal_cutoff,
        )
        return replay.model_dump()
    except Exception as ex:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ex))


@router.post("/continuous/workflows")
def register_workflow(
    req: RegisterWorkflowRequest,
    service: LearningService = Depends(get_learning_service),
) -> dict[str, Any]:
    wf = service.register_workflow(
        name=req.name,
        steps=req.steps,
        preconditions=req.preconditions,
        expected_outcome=req.expected_outcome,
        verification=req.verification,
        failure_modes=req.failure_modes,
    )
    return wf.model_dump()


@router.get("/continuous/workflows")
def list_workflows(
    status: str | None = Query(None),
    service: LearningService = Depends(get_learning_service),
) -> list[dict[str, Any]]:
    wfs = service.workflow_mgr.list_workflows(status=status)
    return [w.model_dump() for w in wfs]


@router.post("/continuous/heuristics")
def register_heuristic(
    req: RegisterHeuristicRequest,
    service: LearningService = Depends(get_learning_service),
) -> dict[str, Any]:
    try:
        h = service.register_heuristic(
            condition=req.condition,
            recommendation=req.recommendation,
            evidence=req.evidence,
            confidence=req.confidence,
            scope=req.scope,
            priority=req.priority,
        )
        return h.model_dump()
    except Exception as ex:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ex))


@router.get("/continuous/heuristics")
def list_heuristics(
    scope: GeneralizationScope | None = Query(None),
    status: str | None = Query(None),
    service: LearningService = Depends(get_learning_service),
) -> list[dict[str, Any]]:
    heurs = service.heuristic_mgr.list_heuristics(scope=scope, status=status)
    return [h.model_dump() for h in heurs]


@router.post("/continuous/corrections")
def handle_user_correction(
    req: UserCorrectionRequest,
    service: LearningService = Depends(get_learning_service),
) -> dict[str, Any]:
    res = service.handle_user_correction(
        target_action=req.target_action,
        user_directive=req.user_directive,
        scope_hint=req.scope_hint,
    )
    return res.model_dump()


@router.get("/continuous/governance")
def get_governance_policy(
    service: LearningService = Depends(get_learning_service),
) -> dict[str, Any]:
    return service.governance_engine.policy.model_dump()

