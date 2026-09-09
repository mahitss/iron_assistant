"""FastAPI endpoints for Kairo Personal Knowledge Graph & Relationship Memory Engine."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.knowledge_graph.schemas import (
    NodeType,
    PreferenceCategory,
    RelationshipType,
    ScopeType,
)
from app.knowledge_graph.service import KnowledgeGraphService

router = APIRouter(prefix="/knowledge-graph", tags=["knowledge-graph"])

_kg_service: Optional[KnowledgeGraphService] = None


def get_kg_service() -> KnowledgeGraphService:
    global _kg_service
    if _kg_service is None:
        _kg_service = KnowledgeGraphService()
    return _kg_service


class CreateNodeRequest(BaseModel):
    canonical_name: str
    node_type: NodeType = NodeType.KNOWLEDGE
    aliases: List[str] = []
    metadata: Dict[str, Any] = {}
    scope: ScopeType = ScopeType.PRIVATE
    confidence: float = 1.0
    user_id: str = "default_user"
    project_id: Optional[str] = None


class CreateEdgeRequest(BaseModel):
    source_node_id: str
    relationship: RelationshipType
    target_node_id: str
    confidence: float = 1.0
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    scope: ScopeType = ScopeType.PRIVATE
    user_id: str = "default_user"
    project_id: Optional[str] = None


class TraverseRequest(BaseModel):
    start_node_id: str
    max_depth: int = 2
    max_nodes: int = 100
    user_id: Optional[str] = None
    as_of: Optional[datetime] = None


class RecordAssertionRequest(BaseModel):
    subject: str
    predicate: str
    object: str
    source: Dict[str, Any] = {}
    confidence: float = 1.0
    scope: ScopeType = ScopeType.PRIVATE
    user_id: str = "default_user"
    is_inferred: bool = False


class RecordDecisionRequest(BaseModel):
    question: str
    decision: str
    alternatives: List[str] = []
    rationale_reference: Optional[str] = None
    owner: str = "user"
    scope: ScopeType = ScopeType.PROJECT
    confidence: float = 1.0
    user_id: str = "default_user"
    project_id: Optional[str] = None
    is_only_discussion: bool = False


class SetPreferenceRequest(BaseModel):
    category: PreferenceCategory
    value: Dict[str, Any]
    scope: ScopeType = ScopeType.PRIVATE
    confidence: float = 1.0
    user_id: str = "default_user"
    project_id: Optional[str] = None


class ForgetEntityRequest(BaseModel):
    node_id: str
    user_id: str = "default_user"
    reason: str = "user_request"


@router.get("/health")
def knowledge_graph_health() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "service": "kairo_personal_knowledge_graph_relationship_memory",
        "supported_node_types": [t.value for t in NodeType],
        "supported_relationship_types": [r.value for r in RelationshipType],
    }


@router.post("/nodes")
def create_node(
    req: CreateNodeRequest,
    service: KnowledgeGraphService = Depends(get_kg_service),
) -> Dict[str, Any]:
    try:
        node = service.create_entity(
            canonical_name=req.canonical_name,
            node_type=req.node_type,
            aliases=req.aliases,
            metadata=req.metadata,
            scope=req.scope,
            confidence=req.confidence,
            user_id=req.user_id,
            project_id=req.project_id,
        )
        return node.model_dump()
    except Exception as ex:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ex))


@router.get("/nodes")
def list_nodes(
    node_type: Optional[NodeType] = Query(None),
    user_id: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None),
    service: KnowledgeGraphService = Depends(get_kg_service),
) -> List[Dict[str, Any]]:
    nodes = service.nodes.list_nodes(node_type=node_type, user_id=user_id, project_id=project_id)
    return [n.model_dump() for n in nodes]


@router.get("/nodes/{node_id}")
def get_node_details(
    node_id: str,
    service: KnowledgeGraphService = Depends(get_kg_service),
) -> Dict[str, Any]:
    node = service.nodes.get_node(node_id)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Node '{node_id}' not found.")
    summary = service.summarizer.summarize_entity(node_id)
    return {
        "node": node.model_dump(),
        "summary": summary.model_dump() if summary else None,
    }


@router.post("/edges")
def create_edge(
    req: CreateEdgeRequest,
    service: KnowledgeGraphService = Depends(get_kg_service),
) -> Dict[str, Any]:
    try:
        edge = service.link_entities(
            source_node_id=req.source_node_id,
            relationship=req.relationship,
            target_node_id=req.target_node_id,
            confidence=req.confidence,
            valid_from=req.valid_from,
            valid_until=req.valid_until,
            scope=req.scope,
            user_id=req.user_id,
            project_id=req.project_id,
        )
        return edge.model_dump()
    except Exception as ex:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ex))


@router.post("/traverse")
def traverse_graph(
    req: TraverseRequest,
    service: KnowledgeGraphService = Depends(get_kg_service),
) -> Dict[str, Any]:
    res = service.graph.traverse(
        start_node_id=req.start_node_id,
        max_depth=req.max_depth,
        max_nodes=req.max_nodes,
        user_id=req.user_id,
        as_of=req.as_of,
    )
    return res.model_dump()


@router.post("/assertions")
def record_assertion(
    req: RecordAssertionRequest,
    service: KnowledgeGraphService = Depends(get_kg_service),
) -> Dict[str, Any]:
    try:
        a = service.record_assertion(
            subject=req.subject,
            predicate=req.predicate,
            object_val=req.object,
            source=req.source,
            confidence=req.confidence,
            scope=req.scope,
            user_id=req.user_id,
            is_inferred=req.is_inferred,
        )
        return a.model_dump()
    except Exception as ex:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ex))


@router.get("/assertions")
def find_assertions(
    subject: str = Query(...),
    user_id: Optional[str] = Query(None),
    service: KnowledgeGraphService = Depends(get_kg_service),
) -> List[Dict[str, Any]]:
    assertions = service.assertions.find_by_subject(subject, user_id=user_id)
    return [a.model_dump() for a in assertions]


@router.post("/decisions")
def record_decision(
    req: RecordDecisionRequest,
    service: KnowledgeGraphService = Depends(get_kg_service),
) -> Dict[str, Any]:
    try:
        d = service.record_decision(
            question=req.question,
            decision=req.decision,
            alternatives=req.alternatives,
            rationale_reference=req.rationale_reference,
            owner=req.owner,
            scope=req.scope,
            confidence=req.confidence,
            user_id=req.user_id,
            project_id=req.project_id,
            is_only_discussion=req.is_only_discussion,
        )
        return d.model_dump()
    except Exception as ex:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ex))


@router.get("/decisions")
def list_decisions(
    project_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    service: KnowledgeGraphService = Depends(get_kg_service),
) -> List[Dict[str, Any]]:
    decisions = service.decisions.list_decisions(project_id=project_id, user_id=user_id)
    return [d.model_dump() for d in decisions]


@router.post("/preferences")
def set_preference(
    req: SetPreferenceRequest,
    service: KnowledgeGraphService = Depends(get_kg_service),
) -> Dict[str, Any]:
    p = service.set_preference(
        category=req.category,
        value=req.value,
        scope=req.scope,
        confidence=req.confidence,
        user_id=req.user_id,
        project_id=req.project_id,
    )
    return p.model_dump()


@router.get("/preferences/resolve")
def resolve_preference(
    category: PreferenceCategory = Query(...),
    user_id: str = Query("default_user"),
    project_id: Optional[str] = Query(None),
    service: KnowledgeGraphService = Depends(get_kg_service),
) -> Dict[str, Any]:
    return service.resolve_preference(category=category, user_id=user_id, project_id=project_id)


@router.get("/temporal/as-of")
def query_as_of(
    timestamp: datetime = Query(...),
    node_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    service: KnowledgeGraphService = Depends(get_kg_service),
) -> Dict[str, Any]:
    return service.temporal.query_as_of(as_of_timestamp=timestamp, node_id=node_id, user_id=user_id)


@router.get("/contradictions")
def list_contradictions(
    user_id: Optional[str] = Query(None),
    service: KnowledgeGraphService = Depends(get_kg_service),
) -> List[Dict[str, Any]]:
    return [c.model_dump() for c in service.contradictions.list_contradictions(user_id=user_id)]


@router.post("/forget")
def forget_entity(
    req: ForgetEntityRequest,
    service: KnowledgeGraphService = Depends(get_kg_service),
) -> Dict[str, Any]:
    try:
        return service.forgetting.forget_entity(node_id=req.node_id, user_id=req.user_id, reason=req.reason)
    except Exception as ex:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ex))


@router.get("/metrics")
def get_metrics(
    service: KnowledgeGraphService = Depends(get_kg_service),
) -> Dict[str, Any]:
    return service.evaluator.get_summary_metrics()
