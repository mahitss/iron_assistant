"""Active task modeling, state tracking, and origin validation (INVARIANTS 37, 38, 117-120)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
import uuid

from app.metacognition.schemas import TaskOrigin, TaskState


class UnknownTaskOriginError(Exception):
    """Raised when an autonomous task has an untraceable or invalid origin."""
    pass


class TaskTracker:
    """Tracks running tasks, execution states, and rigorously enforces task origin legitimacy."""

    def __init__(self) -> None:
        # task_id -> dict
        self._tasks: Dict[str, Dict[str, Any]] = {}

    def register_task(
        self,
        task_name: str,
        origin: TaskOrigin,
        user_id: str = "default_user",
        goal_id: Optional[str] = None,
        authority_scope: str = "DEFAULT",
    ) -> Dict[str, Any]:
        """INVARIANT 117 & 118: Every autonomous task must have an authorized origin. Unknown origins are blocked."""
        valid_origins = {o.value for o in TaskOrigin}
        if origin not in valid_origins and origin not in TaskOrigin:
            raise UnknownTaskOriginError(
                f"Task '{task_name}' has unknown/unauthorized origin '{origin}'. Execution blocked."
            )

        tid = str(uuid.uuid4())
        rec = {
            "task_id": tid,
            "task_name": task_name.strip(),
            "origin": origin.value if isinstance(origin, TaskOrigin) else str(origin),
            "state": TaskState.QUEUED.value,
            "user_id": user_id,
            "goal_id": goal_id,
            "authority_scope": authority_scope,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        self._tasks[tid] = rec
        return rec

    def update_task_state(self, task_id: str, new_state: TaskState) -> Dict[str, Any]:
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task '{task_id}' not found.")
        task["state"] = new_state.value
        task["updated_at"] = datetime.now(UTC).isoformat()
        return task

    def list_active_tasks(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        active_states = {TaskState.QUEUED.value, TaskState.RUNNING.value, TaskState.WAITING.value, TaskState.BLOCKED.value}
        tasks = [t for t in self._tasks.values() if t["state"] in active_states]
        if user_id:
            tasks = [t for t in tasks if t["user_id"] == user_id]
        return tasks

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self._tasks.get(task_id)
