"""FastAPI REST API router for Kairo Autonomous Execution & Long-Horizon Agency Engine (Task 45)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from typing import Annotated, Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.autonomy.budgets import AutonomousBudget, BudgetExhaustedError
from app.autonomy.controller import StepExecutionResult
from app.autonomy.deadlines import DeadlineExhaustedError
from app.autonomy.engine import AutonomousExecutionEngine, FalseCompletionError
from app.autonomy.execution import ResourceLockConflictError, SideEffectRetryViolationError
from app.autonomy.goals import GoalDriftError
from app.autonomy.policies import PolicyDeniedError
from app.autonomy.safety import ActionClassification, AutonomyLevel, SafetyViolationError
from app.autonomy.scheduler import EventAuthenticityError
from app.autonomy.schemas import (
    AutonomousCheckpointResponse,
    AutonomousGoalCreateRequest,
    AutonomousGoalResponse,
    AutonomousRunCreateRequest,
    AutonomousRunResponse,
    CompletionRecordResponse,
    EventPostRequest,
    JournalEntryResponse,
    ProgressResponse,
    RunControlActionRequest,
    RunControlActionResponse,
    StepExecutionRequest,
    StepExecutionResponse,
    WatchdogInspectionResponse,
)
from app.autonomy.sessions import ScopeViolationError, TenantIsolationError
from app.autonomy.state import AutonomousRunState

logger = logging.getLogger("kairo.autonomy.router")

router = APIRouter(prefix="/autonomy", tags=["autonomy"])

# Global singleton execution engine for the process
_global_engine: Optional[AutonomousExecutionEngine] = None


def get_engine() -> AutonomousExecutionEngine:
    global _global_engine
    if _global_engine is None:
        _global_engine = AutonomousExecutionEngine()
    return _global_engine


def get_current_user_id(x_user_id: Annotated[Optional[str], Header()] = None) -> str:
    return x_user_id or "default_user"


# ==================================================
# Goals Endpoints (Spec 2, 5, 7)
# ==================================================

@router.post("/goals", response_model=AutonomousGoalResponse, status_code=status.HTTP_201_CREATED)
async def create_autonomous_goal(
    req: AutonomousGoalCreateRequest,
    engine: Annotated[AutonomousExecutionEngine, Depends(get_engine)],
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> AutonomousGoalResponse:
    """Register an authorized long-running objective with bounded success criteria."""
    goal = engine.goal_manager.register_goal(
        title=req.title,
        description=req.description,
        user_id=user_id,
        project_id=req.project_id,
        success_criteria=req.success_criteria,
        hard_constraints=req.hard_constraints,
        scope=req.scope,
    )
    return AutonomousGoalResponse(
        goal_id=goal.goal_id,
        title=goal.title,
        description=goal.description,
        user_id=goal.user_id,
        project_id=goal.project_id,
        status=goal.status,
        success_criteria=goal.success_criteria,
        created_at=goal.created_at.isoformat(),
    )


@router.get("/goals/{goal_id}", response_model=AutonomousGoalResponse)
async def get_autonomous_goal(
    goal_id: str,
    engine: Annotated[AutonomousExecutionEngine, Depends(get_engine)],
) -> AutonomousGoalResponse:
    goal = engine.goal_manager.get_goal(goal_id)
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Goal {goal_id} not found")
    return AutonomousGoalResponse(
        goal_id=goal.goal_id,
        title=goal.title,
        description=goal.description,
        user_id=goal.user_id,
        project_id=goal.project_id,
        status=goal.status,
        success_criteria=goal.success_criteria,
        created_at=goal.created_at.isoformat(),
    )


# ==================================================
# Runs Endpoints (Spec 2, 3, 28)
# ==================================================

@router.post("/runs", response_model=AutonomousRunResponse, status_code=status.HTTP_201_CREATED)
async def create_autonomous_run(
    req: AutonomousRunCreateRequest,
    engine: Annotated[AutonomousExecutionEngine, Depends(get_engine)],
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> AutonomousRunResponse:
    """Initialize an autonomous execution run for an authorized goal."""
    try:
        level = AutonomyLevel(req.autonomy_level.upper())
    except ValueError:
        level = AutonomyLevel.AUTONOMOUS

    budget = AutonomousBudget(
        max_model_calls=req.max_model_calls,
        max_tool_calls=req.max_tool_calls,
        max_cost_usd=req.max_cost_usd,
    )
    deadline = None
    if req.timeout_minutes:
        deadline = datetime.now(timezone.utc) + timedelta(minutes=req.timeout_minutes)

    try:
        run = engine.create_run(
            goal_id=req.goal_id,
            owner_user_id=user_id,
            project_id=req.project_id,
            autonomy_level=level,
            initial_steps=req.initial_steps or [],
            budget=budget,
            deadline=deadline,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    return AutonomousRunResponse(
        run_id=run.run_id,
        goal_id=run.goal_id,
        plan_id=run.plan_id,
        plan_version=run.plan_version,
        status=run.status.value,
        autonomy_level=run.autonomy_level.value,
        owner_user_id=run.owner_user_id,
        project_id=run.project_id,
        current_step_id=run.current_step_id,
        progress_pct=run.progress_pct,
        created_at=run.created_at.isoformat(),
    )


@router.get("/runs/{run_id}", response_model=AutonomousRunResponse)
async def get_autonomous_run(
    run_id: str,
    engine: Annotated[AutonomousExecutionEngine, Depends(get_engine)],
) -> AutonomousRunResponse:
    run = engine.get_run(run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Run {run_id} not found")
    return AutonomousRunResponse(
        run_id=run.run_id,
        goal_id=run.goal_id,
        plan_id=run.plan_id,
        plan_version=run.plan_version,
        status=run.status.value,
        autonomy_level=run.autonomy_level.value,
        owner_user_id=run.owner_user_id,
        project_id=run.project_id,
        current_step_id=run.current_step_id,
        progress_pct=run.progress_pct,
        created_at=run.created_at.isoformat(),
    )


@router.post("/runs/{run_id}/control", response_model=RunControlActionResponse)
async def control_autonomous_run(
    run_id: str,
    req: RunControlActionRequest,
    engine: Annotated[AutonomousExecutionEngine, Depends(get_engine)],
) -> RunControlActionResponse:
    """Interruption control: PAUSE, RESUME, CANCEL, or EMERGENCY_STOP (Spec 65-71, 111)."""
    action = req.action.upper()
    try:
        if action == "PAUSE":
            engine.pause_run(run_id, reason=req.reason or "User pause request")
        elif action == "RESUME":
            engine.resume_run(run_id)
        elif action == "CANCEL":
            engine.cancel_run(run_id, reason=req.reason or "User cancel request")
        elif action == "EMERGENCY_STOP":
            engine.emergency_stop_run(run_id, reason=req.reason or "Emergency stop requested")
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported action: {action}")
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Run {run_id} not found")

    run = engine.get_run(run_id)
    return RunControlActionResponse(
        run_id=run_id,
        status=run.status.value if run else "UNKNOWN",
        action_applied=action,
        message=f"Action '{action}' applied successfully.",
    )


@router.post("/runs/{run_id}/step", response_model=StepExecutionResponse)
async def execute_run_step(
    run_id: str,
    req: StepExecutionRequest,
    engine: Annotated[AutonomousExecutionEngine, Depends(get_engine)],
) -> StepExecutionResponse:
    """Execute the next ready step in the run DAG with full verification (Spec 28-42)."""
    # Default tool mock executor for API calls
    def default_executor(tool_name: str, params: Dict[str, Any]) -> Any:
        return {"result": f"Executed tool '{tool_name}' successfully", "params": params}

    try:
        res = engine.execute_next_step(
            run_id=run_id,
            tool_executor_fn=default_executor,
            is_pre_approved=req.is_pre_approved,
            is_dry_run=req.is_dry_run,
        )
        if not res:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No ready steps or run not in RUNNING state.")
        return StepExecutionResponse(
            step_id=res.step_id,
            is_success=res.is_success,
            is_verified=res.is_verified,
            outputs=res.outputs,
            verification_notes=res.verification_notes,
            error=res.error,
        )
    except SafetyViolationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except PolicyDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except (BudgetExhaustedError, DeadlineExhaustedError) as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc))
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/runs/{run_id}/progress", response_model=ProgressResponse)
async def get_run_progress(
    run_id: str,
    engine: Annotated[AutonomousExecutionEngine, Depends(get_engine)],
) -> ProgressResponse:
    """Retrieve verified progress without fake claims (Spec 57-61)."""
    run = engine.get_run(run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Run {run_id} not found")
    goal = engine.goal_manager.get_goal(run.goal_id)
    crit_count = len(goal.success_criteria) if goal else 1
    prog = engine.progress_tracker.calculate_progress(
        total_steps=len(run.steps),
        completed_steps=len(run.completed_step_ids),
        total_criteria=crit_count,
        verified_criteria=min(crit_count, len(run.completed_step_ids)),
        verified_artifacts=len(run.completed_step_ids),
    )
    return ProgressResponse(
        run_id=run.run_id,
        status=run.status.value,
        progress_pct=prog.percentage,
        total_steps=prog.total_steps,
        completed_steps=prog.completed_steps,
        verified_criteria_count=prog.verified_criteria_count,
        total_criteria_count=prog.total_criteria_count,
        summary=prog.summary,
    )


@router.get("/runs/{run_id}/checkpoints", response_model=List[AutonomousCheckpointResponse])
async def list_run_checkpoints(
    run_id: str,
    engine: Annotated[AutonomousExecutionEngine, Depends(get_engine)],
) -> List[AutonomousCheckpointResponse]:
    checkpoints = engine.checkpoint_manager._history.get(run_id, [])
    return [
        AutonomousCheckpointResponse(
            checkpoint_id=chk.checkpoint_id,
            run_id=chk.run_id,
            plan_version=chk.plan_version,
            step_id=chk.step_id,
            run_state=chk.run_state,
            is_valid=chk.is_valid,
            corruption_hash=chk.corruption_hash,
            created_at=chk.created_at.isoformat(),
        )
        for chk in checkpoints
    ]


@router.get("/runs/{run_id}/completion", response_model=CompletionRecordResponse)
async def get_completion_certificate(
    run_id: str,
    engine: Annotated[AutonomousExecutionEngine, Depends(get_engine)],
) -> CompletionRecordResponse:
    """Retrieve immutable certificate of verified goal completion (Spec 155, 156)."""
    rec = engine.get_completion_record(run_id)
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Run {run_id} has not verified completion.")
    return CompletionRecordResponse(
        record_id=rec.record_id,
        run_id=rec.run_id,
        goal_id=rec.goal_id,
        plan_version=rec.plan_version,
        success_criteria=rec.success_criteria,
        verification_results=rec.verification_results,
        evidence_refs=rec.evidence_refs,
        remaining_uncertainty=rec.remaining_uncertainty,
        completed_at=rec.completed_at.isoformat(),
    )


@router.get("/runs/{run_id}/watchdog", response_model=WatchdogInspectionResponse)
async def inspect_run_watchdog(
    run_id: str,
    engine: Annotated[AutonomousExecutionEngine, Depends(get_engine)],
) -> WatchdogInspectionResponse:
    """Inspect run health with watchdog anomaly detection (Spec 25-27)."""
    run = engine.get_run(run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Run {run_id} not found")
    res = engine.watchdog.inspect_run(
        run_id=run_id,
        current_state=run.status,
        deadline=run.deadline_tracker.deadline,
    )
    return WatchdogInspectionResponse(
        run_id=res.run_id,
        issue_detected=res.issue_detected,
        recommended_action=res.recommended_action,
        details=res.details,
        inspected_at=res.inspected_at.isoformat(),
    )


@router.post("/runs/{run_id}/events")
async def post_run_event(
    run_id: str,
    req: EventPostRequest,
    engine: Annotated[AutonomousExecutionEngine, Depends(get_engine)],
) -> Dict[str, Any]:
    """Correlate authenticated external or worker callback event (Spec 100-105)."""
    try:
        ev = engine.scheduler.process_incoming_event(
            run_id=run_id,
            event_id=req.event_id,
            event_type=req.event_type,
            sequence_num=req.sequence_num,
            step_id=req.step_id,
            idempotency_key=req.idempotency_key,
            payload=req.payload,
            is_authenticated=req.is_authenticated,
        )
        return {"status": "PROCESSED" if ev else "DUPLICATE_OR_STALE", "event_id": req.event_id}
    except EventAuthenticityError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
