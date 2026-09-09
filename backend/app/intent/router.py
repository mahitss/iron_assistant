"""REST API endpoints for Kairo Unified Command, Intent, and Control Layer (Task 35, Spec 122, 123) and Task 48."""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.intent.commands import CommandService
from app.intent.motivation import MotivationEngine
from app.intent.parser import IntentParser
from app.intent.planner_bridge import CommandRouter
from app.intent.safety import IntentSecurityViolation
from app.intent.schemas import (
    CommandCreateRequest,
    CommandResolveRequest,
    CommandResponse,
    GoalStatus,
    IntentSchema,
    UrgencyLevel,
)
from app.intent.service import get_intent_service

logger = logging.getLogger("kairo.intent.router")

router = APIRouter(prefix="/commands", tags=["commands"])
commands_router = router



def get_current_user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    """Extract authenticated user ID from request header, defaulting to 'default_user'."""
    if not x_user_id or not x_user_id.strip():
        return "default_user"
    return x_user_id.strip()


@router.post("", response_model=CommandResponse, status_code=status.HTTP_200_OK)
async def submit_command(
    request: CommandCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db_session: AsyncSession = Depends(get_db_session),
) -> CommandResponse:
    """
    Submits a natural-language command, extracts structured intent, resolves references,
    persists records, and delegates execution or clarification.
    """
    try:
        cmd_schema, intent_schema = IntentParser.parse_command(
            raw_text=request.text,
            user_id=user_id,
            session_id=request.session_id,
            conversation_id=request.conversation_id,
            attachments=request.attachments,
            source_interface=request.source_interface,
            project_hint=request.project_hint,
            clarification_response=request.clarification_response,
        )

        # Persist command and intent
        await CommandService.record_command_and_intent(
            db_session=db_session,
            command_schema=cmd_schema,
            intent_schema=intent_schema,
        )

        # Route to domain subsystems if unambiguous and valid
        exec_summary = await CommandRouter.route_intent(
            intent=intent_schema,
            user_id=user_id,
            db_session=db_session,
        )

        return CommandResponse(
            command_id=cmd_schema.command_id,
            intent=intent_schema,
            ambiguity=intent_schema.ambiguity,
            execution_summary=exec_summary,
        )
    except Exception as exc:
        logger.error("Error processing command: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Command processing error: {str(exc)}",
        )


@router.post("/resolve", response_model=CommandResponse, status_code=status.HTTP_200_OK)
async def resolve_command(
    request: CommandResolveRequest,
    user_id: str = Depends(get_current_user_id),
) -> CommandResponse:
    """
    Spec 123: Resolve-only endpoint that analyzes intent and references without executing.
    Returns: intent, resolved references, ambiguity, risk, next action.
    """
    try:
        cmd_schema, intent_schema = IntentParser.parse_command(
            raw_text=request.text,
            user_id=user_id,
            session_id=request.session_id,
            conversation_id=request.conversation_id,
            attachments=request.attachments,
            source_interface=request.source_interface,
            project_hint=request.project_hint,
        )

        return CommandResponse(
            command_id=cmd_schema.command_id,
            intent=intent_schema,
            ambiguity=intent_schema.ambiguity,
            execution_summary={"status": "RESOLVED_ONLY", "executed": False},
        )
    except Exception as exc:
        logger.error("Error resolving command: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Command resolution error: {str(exc)}",
        )


