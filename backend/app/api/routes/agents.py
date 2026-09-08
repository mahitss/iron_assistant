"""REST API endpoints for Multi-Agent Orchestration inspection and cancellation."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.executor import MultiAgentExecutor
from app.agents.models import AgentTask
from app.agents.schemas import AgentTaskCancelResponse, AgentTaskRead
from app.db.session import get_db_session

logger = logging.getLogger("kairo.api.agents")

router = APIRouter(prefix="/agents", tags=["agents"])


def get_current_user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    """Extract authenticated user ID from request header, defaulting to 'default_user'."""
    if not x_user_id or not x_user_id.strip():
        return "default_user"
    return x_user_id.strip()


@router.post("/tasks/{task_id}/cancel", response_model=AgentTaskCancelResponse)
async def cancel_agent_task(
    task_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> AgentTaskCancelResponse:
    """Request cancellation of an in-flight orchestrated agent plan or task."""
    MultiAgentExecutor.cancel_task(task_id)

    # Check database row if persisted
    stmt = select(AgentTask).where(AgentTask.id == task_id)
    res = await session.execute(stmt)
    task = res.scalar_one_or_none()
    if task:
        if task.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cannot cancel another user's agent task.",
            )
        task.status = "CANCELLED"
        await session.commit()

    return AgentTaskCancelResponse(
        task_id=task_id,
        status="CANCELLED",
        cancelled=True,
    )


@router.get("/tasks/{task_id}", response_model=AgentTaskRead)
async def get_agent_task(
    task_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> AgentTaskRead:
    """Retrieve status and evidence for an agent task with tenant isolation."""
    stmt = select(AgentTask).where(AgentTask.id == task_id)
    res = await session.execute(stmt)
    task = res.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent task '{task_id}' not found.",
        )

    if task.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Cannot inspect another user's agent task.",
        )

    return AgentTaskRead.model_validate(task)
