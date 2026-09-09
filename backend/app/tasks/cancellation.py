"""Cooperative cancellation tokens and Emergency Stop coordination (Spec 42, 43, 44)."""

import asyncio
import logging
from typing import Dict, Optional
from app.security.emergency_stop import get_emergency_stop_service

logger = logging.getLogger("kairo.tasks.cancellation")


class TaskCancelledError(asyncio.CancelledError):
    """Raised when an autonomous task is halted via user cancellation."""

    def __init__(self, task_id: str, reason: str = "User initiated cancellation") -> None:
        super().__init__(f"TASK_CANCELLED: Task {task_id} cancelled: {reason}")
        self.task_id = task_id
        self.reason = reason


class EmergencyStopActiveError(RuntimeError):
    """Raised when an autonomous task is halted due to Emergency Stop."""

    def __init__(self, user_id: str) -> None:
        super().__init__(f"EMERGENCY_STOP_ACTIVE: Actions halted for user {user_id}")
        self.user_id = user_id


class CancellationToken:
    """Cooperative cancellation token passed through task execution hierarchy."""

    def __init__(self, task_id: str, user_id: str) -> None:
        self.task_id = task_id
        self.user_id = user_id
        self._cancelled = False
        self._reason = ""
        self._callbacks: list[callable] = []

    @property
    def is_cancelled(self) -> bool:
        """Check if explicitly cancelled or if user triggered Emergency Stop."""
        if self._cancelled:
            return True
        es = get_emergency_stop_service()
        if es.is_stopped(self.user_id):
            return True
        return False

    @property
    def reason(self) -> str:
        if self._cancelled:
            return self._reason
        es = get_emergency_stop_service()
        if es.is_stopped(self.user_id):
            return "Emergency Stop is active"
        return ""

    def cancel(self, reason: str = "User cancelled task") -> None:
        """Trigger cooperative cancellation."""
        self._cancelled = True
        self._reason = reason
        logger.info("Task %s cancellation signaled: %s", self.task_id, reason)
        for cb in self._callbacks:
            try:
                cb()
            except Exception as e:
                logger.warning("Error invoking cancellation callback: %s", e)

    def register_callback(self, cb: callable) -> None:
        """Register a callback to be triggered when cancellation is signaled."""
        if self._cancelled:
            cb()
        else:
            self._callbacks.append(cb)

    def check_cancelled(self) -> None:
        """Raise appropriate exception if cancellation or Emergency Stop is active."""
        es = get_emergency_stop_service()
        if es.is_stopped(self.user_id):
            raise EmergencyStopActiveError(self.user_id)
        if self._cancelled:
            raise TaskCancelledError(self.task_id, self._reason)


class CancellationManager:
    """Central registry for tracking and signaling cancellation across all active tasks."""

    def __init__(self) -> None:
        self._tokens: dict[str, CancellationToken] = {}

    def get_or_create_token(self, task_id: str, user_id: str) -> CancellationToken:
        """Fetch existing token or create a new one for the task."""
        if task_id not in self._tokens:
            self._tokens[task_id] = CancellationToken(task_id, user_id)
        return self._tokens[task_id]

    def cancel_task(self, task_id: str, reason: str = "User cancelled task") -> bool:
        """Cancel an active task by ID."""
        token = self._tokens.get(task_id)
        if token:
            token.cancel(reason)
            return True
        return False

    def remove_token(self, task_id: str) -> None:
        """Clean up token upon terminal task completion."""
        self._tokens.pop(task_id, None)


# Global singleton instance
_cancellation_manager: Optional[CancellationManager] = None


def get_cancellation_manager() -> CancellationManager:
    global _cancellation_manager
    if _cancellation_manager is None:
        _cancellation_manager = CancellationManager()
    return _cancellation_manager
