"""Temporal graph reconstruction, immutable snapshots, and graph diff engine for Task 117.

Integrates Task 111 (Temporal Intelligence) to answer:
- What did the evidence graph look like at time T?
- What changed in the evidence supporting this claim between yesterday and today?
- Generate cryptographic snapshots for immutable audit.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import uuid

from app.evidence_graph.domain import (
    DiffChangeType,
    EvidenceGraphEdge,
    EvidenceGraphNode,
    EvidenceGraphSnapshot,
    FreshnessState,
    GraphDiff,
    LifecycleStatus,
)

logger = logging.getLogger(__name__)


class TemporalEngine:
    """Historical reconstruction, snapshot generation, and differential graph analysis."""

    def filter_graph_as_of(
        self,
        nodes: List[EvidenceGraphNode],
        edges: List[EvidenceGraphEdge],
        as_of_iso: str,
    ) -> Tuple[List[EvidenceGraphNode], List[EvidenceGraphEdge]]:
        """Reconstruct the graph state as it existed at `as_of_iso` timestamp."""
        active_nodes: List[EvidenceGraphNode] = []
        valid_node_ids: Set[str] = set()

        for node in nodes:
            # Node must have been created at or before as_of_iso
            if node.created_at <= as_of_iso:
                # Check if it was invalidated or superseded before as_of_iso
                active_nodes.append(node)
                valid_node_ids.add(node.node_id)

        active_edges: List[EvidenceGraphEdge] = []
        for edge in edges:
            if edge.created_at <= as_of_iso:
                # Both endpoints must be valid
                if edge.source_node_id in valid_node_ids and edge.target_node_id in valid_node_ids:
                    # Check validity interval if present
                    if edge.valid_from and edge.valid_from > as_of_iso:
                        continue
                    if edge.valid_until and edge.valid_until < as_of_iso:
                        continue
                    active_edges.append(edge)

        return active_nodes, active_edges

    def create_snapshot(
        self,
        nodes: List[EvidenceGraphNode],
        edges: List[EvidenceGraphEdge],
        scope: Optional[Dict[str, Any]] = None,
        filters: Optional[Dict[str, Any]] = None,
        creation_reason: str = "AUDIT_SNAPSHOT",
    ) -> EvidenceGraphSnapshot:
        """Capture an immutable point-in-time snapshot with SHA-256 digest."""
        now_iso = datetime.now(timezone.utc).isoformat()
        snap_id = f"snap-{uuid.uuid4().hex[:16]}"
        nodes_data = [n.to_dict() for n in nodes]
        edges_data = [e.to_dict() for e in edges]

        content_for_hash = json.dumps({
            "snapshot_id": snap_id,
            "timestamp": now_iso,
            "nodes": [n["node_id"] for n in nodes_data],
            "edges": [e["edge_id"] for e in edges_data],
        }, sort_keys=True)
        checksum = hashlib.sha256(content_for_hash.encode("utf-8")).hexdigest()

        return EvidenceGraphSnapshot(
            snapshot_id=snap_id,
            timestamp=now_iso,
            graph_version=1,
            node_count=len(nodes_data),
            edge_count=len(edges_data),
            query_scope=scope or {},
            filters=filters or {},
            checksum=checksum,
            creation_reason=creation_reason,
            nodes=nodes_data,
            edges=edges_data,
        )

    def compute_diff(
        self,
        base_snapshot: EvidenceGraphSnapshot,
        target_snapshot: EvidenceGraphSnapshot,
    ) -> GraphDiff:
        """Compute the structural and state differences between two snapshots."""
        base_nodes_by_id = {n["node_id"]: n for n in base_snapshot.nodes}
        target_nodes_by_id = {n["node_id"]: n for n in target_snapshot.nodes}

        base_edges_by_id = {e["edge_id"]: e for e in base_snapshot.edges}
        target_edges_by_id = {e["edge_id"]: e for e in target_snapshot.edges}

        added_nodes: List[Dict[str, Any]] = []
        removed_nodes: List[Dict[str, Any]] = []
        changed_nodes: List[Dict[str, Any]] = []
        invalidated_nodes: List[Dict[str, Any]] = []
        stale_nodes: List[Dict[str, Any]] = []
        superseded_nodes: List[Dict[str, Any]] = []

        for nid, t_node in target_nodes_by_id.items():
            if nid not in base_nodes_by_id:
                added_nodes.append(t_node)
            else:
                b_node = base_nodes_by_id[nid]
                if t_node.get("content_hash") != b_node.get("content_hash") or t_node.get("version") != b_node.get("version"):
                    changed_nodes.append(t_node)

                # Check state changes
                if t_node.get("lifecycle_status") == LifecycleStatus.INVALIDATED.value and b_node.get("lifecycle_status") != LifecycleStatus.INVALIDATED.value:
                    invalidated_nodes.append(t_node)
                if t_node.get("freshness_state") == FreshnessState.STALE.value and b_node.get("freshness_state") != FreshnessState.STALE.value:
                    stale_nodes.append(t_node)
                if t_node.get("lifecycle_status") == LifecycleStatus.SUPERSEDED.value and b_node.get("lifecycle_status") != LifecycleStatus.SUPERSEDED.value:
                    superseded_nodes.append(t_node)

        for nid, b_node in base_nodes_by_id.items():
            if nid not in target_nodes_by_id:
                removed_nodes.append(b_node)

        added_edges: List[Dict[str, Any]] = []
        removed_edges: List[Dict[str, Any]] = []
        changed_edges: List[Dict[str, Any]] = []

        for eid, t_edge in target_edges_by_id.items():
            if eid not in base_edges_by_id:
                added_edges.append(t_edge)
            else:
                b_edge = base_edges_by_id[eid]
                if t_edge.get("confidence") != b_edge.get("confidence") or t_edge.get("relationship_type") != b_edge.get("relationship_type"):
                    changed_edges.append(t_edge)

        for eid, b_edge in base_edges_by_id.items():
            if eid not in target_edges_by_id:
                removed_edges.append(b_edge)

        return GraphDiff(
            base_ref=base_snapshot.snapshot_id,
            target_ref=target_snapshot.snapshot_id,
            added_nodes=added_nodes,
            removed_nodes=removed_nodes,
            changed_nodes=changed_nodes,
            added_edges=added_edges,
            removed_edges=removed_edges,
            changed_edges=changed_edges,
            invalidated_nodes=invalidated_nodes,
            stale_nodes=stale_nodes,
            superseded_nodes=superseded_nodes,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
