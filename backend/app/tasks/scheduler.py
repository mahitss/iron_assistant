"""Task scheduler, fairness enforcer, deduplication, and resource locking (Spec 48-51, 56, 57, 131)."""

import asyncio
from datetime import UTC, datetime, timedelta
import logging
from typing import Dict, List, Optional, Set, Tuple
from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.tasks.models import TaskLockModel, TaskModel
from app.tasks.schemas import TaskPriority, TaskStatus

logger = logging.getLogger("kairo.tasks.scheduler")


class ResourceLockConflictError(RuntimeError):
    """Raised when an autonomous task attempts to acquire a locked resource."""
    def __init__(self, resource_type: str, resource_id: str, holding_task_id: str) -> None:
        super().__init__(
            f"Resource '{resource_type}:{resource_id}' is locked by task '{holding_task_id}'"
        )
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.holding_task_id = holding_task_id


class ConcurrencyLimitExceededError(RuntimeError):
    """Raised when user or project exceeds active task limit."""
    pass


class TaskScheduler:
    """Coordinates task fairness, active concurrency limits, and expiring resource locks."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._active_tasks_per_user: dict[str, Set[str]] = {}
        self._active_tasks_per_project: dict[str, Set[str]] = {}
        self._in_memory_locks: dict[Tuple[str, str], Tuple[str, datetime]] = {}  # (type, id) -> (task_id, expires_at)
        self._lock_mutex = asyncio.Lock()

    async def can_admit_task(
        self,
        user_id: str,
        project_id: str | None = None,
        session: AsyncSession | None = None,
    ) -> Tuple[bool, str]:
        """Verify per-user and per-project concurrency limits (Spec 49, 50)."""
        max_user_tasks = getattr(self.settings, "KAIRO_MAX_ACTIVE_TASKS_PER_USER", 5)
        max_project_tasks = getattr(self.settings, "KAIRO_MAX_ACTIVE_TASKS_PER_PROJECT", 10)

        user_active = len(self._active_tasks_per_user.get(user_id, set()))
        if user_active >= max_user_tasks:
            return False, f"User active task limit exceeded ({user_active}/{max_user_tasks})"

        if project_id:
            project_active = len(self._active_tasks_per_project.get(project_id, set()))
            if project_active >= max_project_tasks:
                return False, f"Project active task limit exceeded ({project_active}/{max_project_tasks})"

        return True, ""

    def register_active_task(self, task_id: str, user_id: str, project_id: str | None = None) -> None:
        """Register a task as actively running."""
        if user_id not in self._active_tasks_per_user:
            self._active_tasks_per_user[user_id] = set()
        self._active_tasks_per_user[user_id].add(task_id)

        if project_id:
            if project_id not in self._active_tasks_per_project:
                self._active_tasks_per_project[project_id] = set()
            self._active_tasks_per_project[project_id].add(task_id)

    def unregister_active_task(self, task_id: str, user_id: str, project_id: str | None = None) -> None:
        """Unregister a completed/failed/cancelled task from active tracking."""
        if user_id in self._active_tasks_per_user:
            self._active_tasks_per_user[user_id].discard(task_id)
        if project_id and project_id in self._active_tasks_per_project:
            self._active_tasks_per_project[project_id].discard(task_id)

    async def check_duplicate_active_task(
        self,
        user_id: str,
        objective: str,
        session: AsyncSession | None = None,
    ) -> Optional[str]:
        """Detect identical active objectives submitted recently (Spec 51)."""
        clean_obj = objective.strip().lower()
        if session is not None:
            active_statuses = [TaskStatus.QUEUED.value, TaskStatus.PLANNING.value, TaskStatus.RUNNING.value]
            stmt = select(TaskModel).where(
                and_(
                    TaskModel.user_id == user_id,
                    TaskModel.status.in_(active_statuses),
                )
            )
            res = await session.execute(stmt)
            tasks = res.scalars().all()
            for t in tasks:
                if t.objective.strip().lower() == clean_obj:
                    return t.id
        return None

    # --- Resource Locking (Spec 56, 57, 131) ---

    async def acquire_resource_lock(
        self,
        resource_type: str,
        resource_id: str,
        task_id: str,
        user_id: str,
        ttl_seconds: int = 300,
        session: AsyncSession | None = None,
    ) -> bool:
        """Acquire an expiring resource lock."""
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=ttl_seconds)
        key = (resource_type.upper(), str(resource_id))

        async with self._lock_mutex:
            # Check in-memory lock table first
            if key in self._in_memory_locks:
                holding_task, exp = self._in_memory_locks[key]
                if exp > now and holding_task != task_id:
                    raise ResourceLockConflictError(resource_type, resource_id, holding_task)

            # Persist in memory
            self._in_memory_locks[key] = (task_id, expires_at)

            # Persist in database if session available
            if session is not None:
                # Clean up expired locks first
                await session.execute(
                    delete(TaskLockModel).where(
                        and_(
                            TaskLockModel.resource_type == key[0],
                            TaskLockModel.resource_id == key[1],
                            TaskLockModel.expires_at <= now,
                        )
                    )
                )
                lock = TaskLockModel(
                    resource_type=key[0],
                    resource_id=key[1],
                    task_id=task_id,
                    user_id=user_id,
                    expires_at=expires_at,
                )
                session.add(lock)
                await session.commit()

            return True

    async def release_resource_lock(
        self,
        resource_type: str,
        resource_id: str,
        task_id: str,
        session: AsyncSession | None = None,
    ) -> None:
        """Release a held resource lock."""
        key = (resource_type.upper(), str(resource_id))
        async with self._lock_mutex:
            if key in self._in_memory_locks and self._in_memory_locks[key][0] == task_id:
                del self._in_memory_locks[key]

            if session is not None:
                await session.execute(
                    delete(TaskLockModel).where(
                        and_(
                            TaskLockModel.resource_type == key[0],
                            TaskLockModel.resource_id == key[1],
                            TaskLockModel.task_id == task_id,
                        )
                    )
                )
                await session.commit()

    async def release_all_task_locks(self, task_id: str, session: AsyncSession | None = None) -> None:
        """Release all locks held by a task upon completion or cancellation."""
        async with self._lock_mutex:
            to_remove = [k for k, v in self._in_memory_locks.items() if v[0] == task_id]
            for k in to_remove:
                del self._in_memory_locks[k]

            if session is not None:
                await session.execute(
                    delete(TaskLockModel).where(TaskLockModel.task_id == task_id)
                )
                await session.commit()


# Global singleton
_scheduler_instance: Optional[TaskScheduler] = None


def get_task_scheduler() -> TaskScheduler:
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = TaskScheduler()
    return _scheduler_instance
