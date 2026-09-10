"""Impact analysis, blast radius calculation, and plan/goal threat propagation (Task 60)."""

from __future__ import annotations

import logging
from typing import Any

from app.situational_awareness.schemas import (
    BlastRadiusImpact,
    TaskImpactState,
)

logger = logging.getLogger(__name__)


class ImpactAnalyzer:
    """Traverses service topologies and dependency graphs to calculate blast radius and plan impacts."""

    def calculate_blast_radius(
        self,
        situation_id: str,
        affected_resources: list[str],
        dependency_map: dict[str, list[str]] | None = None,
        active_plans: list[dict[str, Any]] | None = None,
        active_goals: list[dict[str, Any]] | None = None,
    ) -> BlastRadiusImpact:
        """Calculate direct and propagated blast radius across services, plans, and goals."""
        deps = dependency_map or {}
        plans = active_plans or []
        goals = active_goals or []

        known_affected: set[str] = set(affected_resources)
        potentially_affected: set[str] = set()

        # Propagate through downstream dependencies (bounded to avoid infinite loops)
        frontier = set(known_affected)
        for _ in range(3):
            next_frontier = set()
            for res in frontier:
                for downstream, upstream_deps in deps.items():
                    if (
                        res in upstream_deps
                        and downstream not in known_affected
                        and downstream not in potentially_affected
                    ):
                        potentially_affected.add(downstream)
                        next_frontier.add(downstream)
            if not next_frontier:
                break
            frontier = next_frontier

        # Evaluate impact on active strategic plans and tasks
        affected_plan_ids: list[str] = []
        task_impacts: dict[str, TaskImpactState] = {}

        for plan in plans:
            plan_id = plan.get("plan_id", "unknown_plan")
            plan_tasks = plan.get("tasks", [])
            plan_affected = False

            for task in plan_tasks:
                tid = task.get("task_id", task.get("id", "task"))
                task_res = task.get("required_resources", [])
                task_res_ids = [r.get("resource_id", r.get("id")) for r in task_res if isinstance(r, dict)]

                # Check if task depends on any affected resource
                is_task_blocked = any(r in known_affected for r in task_res_ids)
                is_task_at_risk = any(r in potentially_affected for r in task_res_ids)

                if is_task_blocked:
                    task_impacts[tid] = TaskImpactState.BLOCKED
                    plan_affected = True
                elif is_task_at_risk:
                    task_impacts[tid] = TaskImpactState.AT_RISK
                    plan_affected = True
                else:
                    task_impacts[tid] = TaskImpactState.UNBLOCKED

            if plan_affected:
                affected_plan_ids.append(plan_id)

        # Evaluate impact on goals
        affected_goal_ids: list[str] = []
        for goal in goals:
            gid = goal.get("goal_id", goal.get("id", "goal"))
            # If any related plan or service is impacted, goal is threatened
            goal_services = goal.get("related_services", [])
            if any(s in known_affected or s in potentially_affected for s in goal_services):
                affected_goal_ids.append(gid)

        # Confidence is high if dependencies are defined, moderate if empty
        conf = 0.95 if deps else 0.70

        impact = BlastRadiusImpact(
            situation_id=situation_id,
            known_affected_services=list(known_affected),
            potentially_affected_services=list(potentially_affected),
            affected_resources=list(known_affected),
            affected_plans=affected_plan_ids,
            affected_goals=affected_goal_ids,
            task_impacts=task_impacts,
            confidence=conf,
        )

        logger.info(
            "BLAST_RADIUS_CALCULATED: situation=%s direct=%d indirect=%d plans=%d goals=%d",
            situation_id,
            len(known_affected),
            len(potentially_affected),
            len(affected_plan_ids),
            len(affected_goal_ids),
        )
        return impact


impact_analyzer = ImpactAnalyzer()
