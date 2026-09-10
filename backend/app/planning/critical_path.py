"""Critical Path Method (CPM) calculation and schedule sensitivity analysis (Task 58)."""

from __future__ import annotations

import logging
from typing import Any

from app.planning.dependencies import dependency_graph_engine
from app.planning.schemas import PlanTask

logger = logging.getLogger(__name__)


class CriticalPathEngine:
    """Calculates Critical Path, Early/Late Start/Finish times, and task float."""

    def compute_critical_path(
        self,
        tasks: list[PlanTask],
        duration_mode: str = "expected",
    ) -> dict[str, Any]:
        """Compute the critical path through CPM forward and backward passes."""
        if not tasks:
            return {
                "critical_task_ids": [],
                "total_duration": 0.0,
                "task_metrics": {},
                "sensitivity_analysis": {"bottlenecks": []},
            }

        # Validate acyclic and get topological sort
        sorted_tasks = dependency_graph_engine.topological_sort(tasks)
        successors, predecessors = dependency_graph_engine.build_adjacency(tasks)
        task_map = {t.task_id: t for t in tasks}

        def get_duration(task: PlanTask) -> float:
            if duration_mode == "min":
                return task.duration_min
            if duration_mode == "max":
                return task.duration_max
            return task.duration_expected

        # 1. Forward Pass: Calculate Early Start (ES) and Early Finish (EF)
        es: dict[str, float] = {}
        ef: dict[str, float] = {}

        for task in sorted_tasks:
            preds = predecessors.get(task.task_id, [])
            if not preds:
                es[task.task_id] = 0.0
            else:
                es[task.task_id] = max((ef.get(p_id, 0.0) for p_id in preds), default=0.0)
            ef[task.task_id] = round(es[task.task_id] + get_duration(task), 2)

        total_duration = max(ef.values()) if ef else 0.0

        # 2. Backward Pass: Calculate Late Finish (LF) and Late Start (LS)
        lf: dict[str, float] = {}
        ls: dict[str, float] = {}

        for task in reversed(sorted_tasks):
            succs = successors.get(task.task_id, [])
            if not succs:
                lf[task.task_id] = total_duration
            else:
                lf[task.task_id] = min((ls.get(s_id, total_duration) for s_id in succs), default=total_duration)
            ls[task.task_id] = round(lf[task.task_id] - get_duration(task), 2)

        # 3. Calculate Float / Slack & Identify Critical Path
        critical_task_ids: list[str] = []
        task_metrics: dict[str, dict[str, Any]] = {}

        for task in sorted_tasks:
            slack = round(ls[task.task_id] - es[task.task_id], 2)
            is_crit = abs(slack) < 1e-4
            if is_crit:
                critical_task_ids.append(task.task_id)

            task_metrics[task.task_id] = {
                "task_title": task.title,
                "duration": get_duration(task),
                "early_start": es[task.task_id],
                "early_finish": ef[task.task_id],
                "late_start": ls[task.task_id],
                "late_finish": lf[task.task_id],
                "total_slack": slack,
                "is_critical": is_crit,
            }

        # 4. Sensitivity Analysis (Bottlenecks)
        bottlenecks = [
            {
                "task_id": tid,
                "title": task_map[tid].title,
                "duration": get_duration(task_map[tid]),
                "slack": 0.0,
            }
            for tid in critical_task_ids
        ]
        # Sort bottlenecks by duration descending
        bottlenecks.sort(key=lambda x: x["duration"], reverse=True)

        return {
            "critical_task_ids": critical_task_ids,
            "total_duration": total_duration,
            "task_metrics": task_metrics,
            "sensitivity_analysis": {
                "critical_task_count": len(critical_task_ids),
                "total_task_count": len(tasks),
                "schedule_sensitivity_ratio": round(len(critical_task_ids) / max(1, len(tasks)), 2),
                "bottlenecks": bottlenecks,
            },
        }


critical_path_engine = CriticalPathEngine()
