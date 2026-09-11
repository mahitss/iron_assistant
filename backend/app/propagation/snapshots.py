"""Graph snapshot manager for versioned, audit-proof, zero-data-leakage propagation (Task 75)."""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Any, Dict, List, Optional, Set
import uuid

from app.propagation.schemas import (
    EpistemicCategory,
    GraphSnapshotReference,
    PropagationEdge,
    RedundancyState,
    RelationshipType,
    TemporalDelay,
    generate_uuid,
    utc_now,
)

logger = logging.getLogger("kairo.propagation.snapshots")


class GraphSnapshot:
    """Immutable versioned snapshot of graph topology frozen at a specific timestamp (Spec 6, 49, 62)."""

    def __init__(
        self,
        snapshot_id: str,
        tenant_id: str,
        graph_version: int,
        snapshot_timestamp: datetime,
        entities: Dict[str, Dict[str, Any]],
        edges: List[PropagationEdge],
        source_references: List[str],
    ) -> None:
        self.snapshot_id = snapshot_id
        self.tenant_id = tenant_id
        self.graph_version = graph_version
        self.snapshot_timestamp = snapshot_timestamp
        self._entities: Dict[str, Dict[str, Any]] = dict(entities)
        self._edges: List[PropagationEdge] = list(edges)
        self.source_references = list(source_references)

        # Precompute adjacency index for efficient traversal
        # source_entity -> list of outgoing PropagationEdge
        self._out_edges: Dict[str, List[PropagationEdge]] = {}
        # target_entity -> list of incoming PropagationEdge
        self._in_edges: Dict[str, List[PropagationEdge]] = {}

        for edge in self._edges:
            self._out_edges.setdefault(edge.source_entity, []).append(edge)
            self._in_edges.setdefault(edge.target_entity, []).append(edge)

    @property
    def node_count(self) -> int:
        return len(self._entities)

    @property
    def edge_count(self) -> int:
        return len(self._edges)

    def get_entities(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._entities)

    def get_edges(self) -> List[PropagationEdge]:
        return list(self._edges)

    def get_outgoing_edges(self, node_id: str) -> List[PropagationEdge]:
        return list(self._out_edges.get(node_id, []))

    def get_incoming_edges(self, node_id: str) -> List[PropagationEdge]:
        return list(self._in_edges.get(node_id, []))

    def has_node(self, node_id: str) -> bool:
        return node_id in self._entities

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        return self._entities.get(node_id)

    def to_reference(self) -> GraphSnapshotReference:
        return GraphSnapshotReference(
            snapshot_id=self.snapshot_id,
            graph_version=self.graph_version,
            snapshot_timestamp=self.snapshot_timestamp,
            node_count=self.node_count,
            edge_count=self.edge_count,
            source_references=self.source_references,
        )


