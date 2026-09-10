"""Plan task management, strict state transitions, and safety bounds (Task 58)."""

from __future__ import annotations

import logging

from app.planning.safety import sanitize_plan_directive
from app.planning.schemas import (
    PlanTask,
    ResourceRequirement,
    RiskSeverity,
    TaskStatus,
)

logger = logging.getLogger(__name__)


class TaskManager:
    """Manages individual strategic plan tasks and enforces transition rules."""

    def create_task(
        self,
        title: str,
        description: str = "",
        phase_id: str | None = None,
        package_id: str | None = None,
        owner: str | None = None,
        dependencies: list[str] | None = None,
        resources: list[ResourceRequirement] | None = None,
        duration_min: float = 1.0,
        duration_expected: float = 2.0,
        duration_max: float = 4.0,
        is_irreversible: bool = False,
        risk_level: RiskSeverity = RiskSeverity.LOW,
        execution_wave: int = 1,
        verification_criteria: list[str] | None = None,
        output_artifacts: list[str] | None = None,
    ) -> PlanTask:
        """Create a plan task with sanitized inputs and duration sanity bounds."""
        # Sanitize against prompt injections / malicious directives
        clean_title = sanitize_plan_directive(title)
        clean_desc = sanitize_plan_directive(description)

        # Invariant 11: Missing owner is not a fabricated owner
        task_owner = owner.strip() if owner and owner.strip() else "OWNER_UNASSIGNED"

        # Duration bounds sanity
        dur_min = max(0.1, duration_min)
        dur_exp = max(dur_min, duration_expected)
        dur_max = max(dur_exp, duration_max)

        return PlanTask(
            phase_id=phase_id,
            package_id=package_id,
            title=clean_title,
            description=clean_desc,
            owner=task_owner,
            status=TaskStatus.DRAFT,
            dependencies=dependencies or [],
            resources=resources or [],
            duration_min=dur_min,
            duration_expected=dur_exp,
            duration_max=dur_max,
            is_irreversible=is_irreversible,
            risk_level=risk_level,
            execution_wave=execution_wave,
            verification_criteria=verification_criteria or [],
            output_artifacts=output_artifacts or [],
        )

    def transition_task(
        self,
        task: PlanTask,
        target_status: TaskStatus,
        completed_task_ids: set[str] | None = None,
        evidence: list[str] | None = None,
    ) -> tuple[bool, str]:
        """Transition task status enforcing prerequisite resolution and verification."""
        completed_ids = completed_task_ids or set()

        if target_status == TaskStatus.READY:
            unresolved = [dep for dep in task.dependencies if dep not in completed_ids]
            if unresolved:
                task.status = TaskStatus.BLOCKED
                return False, f"Task blocked by unresolved dependencies: {unresolved}"
            task.status = TaskStatus.READY
            return True, "Task is now READY."

        if target_status == TaskStatus.RUNNING:
            if task.status not in (TaskStatus.READY, TaskStatus.QUEUED):
                return False, f"Cannot start task in status {task.status}."
            if task.is_irreversible:
                logger.warning("Starting IRREVERSIBLE task %s (%s).", task.task_id, task.title)
            task.status = TaskStatus.RUNNING
            return True, "Task is now RUNNING."

        if target_status == TaskStatus.COMPLETED:
            if task.verification_criteria:
                evidence_set = set(evidence or [])
                missing = [c for c in task.verification_criteria if c not in evidence_set]
                if missing:
                    return False, f"Task cannot complete without verification: {missing}"
            task.status = TaskStatus.COMPLETED
            return True, "Task successfully completed and verified."

        task.status = target_status
        return True, f"Task transitioned to {target_status}."

    def filter_ready_tasks(
        self,
        tasks: list[PlanTask],
        completed_task_ids: set[str],
    ) -> list[PlanTask]:
        """Identify tasks whose prerequisites are completely satisfied."""
        ready: list[PlanTask] = []
        for task in tasks:
            if task.status in (TaskStatus.DRAFT, TaskStatus.BLOCKED, TaskStatus.READY):
                if all(dep in completed_task_ids for dep in task.dependencies):
                    ready.append(task)
        return ready


task_manager = TaskManager()
