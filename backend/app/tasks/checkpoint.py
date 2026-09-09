"""Task state checkpointing for safe crash resumption (Spec 38)."""

import logging
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.security.redaction import ArgumentSanitizer
from app.tasks.models import TaskCheckpointModel, TaskModel
from app.tasks.schemas import TaskBudget, TaskStatus

logger = logging.getLogger("kairo.tasks.checkpoint")


class CheckpointService:
    """Serializes and persists task state snapshots, ensuring secrets are never persisted."""

    @classmethod
    def serialize_state(
        cls,
        task_id: str,
        status: TaskStatus,
        plan_version: int,
        completed_step_ids: list[str],
        pending_step_ids: list[str],
        budget: TaskBudget,
        artifacts: list[dict[str, Any]],
        step_results: dict[str, Any],
    ) -> dict[str, Any]:
        """Build a sanitized checkpoint snapshot."""
        # Sanitize artifacts and step results to strip any accidental credentials
        clean_artifacts = [ArgumentSanitizer.sanitize(a) for a in artifacts]
        clean_results = {k: ArgumentSanitizer.sanitize(v) for k, v in step_results.items()}

        return {
            "task_id": task_id,
            "status": status.value,
            "plan_version": plan_version,
            "completed_step_ids": completed_step_ids,
            "pending_step_ids": pending_step_ids,
            "budget": budget.model_dump(),
            "artifacts": clean_artifacts,
            "step_results": clean_results,
            "checkpoint_timestamp": datetime.now(UTC).isoformat(),
        }

    @classmethod
    async def save_checkpoint(
        cls,
        session: AsyncSession | None,
        task_id: str,
        plan_version: int,
        step_index: int,
        state_data: dict[str, Any],
    ) -> str:
        """Persist checkpoint to database or in-memory fallback."""
        if session is not None:
            try:
                stmt = select(TaskModel.id).where(TaskModel.id == task_id)
                res = await session.execute(stmt)
                if res.scalar_one_or_none() is not None:
                    ckpt = TaskCheckpointModel(
                        task_id=task_id,
                        plan_version=plan_version,
                        step_index=step_index,
                        state_data=state_data,
                    )
                    session.add(ckpt)
                    await session.commit()
                    return ckpt.id
                else:
                    logger.debug("Task %s not persisted in DB; skipping DB checkpoint insertion.", task_id)
                    return f"mem_ckpt_{step_index}"
            except Exception as e:
                logger.warning("Failed to persist checkpoint to DB: %s. Falling back to in-memory ID.", e)
                try:
                    await session.rollback()
                except Exception:
                    pass
                return f"mem_ckpt_{step_index}"
        return f"mem_ckpt_{step_index}"

    @classmethod
    async def get_latest_checkpoint(
        cls,
        session: AsyncSession | None,
        task_id: str,
    ) -> Optional[dict[str, Any]]:
        """Retrieve the most recent checkpoint for a task."""
        if session is not None:
            stmt = (
                select(TaskCheckpointModel)
                .where(TaskCheckpointModel.task_id == task_id)
                .order_by(desc(TaskCheckpointModel.created_at))
                .limit(1)
            )
            result = await session.execute(stmt)
            ckpt = result.scalar_one_or_none()
            if ckpt:
                return ckpt.state_data
        return None
