"""Scheduling engine, wave clustering, duration uncertainty, and deadline feasibility (Task 58)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from app.planning.dependencies import dependency_graph_engine
from app.planning.schemas import ExecutionWave, PlanTask

logger = logging.getLogger(__name__)


class SchedulingEngine:
    """Computes execution waves, duration bounds, buffers, and deadline feasibility."""

    def cluster_execution_waves(self, tasks: list[PlanTask]) -> list[ExecutionWave]:
        """Group tasks into discrete execution waves respecting dependencies and resource locks."""
        if not tasks:
            return []

        sorted_tasks = dependency_graph_engine.topological_sort(tasks)
        task_map = {t.task_id: t for t in tasks}

        # 1. Dependency-level wave assignment
        task_wave: dict[str, int] = {}
        for t in sorted_tasks:
            if not t.dependencies:
                task_wave[t.task_id] = 1
            else:
                max_pred_wave = max(task_wave.get(dep, 1) for dep in t.dependencies)
                task_wave[t.task_id] = max_pred_wave + 1

        # Group by preliminary wave
        preliminary_waves: dict[int, list[str]] = {}
        for tid, w in task_wave.items():
            preliminary_waves.setdefault(w, []).append(tid)

        # 2. Resource Conflict Separation: split waves if concurrent tasks share exclusive resources
        final_waves: list[ExecutionWave] = []
        current_wave_num = 1

        for w_idx in sorted(preliminary_waves.keys()):
            pending_ids = list(preliminary_waves[w_idx])
            while pending_ids:
                current_batch: list[str] = []
                remaining: list[str] = []
                claimed_exclusive_resources: set[str] = set()

                for tid in pending_ids:
                    t = task_map[tid]
                    task_exclusive_res = {r.name for r in t.resources if r.is_exclusive}
                    # If conflict with current batch, defer to next wave
                    if task_exclusive_res & claimed_exclusive_resources:
                        remaining.append(tid)
                    else:
                        current_batch.append(tid)
                        claimed_exclusive_resources.update(task_exclusive_res)

                batch_tasks = [task_map[tid] for tid in current_batch]
                # Update task's execution_wave attribute
                for t in batch_tasks:
                    t.execution_wave = current_wave_num

                est_duration = max((t.duration_expected for t in batch_tasks), default=0.0)
                final_waves.append(
                    ExecutionWave(
                        wave_number=current_wave_num,
                        task_ids=current_batch,
                        estimated_duration=round(est_duration, 2),
                        prerequisites_verified=False,
                    )
                )
                current_wave_num += 1
                pending_ids = remaining

        return final_waves

    def evaluate_deadline_feasibility(
        self,
        tasks: list[PlanTask],
        start_time: datetime,
        deadline: datetime | None,
        buffer_ratio: float = 0.20,
    ) -> dict[str, Any]:
        """Assess whether a strategic plan can meet a committed deadline without fabrication.

        INVARIANT 6: Estimate is not a guarantee.
        INVARIANT 17: Critical constraints cannot be optimized away.
        """
        if not tasks or not deadline:
            return {
                "is_feasible": True,
                "deadline": deadline,
                "expected_completion": None,
                "slack_hours": None,
                "notes": "No hard deadline specified or empty task list.",
            }

        # Calculate durations
        waves = self.cluster_execution_waves(tasks)
        total_expected_hours = sum(w.estimated_duration for w in waves)
        buffer_hours = total_expected_hours * buffer_ratio
        total_planned_hours = total_expected_hours + buffer_hours

        expected_completion = start_time + timedelta(hours=total_planned_hours)
        time_available_hours = (deadline - start_time).total_seconds() / 3600.0
        slack_hours = time_available_hours - total_planned_hours

        is_feasible = slack_hours >= 0.0

        result = {
            "is_feasible": is_feasible,
            "deadline": deadline.isoformat(),
            "start_time": start_time.isoformat(),
            "expected_duration_hours": round(total_expected_hours, 2),
            "buffer_hours": round(buffer_hours, 2),
            "total_planned_hours": round(total_planned_hours, 2),
            "time_available_hours": round(time_available_hours, 2),
            "slack_hours": round(slack_hours, 2),
            "expected_completion": expected_completion.isoformat(),
        }

        if not is_feasible:
            deficit = abs(round(slack_hours, 2))
            result["infeasibility_details"] = {
                "deficit_hours": deficit,
                "bottleneck_cause": "Sequential execution waves and required buffers exceed available window.",
                "alternatives": [
                    "Increase concurrency by relaxing exclusive resource locks if safe.",
                    "Adopt Parallel or Stabilize-First strategy.",
                    "Negotiate extended deadline with stakeholders.",
                    "Descale non-critical milestones.",
                ],
            }
            logger.warning("Strategic plan deadline is INFEASIBLE by %s hours.", deficit)

        return result


scheduling_engine = SchedulingEngine()
