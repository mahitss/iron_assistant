"""FastAPI REST API routes for Kairo Autonomous Task Engine (Task 31, Spec 123-126)."""

import asyncio
from datetime import UTC, datetime
import logging
from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.tasks.cancellation import get_cancellation_manager
from app.tasks.models import TaskCheckpointModel, TaskModel, TaskPlanModel, TaskStepModel
from app.tasks.policies import TaskPolicyEngine
from app.tasks.registry import get_task_engine
from app.tasks.scheduler import get_task_scheduler
from app.tasks.schemas import (
    ApprovalActionRequest,
    AutonomyLevel,
    StepStatus,
    TaskBudget,
    TaskCreateRequest,
    TaskPriority,
    TaskResponse,
    TaskResultSummary,
    TaskRiskLevel,
    TaskStatus,
    TaskStepResponse,
    UserPromptResponse,
)
from app.tasks.state import TaskStateMachine

logger = logging.getLogger("kairo.api.tasks")

router = APIRouter(prefix="/tasks", tags=["Autonomous Task Engine"])


def get_current_user_id(x_user_id: Annotated[Optional[str], Header()] = None) -> str:
    """Extract authenticated user ID from request header (Spec 124)."""
    if not x_user_id or not x_user_id.strip():
        return "default_user"
    return x_user_id.strip()


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreateRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> TaskResponse:
    """Create and initiate an objective-oriented autonomous Task (Spec 3, 123, 125)."""
    scheduler = get_task_scheduler()

    # 1. Enforce Per-User and Per-Project Concurrency Limits (Spec 49, 50, 126)
    admit_ok, reason = await scheduler.can_admit_task(user_id, payload.project_id, session)
    if not admit_ok:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=reason)

    # 2. Check for Duplicate Active Task (Spec 51)
    dup_id = await scheduler.check_duplicate_active_task(user_id, payload.objective, session)
    if dup_id:
        logger.info("Found duplicate active task %s for objective", dup_id)
        # Fetch existing task
        existing = await session.get(TaskModel, dup_id)
        if existing:
            return await _format_task_response(existing, session)

    # 3. Create Task Record in Database
    autonomy = payload.autonomy_level or AutonomyLevel.SUPERVISED
    budget_dict = payload.budget.model_dump() if payload.budget else TaskBudget().model_dump()

    task = TaskModel(
        user_id=user_id,
        project_id=payload.project_id,
        objective=payload.objective,  # Immutable original objective (Spec 5)
        status=TaskStatus.QUEUED.value,
        priority=payload.priority.value,
        autonomy_level=autonomy.value,
        budget=budget_dict,
        deadline=payload.deadline,
        metadata_json=payload.metadata,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)

    # 4. Asynchronously launch task engine execution loop
    engine = get_task_engine()
    background_tasks.add_task(
        _run_task_background,
        engine=engine,
        task_id=task.id,
        user_id=user_id,
        objective=task.objective,
        project_id=task.project_id,
        autonomy_level=autonomy,
        budget=payload.budget,
        deadline=payload.deadline,
        dry_run=payload.dry_run,
    )

    return await _format_task_response(task, session)


