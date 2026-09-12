"""Deadlock & Contention Engine: bipartite wait-for graph cycle detection and bounded resolution (Task 77)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.orchestration.economy_schemas import (
    ContentionResolutionStrategy,
    DeadlockCycle,
)

logger = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class DeadlockContentionEngine:
    """Maintains resource-task wait-for dependency graph and resolves deadlock cycles."""

    def __init__(self) -> None:
        # Adjacency list: node -> set of successor nodes
        # Node format: "T:<task_id>" or "R:<resource_id>"
        self._graph: dict[str, set[str]] = {}
        self._task_priorities: dict[str, int] = {}
        self._history: list[DeadlockCycle] = []

    def register_task_priority(self, task_id: str, priority: int) -> None:
        """Register priority of a task for victim selection."""
        self._task_priorities[task_id] = priority

    def add_allocation(self, resource_id: str, task_id: str) -> None:
        """Record that resource R is currently held by task T (Edge: R -> T)."""
        r_node = f"R:{resource_id}"
        t_node = f"T:{task_id}"
        if r_node not in self._graph:
            self._graph[r_node] = set()
        self._graph[r_node].add(t_node)
        if t_node not in self._graph:
            self._graph[t_node] = set()

    def remove_allocation(self, resource_id: str, task_id: str) -> None:
        """Remove edge R -> T when task releases resource."""
        r_node = f"R:{resource_id}"
        t_node = f"T:{task_id}"
        if r_node in self._graph:
            self._graph[r_node].discard(t_node)

    def add_wait(self, task_id: str, resource_id: str) -> None:
        """Record that task T is waiting for resource R (Edge: T -> R)."""
        t_node = f"T:{task_id}"
        r_node = f"R:{resource_id}"
        if t_node not in self._graph:
            self._graph[t_node] = set()
        self._graph[t_node].add(r_node)
        if r_node not in self._graph:
            self._graph[r_node] = set()

    def remove_wait(self, task_id: str, resource_id: str) -> None:
        """Remove edge T -> R when wait is satisfied or cancelled."""
        t_node = f"T:{task_id}"
        r_node = f"R:{resource_id}"
        if t_node in self._graph:
            self._graph[t_node].discard(r_node)

    def clear_task(self, task_id: str) -> None:
        """Remove all edges involving task T."""
        t_node = f"T:{task_id}"
        self._graph.pop(t_node, None)
        for _, succs in self._graph.items():
            succs.discard(t_node)

    def detect_deadlocks(self) -> list[DeadlockCycle]:
        """Detect all directed cycles in the wait-for graph using DFS."""
        visited: dict[str, int] = {}  # 0: unvisited, 1: visiting (in stack), 2: visited
        cycles: list[DeadlockCycle] = []
        path: list[str] = []

        for node in list(self._graph.keys()):
            visited[node] = 0

        def dfs(curr: str) -> None:
            visited[curr] = 1
            path.append(curr)

            for neighbor in self._graph.get(curr, set()):
                if visited.get(neighbor, 0) == 1:
                    # Found a cycle from neighbor to curr
                    cycle_start = path.index(neighbor)
                    raw_cycle = path[cycle_start:]
                    tasks = [n[2:] for n in raw_cycle if n.startswith("T:")]
                    resources = [n[2:] for n in raw_cycle if n.startswith("R:")]

                    if tasks and resources:
                        cycle = DeadlockCycle(
                            cycle_id=f"dlk_{uuid.uuid4().hex[:8]}",
                            involved_tasks=tasks,
                            involved_resources=resources,
                            detection_timestamp=_now_utc(),
                            resolution_strategy=ContentionResolutionStrategy.PREEMPT.value,
                            resolved=False,
                        )
                        cycles.append(cycle)
                elif visited.get(neighbor, 0) == 0:
                    dfs(neighbor)

            path.pop()
            visited[curr] = 2

        for node in list(self._graph.keys()):
            if visited.get(node, 0) == 0:
                dfs(node)

        return cycles

    def resolve_deadlock(
        self,
        cycle: DeadlockCycle,
        override_strategy: ContentionResolutionStrategy | None = None,
    ) -> tuple[str, ContentionResolutionStrategy]:
        """Resolve a detected deadlock cycle by selecting the optimal victim task.

        Victim selection criteria: lowest priority task in the cycle.
        """
        if not cycle.involved_tasks:
            return "", ContentionResolutionStrategy.DEFER

        # Select task with lowest priority as victim
        victim = min(
            cycle.involved_tasks,
            key=lambda tid: self._task_priorities.get(tid, 1),
        )

        strategy = override_strategy or ContentionResolutionStrategy.PREEMPT
        cycle.victim_task_id = victim
        cycle.resolution_strategy = strategy.value
        cycle.resolved = True

        # Break cycle in the graph by clearing victim's wait edges
        t_node = f"T:{victim}"
        if t_node in self._graph:
            self._graph[t_node].clear()

        self._history.append(cycle)
        logger.warning(
            "DEADLOCK_RESOLVED: cycle=%s, victim_task=%s, strategy=%s",
            cycle.cycle_id,
            victim,
            strategy.value,
        )
        return victim, strategy

    def get_graph_snapshot(self) -> dict[str, list[str]]:
        """Return human-readable adjacency snapshot of the wait-for graph."""
        return {node: list(neighbors) for node, neighbors in self._graph.items() if neighbors}

    def list_history(self) -> list[DeadlockCycle]:
        """Return historical deadlock cycles."""
        return list(self._history)


default_deadlock_engine = DeadlockContentionEngine()
