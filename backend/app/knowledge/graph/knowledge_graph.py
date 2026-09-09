"""In-memory semantic knowledge graph with entity extraction and neighborhood expansion."""

import logging
import re
from collections import defaultdict, deque
from typing import Any

from app.knowledge.schemas import EntityNode, RelationEdge

logger = logging.getLogger("kairo.knowledge.graph")


class KnowledgeGraph:
    """Stores entities, concepts, dependencies, and relation edges with multi-hop query support."""

    def __init__(self) -> None:
        self._nodes: dict[str, EntityNode] = {}
        self._edges: list[RelationEdge] = []
        self._adj_out: dict[str, list[RelationEdge]] = defaultdict(list)
        self._adj_in: dict[str, list[RelationEdge]] = defaultdict(list)

    def add_node(self, node: EntityNode) -> None:
        """Add or update an entity node in the graph."""
        key = node.name.lower()
        if key in self._nodes:
            # Merge aliases and mentions
            existing = self._nodes[key]
            existing.aliases = list(set(existing.aliases + node.aliases))
            existing.mentions_count += node.mentions_count
            existing.metadata.update(node.metadata)
        else:
            self._nodes[key] = node

    def add_edge(self, edge: RelationEdge) -> None:
        """Add a directed relationship edge between two entities."""
        src_key = edge.source.lower()
        tgt_key = edge.target.lower()

        # Ensure nodes exist
        if src_key not in self._nodes:
            self.add_node(EntityNode(name=edge.source, entity_type="CONCEPT"))
        if tgt_key not in self._nodes:
            self.add_node(EntityNode(name=edge.target, entity_type="CONCEPT"))

        # Check existing edge
        for existing in self._adj_out[src_key]:
            if existing.target.lower() == tgt_key and existing.relation_type == edge.relation_type:
                existing.weight = max(existing.weight, edge.weight)
                existing.evidence_chunks = list(set(existing.evidence_chunks + edge.evidence_chunks))
                return

        self._edges.append(edge)
        self._adj_out[src_key].append(edge)
        self._adj_in[tgt_key].append(edge)

    def get_node(self, name: str) -> EntityNode | None:
        """Fetch node by name or alias."""
        key = name.lower()
        if key in self._nodes:
            return self._nodes[key]
        for node in self._nodes.values():
            if any(a.lower() == key for a in node.aliases):
                return node
        return None

    def expand_neighborhood(self, entity_name: str, max_depth: int = 2) -> tuple[list[EntityNode], list[RelationEdge]]:
        """Perform BFS neighborhood expansion around an entity up to max_depth."""
        start = self.get_node(entity_name)
        if not start:
            return [], []

        visited_nodes: dict[str, EntityNode] = {start.name.lower(): start}
        collected_edges: list[RelationEdge] = []
        queue: deque[tuple[str, int]] = deque([(start.name.lower(), 0)])

        while queue:
            curr_key, depth = queue.popleft()
            if depth >= max_depth:
                continue

            # Check outgoing edges
            for edge in self._adj_out[curr_key]:
                collected_edges.append(edge)
                neighbor_key = edge.target.lower()
                if neighbor_key not in visited_nodes and neighbor_key in self._nodes:
                    visited_nodes[neighbor_key] = self._nodes[neighbor_key]
                    queue.append((neighbor_key, depth + 1))

            # Check incoming edges
            for edge in self._adj_in[curr_key]:
                collected_edges.append(edge)
                neighbor_key = edge.source.lower()
                if neighbor_key not in visited_nodes and neighbor_key in self._nodes:
                    visited_nodes[neighbor_key] = self._nodes[neighbor_key]
                    queue.append((neighbor_key, depth + 1))

        # Deduplicate edges
        dedup_edges = []
        seen_edges = set()
        for e in collected_edges:
            e_key = (e.source.lower(), e.relation_type, e.target.lower())
            if e_key not in seen_edges:
                seen_edges.add(e_key)
                dedup_edges.append(e)

        return list(visited_nodes.values()), dedup_edges

    def extract_and_link_entities(self, text: str, chunk_id: str | None = None) -> list[EntityNode]:
        """Heuristic entity and relation extraction from chunk text."""
        extracted: list[EntityNode] = []

        # Find Capitalized Multi-word phrases (e.g., "PostgreSQL Database", "Autonomous Agent", "Alice Smith")
        named_patterns = re.findall(r"\b[A-Z][a-zA-Z0-9_]+(?:\s+[A-Z][a-zA-Z0-9_]+)*\b", text)
        for name in named_patterns:
            if len(name) < 3 or name.lower() in {"the", "this", "that", "there", "then", "when", "what", "with"}:
                continue

            e_type = "CONCEPT"
            if any(w in name.lower() for w in ["database", "postgres", "redis", "fastapi", "docker"]):
                e_type = "TECHNOLOGY"
            elif any(w in name.lower() for w in ["agent", "router", "executor", "service", "engine"]):
                e_type = "SERVICE"

            node = EntityNode(
                name=name,
                entity_type=e_type,
                mentions_count=1,
                metadata={"source_chunk": chunk_id} if chunk_id else {},
            )
            self.add_node(node)
            extracted.append(node)

        # Detect co-occurrences and form "MENTIONS" or "RELATED_TO" edges between adjacent entities
        if len(extracted) >= 2:
            for i in range(len(extracted) - 1):
                src = extracted[i].name
                tgt = extracted[i + 1].name
                if src.lower() != tgt.lower():
                    edge = RelationEdge(
                        source=src,
                        relation_type="RELATED_TO",
                        target=tgt,
                        weight=0.6,
                        evidence_chunks=[chunk_id] if chunk_id else [],
                    )
                    self.add_edge(edge)

        return extracted

    def format_subgraph_context(self, nodes: list[EntityNode], edges: list[RelationEdge]) -> str:
        """Format nodes and edges into a clean markdown entity relationship block."""
        if not nodes and not edges:
            return ""

        lines = ["### Knowledge Graph Context:"]
        if nodes:
            node_desc = [f"- **{n.name}** ({n.entity_type})" for n in nodes[:15]]
            lines.append("Entities:\n" + "\n".join(node_desc))

        if edges:
            edge_desc = [f"- {e.source} --[{e.relation_type}]--> {e.target}" for e in edges[:20]]
            lines.append("Relationships:\n" + "\n".join(edge_desc))

        return "\n\n".join(lines)

    def total_nodes(self) -> int:
        return len(self._nodes)

    def total_edges(self) -> int:
        return len(self._edges)

    def clear(self) -> None:
        self._nodes.clear()
        self._edges.clear()
        self._adj_out.clear()
        self._adj_in.clear()
