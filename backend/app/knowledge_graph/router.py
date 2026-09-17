"""FastAPI Router for Kairo Autonomous Knowledge Graph Reasoning & Relationship Intelligence (Task 97)."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.knowledge_graph.reasoning_engine import (
    GraphReasoningEngine,
    get_graph_reasoning_engine,
)
from app.knowledge_graph.schemas import (
    CertaintyLevel,
    ConflictRecord,
    ConflictResolutionState,
    GraphDiffResult,
    GraphQueryResultSchema,
    GraphQueryType,
    GraphSnapshot,
    GraphTraversalLimits,
    ImpactAnalysisResult,
    KnowledgeEdgeSchema,
    KnowledgeNodeSchema,
    LineageReconstructionResult,
    NodeType,
    RelationshipType,
    ScopeType,
)

logger = logging.getLogger("kairo.knowledge_graph.router")

# Primary router for Task 97: /api/graph and /api/v1/graph
router = APIRouter(prefix="/graph", tags=["knowledge-graph-reasoning"])


class PathRequest(BaseModel):
    start_node_id: str
    target_node_id: str
    min_confidence: float = 0.5
    max_depth: int = 5
    user_id: str = "default_user"
    as_of: Optional[datetime] = None


class ImpactRequest(BaseModel):
    root_node_id: str
    max_depth: int = 5
    max_nodes: int = 200
    user_id: str = "default_user"
    as_of: Optional[datetime] = None


class DiffRequest(BaseModel):
    snapshot_a_id: str
    snapshot_b_id: str


class SnapshotCreateRequest(BaseModel):
    snapshot_type: str = "CURRENT"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CreateNodeRequest(BaseModel):
    canonical_name: str
    node_type: NodeType = NodeType.KNOWLEDGE
    aliases: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    scope: ScopeType = ScopeType.PRIVATE
    confidence: float = 1.0
    certainty: CertaintyLevel = CertaintyLevel.KNOWN
    user_id: str = "default_user"
    project_id: Optional[str] = None


class CreateEdgeRequest(BaseModel):
    source_node_id: str
    relationship: RelationshipType
    target_node_id: str
    confidence: float = 1.0
    certainty: CertaintyLevel = CertaintyLevel.KNOWN
    provenance: Dict[str, Any] = Field(default_factory=dict)
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    scope: ScopeType = ScopeType.PRIVATE
    user_id: str = "default_user"
    project_id: Optional[str] = None


class ConflictCreateRequest(BaseModel):
    source_node_id: str
    target_node_id: str
    conflict_type: str = "DIRECT_CONTRADICTION"
    evidence_refs: List[str] = Field(default_factory=list)
    user_id: str = "default_user"


# =====================================================================
# 1. NODE ENDPOINTS
# =====================================================================

@router.get("/nodes", response_model=List[KnowledgeNodeSchema])
def list_nodes(
    node_type: Optional[NodeType] = Query(None),
    scope: Optional[ScopeType] = Query(None),
    user_id: str = Query("default_user"),
    limit: int = Query(100, ge=1, le=500),
    engine: GraphReasoningEngine = Depends(get_graph_reasoning_engine),
) -> List[KnowledgeNodeSchema]:
    """List knowledge nodes with optional type and scope filtering."""
    results: List[KnowledgeNodeSchema] = []
    for node in engine.nodes._nodes.values():
        if node.status != "ACTIVE":
            continue
        if node_type and node.node_type != node_type:
            continue
        if scope and node.scope != scope:
            continue
        if node.scope == ScopeType.PRIVATE and node.user_id != user_id:
            continue
        results.append(node)
        if len(results) >= limit:
            break
    return results


@router.post("/nodes", response_model=KnowledgeNodeSchema, status_code=status.HTTP_201_CREATED)
def create_node(
    req: CreateNodeRequest,
    engine: GraphReasoningEngine = Depends(get_graph_reasoning_engine),
) -> KnowledgeNodeSchema:
    """Create a new node or resolve to an existing canonical entity."""
    return engine.resolve_or_create_entity(
        canonical_name=req.canonical_name,
        node_type=req.node_type,
        aliases=req.aliases,
        metadata=req.metadata,
        scope=req.scope,
        confidence=req.confidence,
        user_id=req.user_id,
    )


@router.get("/nodes/{id}", response_model=KnowledgeNodeSchema)
def get_node(
    id: str,
    user_id: str = Query("default_user"),
    engine: GraphReasoningEngine = Depends(get_graph_reasoning_engine),
) -> KnowledgeNodeSchema:
    """Get node details by id."""
    node = engine.nodes.get_node(id)
    if not node or not engine._is_accessible(node, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Node '{id}' not found.")
    return node


@router.get("/nodes/{id}/neighbors", response_model=GraphQueryResultSchema)
def get_node_neighbors(
    id: str,
    user_id: str = Query("default_user"),
    engine: GraphReasoningEngine = Depends(get_graph_reasoning_engine),
) -> GraphQueryResultSchema:
    """Get direct (1-hop) neighbors of a node."""
    return engine.execute_query(
        query_type=GraphQueryType.ONE_HOP,
        start_node_id=id,
        user_id=user_id,
        limits=GraphTraversalLimits(max_depth=1),
    )


@router.get("/nodes/{id}/dependencies", response_model=GraphQueryResultSchema)
def get_node_dependencies(
    id: str,
    max_depth: int = Query(4, ge=1, le=10),
    user_id: str = Query("default_user"),
    as_of: Optional[datetime] = Query(None),
    engine: GraphReasoningEngine = Depends(get_graph_reasoning_engine),
) -> GraphQueryResultSchema:
    """Answers: What depends on X and what does X depend on?"""
    return engine.get_dependencies(node_id=id, max_depth=max_depth, user_id=user_id, as_of=as_of)


@router.get("/nodes/{id}/dependents", response_model=List[KnowledgeNodeSchema])
def get_node_dependents(
    id: str,
    user_id: str = Query("default_user"),
    engine: GraphReasoningEngine = Depends(get_graph_reasoning_engine),
) -> List[KnowledgeNodeSchema]:
    """Gets entities that directly or transitively depend on this node."""
    deps = engine.get_dependencies(node_id=id, user_id=user_id)
    # Incoming edges where target is id
    dependent_ids = {e.source_node_id for e in deps.edges if e.target_node_id == id}
    return [n for n in deps.nodes if n.node_id in dependent_ids]


@router.get("/nodes/{id}/lineage", response_model=LineageReconstructionResult)
def get_node_lineage(
    id: str,
    user_id: str = Query("default_user"),
    engine: GraphReasoningEngine = Depends(get_graph_reasoning_engine),
) -> LineageReconstructionResult:
    """Gets structured operational lineage for a node."""
    node = engine.nodes.get_node(id)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Node '{id}' not found.")

    if node.node_type == NodeType.DECISION:
        return engine.reconstruct_decision_lineage(id, user_id=user_id)
    elif node.node_type == NodeType.ACTION:
        return engine.reconstruct_action_lineage(id, user_id=user_id)
    elif node.node_type == NodeType.MEMORY:
        return engine.reconstruct_memory_lineage(id, user_id=user_id)
    elif node.node_type == NodeType.AGENT:
        return engine.reconstruct_agent_lineage(id, user_id=user_id)
    else:
        # Default dependency lineage
        deps = engine.get_dependencies(id, user_id=user_id)
        steps = [{"step": n.node_type.value, "node_id": n.node_id, "name": n.canonical_name} for n in deps.nodes]
        return LineageReconstructionResult(
            lineage_type=node.node_type.value,
            root_id=id,
            steps=steps,
            is_complete=True,
            provenance_chain=[s["name"] for s in steps],
        )


@router.get("/nodes/{id}/history", response_model=Dict[str, Any])
def get_node_history(
    id: str,
    user_id: str = Query("default_user"),
    engine: GraphReasoningEngine = Depends(get_graph_reasoning_engine),
) -> Dict[str, Any]:
    """Gets version and merge history for a node."""
    node = engine.nodes.get_node(id)
    if not node or not engine._is_accessible(node, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Node '{id}' not found.")
    return {
        "node_id": node.node_id,
        "canonical_name": node.canonical_name,
        "version": node.version,
        "created_at": node.created_at.isoformat(),
        "updated_at": node.updated_at.isoformat(),
        "merge_history": node.metadata.get("merge_history", []),
        "aliases": node.aliases,
    }


# =====================================================================
# 2. EDGE ENDPOINTS
# =====================================================================

@router.get("/edges/{id}", response_model=KnowledgeEdgeSchema)
def get_edge(
    id: str,
    user_id: str = Query("default_user"),
    engine: GraphReasoningEngine = Depends(get_graph_reasoning_engine),
) -> KnowledgeEdgeSchema:
    """Get edge details by id."""
    edge = engine.edges._edges.get(id)
    if not edge or not engine._is_edge_accessible(edge, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Edge '{id}' not found.")
    return edge


@router.post("/edges", response_model=KnowledgeEdgeSchema, status_code=status.HTTP_201_CREATED)
def create_edge(
    req: CreateEdgeRequest,
    engine: GraphReasoningEngine = Depends(get_graph_reasoning_engine),
) -> KnowledgeEdgeSchema:
    """Establish a verified relationship edge between two nodes."""
    return engine.edges.create_edge(
        source_node_id=req.source_node_id,
        relationship=req.relationship,
        target_node_id=req.target_node_id,
        confidence=req.confidence,
        provenance=req.provenance,
        valid_from=req.valid_from,
        valid_until=req.valid_until,
        scope=req.scope,
        user_id=req.user_id,
        project_id=req.project_id,
    )


# =====================================================================
# 3. REASONING & QUERY ENDPOINTS (Phases 10, 12, 15, 32, 33)
# =====================================================================

@router.post("/query", response_model=GraphQueryResultSchema)
def query_graph(
    query_type: GraphQueryType = Query(GraphQueryType.DIRECT_RELATION),
    start_node_id: Optional[str] = Query(None),
    target_node_id: Optional[str] = Query(None),
    max_depth: int = Query(5, ge=1, le=10),
    max_nodes: int = Query(200, ge=10, le=500),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    as_of: Optional[datetime] = Query(None),
    user_id: str = Query("default_user"),
    engine: GraphReasoningEngine = Depends(get_graph_reasoning_engine),
) -> GraphQueryResultSchema:
    """Executes a bounded structured graph query."""
    return engine.execute_query(
        query_type=query_type,
        start_node_id=start_node_id,
        target_node_id=target_node_id,
        min_confidence=min_confidence,
        as_of=as_of,
        limits=GraphTraversalLimits(max_depth=max_depth, max_nodes=max_nodes),
        user_id=user_id,
    )


@router.post("/path", response_model=GraphQueryResultSchema)
def find_path(
    req: PathRequest,
    engine: GraphReasoningEngine = Depends(get_graph_reasoning_engine),
) -> GraphQueryResultSchema:
    """Finds the shortest verified relationship path between two nodes."""
    return engine.find_shortest_verified_path(
        start_node_id=req.start_node_id,
        target_node_id=req.target_node_id,
        min_confidence=req.min_confidence,
        limits=GraphTraversalLimits(max_depth=req.max_depth),
        user_id=req.user_id,
        as_of=req.as_of,
    )


@router.post("/impact", response_model=ImpactAnalysisResult)
def analyze_impact(
    req: ImpactRequest,
    engine: GraphReasoningEngine = Depends(get_graph_reasoning_engine),
) -> ImpactAnalysisResult:
    """Analyzes downstream entities and systems affected by a failure or change."""
    return engine.analyze_downstream_impact(
        root_node_id=req.root_node_id,
        limits=GraphTraversalLimits(max_depth=req.max_depth, max_nodes=req.max_nodes),
        user_id=req.user_id,
        as_of=req.as_of,
    )


@router.post("/diff", response_model=GraphDiffResult)
def diff_snapshots(
    req: DiffRequest,
    engine: GraphReasoningEngine = Depends(get_graph_reasoning_engine),
) -> GraphDiffResult:
    """Computes delta between two graph reference snapshots."""
    return engine.compute_graph_diff(req.snapshot_a_id, req.snapshot_b_id)


@router.post("/snapshot", response_model=GraphSnapshot, status_code=status.HTTP_201_CREATED)
def create_snapshot(
    req: SnapshotCreateRequest,
    engine: GraphReasoningEngine = Depends(get_graph_reasoning_engine),
) -> GraphSnapshot:
    """Creates a point-in-time reference snapshot of active graph state."""
    return engine.create_snapshot(snapshot_type=req.snapshot_type, metadata=req.metadata)


@router.get("/snapshots", response_model=List[GraphSnapshot])
def list_snapshots(
    engine: GraphReasoningEngine = Depends(get_graph_reasoning_engine),
) -> List[GraphSnapshot]:
    """List all created graph snapshots."""
    return list(engine._snapshots.values())


@router.post("/validate", response_model=Dict[str, Any])
def validate_consistency(
    engine: GraphReasoningEngine = Depends(get_graph_reasoning_engine),
) -> Dict[str, Any]:
    """Validates referential integrity, identifies orphan edges and impossible cycles."""
    orphans: List[str] = []
    broken_targets: List[str] = []
    for edge in engine.edges._edges.values():
        if not engine.nodes.get_node(edge.source_node_id):
            orphans.append(edge.edge_id)
        if not engine.nodes.get_node(edge.target_node_id):
            broken_targets.append(edge.edge_id)

    conflicts = engine.list_conflicts(unresolved_only=True)
    return {
        "status": "VALID" if not orphans and not broken_targets else "INCONSISTENT",
        "total_nodes": len(engine.nodes._nodes),
        "total_edges": len(engine.edges._edges),
        "orphan_source_edges": len(orphans),
        "broken_target_edges": len(broken_targets),
        "unresolved_conflicts": len(conflicts),
    }


# =====================================================================
# 4. SUBSYSTEM RECONSTRUCTION ENDPOINTS (Phases 17, 18, 20)
# =====================================================================

@router.post("/reconstruct/decision/{id}", response_model=LineageReconstructionResult)
def reconstruct_decision(
    id: str,
    user_id: str = Query("default_user"),
    engine: GraphReasoningEngine = Depends(get_graph_reasoning_engine),
) -> LineageReconstructionResult:
    """Reconstructs full operational decision lineage."""
    return engine.reconstruct_decision_lineage(id, user_id=user_id)


@router.post("/reconstruct/action/{id}", response_model=LineageReconstructionResult)
def reconstruct_action(
    id: str,
    user_id: str = Query("default_user"),
    engine: GraphReasoningEngine = Depends(get_graph_reasoning_engine),
) -> LineageReconstructionResult:
    """Reconstructs Task 95 ActionTransaction operational lineage."""
    return engine.reconstruct_action_lineage(id, user_id=user_id)


@router.post("/reconstruct/memory/{id}", response_model=LineageReconstructionResult)
def reconstruct_memory(
    id: str,
    user_id: str = Query("default_user"),
    engine: GraphReasoningEngine = Depends(get_graph_reasoning_engine),
) -> LineageReconstructionResult:
    """Reconstructs Task 92 memory derivation and evidence lineage."""
    return engine.reconstruct_memory_lineage(id, user_id=user_id)


# =====================================================================
# 5. CONFLICTS & INFERENCE ENDPOINTS (Phases 13, 22)
# =====================================================================

@router.post("/conflicts", response_model=ConflictRecord, status_code=status.HTTP_201_CREATED)
def record_conflict(
    req: ConflictCreateRequest,
    engine: GraphReasoningEngine = Depends(get_graph_reasoning_engine),
) -> ConflictRecord:
    """Explicitly records a contradiction between two assertions."""
    return engine.record_conflict(
        source_node_id=req.source_node_id,
        target_node_id=req.target_node_id,
        conflict_type=req.conflict_type,
        evidence_refs=req.evidence_refs,
        user_id=req.user_id,
    )


@router.get("/conflicts", response_model=List[ConflictRecord])
def list_conflicts(
    unresolved_only: bool = Query(True),
    engine: GraphReasoningEngine = Depends(get_graph_reasoning_engine),
) -> List[ConflictRecord]:
    """Lists explicit contradiction records and dialectic states."""
    return engine.list_conflicts(unresolved_only=unresolved_only)


@router.post("/infer", response_model=Dict[str, Any])
def run_inference(
    user_id: str = Query("default_user"),
    engine: GraphReasoningEngine = Depends(get_graph_reasoning_engine),
) -> Dict[str, Any]:
    """Executes deterministic bounded inference rules (NEVER infers authorization)."""
    derived = engine.run_inference(user_id=user_id)
    return {
        "derived_edge_count": len(derived),
        "derived_edges": [
            {
                "edge_id": e.edge_id,
                "source": e.source_node_id,
                "relationship": e.relationship.value,
                "target": e.target_node_id,
                "rule": e.derivation_rule,
                "confidence": e.confidence,
            }
            for e in derived
        ],
    }