@router.get("/{command_id}", response_model=dict[str, Any], status_code=status.HTTP_200_OK)
async def get_command(
    command_id: str,
    user_id: str = Depends(get_current_user_id),
    db_session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Retrieve details of a previously submitted command, enforcing user tenant isolation."""
    cmd = await CommandService.get_command(
        db_session=db_session,
        command_id=command_id,
        user_id=user_id,
    )
    if not cmd:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Command '{command_id}' not found.",
        )

    intents_data = []
    for i in cmd.intents:
        intents_data.append({
            "id": i.id,
            "type": i.type,
            "objective": i.objective,
            "risk": i.risk,
            "status": i.status,
            "confidence": i.confidence,
            "target": i.target_json,
            "ambiguity": i.ambiguity_json,
            "created_at": i.created_at.isoformat(),
        })

    return {
        "command_id": cmd.id,
        "user_id": cmd.user_id,
        "session_id": cmd.session_id,
        "conversation_id": cmd.conversation_id,
        "text": cmd.text,
        "original_text": cmd.original_text,
        "source_interface": cmd.source_interface,
        "project_hint": cmd.project_hint,
        "attachments": cmd.attachments_json,
        "created_at": cmd.created_at.isoformat(),
        "intents": intents_data,
    }


# ============================================================================
# Task 48: Intent, Goal, & Motivation Engine REST Router
# ============================================================================

intent_router = APIRouter(prefix="/intent", tags=["intent"])


class IntentParseRequest(BaseModel):
    raw_text: str = Field(..., min_length=1, description="Raw natural-language input from user")
    session_id: str | None = None
    conversation_id: str | None = None
    project_id: str | None = None
    environment: str = "DEVELOPMENT"
    user_timezone: str = "UTC"
    source: str = "DIRECT_USER"


class CreateGoalRequest(BaseModel):
    intent_id: str
    description: str
    desired_state: dict[str, Any] = Field(default_factory=dict)
    success_criteria: list[dict[str, Any]] = Field(default_factory=list)
    scope: dict[str, Any] = Field(default_factory=dict)
    constraints: list[dict[str, Any]] = Field(default_factory=list)
    priority: str = "NORMAL"
    deadline: str | None = None


class AnswerClarificationRequest(BaseModel):
    clarification_id: str
    answer: str = Field(..., min_length=1)


class UserCorrectionRequest(BaseModel):
    session_id: str
    intent_id: str
    correction_text: str = Field(..., min_length=1)
    revised_objective: str | None = None


class RevokeIntentRequest(BaseModel):
    intent_id: str
    reason: str | None = None


class TradeoffAnalysisRequest(BaseModel):
    goal_a: str
    goal_b: str
    cost_a: float = 0.0
    cost_b: float = 0.0
    benefit_a: str = ""
    benefit_b: str = ""
    constraints: list[str] = Field(default_factory=list)


@intent_router.post("/parse", response_model=dict[str, Any], status_code=status.HTTP_200_OK)
async def parse_and_understand_intent(
    request: IntentParseRequest,
    user_id: str = Depends(get_current_user_id),
    intent_svc: Any = Depends(get_intent_service),
) -> dict[str, Any]:
    """Parse, understand, extract goals/constraints/entities, and gate ambiguity (Spec 1-65)."""
    try:
        result = intent_svc.parse_and_understand(
            raw_text=request.raw_text,
            user_id=user_id,
            session_id=request.session_id,
            conversation_id=request.conversation_id,
            project_id=request.project_id,
            environment=request.environment,
            user_timezone=request.user_timezone,
            source=request.source,
        )
        return result
    except IntentSecurityViolation as sec_exc:
        logger.warning("Intent safety violation: %s", sec_exc)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Intent safety violation: {str(sec_exc)}",
        )
    except Exception as exc:
        logger.error("Error understanding intent: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Intent understanding failed: {str(exc)}",
        )


@intent_router.get("/intents", response_model=list[dict[str, Any]], status_code=status.HTTP_200_OK)
async def list_intents(
    user_id: str = Depends(get_current_user_id),
    intent_svc: Any = Depends(get_intent_service),
) -> list[dict[str, Any]]:
    """List all registered intents for the current authenticated user."""
    return intent_svc.list_intents(user_id=user_id)


@intent_router.get("/intents/{intent_id}", response_model=dict[str, Any], status_code=status.HTTP_200_OK)
async def get_intent_by_id(
    intent_id: str,
    user_id: str = Depends(get_current_user_id),
    intent_svc: Any = Depends(get_intent_service),
) -> dict[str, Any]:
    """Retrieve details of an understood intent."""
    record = intent_svc.get_intent(intent_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Intent '{intent_id}' not found.",
        )
    return record


@intent_router.post("/goals", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_goal(
    request: CreateGoalRequest,
    user_id: str = Depends(get_current_user_id),
    intent_svc: Any = Depends(get_intent_service),
) -> dict[str, Any]:
    """Explicitly create a Goal record distinct from execution tasks (Spec 9-14)."""
    try:
        goal = intent_svc.goals.create_goal(
            intent_id=request.intent_id,
            description=request.description,
            desired_state=request.desired_state,
            success_criteria=request.success_criteria,
            scope=request.scope,
            constraints=request.constraints,
            priority=UrgencyLevel(request.priority) if request.priority in UrgencyLevel.__members__ else UrgencyLevel.NORMAL,
            deadline=request.deadline,
            owner=user_id,
        )
        return goal.to_dict()
    except Exception as exc:
        logger.error("Error creating goal: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Goal creation failed: {str(exc)}",
        )


@intent_router.get("/goals", response_model=list[dict[str, Any]], status_code=status.HTTP_200_OK)
async def list_goals(
    status_filter: str | None = None,
    user_id: str = Depends(get_current_user_id),
    intent_svc: Any = Depends(get_intent_service),
) -> list[dict[str, Any]]:
    """List goals with optional status filter."""
    g_status = GoalStatus(status_filter) if status_filter and status_filter in GoalStatus.__members__ else None
    return [g.to_dict() for g in intent_svc.goals.list_goals(status=g_status, owner=user_id)]


@intent_router.post("/clarify", response_model=dict[str, Any], status_code=status.HTTP_200_OK)
async def answer_clarification(
    request: AnswerClarificationRequest,
    intent_svc: Any = Depends(get_intent_service),
) -> dict[str, Any]:
    """Provide answer to an ambiguity clarification request to unlock goal planning (Spec 58-62)."""
    try:
        return intent_svc.answer_clarification(
            clarification_id=request.clarification_id,
            answer=request.answer,
        )
    except KeyError as k_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(k_err),
        )


@intent_router.post("/correct", response_model=dict[str, Any], status_code=status.HTTP_200_OK)
async def apply_user_correction(
    request: UserCorrectionRequest,
    intent_svc: Any = Depends(get_intent_service),
) -> dict[str, Any]:
    """Handle user feedback ('That's not what I meant') non-defensively and revise intent (Spec 67-69)."""
    try:
        return intent_svc.apply_user_correction(
            session_id=request.session_id,
            intent_id=request.intent_id,
            correction_text=request.correction_text,
            revised_objective=request.revised_objective,
        )
    except Exception as exc:
        logger.error("Error applying user correction: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Correction processing failed: {str(exc)}",
        )


@intent_router.post("/revoke", response_model=dict[str, Any], status_code=status.HTTP_200_OK)
async def revoke_intent(
    request: RevokeIntentRequest,
    user_id: str = Depends(get_current_user_id),
    intent_svc: Any = Depends(get_intent_service),
) -> dict[str, Any]:
    """Revoke an active intent and propagate cancellation down to planned goals/tasks (Spec 186-187)."""
    try:
        return intent_svc.revoke_intent(
            intent_id=request.intent_id,
            user_id=user_id,
            reason=request.reason,
        )
    except PermissionError as p_err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(p_err),
        )
    except KeyError as k_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(k_err),
        )


