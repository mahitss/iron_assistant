"""Graph summarization, compact entity profiles, and cache invalidation (INVARIANTS 140-142, 181, 182)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from app.knowledge_graph.graph import KnowledgeGraph
from app.knowledge_graph.schemas import EntitySummarySchema


class GraphSummarizer:
    """Generates grounded entity and project profiles with cache invalidation."""

    def __init__(self, graph: KnowledgeGraph) -> None:
        self.graph = graph
        # entity_id -> (timestamp, EntitySummarySchema)
        self._summary_cache: Dict[str, tuple[datetime, EntitySummarySchema]] = {}

    def summarize_entity(self, node_id: str, force_refresh: bool = False) -> Optional[EntitySummarySchema]:
        """INVARIANT 140 & 141: Compact grounded summaries without introducing unsupported facts."""
        node = self.graph.nodes.get_node(node_id)
        if not node:
            return None

        # Check cache
        if not force_refresh and node_id in self._summary_cache:
            cache_time, cached_summary = self._summary_cache[node_id]
            if cache_time >= node.updated_at:
                return cached_summary

        # Build grounded profile
        out_edges = self.graph.edges.get_outgoing_edges(node_id)
        in_edges = self.graph.edges.get_incoming_edges(node_id)

        key_rels = [
            {"relationship": e.relationship.value, "target": e.target_node_id}
            for e in out_edges[:5]
        ] + [
            {"relationship": e.relationship.value, "source": e.source_node_id}
            for e in in_edges[:5]
        ]

        summary_text = (
            f"Entity '{node.canonical_name}' ({node.node_type.value}) with {len(out_edges) + len(in_edges)} active relationships. "
            f"Scope: {node.scope.value}."
        )

        summary = EntitySummarySchema(
            entity_id=node_id,
            canonical_name=node.canonical_name,
            node_type=node.node_type,
            summary_text=summary_text,
            key_relationships=key_rels,
            recent_changes=[],
            active_decisions=[],
            stale_flags=[],
        )

        self._summary_cache[node_id] = (datetime.now(UTC), summary)
        return summary

    def invalidate_cache(self, node_id: Optional[str] = None) -> None:
        """INVARIANT 182: Invalidate stale summaries when graph changes materially."""
        if node_id:
            self._summary_cache.pop(node_id, None)
        else:
            self._summary_cache.clear()