async def _run_task_background(
    engine: Any,
    task_id: str,
    user_id: str,
    objective: str,
    project_id: str | None,
    autonomy_level: AutonomyLevel,
    budget: TaskBudget | None,
    deadline: datetime | None,
    dry_run: bool,
) -> None:
    """Helper to run the engine loop in background."""
    try:
        await engine.run_task(
            task_id=task_id,
            user_id=user_id,
            objective=objective,
            project_id=project_id,
            autonomy_level=autonomy_level,
            budget=budget,
            deadline=deadline,
            dry_run=dry_run,
        )
    except Exception as e:
        logger.error("Background task %s execution failed: %s", task_id, e)


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    status_filter: Optional[TaskStatus] = Query(None, alias="status"),
    project_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> list[TaskResponse]:
    """List autonomous tasks with filtering (Spec 123)."""
    stmt = select(TaskModel).where(TaskModel.user_id == user_id)
    if status_filter:
        stmt = stmt.where(TaskModel.status == status_filter.value)
    if project_id:
        stmt = stmt.where(TaskModel.project_id == project_id)

    stmt = stmt.order_by(desc(TaskModel.created_at)).offset(offset).limit(limit)
    res = await session.execute(stmt)
    tasks = res.scalars().all()

    return [await _format_task_response(t, session) for t in tasks]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> TaskResponse:
    """Retrieve full task detail including active plan, steps, and progress (Spec 123)."""
    task = await session.get(TaskModel, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if task.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return await _format_task_response(task, session)


@router.post("/{task_id}/pause", response_model=TaskResponse)
async def pause_task(
    task_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> TaskResponse:
    """Pause an active autonomous task (Spec 45, 92)."""
    task = await session.get(TaskModel, task_id)
    if not task or task.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    current_st = TaskStatus(task.status)
    TaskStateMachine.validate_transition(current_st, TaskStatus.PAUSED)

    task.status = TaskStatus.PAUSED.value
    task.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(task)

    return await _format_task_response(task, session)


@router.post("/{task_id}/resume", response_model=TaskResponse)
async def resume_task(
    task_id: str,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> TaskResponse:
    """Resume a paused task after re-validating state and authorization (Spec 45, 94)."""
    task = await session.get(TaskModel, task_id)
    if not task or task.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    current_st = TaskStatus(task.status)
    TaskStateMachine.validate_transition(current_st, TaskStatus.RUNNING)

    task.status = TaskStatus.RUNNING.value
    task.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(task)

    engine = get_task_engine()
    background_tasks.add_task(
        _run_task_background,
        engine=engine,
        task_id=task.id,
        user_id=user_id,
        objective=task.objective,
        project_id=task.project_id,
        autonomy_level=AutonomyLevel(task.autonomy_level),
        budget=TaskBudget(**task.budget) if task.budget else None,
        deadline=task.deadline,
        dry_run=False,
    )

    return await _format_task_response(task, session)


@router.post("/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(
    task_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> TaskResponse:
    """Cooperatively cancel a running task (Spec 42, 43, 92)."""
    task = await session.get(TaskModel, task_id)
    if not task or task.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # Signal cooperative cancellation
    cm = get_cancellation_manager()
    cm.cancel_task(task_id, reason="User requested cancellation via API")

    task.status = TaskStatus.CANCELLED.value
    task.completed_at = datetime.now(UTC)
    task.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(task)

    return await _format_task_response(task, session)


@router.post("/{task_id}/retry", response_model=TaskResponse)
async def retry_task(
    task_id: str,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> TaskResponse:
    """Create a safe new attempt for a failed task (Spec 92, 93)."""
    task = await session.get(TaskModel, task_id)
    if not task or task.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # Reset task to QUEUED
    task.status = TaskStatus.QUEUED.value
    task.started_at = None
    task.completed_at = None
    task.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(task)

    engine = get_task_engine()
    background_tasks.add_task(
        _run_task_background,
        engine=engine,
        task_id=task.id,
        user_id=user_id,
        objective=task.objective,
        project_id=task.project_id,
        autonomy_level=AutonomyLevel(task.autonomy_level),
        budget=TaskBudget(**task.budget) if task.budget else None,
        deadline=task.deadline,
        dry_run=False,
    )

    return await _format_task_response(task, session)


@router.post("/{task_id}/approve", response_model=TaskResponse)
async def approve_step(
    task_id: str,
    payload: ApprovalActionRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> TaskResponse:
    """Approve or reject a step waiting for human approval (Spec 19, 20, 87, 123)."""
    task = await session.get(TaskModel, task_id)
    if not task or task.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # Find step in WAITING_APPROVAL
    stmt = select(TaskStepModel).where(
        TaskStepModel.task_id == task_id,
        TaskStepModel.status == StepStatus.WAITING_APPROVAL.value,
    )
    res = await session.execute(stmt)
    step = res.scalar_one_or_none()

    if not step:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No step awaiting approval")

    if payload.approved:
        step.approval_id = f"appr_{user_id}_{int(datetime.now(UTC).timestamp())}"
        step.status = StepStatus.READY.value
        task.status = TaskStatus.RUNNING.value
    else:
        step.status = StepStatus.FAILED.value
        step.error = f"Approval rejected by user: {payload.reason}"
        task.status = TaskStatus.REPLANNING.value

    task.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(task)

    # Resume execution loop
    if payload.approved:
        engine = get_task_engine()
        background_tasks.add_task(
            _run_task_background,
            engine=engine,
            task_id=task.id,
            user_id=user_id,
            objective=task.objective,
            project_id=task.project_id,
            autonomy_level=AutonomyLevel(task.autonomy_level),
            budget=TaskBudget(**task.budget) if task.budget else None,
            deadline=task.deadline,
            dry_run=False,
        )

    return await _format_task_response(task, session)


@router.post("/{task_id}/respond", response_model=TaskResponse)
async def respond_to_user_prompt(
    task_id: str,
    payload: UserPromptResponse,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> TaskResponse:
    """Submit clarification answer when task is in WAITING_USER state (Spec 64, 65, 88)."""
    task = await session.get(TaskModel, task_id)
    if not task or task.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if task.status != TaskStatus.WAITING_USER.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task is not waiting for user input")

    # Record user response in metadata and resume planning/running
    metadata = dict(task.metadata_json or {})
    metadata["user_clarification"] = payload.response
    task.metadata_json = metadata
    task.status = TaskStatus.PLANNING.value
    task.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(task)

    engine = get_task_engine()
    background_tasks.add_task(
        _run_task_background,
        engine=engine,
        task_id=task.id,
        user_id=user_id,
        objective=f"{task.objective} (User clarified: {payload.response})",
        project_id=task.project_id,
        autonomy_level=AutonomyLevel(task.autonomy_level),
        budget=TaskBudget(**task.budget) if task.budget else None,
        deadline=task.deadline,
        dry_run=False,
    )

    return await _format_task_response(task, session)


@router.get("/{task_id}/activity")
async def get_task_activity(
    task_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Retrieve event activity trail for a task (Spec 68, 70)."""
    task = await session.get(TaskModel, task_id)
    if not task or task.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # Fetch checkpoints as activity milestones
    stmt = (
        select(TaskCheckpointModel)
        .where(TaskCheckpointModel.task_id == task_id)
        .order_by(TaskCheckpointModel.created_at)
    )
    res = await session.execute(stmt)
    ckpts = res.scalars().all()

    return {
        "task_id": task_id,
        "correlation_id": task.correlation_id,
        "status": task.status,
        "milestones": [
            {
                "plan_version": c.plan_version,
                "step_index": c.step_index,
                "timestamp": c.created_at.isoformat(),
                "completed_steps": c.state_data.get("completed_step_ids", []),
            }
            for c in ckpts
        ],
    }


@router.get("/{task_id}/plan")
async def get_task_plans(
    task_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Retrieve plan versions and DAG structure for a task (Spec 6, 37)."""
    task = await session.get(TaskModel, task_id)
    if not task or task.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    stmt = select(TaskPlanModel).where(TaskPlanModel.task_id == task_id).order_by(TaskPlanModel.version)
    res = await session.execute(stmt)
    plans = res.scalars().all()

    return {
        "task_id": task_id,
        "objective": task.objective,
        "plans": [
            {
                "id": p.id,
                "version": p.version,
                "plan_hash": p.plan_hash,
                "supersedes_plan_id": p.supersedes_plan_id,
                "steps": p.steps_data,
                "created_at": p.created_at.isoformat(),
            }
            for p in plans
        ],
    }


# --- Response Helper ---

async def _format_task_response(task: TaskModel, session: AsyncSession) -> TaskResponse:
    """Format SQLAlchemy TaskModel into authoritative TaskResponse DTO."""
    # Fetch steps
    stmt = select(TaskStepModel).where(TaskStepModel.task_id == task.id).order_by(TaskStepModel.sequence)
    res = await session.execute(stmt)
    step_models = res.scalars().all()

    step_responses = [
        TaskStepResponse(
            id=s.id,
            sequence=s.sequence,
            title=s.title,
            objective=s.objective,
            skill_id=s.skill_id,
            tool_name=s.tool_name,
            dependencies=s.dependencies or [],
            status=StepStatus(s.status),
            risk_level=TaskRiskLevel(s.risk_level),
            approval_required=s.approval_required,
            approval_id=s.approval_id,
            retry_count=s.retry_count,
            resources=s.resources or [],
            error=s.error,
            started_at=s.started_at,
            completed_at=s.completed_at,
        )
        for s in step_models
    ]

    total_steps = len(step_responses)
    completed_steps = sum(1 for s in step_responses if s.status == StepStatus.COMPLETED)
    progress_text = f"{completed_steps}/{total_steps} steps complete" if total_steps > 0 else "0/0 steps complete"

    # Pending approval details if any
    pending_appr = None
    for s in step_responses:
        if s.status == StepStatus.WAITING_APPROVAL:
            pending_appr = {
                "step_id": s.id,
                "action": s.title,
                "target": "resource",
                "risk": s.risk_level.value,
            }
            break

    # Waiting user prompt if any
    waiting_user_q = None
    if task.status == TaskStatus.WAITING_USER.value:
        waiting_user_q = (task.metadata_json or {}).get("waiting_question", "Please clarify task parameters.")

    budget_obj = TaskBudget(**task.budget) if task.budget else TaskBudget()
    result_sum = TaskResultSummary(**task.result_summary) if task.result_summary else None

    return TaskResponse(
        id=task.id,
        user_id=task.user_id,
        project_id=task.project_id,
        objective=task.objective,
        status=TaskStatus(task.status),
        priority=TaskPriority(task.priority),
        autonomy_level=AutonomyLevel(task.autonomy_level),
        parent_task_id=task.parent_task_id,
        correlation_id=task.correlation_id,
        current_step_id=task.current_step_id,
        active_plan_id=task.active_plan_id,
        total_steps=total_steps,
        completed_steps=completed_steps,
        progress_text=progress_text,
        budget=budget_obj,
        metadata=task.metadata_json or {},
        result_summary=result_sum,
        deadline=task.deadline,
        started_at=task.started_at,
        completed_at=task.completed_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
        steps=step_responses,
        pending_approval=pending_appr,
        waiting_user_question=waiting_user_q,
    )
