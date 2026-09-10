"""Digital Twin aggregate model and state synthesis engine (Task 54)."""

from __future__ import annotations

import uuid

from app.environment.schemas import (
    DigitalTwin,
    EnvironmentChange,
    EnvironmentEdge,
    EnvironmentNode,
    FreshnessState,
    HealthRecord,
    ScopeType,
)
from app.environment.temporal import calculate_freshness, utc_now


class DigitalTwinEngine:
    """Manages synthesis, versioning, and freshness of DigitalTwin aggregates."""

    @staticmethod
    def create_twin(
        scope: ScopeType = ScopeType.SYSTEM,
        scope_id: str | None = None,
        twin_id: str | None = None,
    ) -> DigitalTwin:
        """Initializes a new DigitalTwin instance for a given scope."""
        now = utc_now()
        tid = twin_id or f"dtw_{scope.value.lower()}_{uuid.uuid4().hex[:8]}"
        return DigitalTwin(
            twin_id=tid,
            scope=scope,
            scope_id=scope_id,
            version=1,
            timestamp=now,
            nodes={},
            edges={},
            health={},
            changes=[],
            confidence=1.0,
            provenance={"initialized_at": now.isoformat(), "scope": scope.value},
            freshness=FreshnessState.FRESH,
        )

    @staticmethod
    def upsert_node(twin: DigitalTwin, node: EnvironmentNode) -> DigitalTwin:
        """Adds or updates an environment node within the twin, incrementing version."""
        twin.nodes[node.node_id] = node
        twin.version += 1
        twin.timestamp = utc_now()
        DigitalTwinEngine._recalculate_twin_freshness_and_confidence(twin)
        return twin

    @staticmethod
    def upsert_edge(twin: DigitalTwin, edge: EnvironmentEdge) -> DigitalTwin:
        """Adds or updates an edge in the twin, incrementing version."""
        twin.edges[edge.edge_id] = edge
        twin.version += 1
        twin.timestamp = utc_now()
        return twin

    @staticmethod
    def update_node_health(twin: DigitalTwin, node_id: str, health: HealthRecord) -> DigitalTwin:
        """Updates health telemetry record for a node."""
        twin.health[node_id] = health
        if node_id in twin.nodes:
            twin.nodes[node_id].status = health.status.value
        twin.version += 1
        twin.timestamp = utc_now()
        return twin

    @staticmethod
    def record_change(twin: DigitalTwin, change: EnvironmentChange) -> DigitalTwin:
        """Appends a change event to the twin."""
        twin.changes.append(change)
        # Cap change log in memory to 500 entries
        if len(twin.changes) > 500:
            twin.changes = twin.changes[-500:]
        twin.version += 1
        twin.timestamp = utc_now()
        return twin

    @staticmethod
    def _recalculate_twin_freshness_and_confidence(twin: DigitalTwin) -> None:
        """Aggregates freshness and confidence across nodes."""
        if not twin.nodes:
            twin.freshness = FreshnessState.FRESH
            twin.confidence = 1.0
            return

        conf_sum = sum(n.confidence for n in twin.nodes.values())
        twin.confidence = round(conf_sum / len(twin.nodes), 2)

        stale_count = 0
        for n in twin.nodes.values():
            freshness = calculate_freshness(n.last_seen)
            if freshness in (FreshnessState.STALE, FreshnessState.EXPIRED):
                stale_count += 1

        if stale_count == 0:
            twin.freshness = FreshnessState.FRESH
        elif stale_count / len(twin.nodes) > 0.4:
            twin.freshness = FreshnessState.STALE
        else:
            twin.freshness = FreshnessState.FRESH
