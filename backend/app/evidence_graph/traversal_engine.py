"""Bounded graph traversal engine for Task 117 Evidence Graph.

Answers:
- Which claims depend on this source?
- Which decisions depend on this evidence?
- What does X depend on (Upstream)?
- What depends on X (Downstream)?
- Which evidence chains are circular?
- What is the minimal sufficient provenance chain?

Strictly bounded: enforces max_depth, max_nodes, timeout guards, and cycle protection.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from app.evidence_graph.domain import (
    EvidenceGraphEdge,
    EvidenceGraphEdgeType,
    EvidenceGraphNode,
    EvidenceGraphNodeType,
    ImpactSeverity,
    ProvenanceMinimalityType,
)

logger = logging.getLogger(__name__)

# Standard edge sets
UPSTREAM_EDGE_TYPES: Set[EvidenceGraphEdgeType] = {
    EvidenceGraphEdgeType.DERIVED_FROM,
    EvidenceGraphEdgeType.EXTRACTED_FROM,
    EvidenceGraphEdgeType.TRANSFORMED_FROM,
    EvidenceGraphEdgeType.SUMMARIZED_FROM,
    EvidenceGraphEdgeType.GENERATED_FROM,
    EvidenceGraphEdgeType.OBSERVED_FROM,
    EvidenceGraphEdgeType.SUPPORTED_BY,
    EvidenceGraphEdgeType.VERIFIED_BY,
    EvidenceGraphEdgeType.CORROBORATED_BY,
    EvidenceGraphEdgeType.DEPENDS_ON,
    EvidenceGraphEdgeType.REQUIRES,
    EvidenceGraphEdgeType.CONFIRMED_BY,
    EvidenceGraphEdgeType.PRODUCED_BY,
    EvidenceGraphEdgeType.REPORTED_BY,
    EvidenceGraphEdgeType.MEASURED_BY,
    EvidenceGraphEdgeType.REPRODUCED_BY,
    EvidenceGraphEdgeType.SIMULATED_BY,
    EvidenceGraphEdgeType.EVALUATED_BY,
}

DOWNSTREAM_EDGE_TYPES: Set[EvidenceGraphEdgeType] = {
    EvidenceGraphEdgeType.USED_BY,
    EvidenceGraphEdgeType.SUPERSEDES,
    EvidenceGraphEdgeType.INVALIDATED_BY,
}


class TraversalEngine:
    """Safe, bounded graph traversal and dependency closure engine."""

    def __init__(
        self,
        default_max_depth: int = 8,
        hard_max_depth: int = 16,
        default_max_nodes: int = 150,
        hard_max_nodes: int = 500,
        default_timeout_ms: int = 5000,
    ):
        self.default_max_depth = default_max_depth
        self.hard_max_depth = hard_max_depth
        self.default_max_nodes = default_max_nodes
        self.hard_max_nodes = hard_max_nodes
        self.default_timeout_ms = default_timeout_ms

    def _normalize_limits(
        self,
        max_depth: Optional[int],
        max_nodes: Optional[int],
    ) -> Tuple[int, int]:
        depth = min(max_depth or self.default_max_depth, self.hard_max_depth)
        nodes = min(max_nodes or self.default_max_nodes, self.hard_max_nodes)
        return max(1, depth), max(1, nodes)

    def traverse_upstream(
        self,
        start_node_id: str,
        get_node_fn: Callable[[str], Optional[EvidenceGraphNode]],
        get_outgoing_edges_fn: Callable[[str], List[EvidenceGraphEdge]],
        get_incoming_edges_fn: Callable[[str], List[EvidenceGraphEdge]],
        max_depth: Optional[int] = None,
        max_nodes: Optional[int] = None,
        edge_type_filter: Optional[Set[EvidenceGraphEdgeType]] = None,
        as_of: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Find upstream dependencies (sources, observations, verifications, claims) that start_node_id depends on."""
        start_time = time.time()
        effective_depth, effective_nodes = self._normalize_limits(max_depth, max_nodes)
        
        visited_nodes: Dict[str, Dict[str, Any]] = {}
        traversed_edges: List[Dict[str, Any]] = []
        queue = deque([(start_node_id, 0, [start_node_id])])
        is_truncated = False
        cycles_detected: List[List[str]] = []

        start_node = get_node_fn(start_node_id)
        if not start_node:
            return {
                "start_node_id": start_node_id,
                "nodes": [],
                "edges": [],
                "depth_reached": 0,
                "is_truncated": False,
                "status": "NOT_FOUND",
                "cycles": [],
            }

        visited_nodes[start_node_id] = {
            "node": start_node.to_dict(),
            "depth": 0,
            "path": [start_node_id],
        }

        while queue:
            current_id, depth, path = queue.popleft()

            if depth >= effective_depth:
                is_truncated = True
                continue

            if len(visited_nodes) >= effective_nodes:
                is_truncated = True
                break

            # Check for timeout
            if (time.time() - start_time) * 1000 > self.default_timeout_ms:
                is_truncated = True
                break

            # In the evidence graph:
            # An edge X -> Y where rel in UPSTREAM_EDGE_TYPES means X depends on Y.
            # An edge Y -> X where rel == USED_BY means X is used by Y (Y depends on X), but conversely X's dependency is from Y if direction is reversed.
            # We inspect outgoing edges for UPSTREAM types and incoming edges for reciprocal types.
            candidate_edges: List[Tuple[EvidenceGraphEdge, str]] = []
            
            for edge in get_outgoing_edges_fn(current_id):
                rel = edge.relationship_type
                if edge_type_filter and rel not in edge_type_filter:
                    continue
                if rel in UPSTREAM_EDGE_TYPES or rel in {EvidenceGraphEdgeType.SUPERSEDED_BY, EvidenceGraphEdgeType.INVALIDATED_BY}:
                    candidate_edges.append((edge, edge.target_node_id))

            for edge in get_incoming_edges_fn(current_id):
                rel = edge.relationship_type
                if edge_type_filter and rel not in edge_type_filter:
                    continue
                if rel == EvidenceGraphEdgeType.USED_BY:
                    # Target is current, source is upstream
                    candidate_edges.append((edge, edge.source_node_id))

            for edge, next_node_id in candidate_edges:
                # Filter by temporal validity if requested
                if as_of:
                    if edge.valid_from and edge.valid_from > as_of:
                        continue
                    if edge.valid_until and edge.valid_until < as_of:
                        continue

                traversed_edges.append(edge.to_dict())

                if next_node_id in path:
                    # Circular dependency detected
                    cycle_slice = path[path.index(next_node_id):] + [next_node_id]
                    if cycle_slice not in cycles_detected:
                        cycles_detected.append(cycle_slice)
                    continue

                if next_node_id not in visited_nodes:
                    next_node = get_node_fn(next_node_id)
                    if next_node:
                        # Check node temporal validity if as_of provided
                        if as_of and next_node.created_at > as_of:
                            continue
                        visited_nodes[next_node_id] = {
                            "node": next_node.to_dict(),
                            "depth": depth + 1,
                            "path": path + [next_node_id],
                        }
                        queue.append((next_node_id, depth + 1, path + [next_node_id]))

        # Deduplicate edges
        dedup_edges = {e["edge_id"]: e for e in traversed_edges}.values()

        return {
            "start_node_id": start_node_id,
            "nodes": [v["node"] for v in visited_nodes.values()],
            "edges": list(dedup_edges),
            "depth_reached": max((v["depth"] for v in visited_nodes.values()), default=0),
            "is_truncated": is_truncated,
            "status": "TRUNCATED" if is_truncated else "COMPLETE",
            "cycles": cycles_detected,
        }

    def traverse_downstream(
        self,
        start_node_id: str,
        get_node_fn: Callable[[str], Optional[EvidenceGraphNode]],
        get_outgoing_edges_fn: Callable[[str], List[EvidenceGraphEdge]],
        get_incoming_edges_fn: Callable[[str], List[EvidenceGraphEdge]],
        max_depth: Optional[int] = None,
        max_nodes: Optional[int] = None,
        edge_type_filter: Optional[Set[EvidenceGraphEdgeType]] = None,
        as_of: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Find downstream dependents (evidence, claims, verifications, beliefs, decisions, actions, missions) that rely on start_node_id."""
        start_time = time.time()
        effective_depth, effective_nodes = self._normalize_limits(max_depth, max_nodes)
        
        visited_nodes: Dict[str, Dict[str, Any]] = {}
        traversed_edges: List[Dict[str, Any]] = []
        queue = deque([(start_node_id, 0, [start_node_id])])
        is_truncated = False
        cycles_detected: List[List[str]] = []

        start_node = get_node_fn(start_node_id)
        if not start_node:
            return {
                "start_node_id": start_node_id,
                "nodes": [],
                "edges": [],
                "depth_reached": 0,
                "is_truncated": False,
                "status": "NOT_FOUND",
                "cycles": [],
            }

        visited_nodes[start_node_id] = {
            "node": start_node.to_dict(),
            "depth": 0,
            "path": [start_node_id],
        }

        while queue:
            current_id, depth, path = queue.popleft()

            if depth >= effective_depth:
                is_truncated = True
                continue

            if len(visited_nodes) >= effective_nodes:
                is_truncated = True
                break

            if (time.time() - start_time) * 1000 > self.default_timeout_ms:
                is_truncated = True
                break

            # In downstream traversal:
            # If edge is X -> current with rel in UPSTREAM_EDGE_TYPES, then X depends on current (X is downstream).
            # If edge is current -> Y with rel == USED_BY, then Y uses current (Y is downstream).
            candidate_edges: List[Tuple[EvidenceGraphEdge, str]] = []

            for edge in get_incoming_edges_fn(current_id):
                rel = edge.relationship_type
                if edge_type_filter and rel not in edge_type_filter:
                    continue
                if rel in UPSTREAM_EDGE_TYPES or rel in {EvidenceGraphEdgeType.SUPERSEDED_BY, EvidenceGraphEdgeType.INVALIDATED_BY}:
                    candidate_edges.append((edge, edge.source_node_id))

            for edge in get_outgoing_edges_fn(current_id):
                rel = edge.relationship_type
                if edge_type_filter and rel not in edge_type_filter:
                    continue
                if rel == EvidenceGraphEdgeType.USED_BY or rel == EvidenceGraphEdgeType.SUPERSEDES:
                    candidate_edges.append((edge, edge.target_node_id))

            for edge, next_node_id in candidate_edges:
                if as_of:
                    if edge.valid_from and edge.valid_from > as_of:
                        continue
                    if edge.valid_until and edge.valid_until < as_of:
                        continue

                traversed_edges.append(edge.to_dict())

                if next_node_id in path:
                    cycle_slice = path[path.index(next_node_id):] + [next_node_id]
                    if cycle_slice not in cycles_detected:
                        cycles_detected.append(cycle_slice)
                    continue

                if next_node_id not in visited_nodes:
                    next_node = get_node_fn(next_node_id)
                    if next_node:
                        if as_of and next_node.created_at > as_of:
                            continue
                        visited_nodes[next_node_id] = {
                            "node": next_node.to_dict(),
                            "depth": depth + 1,
                            "path": path + [next_node_id],
                        }
                        queue.append((next_node_id, depth + 1, path + [next_node_id]))

        dedup_edges = {e["edge_id"]: e for e in traversed_edges}.values()

        return {
            "start_node_id": start_node_id,
            "nodes": [v["node"] for v in visited_nodes.values()],
            "edges": list(dedup_edges),
            "depth_reached": max((v["depth"] for v in visited_nodes.values()), default=0),
            "is_truncated": is_truncated,
            "status": "TRUNCATED" if is_truncated else "COMPLETE",
            "cycles": cycles_detected,
        }

    def detect_cycles(
        self,
        get_all_nodes_fn: Callable[[], List[EvidenceGraphNode]],
        get_outgoing_edges_fn: Callable[[str], List[EvidenceGraphEdge]],
        max_depth: int = 12,
    ) -> List[Dict[str, Any]]:
        """Detect circular dependencies in provenance using bounded cycle detection."""
        all_nodes = get_all_nodes_fn()
        visited_global: Set[str] = set()
        cycles: List[Dict[str, Any]] = []

        def dfs(node_id: str, path: List[str], depth: int):
            if depth > max_depth:
                return
            for edge in get_outgoing_edges_fn(node_id):
                if edge.relationship_type in UPSTREAM_EDGE_TYPES:
                    target = edge.target_node_id
                    if target in path:
                        cycle_path = path[path.index(target):] + [target]
                        cycle_repr = " -> ".join(cycle_path)
                        # Check if already added
                        if not any(c["cycle_path"] == cycle_path for c in cycles):
                            cycles.append({
                                "cycle_path": cycle_path,
                                "cycle_repr": cycle_repr,
                                "length": len(cycle_path) - 1,
                                "status": "CIRCULAR_PROVENANCE",
                            })
                    elif target not in visited_global:
                        dfs(target, path + [target], depth + 1)

        for node in all_nodes:
            if node.node_id not in visited_global:
                dfs(node.node_id, [node.node_id], 0)
                visited_global.add(node.node_id)

        return cycles

    def find_minimal_sufficient_provenance(
        self,
        target_node_id: str,
        get_node_fn: Callable[[str], Optional[EvidenceGraphNode]],
        get_outgoing_edges_fn: Callable[[str], List[EvidenceGraphEdge]],
        max_depth: int = 10,
    ) -> Dict[str, Any]:
        """Compute the smallest explainable subset of upstream nodes/edges required to reproduce lineage."""
        target_node = get_node_fn(target_node_id)
        if not target_node:
            return {
                "target_node_id": target_node_id,
                "chain_type": ProvenanceMinimalityType.PARTIAL_CHAIN.value,
                "nodes": [],
                "edges": [],
                "depth": 0,
                "root_sources": [],
            }

        # BFS to find shortest paths to root sources
        queue = deque([(target_node_id, [target_node_id], [])])
        shortest_to_sources: List[Tuple[List[str], List[EvidenceGraphEdge]]] = []
        visited = {target_node_id}

        while queue:
            current_id, path, edges = queue.popleft()
            curr_node = get_node_fn(current_id)

            if len(path) > max_depth:
                continue

            # If node is a terminal SOURCE or SOURCE_SNAPSHOT, we found a root
            if curr_node and curr_node.node_type in {
                EvidenceGraphNodeType.SOURCE,
                EvidenceGraphNodeType.SOURCE_SNAPSHOT,
                EvidenceGraphNodeType.OBSERVATION,
            } and current_id != target_node_id:
                shortest_to_sources.append((path, edges))
                continue

            outgoing = get_outgoing_edges_fn(current_id)
            has_upstream = False
            for edge in outgoing:
                if edge.relationship_type in UPSTREAM_EDGE_TYPES:
                    has_upstream = True
                    tgt = edge.target_node_id
                    if tgt not in path:
                        visited.add(tgt)
                        queue.append((tgt, path + [tgt], edges + [edge]))

            # If no further upstream edges, consider current node an leaf
            if not has_upstream and current_id != target_node_id:
                shortest_to_sources.append((path, edges))

        if not shortest_to_sources:
            return {
                "target_node_id": target_node_id,
                "chain_type": ProvenanceMinimalityType.PARTIAL_CHAIN.value,
                "nodes": [target_node.to_dict()],
                "edges": [],
                "depth": 0,
                "root_sources": [],
            }

        # Select minimal known chain
        # Sort by shortest path length
        shortest_to_sources.sort(key=lambda x: len(x[0]))
        minimal_path, minimal_edges = shortest_to_sources[0]

        chain_nodes = []
        for nid in minimal_path:
            node = get_node_fn(nid)
            if node:
                chain_nodes.append(node.to_dict())

        root_sources = [minimal_path[-1]]

        return {
            "target_node_id": target_node_id,
            "chain_type": ProvenanceMinimalityType.MINIMAL_KNOWN_CHAIN.value,
            "nodes": chain_nodes,
            "edges": [e.to_dict() for e in minimal_edges],
            "depth": len(minimal_path) - 1,
            "root_sources": root_sources,
        }
