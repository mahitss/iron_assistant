"""Resource planning, conflict detection, and non-fabricated capacity validation (Task 58)."""

from __future__ import annotations

import logging
from typing import Any

from app.planning.schemas import PlanTask

logger = logging.getLogger(__name__)


class ResourceManager:
    """Manages strategic resource allocations, mutual-exclusion locks, and conflict detection."""

    def detect_wave_conflicts(self, wave_tasks: list[PlanTask]) -> list[dict[str, Any]]:
        """Detect when two concurrent tasks in the same execution wave require the same exclusive resource."""
        conflicts: list[dict[str, Any]] = []
        exclusive_claims: dict[str, list[PlanTask]] = {}

        for task in wave_tasks:
            for req in task.resources:
                if req.is_exclusive:
                    exclusive_claims.setdefault(req.name, []).append(task)

        for res_name, claiming_tasks in exclusive_claims.items():
            if len(claiming_tasks) > 1:
                conflicts.append({
                    "resource_name": res_name,
                    "task_ids": [t.task_id for t in claiming_tasks],
                    "task_titles": [t.title for t in claiming_tasks],
                    "conflict_type": "MUTUAL_EXCLUSION_VIOLATION",
                    "recommendation": "Sequence tasks into separate waves or acquire a dedicated environment.",
                })

        return conflicts

    def validate_resource_availability(
        self,
        tasks: list[PlanTask],
        known_system_resources: dict[str, float] | None = None,
    ) -> tuple[bool, list[str]]:
        """Check if all required resources are verified and available in the target environment.

        INVARIANT 10: Unknown resource is not available resource. Never assume availability.
        """
        known = known_system_resources if known_system_resources is not None else {}
        missing_or_unknown: list[str] = []

        for task in tasks:
            for req in task.resources:
                if req.name not in known:
                    missing_or_unknown.append(
                        f"Resource '{req.name}' required by task '{task.title}' ({task.task_id}) "
                        f"is UNKNOWN or unverified in current environment."
                    )
                else:
                    avail = known[req.name]
                    if avail < req.amount:
                        missing_or_unknown.append(
                            f"Resource '{req.name}' has insufficient capacity: "
                            f"requested {req.amount} {req.unit}, available {avail} {req.unit}."
                        )

        is_valid = len(missing_or_unknown) == 0
        return is_valid, missing_or_unknown

    def calculate_total_requirements(self, tasks: list[PlanTask]) -> dict[str, dict[str, Any]]:
        """Aggregate total resource requirements across all tasks in the plan."""
        totals: dict[str, dict[str, Any]] = {}
        for task in tasks:
            for req in task.resources:
                if req.name not in totals:
                    totals[req.name] = {
                        "type": req.resource_type.value,
                        "amount": 0.0,
                        "unit": req.unit,
                        "is_exclusive": req.is_exclusive,
                        "consumer_task_count": 0,
                    }
                totals[req.name]["amount"] += req.amount
                totals[req.name]["consumer_task_count"] += 1
        return totals


resource_manager = ResourceManager()
