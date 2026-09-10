"""Execution topology generation, dependency graphs, and synchronization barriers (Task 59)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.orchestration.safety import OrchestrationSafetyError
from app.orchestration.schemas import (
    ExecutionTopology,
    ProviderAssignment,
    TaskCapabilityRequirement,
)

logger = logging.getLogger(__name__)


class TopologyEngine:
    """Constructs execution topologies, task-provider dependency graphs, and execution waves."""

    def build_topology(
        self,
        requirements: list[TaskCapabilityRequirement],
        assignments: list[ProviderAssignment],
        task_dependencies: dict[str, list[str]] | None = None,
    ) -> ExecutionTopology:
        """Construct an ExecutionTopology mapping tasks, providers, resources, and barriers."""
        deps = task_dependencies or {}
        assignment_map = {a.task_id: a for a in assignments}
        req_map = {r.task_id: r for r in requirements}

        # Validate DAG and detect cycles
        self._detect_cycles(list(req_map.keys()), deps)

        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []

        for tid, req in req_map.items():
            asgn = assignment_map.get(tid)
            node_data = {
                "id": tid,
                "title": req.title,
                "provider": asgn.provider_name if asgn else "UNASSIGNED",
                "provider_type": asgn.provider_type.value if asgn else "TOOL",
                "capabilities": req.required_capabilities,
                "environment": req.environment,
                "resources": req.required_resources,
                "verification": req.verification_criteria,
                "is_irreversible": req.is_irreversible,
                "priority": req.priority,
            }
            nodes.append(node_data)

            # Dependencies create directed edges
            for parent_id in deps.get(tid, []):
                edges.append({
                    "from": parent_id,
                    "to": tid,
                    "type": "DEPENDS_ON",
                })

        # Calculate execution waves via topological leveling
        waves = self._calculate_waves(list(req_map.keys()), deps, assignment_map)

        # Identify synchronization barriers (points where multiple parallel paths converge)
        barriers: list[dict[str, Any]] = []
        handoffs: list[dict[str, Any]] = []

        in_degree: dict[str, list[str]] = {}
        for edge in edges:
            to_node = edge["to"]
            from_node = edge["from"]
            in_degree.setdefault(to_node, []).append(from_node)

        for tid, parents in in_degree.items():
            if len(parents) > 1:
                barriers.append({
                    "barrier_id": f"bar_{tid}_{uuid.uuid4().hex[:6]}",
                    "converging_tasks": parents,
                    "target_task": tid,
                    "description": f"All parent tasks {parents} must successfully complete and verify before {tid} begins.",
                })
            elif len(parents) == 1:
                parent = parents[0]
                p_asgn = assignment_map.get(parent)
                t_asgn = assignment_map.get(tid)
                if p_asgn and t_asgn and p_asgn.provider_name != t_asgn.provider_name:
                    handoffs.append({
                        "from_task": parent,
                        "from_provider": p_asgn.provider_name,
                        "to_task": tid,
                        "to_provider": t_asgn.provider_name,
                    })

        topo = ExecutionTopology(
            execution_waves=waves,
            synchronization_barriers=barriers,
            handoff_points=handoffs,
            nodes=nodes,
            edges=edges,
        )
        logger.info(
            "TOPOLOGY_BUILT: nodes=%d edges=%d waves=%d barriers=%d",
            len(nodes),
            len(edges),
            len(waves),
            len(barriers),
        )
        return topo

    def _detect_cycles(self, task_ids: list[str], deps: dict[str, list[str]]) -> None:
        """Kahn's or DFS cycle detection."""
        visited: dict[str, int] = {}  # 0=unvisited, 1=visiting, 2=visited

        def dfs(node: str) -> None:
            visited[node] = 1
            for parent in deps.get(node, []):
                state = visited.get(parent, 0)
                if state == 1:
                    raise OrchestrationSafetyError(
                        f"Cycle detected in task dependencies: {node} -> {parent} creates an infinite dependency loop."
                    )
                if state == 0:
                    dfs(parent)
            visited[node] = 2

        for tid in task_ids:
            if visited.get(tid, 0) == 0:
                dfs(tid)

    def _calculate_waves(
        self,
        task_ids: list[str],
        deps: dict[str, list[str]],
        assignment_map: dict[str, ProviderAssignment],
    ) -> list[dict[str, Any]]:
        """Group tasks into discrete execution waves respecting dependencies."""
        levels: dict[str, int] = {}

        def get_level(node: str) -> int:
            if node in levels:
                return levels[node]
            parents = deps.get(node, [])
            if not parents:
                levels[node] = 0
                return 0
            lvl = max(get_level(p) for p in parents if p in task_ids) + 1
            levels[node] = lvl
            return lvl

        for tid in task_ids:
            get_level(tid)

        max_level = max(levels.values()) if levels else 0
        waves: list[dict[str, Any]] = []

        for lvl_idx in range(max_level + 1):
            tasks_in_level = [t for t, lvl in levels.items() if lvl == lvl_idx]
            wave_tasks = []
            for tid in tasks_in_level:
                asgn = assignment_map.get(tid)
                wave_tasks.append({
                    "task_id": tid,
                    "provider": asgn.provider_name if asgn else "UNASSIGNED",
                })
            waves.append({
                "wave_number": lvl_idx + 1,
                "tasks": wave_tasks,
                "is_parallel": len(tasks_in_level) > 1,
            })

        return waves


topology_engine = TopologyEngine()
