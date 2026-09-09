"""Dependency graph, cycle detection, topological sorting, and parallel safety for Kairo Cognitive Planning (Task 41)."""

from collections import defaultdict, deque
from typing import Any

from app.cognition.steps import PlanStep, StepRiskLevel


class DependencyCycleError(ValueError):
    """Raised when a dependency cycle is detected in a plan's steps."""
    pass


class ResourceConflictError(ValueError):
    """Raised when conflicting mutable operations cannot be safely coordinated."""
    pass


class DependencyGraph:
    """Directed Acyclic Graph (DAG) manager for plan step dependencies and parallel execution safety."""

    def __init__(self, steps: list[PlanStep] | None = None) -> None:
        self.steps_by_id: dict[str, PlanStep] = {}
        self.adjacency: dict[str, set[str]] = defaultdict(set)  # prereq -> set of dependents
        self.reverse_adjacency: dict[str, set[str]] = defaultdict(set)  # step -> set of prerequisites
        if steps:
            for s in steps:
                self.add_step(s)

    def add_step(self, step: PlanStep) -> None:
        """Register a step and its dependencies."""
        self.steps_by_id[step.step_id] = step
        if step.step_id not in self.adjacency:
            self.adjacency[step.step_id] = set()
        if step.step_id not in self.reverse_adjacency:
            self.reverse_adjacency[step.step_id] = set()

        for dep_id in step.dependencies:
            self.adjacency[dep_id].add(step.step_id)
            self.reverse_adjacency[step.step_id].add(dep_id)

    def detect_cycles(self) -> list[str]:
        """Detect if the graph contains any cycle using DFS color marking."""
        visited: dict[str, int] = {}  # 0=unvisited, 1=visiting, 2=visited
        cycle_nodes: list[str] = []

        def dfs(node: str, path: list[str]) -> bool:
            visited[node] = 1
            for neighbor in self.adjacency.get(node, set()):
                if visited.get(neighbor, 0) == 1:
                    cycle_start = path.index(neighbor) if neighbor in path else 0
                    cycle_nodes.extend(path[cycle_start:] + [neighbor])
                    return True
                if visited.get(neighbor, 0) == 0:
                    if dfs(neighbor, path + [neighbor]):
                        return True
            visited[node] = 2
            return False

        for node in self.steps_by_id:
            if visited.get(node, 0) == 0:
                if dfs(node, [node]):
                    return cycle_nodes

        return []

    def validate_acyclic(self) -> None:
        """Validate that the dependency graph has no cycles. Raises DependencyCycleError if a cycle is found."""
        cycle = self.detect_cycles()
        if cycle:
            raise DependencyCycleError(f"Dependency cycle detected among steps: {' -> '.join(cycle)}")

    def topological_sort(self) -> list[str]:
        """Return a valid linear execution order using Kahn's algorithm."""
        self.validate_acyclic()
        in_degree: dict[str, int] = {node: len(self.reverse_adjacency[node]) for node in self.steps_by_id}
        queue = deque([node for node, deg in in_degree.items() if deg == 0])
        order: list[str] = []

        while queue:
            node = queue.popleft()
            order.append(node)
            for neighbor in self.adjacency[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(self.steps_by_id):
            raise DependencyCycleError("Failed to sort dependency graph: unresolved cycle exists.")

        return order

    def compute_parallel_execution_tiers(self) -> list[list[str]]:
        """Compute execution tiers of steps that can safely run in parallel."""
        self.validate_acyclic()
        order = self.topological_sort()

        # Step levels: max(level of prereqs) + 1
        levels: dict[str, int] = {}
        for node in order:
            prereqs = self.reverse_adjacency[node]
            if not prereqs:
                levels[node] = 0
            else:
                levels[node] = max(levels[p] for p in prereqs) + 1

        tiers: dict[int, list[str]] = defaultdict(list)
        for node, lvl in levels.items():
            tiers[lvl].append(node)

        # Enforce parallel safety within each tier
        safe_tiers: list[list[str]] = []
        for lvl in sorted(tiers.keys()):
            tier_steps = [self.steps_by_id[sid] for sid in tiers[lvl]]
            disjoint_groups = self.partition_parallel_safe_steps(tier_steps)
            safe_tiers.extend(disjoint_groups)

        return safe_tiers

    def partition_parallel_safe_steps(self, steps: list[PlanStep]) -> list[list[str]]:
        """Partition steps into groups that are safe to run concurrently."""
        if len(steps) <= 1:
            return [[s.step_id for s in steps]]

        groups: list[list[PlanStep]] = []
        for step in steps:
            placed = False
            for group in groups:
                # Check for resource conflict with any step in this group
                if all(not self.has_resource_conflict(step, other) for other in group):
                    group.append(step)
                    placed = True
                    break
            if not placed:
                groups.append([step])

        return [[s.step_id for s in g] for g in groups]

    @staticmethod
    def extract_targeted_resources(step: PlanStep) -> set[str]:
        """Extract resource targets from step inputs."""
        resources = set()
        inputs = step.inputs or {}
        for key in ("file", "path", "file_path", "target", "resource", "table", "url", "repo"):
            if key in inputs and isinstance(inputs[key], str):
                resources.add(inputs[key].strip().lower())
        if "files" in inputs and isinstance(inputs["files"], list):
            for f in inputs["files"]:
                if isinstance(f, str):
                    resources.add(f.strip().lower())
        return resources

    @classmethod
    def has_resource_conflict(cls, step_a: PlanStep, step_b: PlanStep) -> bool:
        """Return true if step_a and step_b conflict and cannot run concurrently."""
        # Both read-only steps targeting the same resource do NOT conflict
        if step_a.risk == StepRiskLevel.READ and step_b.risk == StepRiskLevel.READ:
            return False

        # If either step writes or is destructive, check resource intersection
        res_a = cls.extract_targeted_resources(step_a)
        res_b = cls.extract_targeted_resources(step_b)

        if res_a and res_b and (res_a & res_b):
            return True

        # If both are write/destructive and resource is unspecified, assume conflict for safety
        if not res_a and not res_b and (step_a.risk != StepRiskLevel.READ or step_b.risk != StepRiskLevel.READ):
            if step_a.action == step_b.action:
                return True

        return False
