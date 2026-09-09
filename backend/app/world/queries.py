"""Structured world queries, bounded graph traversal, and dependency extraction (Task 32, Spec 38, 41, 42, 98, 100)."""

from collections import deque
from datetime import UTC, datetime, timedelta
import logging
from typing import Any, Dict, List, Optional, Set

from app.world.entities import EntityType, WorldEntitySchema
from app.world.policies import WorldPolicyEngine
from app.world.relationships import RelationshipType, WorldRelationshipSchema

logger = logging.getLogger("kairo.world.queries")


class QueryBudgetExceededError(RuntimeError):
    """Raised when a query exceeds graph depth or entity count ceilings."""
    pass


class WorldQueryEngine:
    """Executes authorization-checked, bounded graph queries on World Model state."""

    MAX_TRAVERSAL_DEPTH: int = 3       # Prevent infinite graph recursion (Spec 42)
    MAX_ENTITIES_PER_QUERY: int = 100   # Bounded result count ceiling (Spec 41)

    @classmethod
    def get_project_state(
        cls,
        project_id: str,
        user_id: str,
        entities: list[WorldEntitySchema],
        relationships: list[WorldRelationshipSchema],
    ) -> dict[str, Any]:
        """Aggregate current operational state for a specific project (Spec 38, 43)."""
        project_entity: Optional[WorldEntitySchema] = None
        contained_entities: list[WorldEntitySchema] = []

        for e in entities:
            if e.project_id == project_id or e.id == project_id or e.source_id == project_id:
                WorldPolicyEngine.check_query_permission(user_id, e.owner_id, e.id)
                if e.type == EntityType.PROJECT:
                    project_entity = e
                else:
                    contained_entities.append(e)

        return {
            "project": project_entity.model_dump() if project_entity else None,
            "entities_count": len(contained_entities),
            "repositories": [e.model_dump() for e in contained_entities if e.type == EntityType.REPOSITORY],
            "tasks": [e.model_dump() for e in contained_entities if e.type == EntityType.TASK],
            "services": [e.model_dump() for e in contained_entities if e.type == EntityType.SERVICE],
            "all_entities": [e.model_dump() for e in contained_entities[:cls.MAX_ENTITIES_PER_QUERY]],
        }

    @classmethod
    def get_active_tasks(
        cls,
        user_id: str,
        project_id: Optional[str],
        entities: list[WorldEntitySchema],
    ) -> list[WorldEntitySchema]:
        """Query currently active/running autonomous tasks (Spec 38)."""
        active_states = {"QUEUED", "PLANNING", "RUNNING", "WAITING_APPROVAL", "WAITING_USER", "REPLANNING", "VERIFYING"}
        results: list[WorldEntitySchema] = []

        for e in entities:
            if e.type == EntityType.TASK and e.owner_id == user_id:
                if project_id and e.project_id != project_id:
                    continue
                if e.state.upper() in active_states:
                    results.append(e)

        return results[:cls.MAX_ENTITIES_PER_QUERY]

    @classmethod
    def get_connected_devices(
        cls,
        user_id: str,
        entities: list[WorldEntitySchema],
    ) -> list[WorldEntitySchema]:
        """Query currently connected devices for the user (Spec 38, 93)."""
        results: list[WorldEntitySchema] = []
        for e in entities:
            if e.type == EntityType.DEVICE and e.owner_id == user_id:
                if e.state.upper() == "CONNECTED":
                    results.append(e)
        return results

    @classmethod
    def get_repository_state(
        cls,
        repo_id_or_name: str,
        user_id: str,
        entities: list[WorldEntitySchema],
    ) -> Optional[WorldEntitySchema]:
        """Find a repository entity by internal ID or name/source_id."""
        for e in entities:
            if e.type == EntityType.REPOSITORY and e.owner_id == user_id:
                if e.id == repo_id_or_name or e.name.lower() == repo_id_or_name.lower() or e.source_id == repo_id_or_name:
                    return e
        return None

    @classmethod
    def get_service_health(
        cls,
        environment: str,
        user_id: str,
        entities: list[WorldEntitySchema],
    ) -> list[WorldEntitySchema]:
        """Query services matching an environment (Spec 38)."""
        results: list[WorldEntitySchema] = []
        clean_env = environment.lower().strip()
        for e in entities:
            if e.type == EntityType.SERVICE and e.owner_id == user_id:
                svc_env = str(e.metadata.get("environment", "development")).lower().strip()
                if svc_env == clean_env:
                    results.append(e)
        return results

    @classmethod
    def get_dependencies(
        cls,
        entity_id: str,
        user_id: str,
        entities_by_id: dict[str, WorldEntitySchema],
        relationships: list[WorldRelationshipSchema],
        max_depth: int = 3,
    ) -> dict[str, Any]:
        """
        Traverse dependency graph from root entity up to bounded depth (Spec 41, 42, 100).
        Uses BFS with visited set to guarantee cycle safety.
        """
        depth_limit = min(max_depth, cls.MAX_TRAVERSAL_DEPTH)
        root = entities_by_id.get(entity_id)
        if not root:
            return {"root": None, "dependencies": [], "depth": 0}

        WorldPolicyEngine.check_query_permission(user_id, root.owner_id, root.id)

        # Build adjacency list: source -> [targets]
        adj: dict[str, list[WorldRelationshipSchema]] = {}
        for r in relationships:
            if r.owner_id == user_id:
                adj.setdefault(r.source_entity_id, []).append(r)

        visited: Set[str] = {entity_id}
        queue: deque[tuple[str, int]] = deque([(entity_id, 0)])
        dep_entities: list[dict[str, Any]] = []
        traversed_edges: list[dict[str, Any]] = []

        while queue:
            curr_id, curr_depth = queue.popleft()
            if curr_depth >= depth_limit:
                continue

            for rel in adj.get(curr_id, []):
                target_id = rel.target_entity_id
                traversed_edges.append(rel.model_dump())
                if target_id not in visited:
                    visited.add(target_id)
                    target_ent = entities_by_id.get(target_id)
                    if target_ent:
                        dep_entities.append(target_ent.model_dump())
                        queue.append((target_id, curr_depth + 1))

        return {
            "root": root.model_dump(),
            "dependencies": dep_entities,
            "edges": traversed_edges,
            "depth_reached": min(depth_limit, len(visited) - 1),
        }

    @classmethod
    def get_recent_changes(
        cls,
        since: datetime,
        user_id: str,
        entities: list[WorldEntitySchema],
        project_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Filter domain entity state changes since timestamp (Spec 98, 99)."""
        changes: list[dict[str, Any]] = []

        for e in entities:
            if e.owner_id != user_id:
                continue
            if project_id and e.project_id != project_id:
                continue
            if e.observed_at >= since:
                changes.append({
                    "entity_id": e.id,
                    "type": e.type.value,
                    "name": e.name,
                    "state": e.state,
                    "source": e.source,
                    "observed_at": e.observed_at.isoformat(),
                    "summary": f"{e.type.value} '{e.name}' is {e.state} (via {e.source})",
                })

        # Sort newest first
        changes.sort(key=lambda c: c["observed_at"], reverse=True)
        return changes[:cls.MAX_ENTITIES_PER_QUERY]
