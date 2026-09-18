"""FastAPI Router for Task 117:
Autonomous Evidence Graph, Provenance Intelligence & Verification Dependency Engine.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.evidence_graph.domain import (
    EvidenceGraphEdge,
    EvidenceGraphEdgeType,
    EvidenceGraphNode,
    EvidenceGraphNodeType,
    FreshnessState,
    ImpactSeverity,
    LifecycleStatus,
    LineageRecord,
    ProvenanceStatus,
)
from app.evidence_graph.schemas import (
    EvidenceFragilityResponse,
    EvidenceGraphEdgeCreate,
    EvidenceGraphEdgeResponse,
    EvidenceGraphNodeCreate,
    EvidenceGraphNodeResponse,
    GraphDiffResponse,
    GraphHealthResponse,
    ImpactAssessmentResponse,
    LineageRecordIngest,
    MinimalChainResponse,
    ProvenanceGapResponse,
    RevalidationCandidateResponse,
    SnapshotResponse,
    SourceConcentrationResponse,
    TraversalResponse,
)
from app.evidence_graph.service import get_evidence_graph_service

router = APIRouter(prefix="/api/evidence-graph", tags=["Evidence Graph"])


# -----------------------------------------------------------------------------
# Nodes & CRUD
# -----------------------------------------------------------------------------

@router.get("/nodes", response_model=List[EvidenceGraphNodeResponse])
async def list_nodes(
    node_type: Optional[str] = Query(None, description="Filter by node type"),
    source_system: Optional[str] = Query(None, description="Filter by source system"),
    freshness_state: Optional[str] = Query(None, description="Filter by freshness state"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    svc = get_evidence_graph_service()
    nodes = svc.list_nodes(
        node_type=node_type,
        source_system=source_system,
        freshness_state=freshness_state,
        limit=limit,
        offset=offset,
    )
    return [n.to_dict() for n in nodes]


@router.post("/nodes", response_model=EvidenceGraphNodeResponse, status_code=status.HTTP_201_CREATED)
async def create_node(req: EvidenceGraphNodeCreate):
    svc = get_evidence_graph_service()
    node = EvidenceGraphNode(
        node_id=req.node_id,
        node_type=EvidenceGraphNodeType(req.node_type) if req.node_type in EvidenceGraphNodeType.__members__ else EvidenceGraphNodeType.EVIDENCE,
        source_system=req.source_system,
        version=req.version,
        temporal_scope=req.temporal_scope,
        lifecycle_status=LifecycleStatus(req.lifecycle_status) if req.lifecycle_status in LifecycleStatus.__members__ else LifecycleStatus.ACTIVE,
        provenance_status=ProvenanceStatus(req.provenance_status) if req.provenance_status in ProvenanceStatus.__members__ else ProvenanceStatus.UNVERIFIED,
        freshness_state=FreshnessState(req.freshness_state) if req.freshness_state in FreshnessState.__members__ else FreshnessState.FRESH,
        payload=req.payload,
    )
    created = await svc.add_node(node)
    return created.to_dict()


@router.get("/nodes/{node_id}", response_model=EvidenceGraphNodeResponse)
async def get_node(node_id: str):
    svc = get_evidence_graph_service()
    node = svc.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Evidence graph node '{node_id}' not found")
    return node.to_dict()


# -----------------------------------------------------------------------------
# Edges & CRUD
# -----------------------------------------------------------------------------

@router.get("/edges", response_model=List[EvidenceGraphEdgeResponse])
async def list_edges(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    svc = get_evidence_graph_service()
    edges = svc.list_edges(limit=limit, offset=offset)
    return [e.to_dict() for e in edges]


@router.post("/edges", response_model=EvidenceGraphEdgeResponse, status_code=status.HTTP_201_CREATED)
async def create_edge(req: EvidenceGraphEdgeCreate):
    svc = get_evidence_graph_service()
    import uuid
    edge = EvidenceGraphEdge(
        edge_id=req.edge_id or f"edge-{uuid.uuid4().hex[:12]}",
        source_node_id=req.source_node_id,
        target_node_id=req.target_node_id,
        relationship_type=EvidenceGraphEdgeType(req.relationship_type) if req.relationship_type in EvidenceGraphEdgeType.__members__ else EvidenceGraphEdgeType.DEPENDS_ON,
        confidence=req.confidence,
        provenance=req.provenance,
        valid_from=req.valid_from,
        valid_until=req.valid_until,
        source_system=req.source_system,
        actor_component=req.actor_component,
    )
    created = await svc.add_edge(edge)
    return created.to_dict()


# -----------------------------------------------------------------------------
# Traversals & Dependency Queries
# -----------------------------------------------------------------------------

@router.get("/nodes/{node_id}/upstream", response_model=TraversalResponse)
async def get_upstream_dependencies(
    node_id: str,
    max_depth: int = Query(8, ge=1, le=16),
    max_nodes: int = Query(150, ge=1, le=500),
    as_of: Optional[str] = Query(None, description="Historical as-of ISO timestamp"),
):
    svc = get_evidence_graph_service()
    return svc.get_upstream(node_id=node_id, max_depth=max_depth, max_nodes=max_nodes, as_of=as_of)


@router.get("/nodes/{node_id}/downstream", response_model=TraversalResponse)
async def get_downstream_dependents(
    node_id: str,
    max_depth: int = Query(8, ge=1, le=16),
    max_nodes: int = Query(150, ge=1, le=500),
    as_of: Optional[str] = Query(None, description="Historical as-of ISO timestamp"),
):
    svc = get_evidence_graph_service()
    return svc.get_downstream(node_id=node_id, max_depth=max_depth, max_nodes=max_nodes, as_of=as_of)


@router.get("/nodes/{node_id}/lineage", response_model=MinimalChainResponse)
async def get_minimal_provenance_lineage(
    node_id: str,
    max_depth: int = Query(10, ge=1, le=16),
):
    svc = get_evidence_graph_service()
    return svc.get_minimal_chain(node_id=node_id, max_depth=max_depth)


@router.get("/nodes/{node_id}/sources")
async def get_node_sources(node_id: str):
    """Retrieve all root sources underlying node_id."""
    svc = get_evidence_graph_service()
    finding = svc.analyze_source_concentration(node_id)
    return finding.to_dict()


@router.get("/nodes/{node_id}/dependents")
async def get_node_dependents(node_id: str):
    """Retrieve all downstream dependents relying on node_id."""
    svc = get_evidence_graph_service()
    return svc.get_downstream(node_id=node_id)


# -----------------------------------------------------------------------------
# Blast Radius & Invalidation
# -----------------------------------------------------------------------------

@router.get("/nodes/{node_id}/impact", response_model=ImpactAssessmentResponse)
async def assess_impact(
    node_id: str,
    reason: str = Query("Simulated blast-radius query", description="Reason for impact analysis"),
):
    svc = get_evidence_graph_service()
    assessment = await svc.assess_blast_radius(node_id=node_id, cause_reason=reason)
    return assessment.to_dict()


@router.post("/nodes/{node_id}/invalidate", response_model=ImpactAssessmentResponse)
async def invalidate_node(
    node_id: str,
    reason: str = Query(..., description="Reason for invalidating upstream node"),
):
    svc = get_evidence_graph_service()
    assessment = await svc.propagate_invalidation(node_id=node_id, reason=reason)
    return assessment.to_dict()


@router.get("/revalidation", response_model=List[RevalidationCandidateResponse])
async def list_revalidation_candidates(limit: int = Query(50, ge=1, le=200)):
    svc = get_evidence_graph_service()
    candidates = svc.list_revalidation_candidates(limit=limit)
    return [c.to_dict() for c in candidates]


# -----------------------------------------------------------------------------
# Intelligence & Fragility
# -----------------------------------------------------------------------------

@router.get("/nodes/{node_id}/fragility", response_model=EvidenceFragilityResponse)
async def assess_fragility(node_id: str):
    svc = get_evidence_graph_service()
    fragility = svc.assess_fragility(node_id)
    return fragility.to_dict()


@router.get("/concentrations", response_model=List[SourceConcentrationResponse])
async def list_concentrations():
    svc = get_evidence_graph_service()
    results = []
    for node in svc.list_nodes(limit=100):
        if node.node_type in {EvidenceGraphNodeType.CLAIM, EvidenceGraphNodeType.DECISION, EvidenceGraphNodeType.BELIEF}:
            finding = svc.analyze_source_concentration(node.node_id)
            if finding.is_high_concentration or finding.origin_count == 1:
                results.append(finding.to_dict())
    return results


@router.get("/cycles")
async def get_cycles():
    svc = get_evidence_graph_service()
    return svc.detect_cycles()


@router.get("/provenance-gaps", response_model=List[ProvenanceGapResponse])
async def list_provenance_gaps(node_id: Optional[str] = Query(None)):
    svc = get_evidence_graph_service()
    gaps = svc.list_provenance_gaps(node_id=node_id)
    return [g.to_dict() for g in gaps]


# -----------------------------------------------------------------------------
# Snapshots & Diffs
# -----------------------------------------------------------------------------

@router.post("/snapshots", response_model=SnapshotResponse, status_code=status.HTTP_201_CREATED)
async def create_snapshot(reason: str = Query("User requested snapshot", description="Reason for snapshot")):
    svc = get_evidence_graph_service()
    snap = await svc.create_snapshot(reason=reason)
    return snap.to_dict()


@router.get("/snapshots/{snapshot_id}", response_model=SnapshotResponse)
async def get_snapshot(snapshot_id: str):
    svc = get_evidence_graph_service()
    snap = svc.get_snapshot(snapshot_id)
    if not snap:
        raise HTTPException(status_code=404, detail=f"Snapshot '{snapshot_id}' not found")
    return snap.to_dict()


@router.get("/snapshots/{snapshot_id}/diff", response_model=GraphDiffResponse)
async def diff_snapshot(
    snapshot_id: str,
    target_id: str = Query(..., description="Target snapshot ID to compare with"),
):
    svc = get_evidence_graph_service()
    diff = svc.diff_snapshots(base_id=snapshot_id, target_id=target_id)
    if not diff:
        raise HTTPException(status_code=404, detail="One or both snapshots could not be found for comparison")
    return diff.to_dict()


# -----------------------------------------------------------------------------
# Lineage Ingestion
# -----------------------------------------------------------------------------

@router.post("/lineage", response_model=EvidenceGraphNodeResponse, status_code=status.HTTP_201_CREATED)
async def ingest_lineage(record: LineageRecordIngest):
    svc = get_evidence_graph_service()
    rec = LineageRecord(
        producer=record.producer,
        object_type=record.object_type,
        object_id=record.object_id,
        object_version=record.object_version,
        input_references=record.input_references,
        output_references=record.output_references,
        operation=record.operation,
        timestamp=record.timestamp or "",
        correlation_id=record.correlation_id or "",
        causation_id=record.causation_id,
        provenance=record.provenance,
        scope=record.scope,
        deterministic_status=record.deterministic_status,
    )
    node = await svc.ingest_lineage_record(rec)
    return node.to_dict()


# -----------------------------------------------------------------------------
# Health & Consistency
# -----------------------------------------------------------------------------

@router.get("/health", response_model=GraphHealthResponse)
async def get_health():
    svc = get_evidence_graph_service()
    health = svc.get_health()
    return health.to_dict()