class GraphSnapshotEngine:
    """Creates, validates, and freezes graph snapshots with strict zero-leakage temporal isolation (Spec 62)."""

    def __init__(self) -> None:
        # snapshot_id -> GraphSnapshot
        self._snapshots: Dict[str, GraphSnapshot] = {}

    def create_snapshot(
        self,
        tenant_id: str = "default_tenant",
        entities: Optional[Dict[str, Dict[str, Any]]] = None,
        edges: Optional[List[PropagationEdge]] = None,
        as_of_timestamp: Optional[datetime] = None,
        source_references: Optional[List[str]] = None,
        snapshot_id: Optional[str] = None,
        graph_version: int = 1,
    ) -> GraphSnapshot:
        """Create an immutable snapshot with strict temporal cutoff (Spec 6, 62).
        
        Zero Future-Data Leakage: Any edge whose valid_from > as_of_timestamp
        or that has expired before as_of_timestamp is strictly handled according
        to temporal validity rules.
        """
        snapshot_time = as_of_timestamp or utc_now()
        raw_entities = entities or {}
        raw_edges = edges or []
        sid = snapshot_id or generate_uuid()

        filtered_entities: Dict[str, Dict[str, Any]] = {}
        for nid, n_data in raw_entities.items():
            # Check node temporal validity if present
            n_valid_from = n_data.get("valid_from")
            n_valid_until = n_data.get("valid_until")
            if n_valid_from and n_valid_from > snapshot_time:
                continue  # Future node leaked!
            if n_valid_until and n_valid_until < snapshot_time:
                continue  # Expired node
            filtered_entities[nid] = dict(n_data)

        filtered_edges: List[PropagationEdge] = []
        for edge in raw_edges:
            # Enforce temporal validity cutoff
            if edge.valid_from and edge.valid_from > snapshot_time:
                logger.debug("Excluded future edge %s -> %s (valid_from: %s > as_of: %s)", edge.source_entity, edge.target_entity, edge.valid_from, snapshot_time)
                continue
            if edge.valid_until and edge.valid_until < snapshot_time:
                logger.debug("Excluded expired edge %s -> %s (valid_until: %s < as_of: %s)", edge.source_entity, edge.target_entity, edge.valid_until, snapshot_time)
                continue

            # Ensure referenced nodes are registered in entities map
            if edge.source_entity not in filtered_entities:
                filtered_entities[edge.source_entity] = {"id": edge.source_entity, "name": edge.source_entity}
            if edge.target_entity not in filtered_entities:
                filtered_entities[edge.target_entity] = {"id": edge.target_entity, "name": edge.target_entity}

            filtered_edges.append(edge)

        snapshot = GraphSnapshot(
            snapshot_id=sid,
            tenant_id=tenant_id,
            graph_version=graph_version,
            snapshot_timestamp=snapshot_time,
            entities=filtered_entities,
            edges=filtered_edges,
            source_references=source_references or ["manual_topology"],
        )
        self._snapshots[sid] = snapshot
        logger.info(
            "Created GraphSnapshot %s (tenant=%s, nodes=%d, edges=%d, as_of=%s)",
            sid, tenant_id, snapshot.node_count, snapshot.edge_count, snapshot_time.isoformat(),
        )
        return snapshot

    def get_snapshot(self, snapshot_id: str) -> Optional[GraphSnapshot]:
        return self._snapshots.get(snapshot_id)

    def import_from_knowledge_graph(
        self,
        kg_edges: List[Dict[str, Any]],
        kg_nodes: Optional[List[Dict[str, Any]]] = None,
        as_of_timestamp: Optional[datetime] = None,
        tenant_id: str = "default_tenant",
    ) -> GraphSnapshot:
        """Bridge knowledge graph records into a Propagation snapshot."""
        entities: Dict[str, Dict[str, Any]] = {}
        if kg_nodes:
            for n in kg_nodes:
                nid = n.get("node_id", n.get("id"))
                if nid:
                    entities[nid] = n

        edges: List[PropagationEdge] = []
        for e in kg_edges:
            rel_str = str(e.get("relationship", "DEPENDS_ON")).upper()
            try:
                rel_type = RelationshipType(rel_str)
            except ValueError:
                rel_type = RelationshipType.DEPENDS_ON

            # Distinguish causal edges from correlational / dependency
            epistemic = EpistemicCategory.DEPENDENCY
            if rel_type == RelationshipType.CAUSES:
                epistemic = EpistemicCategory.CAUSAL_RELATIONSHIP
            elif rel_type == RelationshipType.CORRELATES_WITH:
                epistemic = EpistemicCategory.CORRELATION

            edges.append(
                PropagationEdge(
                    edge_id=e.get("edge_id", generate_uuid()),
                    source_entity=e.get("source_node_id", e.get("source", "")),
                    target_entity=e.get("target_node_id", e.get("target", "")),
                    relationship_type=rel_type,
                    epistemic_category=epistemic,
                    confidence=float(e.get("confidence", 1.0)),
                    evidence=e.get("evidence", []),
                    provenance=e.get("provenance", {}),
                    valid_from=e.get("valid_from"),
                    valid_until=e.get("valid_until"),
                    source="knowledge_graph",
                )
            )

        return self.create_snapshot(
            tenant_id=tenant_id,
            entities=entities,
            edges=edges,
            as_of_timestamp=as_of_timestamp,
            source_references=["knowledge_graph"],
        )


# Global default snapshot engine
default_snapshot_engine = GraphSnapshotEngine()
