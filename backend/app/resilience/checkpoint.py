"""Transactional, versioned task state checkpoints for crash recovery."""

from datetime import UTC, datetime
import logging
from typing import Any
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.resilience.failures import ErrorSanitizer
from app.resilience.models import ResilienceCheckpointModel
from app.resilience.schemas import TaskCheckpoint, generate_uuid, utc_now

logger = logging.getLogger(__name__)

CURRENT_CHECKPOINT_SCHEMA_VERSION = 1


class CorruptCheckpointError(Exception):
    """Raised when a checkpoint is unreadable, invalid, or corrupted."""
    pass


class ResilienceCheckpointManager:
    """Manages transactional, versioned task checkpoints with schema validation and sanitization."""

    def __init__(self) -> None:
        self._memory_checkpoints: dict[str, list[TaskCheckpoint]] = {}

    async def save_checkpoint(
        self,
        task_id: str,
        state: dict[str, Any],
        step_id: str | None = None,
        policy_version: int | None = None,
        session: AsyncSession | None = None,
    ) -> TaskCheckpoint:
        """Atomically saves a sanitized checkpoint at a meaningful boundary."""
        # Sanitize sensitive data out of checkpoint state
        sanitized_state = ErrorSanitizer.sanitize_dict(state)

        ckpt_id = generate_uuid("ckpt")
        now = utc_now()

        # Check existing version count
        history = self._memory_checkpoints.setdefault(task_id, [])
        version = len(history) + 1

        ckpt = TaskCheckpoint(
            id=ckpt_id,
            task_id=task_id,
            step_id=step_id,
            version=version,
            state_json=sanitized_state,
            policy_version=policy_version,
            is_valid=True,
            created_at=now,
        )
        history.append(ckpt)

        if session:
            try:
                db_item = ResilienceCheckpointModel(
                    id=ckpt_id,
                    task_id=task_id,
                    step_id=step_id,
                    version=version,
                    state_json=sanitized_state,
                    policy_version=policy_version,
                    is_valid=True,
                    created_at=now,
                )
                session.add(db_item)
                await session.commit()
                logger.debug("Resilience: Saved checkpoint %s (v%d) for task %s", ckpt_id, version, task_id)
            except Exception as e:
                logger.error("Resilience: Failed to save checkpoint to DB for %s: %s", task_id, e)
                raise

        return ckpt

    async def get_latest_valid_checkpoint(
        self,
        task_id: str,
        session: AsyncSession | None = None,
    ) -> TaskCheckpoint | None:
        """Retrieves the latest valid checkpoint. If latest is corrupt, tries previous valid checkpoint."""
        if session:
            try:
                stmt = (
                    select(ResilienceCheckpointModel)
                    .where(ResilienceCheckpointModel.task_id == task_id)
                    .order_by(desc(ResilienceCheckpointModel.created_at))
                )
                res = await session.execute(stmt)
                all_ckpts = res.scalars().all()
                for item in all_ckpts:
                    if item.is_valid and isinstance(item.state_json, dict):
                        return TaskCheckpoint.model_validate(item)
                    else:
                        logger.warning("Resilience: Found corrupt checkpoint %s for task %s", item.id, task_id)
                return None
            except Exception as e:
                logger.warning("Resilience: DB error fetching checkpoint for %s: %s", task_id, e)

        # Fallback to memory
        history = self._memory_checkpoints.get(task_id, [])
        for item in reversed(history):
            if item.is_valid and isinstance(item.state_json, dict):
                return item
            logger.warning("Resilience: Skipping corrupt in-memory checkpoint %s for task %s", item.id, task_id)

        return None

    async def invalidate_checkpoint(
        self,
        checkpoint_id: str,
        session: AsyncSession | None = None,
    ) -> None:
        """Marks a checkpoint as invalid/corrupted."""
        for history in self._memory_checkpoints.values():
            for item in history:
                if item.id == checkpoint_id:
                    item.is_valid = False

        if session:
            try:
                stmt = select(ResilienceCheckpointModel).where(ResilienceCheckpointModel.id == checkpoint_id)
                res = await session.execute(stmt)
                db_item = res.scalar_one_or_none()
                if db_item:
                    db_item.is_valid = False
                    await session.commit()
            except Exception as e:
                logger.warning("Resilience: DB error invalidating checkpoint %s: %s", checkpoint_id, e)