@intent_router.get("/graph/{intent_id}", response_model=dict[str, Any], status_code=status.HTTP_200_OK)
async def get_intent_graph(
    intent_id: str,
    intent_svc: Any = Depends(get_intent_service),
) -> dict[str, Any]:
    """Retrieve full DAG graph representation (Intent -> Goal -> Objectives -> Constraints -> Tasks -> Outcomes)."""
    return intent_svc.get_intent_graph(intent_id)


@intent_router.post("/tradeoffs", response_model=dict[str, Any], status_code=status.HTTP_200_OK)
async def analyze_tradeoffs(
    request: TradeoffAnalysisRequest,
) -> dict[str, Any]:
    """Evaluate and surface tradeoffs between conflicting goals (Spec 82-84)."""
    tradeoff = MotivationEngine.analyze_tradeoff(
        goal_a=request.goal_a,
        goal_b=request.goal_b,
        cost_a=request.cost_a,
        cost_b=request.cost_b,
        benefit_a=request.benefit_a,
        benefit_b=request.benefit_b,
        constraints=request.constraints,
    )
    return tradeoff.to_dict()


@intent_router.get("/health", response_model=dict[str, Any], status_code=status.HTTP_200_OK)
async def get_intent_engine_health(
    intent_svc: Any = Depends(get_intent_service),
) -> dict[str, Any]:
    """Retrieve Intent & Motivation engine health metrics, active goals, and calibration ratios."""
    return intent_svc.get_health_metrics()

