"""Operational System State Graph with bounded traversal and cycle safety (Task 93 Phase 4 & Phase 16).

Maintains a live, thread-safe operational model of Kairo's active objectives, tasks,
capabilities, runtimes, resources, and incidents without creating a duplicate database.
"""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
import logging
import threading
from typing import Any

from app.system_state.hasher import compute_state_hash
from app.system_state.models import (
    EdgeType,
    EpistemicStatus,
    StateCategory,
    StateEdge,
    StateEntity,
    StateType,
    SystemStateSnapshot,
)

logger = logging.getLogger("kairo.system_state.graph")


class SystemStateGraph:
    """In-memory bounded operational state graph connecting Kairo's subsystems."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._entities: dict[str, StateEntity] = {}
        # Forward edges: source_id -> set of target_ids
        self._forward_adj: dict[str, set[str]] = {}
        # Reverse edges: target_id -> set of source_ids
        self._reverse_adj: dict[str, set[str]] = {}
        # Full edge descriptors keyed by (source_id, target_id, edge_type)
        self._edges: dict[tuple[str, str, EdgeType], StateEdge] = {}

    def clear(self) -> None:
        """Reset the graph state."""
        with self._lock:
            self._entities.clear()
            self._forward_adj.clear()
            self._reverse_adj.clear()
            self._edges.clear()

    # =========================================================================
    # Entity Operations
    # =========================================================================

    def add_entity(self, entity: StateEntity) -> StateEntity:
        """Register or update an operational entity in the graph."""
        with self._lock:
            existing = self._entities.get(entity.id)
            if existing and existing.version >= entity.version:
                # Retain monotonic version ordering
                return existing

            self._entities[entity.id] = entity
            if entity.id not in self._forward_adj:
                self._forward_adj[entity.id] = set()
            if entity.id not in self._reverse_adj:
                self._reverse_adj[entity.id] = set()
            return entity

    def get_entity(self, entity_id: str) -> StateEntity | None:
        """Retrieve an entity by unique identifier."""
        with self._lock:
            return self._entities.get(entity_id)

    def list_entities(
        self,
        state_type: StateType | None = None,
        status: StateCategory | None = None,
        epistemic_status: EpistemicStatus | None = None,
    ) -> list[StateEntity]:
        """List entities filtered by type, status, or epistemic classification."""
        with self._lock:
            results = list(self._entities.values())
            if state_type is not None:
                results = [e for e in results if e.state_type == state_type]
            if status is not None:
                results = [e for e in results if e.status == status]
            if epistemic_status is not None:
                results = [e for e in results if e.epistemic_status == epistemic_status]
            return results

    def remove_entity(self, entity_id: str) -> bool:
        """Remove an entity and all incident edges from the graph."""
        with self._lock:
            if entity_id not in self._entities:
                return False

            del self._entities[entity_id]

            # Remove associated forward and reverse edges
            for target_id in list(self._forward_adj.get(entity_id, [])):
                self._reverse_adj.get(target_id, set()).discard(entity_id)
            self._forward_adj.pop(entity_id, None)

            for source_id in list(self._reverse_adj.get(entity_id, [])):
                self._forward_adj.get(source_id, set()).discard(entity_id)
            self._reverse_adj.pop(entity_id, None)

            # Prune edge records
            keys_to_del = [k for k in self._edges if k[0] == entity_id or k[1] == entity_id]
            for k in keys_to_del:
                del self._edges[k]

            return True

    # =========================================================================
    # Edge Operations
    # =========================================================================

    def add_edge(self, edge: StateEdge) -> StateEdge:
        """Add a directed operational edge between existing entities."""
        with self._lock:
            # Ensure entity placeholders exist if external
            if edge.source_id not in self._entities:
                logger.warning("Adding edge from unknown source: %s", edge.source_id)
            if edge.target_id not in self._entities:
                logger.warning("Adding edge to unknown target: %s", edge.target_id)

            self._forward_adj.setdefault(edge.source_id, set()).add(edge.target_id)
            self._reverse_adj.setdefault(edge.target_id, set()).add(edge.source_id)
            self._edges[(edge.source_id, edge.target_id, edge.edge_type)] = edge
            return edge

    def remove_edge(self, source_id: str, target_id: str, edge_type: EdgeType | None = None) -> bool:
        """Remove an edge between two entities."""
        with self._lock:
            removed = False
            keys_to_remove = []
            for (s, t, et), edge in self._edges.items():
                if s == source_id and t == target_id:
                    if edge_type is None or et == edge_type:
                        keys_to_remove.append((s, t, et))

            for k in keys_to_remove:
                del self._edges[k]
                removed = True

            # If no edges remain between source and target, prune adjacency sets
            has_more = any(k[0] == source_id and k[1] == target_id for k in self._edges)
            if not has_more:
                self._forward_adj.get(source_id, set()).discard(target_id)
                self._reverse_adj.get(target_id, set()).discard(source_id)

            return removed

    def list_edges(self) -> list[StateEdge]:
        """Return all edges in the graph."""
        with self._lock:
            return list(self._edges.values())

    # =========================================================================
    # Bounded Graph Traversal & Impact Queries (Phase 16)
    # =========================================================================

    def impact_of(self, component_id: str, max_depth: int = 10) -> list[StateEntity]:
        """Find all downstream entities transitively affected if this component degrades.

        Traverses forward edges (e.g. INCIDENT -> COMPONENT, FAILURE -> GOAL)
        and reverse dependencies (CAPABILITY depends on RUNTIME => RUNTIME impact affects CAPABILITY).
        """
        with self._lock:
            if component_id not in self._entities:
                return []

            visited: set[str] = {component_id}
            queue: deque[tuple[str, int]] = deque([(component_id, 0)])
            affected_ids: list[str] = []

            while queue:
                current_id, depth = queue.popleft()
                if depth >= max_depth:
                    continue

                # 1. Direct forward impacts (e.g. INCIDENT -> AFFECTS -> COMPONENT)
                forward_neighbors = self._forward_adj.get(current_id, set())
                # 2. Reverse dependencies (nodes whose execution depends on current_id)
                reverse_neighbors = self._reverse_adj.get(current_id, set())

                for neighbor_id in forward_neighbors | reverse_neighbors:
                    if neighbor_id not in visited:
                        visited.add(neighbor_id)
                        affected_ids.append(neighbor_id)
                        queue.append((neighbor_id, depth + 1))

            return [self._entities[eid] for eid in affected_ids if eid in self._entities]

    def dependents_of(self, component_id: str, max_depth: int = 10) -> list[StateEntity]:
        """Find entities that directly or indirectly depend on this component."""
        with self._lock:
            visited: set[str] = {component_id}
            queue: deque[tuple[str, int]] = deque([(component_id, 0)])
            dependents: list[str] = []

            while queue:
                curr, depth = queue.popleft()
                if depth >= max_depth:
                    continue

                for predecessor in self._reverse_adj.get(curr, set()):
                    if predecessor not in visited:
                        visited.add(predecessor)
                        dependents.append(predecessor)
                        queue.append((predecessor, depth + 1))

            return [self._entities[eid] for eid in dependents if eid in self._entities]

    def dependencies_of(self, component_id: str, max_depth: int = 10) -> list[StateEntity]:
        """Find entities that this component directly or indirectly depends upon."""
        with self._lock:
            visited: set[str] = {component_id}
            queue: deque[tuple[str, int]] = deque([(component_id, 0)])
            deps: list[str] = []

            while queue:
                curr, depth = queue.popleft()
                if depth >= max_depth:
                    continue

                for successor in self._forward_adj.get(curr, set()):
                    if successor not in visited:
                        visited.add(successor)
                        deps.append(successor)
                        queue.append((successor, depth + 1))

            return [self._entities[eid] for eid in deps if eid in self._entities]

    def goals_affected_by(self, component_id: str) -> list[StateEntity]:
        """Return all active goals impacted if component_id fails or degrades."""
        impacted = self.impact_of(component_id)
        return [e for e in impacted if e.state_type == StateType.GOAL]

    def tasks_affected_by(self, component_id: str) -> list[StateEntity]:
        """Return all active tasks impacted if component_id fails or degrades."""
        impacted = self.impact_of(component_id)
        return [e for e in impacted if e.state_type == StateType.TASK]

    def capabilities_affected_by(self, component_id: str) -> list[StateEntity]:
        """Return all capabilities affected by degradation in component_id."""
        impacted = self.impact_of(component_id)
        return [e for e in impacted if e.state_type == StateType.CAPABILITY]

    def resources_used_by(self, goal_id: str) -> list[StateEntity]:
        """Discover resources consumed transitively across the operational tree of a goal."""
        dependencies = self.dependencies_of(goal_id)
        return [e for e in dependencies if e.state_type == StateType.RESOURCE]

    def incidents_affecting(self, goal_id: str) -> list[StateEntity]:
        """Find all active incidents impacting the goal or any of its supporting elements."""
        supporting = self.dependencies_of(goal_id)
        supporting_ids = {e.id for e in supporting}
        supporting_ids.add(goal_id)

        active_incidents = [
            e for e in self._entities.values()
            if e.state_type == StateType.INCIDENT and e.status in (StateCategory.ACTIVE, StateCategory.DEGRADED, StateCategory.FAILED)
        ]

        affecting = []
        for inc in active_incidents:
            # Check if incident impacts any supporting element
            impacted_by_incident = {e.id for e in self.impact_of(inc.id)}
            if not impacted_by_incident.isdisjoint(supporting_ids):
                affecting.append(inc)

        return affecting

    def blockers_for(self, goal_id: str) -> list[StateEntity]:
        """Identify degraded, failed, blocked, or unavailable entities supporting this goal."""
        unhealthy_statuses = {
            StateCategory.DEGRADED,
            StateCategory.FAILED,
            StateCategory.UNAVAILABLE,
            StateCategory.BLOCKED,
            StateCategory.STALE,
        }
        supporting = self.dependencies_of(goal_id)
        return [e for e in supporting if e.status in unhealthy_statuses]

    # =========================================================================
    # Freshness, Staleness & Snapshotting (Phase 5 & 20)
    # =========================================================================

    def mark_stale_entities(self, now: datetime | None = None) -> list[StateEntity]:
        """Scan entities and transition expired ones to STALE or UNKNOWN (Phase 19/20)."""
        current_time = now or datetime.now(UTC)
        stale_list: list[StateEntity] = []

        with self._lock:
            for entity_id, entity in list(self._entities.items()):
                if entity.is_stale(current_time):
                    # Invariant: Never assume FAILED without evidence. Transition to STALE or UNKNOWN.
                    new_status = StateCategory.UNKNOWN if entity.state_type == StateType.RUNTIME else StateCategory.STALE
                    updated = entity.with_update(
                        status=new_status,
                        epistemic_status=EpistemicStatus.UNKNOWN,
                        confidence=0.2,
                        metadata={"stale_detected_at": current_time.isoformat()},
                    )
                    self._entities[entity_id] = updated
                    stale_list.append(updated)

        return stale_list

    def export_snapshot(
        self, snapshot_id: str, watermark: int = 0, metadata: dict[str, Any] | None = None
    ) -> SystemStateSnapshot:
        """Create an immutable snapshot of the operational graph with deterministic state hash."""
        with self._lock:
            entities_copy = {k: v for k, v in self._entities.items()}
            edges_copy = list(self._edges.values())
            meta = metadata or {}

            state_hash = compute_state_hash(entities_copy, edges_copy)

            return SystemStateSnapshot(
                snapshot_id=snapshot_id,
                created_at=datetime.now(UTC),
                schema_version="v1",
                system_version="0.93.0",
                source_event_watermark=watermark,
                state_hash=state_hash,
                entities=entities_copy,
                edges=edges_copy,
                metadata=meta,
            )
