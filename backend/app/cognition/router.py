"""FastAPI REST API router for Kairo Cognitive Planning & Reasoning (Task 41)."""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.cognition.evaluator import PlanEvaluator, PlanValidationReport
from app.cognition.explain import PlanExplainer, PlanPreview, StepExplanation
from app.cognition.goals import Goal, GoalPriority, GoalType
from app.cognition.planner import CognitivePlanner
from app.cognition.plans import Plan, PlanDiff, PlanRiskLevel, PlanStatus
from app.cognition.reasoning import ReasoningMode
from app.cognition.replanner import ReplanReason
from app.cognition.schemas import (
    GoalCreateRequest,
    GoalResponse,
    PlanBuildRequest,
    PlanResponse,
    ReplanApiRequest,
    ReplanApiResponse,
    StepVerifyApiRequest,
    StepVerifyApiResponse,
)

logger = logging.getLogger("kairo.cognition.router")

router = APIRouter(prefix="/cognition", tags=["Cognitive Planning & Reasoning"])

# Central singleton instance for API requests
_planner_instance: CognitivePlanner | None = None


def get_cognitive_planner() -> CognitivePlanner:
    """Dependency provider for the CognitivePlanner service."""
    global _planner_instance
    if _planner_instance is None:
        _planner_instance = CognitivePlanner()
    return _planner_instance


def get_current_user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    """Extract authenticated user ID from request header."""
    if not x_user_id or not x_user_id.strip():
        return "default_user"
    return x_user_id.strip()


def _to_plan_response(plan: Plan, planner: CognitivePlanner) -> PlanResponse:
    """Helper to assemble a comprehensive PlanResponse."""
    validation = PlanEvaluator.evaluate_plan(plan)
    preview = PlanExplainer.generate_preview(plan)
    return PlanResponse(
        plan_id=plan.plan_id,
        goal_id=plan.goal_id,
        user_id=plan.user_id,
        project_id=plan.project_id,
        version=plan.version,
        status=plan.status,
        reasoning_mode=plan.reasoning_mode,
        risk=plan.risk,
        steps=plan.steps,
        success_criteria=plan.success_criteria,
        validation=validation,
        alternatives=[],
        preview=preview,
    )


