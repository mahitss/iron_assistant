"""FastAPI REST API router for Kairo Strategic Planning Engine (Task 58)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.planning.engine import strategic_planning_engine
from app.planning.safety import (
    PlanningExecutionBoundaryError,
    PlanStaleError,
)
from app.planning.schemas import (
    CurrentStateAssessment,
    DesiredStateDefinition,
    PlanOutcome,
    StrategicPlan,
    StrategyOption,
)
from app.planning.service import planning_service

router = APIRouter(prefix="/api/v1/planning", tags=["planning"])


# Request payload models
class CreatePlanRequest(BaseModel):
    name: str
    purpose: str
    current_state: CurrentStateAssessment
    desired_state: DesiredStateDefinition
    goal_id: str | None = None
    strategy_option: StrategyOption | None = None
    author: str = "SYSTEM_USER"
    deadline: datetime | None = None
    decision_id: str | None = None


class ValidatePlanRequest(BaseModel):
    known_resources: dict[str, float] | None = None


class ActionRequest(BaseModel):
    actor: str = "OPERATOR"
    reason: str = "Manual operation"


class ReplanRequest(BaseModel):
    actor: str = "SYSTEM_REPLANNER"
    reason: str
    modifications: list[dict[str, Any]] | None = None


class RecordOutcomeRequest(BaseModel):
    success: bool
    actual_duration_hours: float
    actual_cost: float = 0.0
    lessons_learned: list[str] = Field(default_factory=list)


@router.post("/plans", response_model=StrategicPlan)
async def create_plan(payload: CreatePlanRequest) -> StrategicPlan:
    """Create and register a new strategic living plan."""
    try:
        return planning_service.create_plan(
            name=payload.name,
            purpose=payload.purpose,
            current_state=payload.current_state,
            desired_state=payload.desired_state,
            goal_id=payload.goal_id,
            strategy_option=payload.strategy_option,
            author=payload.author,
            deadline=payload.deadline,
            decision_id=payload.decision_id,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/plans", response_model=list[StrategicPlan])
async def list_plans() -> list[StrategicPlan]:
    """List all registered strategic plans."""
    return planning_service.list_plans()


@router.get("/plans/{plan_id}", response_model=StrategicPlan)
async def get_plan(plan_id: str) -> StrategicPlan:
    """Get a strategic plan by ID."""
    plan = planning_service.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan '{plan_id}' not found.")
    return plan


@router.post("/plans/{plan_id}/validate")
async def validate_plan(plan_id: str, payload: ValidatePlanRequest | None = None) -> dict[str, Any]:
    """Validate graph integrity, cycle absence, resources, and freshness."""
    known_res = payload.known_resources if payload else None
    result = planning_service.validate_plan(plan_id, known_resources=known_res)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/plans/{plan_id}/analyze")
async def analyze_plan(plan_id: str) -> dict[str, Any]:
    """Perform CPM critical path, duration, wave, and risk analysis."""
    result = planning_service.analyze_plan(plan_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/plans/{plan_id}/start")
async def start_plan(plan_id: str, payload: ActionRequest | None = None) -> dict[str, Any]:
    """Start plan execution wave sequencing."""
    actor = payload.actor if payload else "OPERATOR"
    try:
        ok, msg = planning_service.start_plan(plan_id, actor=actor)
        if not ok:
            raise HTTPException(status_code=400, detail=msg)
        return {"success": True, "message": msg}
    except PlanStaleError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.post("/plans/{plan_id}/pause")
async def pause_plan(plan_id: str, payload: ActionRequest | None = None) -> dict[str, Any]:
    """Pause plan execution."""
    actor = payload.actor if payload else "OPERATOR"
    reason = payload.reason if payload else "Operator pause request"
    ok, msg = planning_service.pause_plan(plan_id, actor=actor, reason=reason)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}


@router.post("/plans/{plan_id}/resume")
async def resume_plan(plan_id: str, payload: ActionRequest | None = None) -> dict[str, Any]:
    """Resume a paused plan."""
    actor = payload.actor if payload else "OPERATOR"
    try:
        ok, msg = planning_service.resume_plan(plan_id, actor=actor)
        if not ok:
            raise HTTPException(status_code=400, detail=msg)
        return {"success": True, "message": msg}
    except PlanStaleError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.post("/plans/{plan_id}/cancel")
async def cancel_plan(plan_id: str, payload: ActionRequest | None = None) -> dict[str, Any]:
    """Cancel a plan."""
    actor = payload.actor if payload else "OPERATOR"
    reason = payload.reason if payload else "Operator cancellation"
    ok, msg = planning_service.cancel_plan(plan_id, actor=actor, reason=reason)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}


@router.post("/plans/{plan_id}/replan", response_model=StrategicPlan)
async def replan(plan_id: str, payload: ReplanRequest) -> StrategicPlan:
    """Create a new plan revision preserving historical snapshots."""
    try:
        return planning_service.replan(
            plan_id=plan_id,
            actor=payload.actor,
            reason=payload.reason,
            new_tasks=payload.modifications,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/plans/{plan_id}/progress")
async def get_progress(plan_id: str) -> dict[str, Any]:
    """Get holistic outcome-based and milestone progress."""
    result = planning_service.get_progress(plan_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/plans/{plan_id}/timeline")
async def get_timeline(plan_id: str) -> dict[str, Any]:
    """Get execution wave timeline and critical path timings."""
    result = planning_service.get_timeline(plan_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/plans/{plan_id}/dependencies")
async def get_dependencies(plan_id: str) -> dict[str, Any]:
    """Get task dependency graph adjacency and cycle detection status."""
    result = planning_service.get_dependencies(plan_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/plans/{plan_id}/risks")
async def get_risks(plan_id: str) -> dict[str, Any]:
    """Get multi-level risk register and rollback plan."""
    result = planning_service.get_risks(plan_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/plans/{plan_id}/outcomes")
async def get_outcomes(plan_id: str) -> list[dict[str, Any]]:
    """Get recorded execution outcomes for plan."""
    return planning_service.get_outcomes(plan_id)


@router.post("/plans/{plan_id}/outcomes", response_model=PlanOutcome)
async def record_outcome(plan_id: str, payload: RecordOutcomeRequest) -> PlanOutcome:
    """Record verified post-execution outcome and calibrate future estimations."""
    try:
        return planning_service.record_outcome(
            plan_id=plan_id,
            success=payload.success,
            actual_duration_hours=payload.actual_duration_hours,
            actual_cost=payload.actual_cost,
            lessons_learned=payload.lessons_learned,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/plans/{plan_id}/proposal")
async def get_execution_proposal(plan_id: str) -> dict[str, Any]:
    """Generate execution proposal for handoff to Autonomous Execution / Policy Engine."""
    plan = planning_service.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan '{plan_id}' not found.")
    try:
        return strategic_planning_engine.generate_execution_proposal(plan)
    except PlanningExecutionBoundaryError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


@router.get("/plans/{plan_id}/audit")
async def get_audit(plan_id: str) -> list[dict[str, Any]]:
    """Retrieve tamper-evident audit trail for plan."""
    return planning_service.get_audit_trail(plan_id)
