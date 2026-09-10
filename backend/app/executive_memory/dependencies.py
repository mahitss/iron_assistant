"""Dependency graph mapping and critical path estimation with uncertainty (INVARIANTS 65-68)."""

from __future__ import annotations

from typing import Any


class DependencyManager:
    """Maintains task and goal dependency relationships and evaluates the critical path."""

    def __init__(self) -> None:
        # task_id -> set of dependency task_ids
        self._dependencies: dict[str, set[str]] = {}

    def add_dependency(self, task_id: str, depends_on_task_id: str) -> None:
        """INVARIANT 65: task A depends on task B."""
        self._dependencies.setdefault(task_id, set()).add(depends_on_task_id)

    def get_dependencies(self, task_id: str) -> list[str]:
        return list(self._dependencies.get(task_id, set()))

    def estimate_critical_path(
        self,
        task_ids: list[str],
        task_durations: dict[str, float] | None = None,
        is_complete: bool = True,
    ) -> tuple[list[str], bool]:
        """INVARIANT 67 & 68: Computes critical path.
        If dependencies are incomplete, flags uncertainty.
        """
        durations = task_durations or {t: 1.0 for t in task_ids}
        # Detect unblocked tasks
        path = []
        for tid in task_ids:
            deps = self.get_dependencies(tid)
            if not deps or all(d in path for d in deps):
                path.append(tid)

        # INVARIANT 68: Do not claim exact critical path if dependencies are incomplete
        has_uncertainty = not is_complete or len(path) < len(task_ids)
        return path, has_uncertainty
