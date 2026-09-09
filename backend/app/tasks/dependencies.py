"""Dependency graph validation, cycle detection, and ready-step resolution for Tasks (Spec 9, 10)."""

from collections import defaultdict, deque
from typing import Dict, List, Set, Tuple
from app.tasks.schemas import StepStatus, TaskRiskLevel, TaskStepSchema


class DependencyError(ValueError):
    """Base exception for dependency graph validation failures."""
    pass


class CircularDependencyError(DependencyError):
    """Raised when a circular reference is detected in the plan DAG."""

    def __init__(self, cycle: list[str]) -> None:
        super().__init__(f"Circular dependency detected in plan: {' -> '.join(cycle)}")
        self.cycle = cycle


class MissingDependencyError(DependencyError):
    """Raised when a step references a dependency that does not exist in the plan."""

    def __init__(self, step_id: str, missing_dep: str) -> None:
        super().__init__(f"Step '{step_id}' references non-existent dependency '{missing_dep}'")
        self.step_id = step_id
        self.missing_dep = missing_dep


class DependencyResolver:
    """Validates DAG integrity, detects cycles, and calculates executable step sets."""

    @classmethod
    def validate_dag(cls, steps: list[TaskStepSchema]) -> list[str]:
        """Validate DAG integrity and return a valid topological execution order of step IDs.

        Raises:
            MissingDependencyError: If a step references a missing ID.
            CircularDependencyError: If a cycle exists.
        """
        step_ids = {s.id for s in steps}
        adj: dict[str, list[str]] = defaultdict(list)
        in_degree: dict[str, int] = {s.id: 0 for s in steps}

        # Build adjacency graph (dep -> dependent)
        for s in steps:
            for dep in s.dependencies:
                if dep == s.id:
                    raise CircularDependencyError([s.id, s.id])
                if dep not in step_ids:
                    raise MissingDependencyError(s.id, dep)
                adj[dep].append(s.id)
                in_degree[s.id] += 1

        # Kahn's algorithm for topological sort and cycle detection
        queue = deque([sid for sid, deg in in_degree.items() if deg == 0])
        topo_order: list[str] = []

        while queue:
            node = queue.popleft()
            topo_order.append(node)
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(topo_order) != len(steps):
            # Find cycle nodes for clear error message
            remaining = [sid for sid, deg in in_degree.items() if deg > 0]
            raise CircularDependencyError(remaining[:5] + [remaining[0]])

        return topo_order

    @classmethod
    def get_ready_steps(
        cls,
        steps: list[TaskStepSchema],
        completed_step_ids: Set[str],
        active_running_steps: list[TaskStepSchema] | None = None,
        max_parallel: int = 4,
    ) -> list[TaskStepSchema]:
        """Resolve all steps that are currently eligible for execution.

        Rules:
        - Step must be in PENDING or READY status.
        - All declared dependencies must be present in completed_step_ids.
        - Independent READ steps can be executed concurrently up to max_parallel.
        - WRITE / DESTRUCTIVE steps must execute serially (cannot run concurrently with other writes or if conflicting resources are locked).
        """
        active_running = active_running_steps or []
        running_writes = [
            s for s in active_running
            if s.risk_level in (TaskRiskLevel.WRITE, TaskRiskLevel.DESTRUCTIVE)
        ]

        # Extract currently locked resources
        locked_resources: Set[Tuple[str, str]] = set()
        for s in active_running:
            for r in s.resources:
                locked_resources.add((r.type.value if hasattr(r.type, 'value') else str(r.type), r.id))

        ready_candidates: list[TaskStepSchema] = []

        for step in steps:
            if step.id in completed_step_ids:
                continue

            if step.status not in (StepStatus.PENDING, StepStatus.READY):
                continue

            # Check if all dependencies are satisfied
            deps_satisfied = all(dep in completed_step_ids for dep in step.dependencies)
            if not deps_satisfied:
                continue

            # Check resource conflicts with currently running steps
            has_resource_conflict = False
            for r in step.resources:
                key = (r.type.value if hasattr(r.type, 'value') else str(r.type), r.id)
                if key in locked_resources:
                    has_resource_conflict = True
                    break

            if has_resource_conflict:
                continue

            # If this is a WRITE step and any other WRITE is already running, serialize it
            if step.risk_level in (TaskRiskLevel.WRITE, TaskRiskLevel.DESTRUCTIVE):
                if running_writes:
                    continue
                # Also serialize if multiple writes appear in the same ready candidate batch
                candidate_writes = [
                    c for c in ready_candidates
                    if c.risk_level in (TaskRiskLevel.WRITE, TaskRiskLevel.DESTRUCTIVE)
                ]
                if candidate_writes:
                    continue

            ready_candidates.append(step)

        # Apply concurrency limit
        available_slots = max(0, max_parallel - len(active_running))
        return ready_candidates[:available_slots]