@router.post("/goals", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
async def create_goal(
    payload: GoalCreateRequest,
    user_id: str = Depends(get_current_user_id),
    planner: CognitivePlanner = Depends(get_cognitive_planner),
) -> GoalResponse:
    """Register a new structured goal for cognitive planning."""
    goal = planner.create_goal(
        description=payload.description,
        user_id=user_id,
        project_id=payload.project_id,
        goal_type=payload.goal_type,
        priority=payload.priority,
        constraints=payload.constraints,
        success_criteria=payload.success_criteria,
        allowed_resources=payload.allowed_resources,
        allowed_environments=payload.allowed_environments,
        deadline=payload.deadline,
    )
    return GoalResponse(
        goal_id=goal.goal_id,
        description=goal.description,
        source=goal.source,
        goal_type=goal.goal_type.value,
        priority=goal.priority.value,
        status=goal.status.value,
        success_criteria=goal.success_criteria,
        created_at=goal.created_at,
        deadline=goal.deadline,
    )


@router.get("/goals/{goal_id}", response_model=GoalResponse)
async def get_goal(
    goal_id: str,
    user_id: str = Depends(get_current_user_id),
    planner: CognitivePlanner = Depends(get_cognitive_planner),
) -> GoalResponse:
    """Retrieve goal details by ID."""
    goal = planner.get_goal(goal_id)
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Goal '{goal_id}' not found.")
    if goal.scope.user_id != user_id and user_id != "default_user":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this goal.")

    return GoalResponse(
        goal_id=goal.goal_id,
        description=goal.description,
        source=goal.source,
        goal_type=goal.goal_type.value,
        priority=goal.priority.value,
        status=goal.status.value,
        success_criteria=goal.success_criteria,
        created_at=goal.created_at,
        deadline=goal.deadline,
    )


@router.post("/goals/{goal_id}/plan", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
async def build_plan_for_goal(
    goal_id: str,
    payload: PlanBuildRequest,
    user_id: str = Depends(get_current_user_id),
    planner: CognitivePlanner = Depends(get_cognitive_planner),
) -> PlanResponse:
    """Generate an execution plan with alternatives and feasibility verification for a goal."""
    goal = planner.get_goal(goal_id)
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Goal '{goal_id}' not found.")
    if goal.scope.user_id != user_id and user_id != "default_user":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this goal.")

    mode = ReasoningMode(payload.reasoning_mode) if payload.reasoning_mode else None
    plan, validation, alternatives = planner.build_plan(
        goal=goal,
        reasoning_mode=mode,
        override_risk=payload.override_risk,
        context=payload.context,
    )

    preview = PlanExplainer.generate_preview(plan)
    return PlanResponse(
        plan_id=plan.plan_id,
        goal_id=plan.goal_id,
        user_id=plan.user_id,
        project_id=plan.project_id,
        version=plan.version,
        status=plan.status,
        reasoning_mode=plan.reasoning_mode,
        risk=plan.risk,
        steps=plan.steps,
        success_criteria=plan.success_criteria,
        validation=validation,
        alternatives=alternatives,
        preview=preview,
    )


@router.get("/plans/{plan_id}", response_model=PlanResponse)
async def get_plan(
    plan_id: str,
    user_id: str = Depends(get_current_user_id),
    planner: CognitivePlanner = Depends(get_cognitive_planner),
) -> PlanResponse:
    """Inspect full plan structure, steps, dependencies, and validation status."""
    plan = planner.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Plan '{plan_id}' not found.")
    if plan.user_id != user_id and user_id != "default_user":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this plan.")

    return _to_plan_response(plan, planner)


@router.post("/plans/{plan_id}/validate", response_model=PlanValidationReport)
async def validate_plan(
    plan_id: str,
    user_id: str = Depends(get_current_user_id),
    planner: CognitivePlanner = Depends(get_cognitive_planner),
) -> PlanValidationReport:
    """Run full feasibility, dependency graph, and security policy checks on a plan."""
    plan = planner.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Plan '{plan_id}' not found.")
    if plan.user_id != user_id and user_id != "default_user":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this plan.")

    return PlanEvaluator.evaluate_plan(plan)


@router.post("/plans/{plan_id}/replan", response_model=ReplanApiResponse)
async def replan_plan_endpoint(
    plan_id: str,
    payload: ReplanApiRequest,
    user_id: str = Depends(get_current_user_id),
    planner: CognitivePlanner = Depends(get_cognitive_planner),
) -> ReplanApiResponse:
    """Trigger adaptive re-planning due to failure, drift, or changed conditions."""
    plan = planner.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Plan '{plan_id}' not found.")
    if plan.user_id != user_id and user_id != "default_user":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this plan.")

    new_plan, diff = planner.replan_plan(
        plan_id=plan_id,
        reason=payload.reason,
        failure_description=payload.observed_failure,
    )

    return ReplanApiResponse(
        new_plan=_to_plan_response(new_plan, planner),
        diff=diff,
    )


@router.post("/plans/{plan_id}/verify-step", response_model=StepVerifyApiResponse)
async def verify_step(
    plan_id: str,
    payload: StepVerifyApiRequest,
    user_id: str = Depends(get_current_user_id),
    planner: CognitivePlanner = Depends(get_cognitive_planner),
) -> StepVerifyApiResponse:
    """Verify execution outcome of a plan step. Enforces anti-self-attestation."""
    plan = planner.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Plan '{plan_id}' not found.")
    if plan.user_id != user_id and user_id != "default_user":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this plan.")

    v_result = planner.verify_step_execution(
        plan_id=plan_id,
        step_id=payload.step_id,
        output_result=payload.output_result,
        current_state=payload.observed_state,
    )

    return StepVerifyApiResponse(
        step_id=v_result.step_id,
        verified=v_result.verified,
        check_type=v_result.check_type,
        evidence=v_result.evidence,
        failure_reason=v_result.failure_reason,
        plan_completed=plan.is_all_completed(),
    )


@router.get("/plans/{plan_id}/preview", response_model=PlanPreview)
async def get_plan_preview(
    plan_id: str,
    user_id: str = Depends(get_current_user_id),
    planner: CognitivePlanner = Depends(get_cognitive_planner),
) -> PlanPreview:
    """Get a concise, user-friendly plan preview."""
    plan = planner.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Plan '{plan_id}' not found.")
    return planner.get_plan_preview(plan_id)


@router.get("/plans/{plan_id}/steps/{step_id}/explain", response_model=StepExplanation)
async def explain_step_endpoint(
    plan_id: str,
    step_id: str,
    user_id: str = Depends(get_current_user_id),
    planner: CognitivePlanner = Depends(get_cognitive_planner),
) -> StepExplanation:
    """Get structured decision factors explaining 'Why this step?'."""
    plan = planner.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Plan '{plan_id}' not found.")
    return planner.explain_step(plan_id, step_id)


@router.get("/dashboard")
async def get_cognitive_dashboard(
    user_id: str = Depends(get_current_user_id),
    planner: CognitivePlanner = Depends(get_cognitive_planner),
) -> dict[str, Any]:
    """Retrieve high-level cognitive telemetry and active plans for UI Command Center."""
    return planner.get_dashboard_summary(user_id)


@router.get("/templates")
async def list_templates(
    planner: CognitivePlanner = Depends(get_cognitive_planner),
) -> list[dict[str, Any]]:
    """List approved, policy-compliant reusable plan templates."""
    return [t.model_dump() for t in planner.strategies.list_templates()]
