"""Project continuity, lifecycle tracking, and pivot history (INVARIANTS 7, 8, 143-146)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.executive_memory.safety import ExecutiveSafetyGuard, NoMemoryOnlyStateError
from app.executive_memory.schemas import ProjectLifecycleState


class ProjectContinuityManager:
    """Tracks project lifecycle transitions, scope adjustments, and pivot history."""

    def __init__(self) -> None:
        # project_id -> dict of project metadata & lifecycle
        self._projects: dict[str, dict[str, Any]] = {}
        # project_id -> list of pivot history records
        self._pivots: dict[str, list[dict[str, Any]]] = {}

    def register_project(
        self,
        project_id: str,
        name: str,
        status: ProjectLifecycleState = ProjectLifecycleState.ACTIVE,
        authoritative_status: str | None = None,
    ) -> dict[str, Any]:
        """Registers a project, checking authoritative backing if asserting COMPLETED."""
        status_val = status.value if hasattr(status, "value") else str(status)
        if status_val == "COMPLETED":
            ExecutiveSafetyGuard.assert_authoritative_grounding(
                claimed_status=status_val,
                authoritative_status=authoritative_status,
                entity_type="project",
            )

        now = datetime.now(UTC)
        record = {
            "project_id": project_id,
            "name": name,
            "status": status_val,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        self._projects[project_id] = record
        return record

    def update_project_status(
        self,
        project_id: str,
        new_status: ProjectLifecycleState,
        authoritative_status: str | None = None,
    ) -> dict[str, Any]:
        """INVARIANT 6: Validates against authoritative status before transitioning."""
        status_val = new_status.value if hasattr(new_status, "value") else str(new_status)
        if status_val == "COMPLETED":
            ExecutiveSafetyGuard.assert_authoritative_grounding(
                claimed_status=status_val,
                authoritative_status=authoritative_status,
                entity_type="project",
            )

        proj = self._projects.get(project_id)
        if not proj:
            proj = self.register_project(project_id, name=project_id, status=new_status, authoritative_status=authoritative_status)

        proj["status"] = status_val
        proj["updated_at"] = datetime.now(UTC).isoformat()
        return proj

    def record_project_pivot(
        self,
        project_id: str,
        old_direction: str,
        new_direction: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """INVARIANT 144-146: Records direction pivots. If reason is unknown, explicitly marks UNKNOWN."""
        record = {
            "project_id": project_id,
            "old_direction": old_direction,
            "new_direction": new_direction,
            "reason": reason.strip() if reason and reason.strip() else "UNKNOWN",
            "timestamp": datetime.now(UTC).isoformat(),
        }
        self._pivots.setdefault(project_id, []).append(record)
        return record

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        return self._projects.get(project_id)

    def list_pivots(self, project_id: str) -> list[dict[str, Any]]:
        return self._pivots.get(project_id, [])
