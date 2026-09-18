"""Singleton EvidenceGraphService for Task 117.

Coordinates:
- In-memory projection and query cache
- Traversal, impact, intelligence, temporal, and health engines
- Downstream bridges and lineage ingestion
- Database persistence and historical versioning
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

from app.evidence_graph.domain import (
    DuplicateEvidenceType,
    EvidenceFragilityAssessment,
    EvidenceGraphEdge,
    EvidenceGraphEdgeType,
    EvidenceGraphEdgeVersion,
    EvidenceGraphNode,
    EvidenceGraphNodeType,
    EvidenceGraphNodeVersion,
    EvidenceGraphSnapshot,
    FreshnessState,
    GraphDiff,
    GraphHealthAssessment,
    ImpactAssessment,
    ImpactSeverity,
    LifecycleStatus,
    LineageRecord,
    ProvenanceGap,
    ProvenanceStatus,
    RevalidationCandidate,
    RevalidationRecommendation,
    SourceConcentrationFinding,
)
from app.evidence_graph.downstream_bridges import EmergencyStopBridge, SubsystemLineageBridge
from app.evidence_graph.health_engine import HealthEngine
from app.evidence_graph.impact_engine import ImpactEngine
from app.evidence_graph.intelligence_engine import IntelligenceEngine
from app.evidence_graph.temporal_engine import TemporalEngine
from app.evidence_graph.traversal_engine import TraversalEngine

logger = logging.getLogger(__name__)


class EvidenceGraphService:
    """Production-grade Evidence Graph and Provenance Intelligence service."""

    def __init__(self):
        self._lock = asyncio.Lock()
        
        # In-memory storage
        self._nodes: Dict[str, EvidenceGraphNode] = {}
        self._edges: Dict[str, EvidenceGraphEdge] = {}
        self._outgoing_edges: Dict[str, List[str]] = {}
        self._incoming_edges: Dict[str, List[str]] = {}
        
        # Versions & Snapshots
        self._node_versions: Dict[str, List[EvidenceGraphNodeVersion]] = {}
        self._edge_versions: Dict[str, List[EvidenceGraphEdgeVersion]] = {}
        self._snapshots: Dict[str, EvidenceGraphSnapshot] = {}
        
        # Intelligence artifacts
        self._revalidation_candidates: Dict[str, RevalidationCandidate] = {}
        self._provenance_gaps: Dict[str, ProvenanceGap] = {}
        self._impact_records: Dict[str, ImpactAssessment] = {}
        self._fragility_records: Dict[str, EvidenceFragilityAssessment] = {}
        
        # Query cache with version tags
        self._graph_version: int = 1
        self._query_cache: Dict[str, Any] = {}
        
        # Engines
        self.traversal_engine = TraversalEngine()
        self.impact_engine = ImpactEngine(self.traversal_engine)
        self.intelligence_engine = IntelligenceEngine(self.traversal_engine)
        self.temporal_engine = TemporalEngine()
        self.health_engine = HealthEngine()
        
        # Bridges
        self.lineage_bridge = SubsystemLineageBridge(
            add_node_fn=self._add_node_internal,
            add_edge_fn=self._add_edge_internal,
        )

    def _invalidate_cache(self):
        self._graph_version += 1
        self._query_cache.clear()

    # -------------------------------------------------------------------------
    # Node Management
    # -------------------------------------------------------------------------

    def _add_node_internal(self, node: EvidenceGraphNode) -> None:
        self._nodes[node.node_id] = node
        if node.node_id not in self._outgoing_edges:
            self._outgoing_edges[node.node_id] = []
        if node.node_id not in self._incoming_edges:
            self._incoming_edges[node.node_id] = []
        self._invalidate_cache()

    async def add_node(self, node: EvidenceGraphNode) -> EvidenceGraphNode:
        EmergencyStopBridge.assert_operational(f"add_node_{node.node_id}")
        async with self._lock:
            # Check if updating an existing node -> version it
            if node.node_id in self._nodes:
                old = self._nodes[node.node_id]
                version_record = EvidenceGraphNodeVersion(
                    version_id=f"nver-{uuid.uuid4().hex[:12]}",
                    node_id=old.node_id,
                    version_number=old.version,
                    node_type=old.node_type,
                    payload=old.payload,
                    content_hash=old.content_hash,
                    created_at=old.updated_at,
                    supersedes_version=old.version - 1 if old.version > 1 else None,
                )
                if old.node_id not in self._node_versions:
                    self._node_versions[old.node_id] = []
                self._node_versions[old.node_id].append(version_record)
                node.version = old.version + 1

            self._add_node_internal(node)
            return node

    def get_node(self, node_id: str) -> Optional[EvidenceGraphNode]:
        return self._nodes.get(node_id)

    def list_nodes(
        self,
        node_type: Optional[str] = None,
        source_system: Optional[str] = None,
        freshness_state: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[EvidenceGraphNode]:
        res = list(self._nodes.values())
        if node_type:
            res = [n for n in res if n.node_type.value == node_type or str(n.node_type) == node_type]
        if source_system:
            res = [n for n in res if n.source_system == source_system]
        if freshness_state:
            res = [n for n in res if n.freshness_state.value == freshness_state or str(n.freshness_state) == freshness_state]
        return res[offset : offset + limit]

    # -------------------------------------------------------------------------
    # Edge Management
    # -------------------------------------------------------------------------

    def _add_edge_internal(self, edge: EvidenceGraphEdge) -> None:
        self._edges[edge.edge_id] = edge
        if edge.source_node_id not in self._outgoing_edges:
            self._outgoing_edges[edge.source_node_id] = []
        if edge.edge_id not in self._outgoing_edges[edge.source_node_id]:
            self._outgoing_edges[edge.source_node_id].append(edge.edge_id)

        if edge.target_node_id not in self._incoming_edges:
            self._incoming_edges[edge.target_node_id] = []
        if edge.edge_id not in self._incoming_edges[edge.target_node_id]:
            self._incoming_edges[edge.target_node_id].append(edge.edge_id)
        self._invalidate_cache()

    async def add_edge(self, edge: EvidenceGraphEdge) -> EvidenceGraphEdge:
        EmergencyStopBridge.assert_operational(f"add_edge_{edge.edge_id}")
        async with self._lock:
            # Ensure endpoints exist
            if edge.source_node_id not in self._nodes:
                # Create placeholder node if not yet registered
                placeholder = EvidenceGraphNode(
                    node_id=edge.source_node_id,
                    node_type=EvidenceGraphNodeType.EVIDENCE,
                    source_system="auto_discovered",
                )
                self._add_node_internal(placeholder)

            if edge.target_node_id not in self._nodes:
                placeholder = EvidenceGraphNode(
                    node_id=edge.target_node_id,
                    node_type=EvidenceGraphNodeType.SOURCE,
                    source_system="auto_discovered",
                )
                self._add_node_internal(placeholder)

            self._add_edge_internal(edge)
            return edge

    def get_edge(self, edge_id: str) -> Optional[EvidenceGraphEdge]:
        return self._edges.get(edge_id)

    def get_outgoing_edges(self, node_id: str) -> List[EvidenceGraphEdge]:
        eids = self._outgoing_edges.get(node_id, [])
        return [self._edges[eid] for eid in eids if eid in self._edges]

    def get_incoming_edges(self, node_id: str) -> List[EvidenceGraphEdge]:
        eids = self._incoming_edges.get(node_id, [])
        return [self._edges[eid] for eid in eids if eid in self._edges]

    def list_edges(self, limit: int = 100, offset: int = 0) -> List[EvidenceGraphEdge]:
        res = list(self._edges.values())
        return res[offset : offset + limit]

    # -------------------------------------------------------------------------
    # Traversal & Dependency Queries
    # -------------------------------------------------------------------------

    def get_upstream(
        self,
        node_id: str,
        max_depth: Optional[int] = None,
        max_nodes: Optional[int] = None,
        as_of: Optional[str] = None,
    ) -> Dict[str, Any]:
        cache_key = f"upstream:{node_id}:{max_depth}:{max_nodes}:{as_of}:{self._graph_version}"
        if cache_key in self._query_cache:
            return self._query_cache[cache_key]

        try:
            res = self.traversal_engine.traverse_upstream(
                start_node_id=node_id,
                get_node_fn=self.get_node,
                get_outgoing_edges_fn=self.get_outgoing_edges,
                get_incoming_edges_fn=self.get_incoming_edges,
                max_depth=max_depth,
                max_nodes=max_nodes,
                as_of=as_of,
            )
            self.health_engine.record_query_execution(success=True)
            self._query_cache[cache_key] = res
            return res
        except Exception as e:
            self.health_engine.record_query_execution(success=False)
            logger.error("Upstream traversal failed for %s: %s", node_id, e)
            raise

    def get_downstream(
        self,
        node_id: str,
        max_depth: Optional[int] = None,
        max_nodes: Optional[int] = None,
        as_of: Optional[str] = None,
    ) -> Dict[str, Any]:
        cache_key = f"downstream:{node_id}:{max_depth}:{max_nodes}:{as_of}:{self._graph_version}"
        if cache_key in self._query_cache:
            return self._query_cache[cache_key]

        try:
            res = self.traversal_engine.traverse_downstream(
                start_node_id=node_id,
                get_node_fn=self.get_node,
                get_outgoing_edges_fn=self.get_outgoing_edges,
                get_incoming_edges_fn=self.get_incoming_edges,
                max_depth=max_depth,
                max_nodes=max_nodes,
                as_of=as_of,
            )
            self.health_engine.record_query_execution(success=True)
            self._query_cache[cache_key] = res
            return res
        except Exception as e:
            self.health_engine.record_query_execution(success=False)
            logger.error("Downstream traversal failed for %s: %s", node_id, e)
            raise

    def get_minimal_chain(self, node_id: str, max_depth: int = 10) -> Dict[str, Any]:
        return self.traversal_engine.find_minimal_sufficient_provenance(
            target_node_id=node_id,
            get_node_fn=self.get_node,
            get_outgoing_edges_fn=self.get_outgoing_edges,
            max_depth=max_depth,
        )

    def detect_cycles(self) -> List[Dict[str, Any]]:
        return self.traversal_engine.detect_cycles(
            get_all_nodes_fn=lambda: list(self._nodes.values()),
            get_outgoing_edges_fn=self.get_outgoing_edges,
        )

    # -------------------------------------------------------------------------
    # Impact & Controlled Invalidation
    # -------------------------------------------------------------------------

    async def assess_blast_radius(self, node_id: str, cause_reason: str) -> ImpactAssessment:
        assessment = self.impact_engine.assess_blast_radius(
            root_node_id=node_id,
            cause_reason=cause_reason,
            get_node_fn=self.get_node,
            get_outgoing_edges_fn=self.get_outgoing_edges,
            get_incoming_edges_fn=self.get_incoming_edges,
        )
        self._impact_records[node_id] = assessment
        for c in assessment.revalidation_candidates:
            self._revalidation_candidates[c.candidate_id] = c
        return assessment

    async def propagate_invalidation(self, node_id: str, reason: str) -> ImpactAssessment:
        """Controlled invalidation without silent truth deletion."""
        EmergencyStopBridge.assert_operational(f"propagate_invalidation_{node_id}")
        async with self._lock:
            target = self._nodes.get(node_id)
            if target:
                target.lifecycle_status = LifecycleStatus.INVALIDATED
                target.freshness_state = FreshnessState.INVALID
                target.updated_at = datetime.now(timezone.utc).isoformat()

            assessment = await self.assess_blast_radius(node_id, reason)

            # Mark downstream nodes as requiring revalidation (do NOT delete them!)
            for d in assessment.direct_impacts + assessment.indirect_impacts:
                dep_id = d["node_id"]
                dep_node = self._nodes.get(dep_id)
                if dep_node:
                    dep_node.provenance_status = ProvenanceStatus.UNCERTAIN
                    dep_node.freshness_state = FreshnessState.STALE
                    dep_node.updated_at = datetime.now(timezone.utc).isoformat()

            self._invalidate_cache()
            return assessment

    def list_revalidation_candidates(self, limit: int = 50) -> List[RevalidationCandidate]:
        return list(self._revalidation_candidates.values())[:limit]

    # -------------------------------------------------------------------------
    # Intelligence Analysis
    # -------------------------------------------------------------------------

    def analyze_source_concentration(self, node_id: str) -> SourceConcentrationFinding:
        return self.intelligence_engine.analyze_source_concentration(
            node_id=node_id,
            get_node_fn=self.get_node,
            get_outgoing_edges_fn=self.get_outgoing_edges,
            get_incoming_edges_fn=self.get_incoming_edges,
        )

    def assess_fragility(self, node_id: str) -> EvidenceFragilityAssessment:
        fragility = self.intelligence_engine.assess_evidence_fragility(
            node_id=node_id,
            get_node_fn=self.get_node,
            get_outgoing_edges_fn=self.get_outgoing_edges,
            get_incoming_edges_fn=self.get_incoming_edges,
        )
        self._fragility_records[node_id] = fragility
        return fragility

    def list_provenance_gaps(self, node_id: Optional[str] = None) -> List[ProvenanceGap]:
        if node_id:
            return self.intelligence_engine.identify_provenance_gaps(
                node_id=node_id,
                get_node_fn=self.get_node,
                get_outgoing_edges_fn=self.get_outgoing_edges,
                get_incoming_edges_fn=self.get_incoming_edges,
            )
        # All gaps across all claims
        gaps: List[ProvenanceGap] = []
        for n in self._nodes.values():
            if n.node_type == EvidenceGraphNodeType.CLAIM:
                gaps.extend(
                    self.intelligence_engine.identify_provenance_gaps(
                        node_id=n.node_id,
                        get_node_fn=self.get_node,
                        get_outgoing_edges_fn=self.get_outgoing_edges,
                        get_incoming_edges_fn=self.get_incoming_edges,
                    )
                )
        return gaps

    def detect_duplicate_evidence(self) -> List[Dict[str, Any]]:
        ev_nodes = [n for n in self._nodes.values() if n.node_type == EvidenceGraphNodeType.EVIDENCE]
        return self.intelligence_engine.detect_duplicate_evidence(ev_nodes)

    # -------------------------------------------------------------------------
    # Temporal, Snapshots & Diff
    # -------------------------------------------------------------------------

    async def create_snapshot(self, reason: str = "AUDIT_SNAPSHOT") -> EvidenceGraphSnapshot:
        EmergencyStopBridge.assert_operational("create_snapshot")
        async with self._lock:
            snap = self.temporal_engine.create_snapshot(
                nodes=list(self._nodes.values()),
                edges=list(self._edges.values()),
                creation_reason=reason,
            )
            self._snapshots[snap.snapshot_id] = snap
            return snap

    def get_snapshot(self, snapshot_id: str) -> Optional[EvidenceGraphSnapshot]:
        return self._snapshots.get(snapshot_id)

    def diff_snapshots(self, base_id: str, target_id: str) -> Optional[GraphDiff]:
        base_snap = self.get_snapshot(base_id)
        target_snap = self.get_snapshot(target_id)
        if not base_snap or not target_snap:
            return None
        return self.temporal_engine.compute_diff(base_snap, target_snap)

    # -------------------------------------------------------------------------
    # Lineage Ingestion
    # -------------------------------------------------------------------------

    async def ingest_lineage_record(self, record: LineageRecord) -> EvidenceGraphNode:
        EmergencyStopBridge.assert_operational(f"ingest_lineage_{record.object_id}")
        async with self._lock:
            node = self.lineage_bridge.ingest_lineage_record(record)
            return node

    # -------------------------------------------------------------------------
    # Health & Diagnostics
    # -------------------------------------------------------------------------

    def get_health(self) -> GraphHealthAssessment:
        cycles = self.detect_cycles()
        gaps = self.list_provenance_gaps()
        return self.health_engine.assess_graph_health(
            nodes=list(self._nodes.values()),
            edges=list(self._edges.values()),
            cycles_count=len(cycles),
            unresolved_gaps_count=len(gaps),
        )


# Global Singleton
_evidence_graph_service: Optional[EvidenceGraphService] = None


def get_evidence_graph_service() -> EvidenceGraphService:
    global _evidence_graph_service
    if _evidence_graph_service is None:
        _evidence_graph_service = EvidenceGraphService()
    return _evidence_graph_service
