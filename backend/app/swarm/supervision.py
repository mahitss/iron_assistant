"""Supervision, Stall Detection, DAG Validation, and Failure Isolation Engine (Phases 6, 7, 24, 25, 27, 28).

Enforces:
- DAGs must be strictly acyclic (cycles rejected immediately).
- Delegation depth must not exceed hard limit (max depth <= 4).
- Stalled, failing, or runaway agents must be detected deterministically.
- Failure isolation prevents a single failed worker from destroying the entire swarm.
"""

from __future__ import annotations

from collections import deque
import logging
import time
from typing import Any

from app.swarm.orchestration_domain import (
    AgentIdentity,
    AgentLifecycleState,
    AgentTask,
    DelegationLimits,
    StallState,
    TaskDependencyState,
)

logger = logging.getLogger("kairo.swarm.supervision")


class SwarmSupervisionEngine:
    """Supervises task execution, detects stalls, and validates DAG topologies."""

    def __init__(self, limits: DelegationLimits | None = None) -> None:
        self.limits = limits or DelegationLimits()

    # --------------------------------------------------------------------------
    # 1. DAG Topology & Cycle Validation (Phase 7)
    # --------------------------------------------------------------------------

    def validate_dag(self, tasks: list[AgentTask]) -> tuple[bool, str]:
        """Validate task graph for cycles, missing dependencies, and depth violations."""
        if not tasks:
            return True, "Empty task graph is valid"

        if len(tasks) > self.limits.max_tasks:
            return False, f"Task count ({len(tasks)}) exceeds maximum limit ({self.limits.max_tasks})"

        task_map = {t.task_id: t for t in tasks}
        in_degree: dict[str, int] = {t.task_id: 0 for t in tasks}
        adj_list: dict[str, list[str]] = {t.task_id: [] for t in tasks}

        for t in tasks:
            for dep_id in t.dependencies:
                if dep_id not in task_map:
                    return False, f"Task '{t.task_id}' references non-existent dependency '{dep_id}'"
                adj_list[dep_id].append(t.task_id)
                in_degree[t.task_id] += 1

        # Kahn's algorithm for cycle detection
        queue = deque([tid for tid, deg in in_degree.items() if deg == 0])
        visited_count = 0

        while queue:
            curr = queue.popleft()
            visited_count += 1
            for neighbor in adj_list[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if visited_count != len(tasks):
            return False, "Cycle detected in task dependency graph (Deadlock detected)"

        # Check delegation depth limit
        depth_ok, max_d = self._check_delegation_depth(tasks)
        if not depth_ok:
            return False, f"Delegation depth ({max_d}) exceeds maximum allowed depth ({self.limits.max_depth})"

        return True, "Task DAG is valid and acyclic"

    def validate_task_graph(
        self,
        tasks: dict[str, AgentTask] | list[AgentTask],
        limits: DelegationLimits | None = None,
    ) -> list[str]:
        """Validate task graph and return any constraint violation error strings."""
        active_limits = limits or self.limits
        old_limits = self.limits
        self.limits = active_limits
        try:
            task_list = list(tasks.values()) if isinstance(tasks, dict) else tasks
            ok, msg = self.validate_dag(task_list)
            if not ok:
                return [msg]
            return []
        finally:
            self.limits = old_limits

    def _check_delegation_depth(self, tasks: list[AgentTask]) -> tuple[bool, int]:
        """Verify maximum parent-child task hierarchy depth."""
        task_map = {t.task_id: t for t in tasks}
        max_depth = 0

        for t in tasks:
            depth = 1
            curr = t
            visited = {curr.task_id}
            while curr.parent_task_id and curr.parent_task_id in task_map:
                curr = task_map[curr.parent_task_id]
                if curr.task_id in visited:
                    return False, 999  # Cycle in hierarchy
                visited.add(curr.task_id)
                depth += 1

            if depth > max_depth:
                max_depth = depth

        return max_depth <= self.limits.max_depth, max_depth

    # --------------------------------------------------------------------------
    # 2. Dependency State Resolution (Phase 6)
    # --------------------------------------------------------------------------

    def resolve_dependencies(
        self,
        tasks: list[AgentTask],
        completed_task_ids: set[str],
    ) -> list[AgentTask]:
        """Update dependency states and identify runnable tasks."""
        runnable = []
        for t in tasks:
            if t.status in ("COMPLETED", "FAILED", "CANCELLED"):
                continue

            unmet = [dep for dep in t.dependencies if dep not in completed_task_ids]
            if not unmet:
                t.dependency_state = TaskDependencyState.RUNNABLE
                runnable.append(t)
            else:
                t.dependency_state = TaskDependencyState.BLOCKED_BY_DEPENDENCY

        return runnable

    # --------------------------------------------------------------------------
    # 3. Stall & Anomaly Detection (Phase 24 & 25)
    # --------------------------------------------------------------------------

    def assess_agent_health(
        self,
        agent: AgentIdentity,
        task: AgentTask | None,
        duration_seconds: float,
        consecutive_failures: int = 0,
    ) -> StallState:
        """Inspect agent behavior to identify slow, stalled, failing, or runaway execution."""
        # 1. Check runaway recursion / resource explosion
        if consecutive_failures >= 3:
            return StallState.FAILING

        # 2. Check hard timeout
        if duration_seconds > self.limits.max_runtime_seconds:
            return StallState.STALLED

        # 3. Check deadline proximity
        if task and task.deadline:
            from datetime import UTC, datetime
            now = datetime.now(UTC)
            if now > task.deadline:
                return StallState.STALLED
            remaining = (task.deadline - now).total_seconds()
            if remaining < 10.0 and agent.lifecycle_state == AgentLifecycleState.RUNNING:
                return StallState.SLOW

        if agent.lifecycle_state == AgentLifecycleState.WAITING and duration_seconds > 60.0:
            return StallState.STALLED

        if agent.lifecycle_state in (AgentLifecycleState.RUNNING, AgentLifecycleState.WAITING):
            if duration_seconds > 180.0:
                return StallState.SLOW

        return StallState.HEALTHY
