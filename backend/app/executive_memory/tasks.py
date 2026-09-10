"""Task continuity, execution status synthesis, and progress tracking (INVARIANTS 47, 116, 198)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.executive_memory.safety import ExecutiveSafetyGuard


class TaskContinuityManager:
    """Synthesizes task progress from authoritative Task Engine state without fabricating completions."""

    def __init__(self) -> None:
        # task_id -> task status dict
        self._tasks: dict[str, dict[str, Any]] = {}

    def track_task_state(
        self,
        task_id: str,
        name: str,
        status: str,
        project_id: str | None = None,
        authoritative_status: str | None = None,
    ) -> dict[str, Any]:
        """INVARIANT 6 & 198: Ensures claimed completion matches authoritative Task Engine status."""
        if status.upper() == "COMPLETED":
            ExecutiveSafetyGuard.assert_authoritative_grounding(
                claimed_status="COMPLETED",
                authoritative_status=authoritative_status,
                entity_type="task",
            )

        now = datetime.now(UTC)
        record = {
            "task_id": task_id,
            "name": name,
            "status": status.upper(),
            "project_id": project_id,
            "updated_at": now.isoformat(),
        }
        self._tasks[task_id] = record
        return record

    def list_active_tasks(self, project_id: str | None = None) -> list[dict[str, Any]]:
        results = [t for t in self._tasks.values() if t["status"] in ("PENDING", "IN_PROGRESS", "RUNNING", "ACTIVE")]
        if project_id:
            results = [t for t in results if t.get("project_id") == project_id]
        return results

    def list_completed_tasks(self, project_id: str | None = None) -> list[dict[str, Any]]:
        results = [t for t in self._tasks.values() if t["status"] == "COMPLETED"]
        if project_id:
            results = [t for t in results if t.get("project_id") == project_id]
        return results
