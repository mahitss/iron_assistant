"""Task Preemption Engine: priority-based preemption, checkpointing, and safe resumption (Task 77)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.orchestration.economy_schemas import (
    PreemptionPolicy,
    PreemptionState,
    TaskPreemptionRecord,
)

logger = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class TaskPreemptionEngine:
    """Manages preemption lifecycle, checkpointing, and resumption to prevent priority inversion."""

    def __init__(self) -> None:
        self._records: dict[str, TaskPreemptionRecord] = {}  # task_id -> record
        self._checkpoints: dict[str, dict[str, Any]] = {}  # checkpoint_token -> state

    def register_task(
        self,
        task_id: str,
        priority: int = 1,
    ) -> TaskPreemptionRecord:
        """Register a running task for preemption monitoring."""
        record = TaskPreemptionRecord(
            preemption_id=f"prm_{uuid.uuid4().hex[:8]}",
            task_id=task_id,
            priority=priority,
            state=PreemptionState.RUNNING,
            created_at=_now_utc(),
        )
        self._records[task_id] = record
        return record

    def get_task_record(self, task_id: str) -> TaskPreemptionRecord | None:
        """Retrieve preemption record for a task."""
        return self._records.get(task_id)

    def request_preemption(
        self,
        task_id: str,
        preempted_by_task_id: str,
        requestor_priority: int,
        policy: PreemptionPolicy = PreemptionPolicy.COOPERATIVE,
    ) -> tuple[bool, str, TaskPreemptionRecord | None]:
        """Request preemption of a lower-priority task.

        Enforces invariant: requestor priority must be strictly greater than target task priority.
        """
        if policy == PreemptionPolicy.NEVER:
            return False, "Task policy is NEVER preemptible", None

        record = self._records.get(task_id)
        if record is None:
            # Auto-register if not yet tracked
            record = self.register_task(task_id=task_id, priority=1)

        if requestor_priority <= record.priority:
            return (
                False,
                f"Priority inversion rejected: requestor priority ({requestor_priority}) <= "
                f"victim priority ({record.priority})",
                record,
            )

        if record.state in (PreemptionState.PAUSED, PreemptionState.CANCELLED):
            return False, f"Task {task_id} is already in state {record.state.value}", record

        record.preempted_by_task_id = preempted_by_task_id
        record.state = PreemptionState.PREEMPTION_REQUESTED
        logger.info("PREEMPTION_REQUESTED: task %s preempted by %s", task_id, preempted_by_task_id)

        return True, "Preemption requested", record

    def checkpoint_task(
        self,
        task_id: str,
        state_snapshot: dict[str, Any],
        saved_context_tokens: int = 0,
        cost_of_preemption: float = 0.0,
    ) -> TaskPreemptionRecord:
        """Create safe execution checkpoint and pause the task."""
        record = self._records.get(task_id)
        if record is None:
            record = self.register_task(task_id=task_id)

        checkpoint_token = f"chk_{uuid.uuid4().hex[:12]}"
        record.state = PreemptionState.CHECKPOINTING
        record.checkpoint_token = checkpoint_token
        record.state_snapshot = state_snapshot
        record.saved_context_tokens = saved_context_tokens
        record.cost_of_preemption = cost_of_preemption

        # Transition to PAUSED / RESUMABLE
        record.state = PreemptionState.PAUSED
        self._checkpoints[checkpoint_token] = {
            "task_id": task_id,
            "snapshot": state_snapshot,
            "timestamp": _now_utc(),
        }

        logger.info("Task %s checkpointed successfully with token %s", task_id, checkpoint_token)
        return record

    def resume_task(self, task_id: str) -> tuple[bool, str, dict[str, Any]]:
        """Resume a paused preempted task using its saved checkpoint."""
        record = self._records.get(task_id)
        if record is None:
            return False, f"No record found for task {task_id}", {}

        if record.state not in (PreemptionState.PAUSED, PreemptionState.RESUMABLE):
            return False, f"Task {task_id} cannot be resumed from state {record.state.value}", {}

        checkpoint_data = self._checkpoints.get(record.checkpoint_token or "", {})
        snapshot = checkpoint_data.get("snapshot", record.state_snapshot)

        # Calculate wait time
        wait_seconds = (_now_utc() - record.created_at).total_seconds()
        record.wait_time_s = max(0.0, wait_seconds)
        record.state = PreemptionState.RESUMED
        record.resumed_at = _now_utc()

        logger.info("Task %s resumed after %.2fs wait time", task_id, record.wait_time_s)
        return True, "Task resumed", snapshot

    def cancel_task(self, task_id: str, reason: str = "Preemption expired") -> TaskPreemptionRecord | None:
        """Cancel a paused preempted task."""
        record = self._records.get(task_id)
        if record is None:
            return None

        record.state = PreemptionState.CANCELLED
        logger.info("Task %s cancelled while preempted: %s", task_id, reason)
        return record

    def list_preempted_tasks(self) -> list[TaskPreemptionRecord]:
        """List all tasks currently in paused or checkpointed state."""
        return [
            r for r in self._records.values()
            if r.state in (PreemptionState.PAUSED, PreemptionState.CHECKPOINTING, PreemptionState.PREEMPTION_REQUESTED)
        ]


default_preemption_engine = TaskPreemptionEngine()
