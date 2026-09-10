"""Dependency graph builder, topological sort, and cycle detection (Task 58)."""

from __future__ import annotations

import logging

from app.planning.safety import DependencyCycleError
from app.planning.schemas import PlanTask

logger = logging.getLogger(__name__)


class DependencyGraphEngine:
    """Constructs and validates directed dependency graphs for strategic tasks."""

    def build_adjacency(self, tasks: list[PlanTask]) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
        """Build forward (task -> successors) and reverse (task -> predecessors) adjacency maps."""
        successors: dict[str, list[str]] = {t.task_id: [] for t in tasks}
        predecessors: dict[str, list[str]] = {t.task_id: [] for t in tasks}

        for t in tasks:
            for dep_id in t.dependencies:
                if dep_id in successors:
                    successors[dep_id].append(t.task_id)
                if t.task_id in predecessors:
                    predecessors[t.task_id].append(dep_id)

        return successors, predecessors

    def validate_dependencies(self, tasks: list[PlanTask]) -> tuple[bool, list[str]]:
        """Verify that all referenced dependencies exist within the task set."""
        known_ids = {t.task_id for t in tasks}
        errors: list[str] = []

        for t in tasks:
            for dep_id in t.dependencies:
                if dep_id not in known_ids:
                    errors.append(f"Task '{t.title}' ({t.task_id}) references missing dependency: {dep_id}")

        return len(errors) == 0, errors

    def detect_cycles(self, tasks: list[PlanTask]) -> list[str]:
        """Detect circular dependencies using DFS graph coloring. Returns cycle path if found."""
        _, predecessors = self.build_adjacency(tasks)

        # Predecessor graph: task -> tasks it depends on
        # State: 0 = unvisited, 1 = visiting, 2 = visited
        state: dict[str, int] = {t.task_id: 0 for t in tasks}
        parent_map: dict[str, str] = {}
        cycle_path: list[str] = []

        def dfs(node: str, path: list[str]) -> bool:
            state[node] = 1  # visiting
            for pred in predecessors.get(node, []):
                if pred not in state:
                    continue
                if state[pred] == 1:
                    # Found cycle
                    cycle_start_idx = path.index(pred) if pred in path else 0
                    cycle_path.extend(path[cycle_start_idx:])
                    cycle_path.append(pred)
                    return True
                if state[pred] == 0:
                    parent_map[pred] = node
                    if dfs(pred, path + [pred]):
                        return True
            state[node] = 2  # visited
            return False

        for t in tasks:
            if state[t.task_id] == 0:
                if dfs(t.task_id, [t.task_id]):
                    return cycle_path

        return []

    def topological_sort(self, tasks: list[PlanTask]) -> list[PlanTask]:
        """Return tasks ordered topologically. Raises DependencyCycleError if a cycle is present."""
        cycle = self.detect_cycles(tasks)
        if cycle:
            cycle_str = " -> ".join(cycle)
            raise DependencyCycleError(f"Circular dependency detected: {cycle_str}")

        successors, predecessors = self.build_adjacency(tasks)
        in_degree = {t.task_id: len(predecessors[t.task_id]) for t in tasks}
        task_map = {t.task_id: t for t in tasks}

        zero_in = [tid for tid, deg in in_degree.items() if deg == 0]
        sorted_tasks: list[PlanTask] = []

        while zero_in:
            curr_id = zero_in.pop(0)
            sorted_tasks.append(task_map[curr_id])
            for succ_id in successors.get(curr_id, []):
                in_degree[succ_id] -= 1
                if in_degree[succ_id] == 0:
                    zero_in.append(succ_id)

        if len(sorted_tasks) != len(tasks):
            raise DependencyCycleError("Dependency graph contains an unresolved cycle or isolated loop.")

        return sorted_tasks


dependency_graph_engine = DependencyGraphEngine()
