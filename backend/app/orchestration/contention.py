"""Resource contention detection, anti-starvation fairness, and conflict resolution (Task 59)."""

from __future__ import annotations

import logging
from typing import Any

from app.orchestration.resource_registry import ResourceRegistry, default_resource_registry
from app.orchestration.schemas import (
    ContentionStrategy,
    TaskCapabilityRequirement,
)

logger = logging.getLogger(__name__)


class ContentionResolver:
    """Detects resource conflicts between parallel tasks and determines optimal resolution strategies."""

    def __init__(self, resource_registry: ResourceRegistry | None = None) -> None:
        self._registry = resource_registry or default_resource_registry
        self._task_wait_turns: dict[str, int] = {}  # Anti-starvation counter

    def detect_contention(
        self,
        tasks: list[TaskCapabilityRequirement],
    ) -> list[dict[str, Any]]:
        """Identify shared resource over-subscription among a batch of concurrent tasks."""
        # Clean expired reservations first
        self._registry.clean_expired_reservations()

        resource_demands: dict[str, list[dict[str, Any]]] = {}
        for task in tasks:
            for req_res in task.required_resources:
                res_id = req_res.get("resource_id", req_res.get("id"))
                amount = float(req_res.get("amount", 1.0))
                if not res_id:
                    continue
                if res_id not in resource_demands:
                    resource_demands[res_id] = []
                resource_demands[res_id].append({
                    "task_id": task.task_id,
                    "priority": task.priority,
                    "amount": amount,
                    "is_irreversible": task.is_irreversible,
                })

        conflicts: list[dict[str, Any]] = []
        for res_id, demands in resource_demands.items():
            if not self._registry.has_resource(res_id):
                continue
            res = self._registry.get(res_id)
            total_demanded = sum(d["amount"] for d in demands)

            if total_demanded > res.available_capacity:
                conflicts.append({
                    "resource_id": res_id,
                    "resource_name": res.name,
                    "available_capacity": res.available_capacity,
                    "total_demanded": total_demanded,
                    "competing_tasks": demands,
                    "strategy": ContentionStrategy.SEQUENCE if len(demands) > 1 else ContentionStrategy.DEFER,
                })

        return conflicts

    def resolve_contention(
        self,
        tasks: list[TaskCapabilityRequirement],
        strategy: ContentionStrategy = ContentionStrategy.SEQUENCE,
    ) -> list[list[TaskCapabilityRequirement]]:
        """Resolve contention by partitioning competing tasks into sequential execution waves.

        Uses priority and anti-starvation age weighting.
        """
        conflicts = self.detect_contention(tasks)
        if not conflicts:
            # No contention, can run concurrently in a single wave
            return [tasks]

        logger.warning("CONTENTION_DETECTED: %d resource conflicts found. Applying %s strategy.", len(conflicts), strategy.value)

        # Sort tasks by effective priority (priority + wait_turns / 2) to prevent starvation
        sorted_tasks = list(tasks)
        for t in sorted_tasks:
            current_turns = self._task_wait_turns.get(t.task_id, 0)
            t_score = t.priority + (current_turns * 0.5)
            # Store temporary sort score
            setattr(t, "_effective_priority", t_score)

        sorted_tasks.sort(key=lambda t: getattr(t, "_effective_priority", t.priority), reverse=True)

        # Greedy bin-packing into conflict-free waves
        waves: list[list[TaskCapabilityRequirement]] = []
        for task in sorted_tasks:
            placed = False
            for wave in waves:
                candidate_wave = wave + [task]
                wave_conflicts = self.detect_contention(candidate_wave)
                if not wave_conflicts:
                    wave.append(task)
                    placed = True
                    break
            if not placed:
                waves.append([task])

        # Update wait turns for anti-starvation
        # Tasks placed in wave 0 get wait turn reset, subsequent waves get wait turn incremented
        for idx, wave in enumerate(waves):
            for t in wave:
                if idx == 0:
                    self._task_wait_turns[t.task_id] = 0
                else:
                    self._task_wait_turns[t.task_id] = self._task_wait_turns.get(t.task_id, 0) + idx

        return waves


contention_resolver = ContentionResolver()
