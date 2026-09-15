"""Lifecycle-aware capability dependency tracking and health propagation (Task 91 Phase 5)."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Set, Tuple

from app.capability_lifecycle.models import (
    CapabilityDependency,
    CapabilityMetadata,
    DependencyType,
    HealthStatus,
)
from app.capability_lifecycle.versioning import satisfies_constraint

logger = logging.getLogger("kairo.capability_lifecycle.dependency_graph")


class CapabilityDependencyGraph:
    """Tracks directed dependency relationships and propagates health state changes."""

    def __init__(self) -> None:
        # capability_id -> list of dependencies
        self._dependencies: Dict[str, List[CapabilityDependency]] = {}
        # target_id -> set of capability_ids that depend on it
        self._reverse_dependents: Dict[str, Set[str]] = {}

    def register_dependencies(
        self,
        capability_id: str,
        dependencies: List[CapabilityDependency],
    ) -> None:
        """Registers or updates dependencies for a given capability."""
        # Clear existing reverse mapping for capability
        self.remove_capability(capability_id)

        self._dependencies[capability_id] = list(dependencies)
        for dep in dependencies:
            self._reverse_dependents.setdefault(dep.target_id, set()).add(capability_id)

        logger.debug(
            "Registered %d dependencies for capability '%s'",
            len(dependencies),
            capability_id,
        )

    def remove_capability(self, capability_id: str) -> None:
        """Removes a capability and cleans up all reverse graph mappings."""
        old_deps = self._dependencies.pop(capability_id, [])
        for dep in old_deps:
            if dep.target_id in self._reverse_dependents:
                self._reverse_dependents[dep.target_id].discard(capability_id)
                if not self._reverse_dependents[dep.target_id]:
                    del self._reverse_dependents[dep.target_id]

    def get_dependencies(self, capability_id: str) -> List[CapabilityDependency]:
        """Returns direct dependencies for a capability."""
        return list(self._dependencies.get(capability_id, []))

    def get_dependents(self, target_id: str) -> List[str]:
        """Returns all capability IDs that depend on the given target_id (impact analysis)."""
        return list(self._reverse_dependents.get(target_id, set()))

    def get_transitive_dependents(self, target_id: str) -> Set[str]:
        """Performs BFS graph traversal to find all directly and indirectly affected capabilities."""
        visited: Set[str] = set()
        queue = list(self._reverse_dependents.get(target_id, set()))

        while queue:
            curr = queue.pop(0)
            if curr not in visited:
                visited.add(curr)
                # Enqueue anything that depends on curr
                queue.extend(self._reverse_dependents.get(curr, set()) - visited)

        return visited

    def validate_dependency_versions(
        self,
        capability_id: str,
        available_target_versions: Dict[str, str],
    ) -> Tuple[bool, List[str]]:
        """Verifies that currently available dependency targets satisfy version constraints."""
        deps = self._dependencies.get(capability_id, [])
        errors: List[str] = []

        for dep in deps:
            target_version = available_target_versions.get(dep.target_id)
            if not target_version:
                if not dep.is_optional:
                    errors.append(f"Required dependency '{dep.target_id}' ({dep.dependency_type.value}) is missing")
                continue

            if not satisfies_constraint(target_version, dep.version_constraint):
                errors.append(
                    f"Dependency '{dep.target_id}' version {target_version} violates constraint '{dep.version_constraint}'"
                )

        return len(errors) == 0, errors

    def propagate_health_degradation(
        self,
        unhealthy_target_id: str,
        target_health: HealthStatus,
        known_capabilities: Dict[str, CapabilityMetadata],
    ) -> List[str]:
        """Propagates failure or degradation of a dependency to all affected downstream capabilities."""
        affected_cap_ids = self.get_transitive_dependents(unhealthy_target_id)
        impacted: List[str] = []

        for cap_id in affected_cap_ids:
            cap = known_capabilities.get(cap_id)
            if not cap:
                continue

            # Update dependency health record within capability
            for dep in cap.dependencies:
                if dep.target_id == unhealthy_target_id:
                    dep.health_status = target_health

            # Downstream capability degrades if dependency is degraded or unsafe
            if target_health in (HealthStatus.DEGRADED, HealthStatus.UNSTABLE, HealthStatus.UNSAFE):
                if cap.health_state != target_health:
                    cap.health_state = HealthStatus.DEGRADED
                    impacted.append(cap_id)
                    logger.warning(
                        "Capability '%s' health degraded due to dependency '%s' becoming %s",
                        cap_id,
                        unhealthy_target_id,
                        target_health.value,
                    )

        return impacted


_global_dependency_graph: Optional[CapabilityDependencyGraph] = None


def get_capability_dependency_graph() -> CapabilityDependencyGraph:
    global _global_dependency_graph
    if _global_dependency_graph is None:
        _global_dependency_graph = CapabilityDependencyGraph()
    return _global_dependency_graph
