"""Work package model and lifecycle management for Strategic Planning (Task 58)."""

from __future__ import annotations

import logging

from app.planning.schemas import PhaseStatus, PlanTask, TaskStatus, WorkPackage

logger = logging.getLogger(__name__)


class WorkPackageManager:
    """Manages work packages grouping related tasks into cohesive execution units."""

    def create_package(
        self,
        name: str,
        phase_id: str | None = None,
        description: str = "",
        owner: str = "OWNER_UNASSIGNED",
        task_ids: list[str] | None = None,
    ) -> WorkPackage:
        """Create a new work package."""
        return WorkPackage(
            name=name,
            phase_id=phase_id,
            description=description,
            owner=owner,
            status=PhaseStatus.PLANNED,
            task_ids=task_ids or [],
        )

    def add_task(self, package: WorkPackage, task_id: str) -> None:
        """Add a task ID to the package if not already present."""
        if task_id not in package.task_ids:
            package.task_ids.append(task_id)

    def evaluate_status(self, package: WorkPackage, tasks: list[PlanTask]) -> PhaseStatus:
        """Derive package status from child task statuses."""
        package_tasks = [t for t in tasks if t.task_id in package.task_ids]
        if not package_tasks:
            return package.status

        statuses = {t.status for t in package_tasks}

        if all(s == TaskStatus.COMPLETED for s in statuses):
            package.status = PhaseStatus.COMPLETED
        elif any(s in (TaskStatus.FAILED, TaskStatus.BLOCKED) for s in statuses):
            package.status = PhaseStatus.BLOCKED
        elif any(s in (TaskStatus.RUNNING, TaskStatus.QUEUED, TaskStatus.READY) for s in statuses):
            package.status = PhaseStatus.IN_PROGRESS
        else:
            package.status = PhaseStatus.PLANNED

        return package.status


work_package_manager = WorkPackageManager()
