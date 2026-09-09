"""Crash recovery, idempotency key verification, and restart resumption (Spec 39, 40, 41, 129, 130)."""

import hashlib
import logging
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.models import TaskModel, TaskStepModel
from app.tasks.schemas import StepStatus, TaskStatus

logger = logging.getLogger("kairo.tasks.recovery")


class TaskRecoveryService:
    """Manages crash recovery, idempotency key checks, and safe resumption."""

    @classmethod
    def generate_idempotency_key(cls, task_id: str, step_id: str, attempt: int) -> str:
        """Generate deterministic idempotency key for external mutations (Spec 40)."""
        raw = f"{task_id}:{step_id}:attempt_{attempt}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]

    @classmethod
    async def find_interrupted_tasks(cls, session: AsyncSession) -> list[TaskModel]:
        """Find active tasks that were running when worker process crashed (Spec 129)."""
        active_statuses = [
            TaskStatus.RUNNING.value,
            TaskStatus.PLANNING.value,
            TaskStatus.REPLANNING.value,
            TaskStatus.VERIFYING.value,
        ]
        stmt = select(TaskModel).where(TaskModel.status.in_(active_statuses))
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    async def evaluate_step_execution_state(
        cls,
        session: AsyncSession,
        task_id: str,
        step_id: str,
        idempotency_key: str,
    ) -> Tuple[bool, Optional[dict[str, Any]]]:
        """Determine if a step already completed its write before crash (Spec 130).

        Returns:
            (already_executed, result_reference)
        """
        stmt = select(TaskStepModel).where(
            and_(
                TaskStepModel.task_id == task_id,
                TaskStepModel.id == step_id,
                TaskStepModel.idempotency_key == idempotency_key,
                TaskStepModel.status == StepStatus.COMPLETED.value,
            )
        )
        result = await session.execute(stmt)
        completed_step = result.scalar_one_or_none()
        if completed_step and completed_step.result_reference:
            logger.info("Found completed write for step %s with key %s", step_id, idempotency_key)
            return True, completed_step.result_reference
        return False, None

    @classmethod
    def prepare_resumption(
        cls,
        task: TaskModel,
        checkpoint_data: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Prepare task resumption payload ensuring no blind replay of writes."""
        if not checkpoint_data:
            return {
                "can_resume": False,
                "reason": "No valid checkpoint found to safely resume execution.",
            }

        completed = checkpoint_data.get("completed_step_ids", [])
        pending = checkpoint_data.get("pending_step_ids", [])
        return {
            "can_resume": True,
            "completed_step_ids": completed,
            "pending_step_ids": pending,
            "budget": checkpoint_data.get("budget", {}),
            "step_results": checkpoint_data.get("step_results", {}),
            "plan_version": checkpoint_data.get("plan_version", 1),
        }
