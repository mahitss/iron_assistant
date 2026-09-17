"""FastAPI REST router for Kairo Autonomous Cognitive Memory & Lifelong Learning Fabric (Task 103).

Provides safe query, context packing, and governance-compliant inspection endpoints.
Enforces:
- MEMORY != TRUTH
- MEMORY != AUTHORIZATION
- MEMORY != REALITY
- World-State primacy for current operational state.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.cognitive_memory.domain import (
    CognitiveMemoryItem,
    Experience,
    ExperienceSource,
    ExperienceTrust,
    FreshnessState,
    MemoryConflict,
    MemoryContextPack,
    MemoryLifecycleState,
    MemoryPattern,
    MemoryScope,
    MemorySnapshot,
    MemoryType,
)
from app.cognitive_memory.service import CognitiveMemoryService, get_cognitive_memory_service
from app.db.session import get_db

router = APIRouter(prefix="/api/v1/memory", tags=["cognitive-memory"])


def get_service(
    session: Optional[AsyncSession] = Depends(get_db),
) -> CognitiveMemoryService:
    return get_cognitive_memory_service(db=session)


# Request schemas
class RecordExperienceRequest(BaseModel):
    summary: str = Field(..., description="Concise statement of operational occurrence")
    source_type: ExperienceSource = Field(ExperienceSource.OBSERVATION, description="Source classification")
    source_id: Optional[str] = None
    scope: MemoryScope = Field(MemoryScope.PROJECT, description="Multi-tenant boundary")
    actor: str = "kairo_system"
    structured_facts: Optional[Dict[str, Any]] = None
    outcome: str = "SUCCESS"
    confidence: float = 0.8
    trust_classification: Optional[ExperienceTrust] = None
    importance: float = 0.5
    related_entities: Optional[List[str]] = None
    related_missions: Optional[List[str]] = None
    related_situations: Optional[List[str]] = None
    related_decisions: Optional[List[str]] = None
    related_actions: Optional[List[str]] = None
    verification_references: Optional[List[str]] = None
    world_state_references: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    auto_consolidate: bool = True


class SearchMemoryRequest(BaseModel):
    query: str
    scope: MemoryScope = MemoryScope.PROJECT
    scope_id: Optional[str] = None
    memory_types: Optional[List[MemoryType]] = None
    include_stale: bool = False
    min_confidence: float = 0.5
    limit: int = 10


class ContextPackRequest(BaseModel):
    query: str
    scope: MemoryScope = MemoryScope.PROJECT
    scope_id: Optional[str] = None
    max_items: int = 8


class UserCorrectionRequest(BaseModel):
    new_content: str
    new_facts: Optional[Dict[str, Any]] = None


class InvalidationRequest(BaseModel):
    reason: str = "MANUAL_INVALIDATION"


class ReplayRequest(BaseModel):
    experience_ids: Optional[List[str]] = None


# Endpoints

@router.get("/status")
async def get_memory_status(
    service: CognitiveMemoryService = Depends(get_service),
) -> Dict[str, Any]:
    """Returns high-level cognitive memory fabric metrics and counts."""
    return service.get_status()


@router.get("", response_model=List[CognitiveMemoryItem])
@router.get("/list", response_model=List[CognitiveMemoryItem])
async def list_memories(
    scope: Optional[str] = Query(None, description="MemoryScope filter"),
    lifecycle_state: Optional[str] = Query(None, description="LifecycleState filter"),
    memory_type: Optional[str] = Query(None, description="MemoryType filter"),
    limit: int = Query(50, ge=1, le=200),
    service: CognitiveMemoryService = Depends(get_service),
) -> List[CognitiveMemoryItem]:
    """Lists cognitive memories with optional scope, lifecycle, or type filtering."""
    return service.list_memories(
        scope=scope,
        lifecycle_state=lifecycle_state,
        memory_type=memory_type,
        limit=limit,
    )


@router.post("/experiences")
async def capture_experience(
    req: RecordExperienceRequest,
    service: CognitiveMemoryService = Depends(get_service),
) -> Dict[str, Any]:
    """Captures a new experience and optionally consolidates a candidate memory."""
    exp, cand = service.record_experience(
        summary=req.summary,
        source_type=req.source_type,
        source_id=req.source_id,
        scope=req.scope,
        actor=req.actor,
        structured_facts=req.structured_facts,
        outcome=req.outcome,
        confidence=req.confidence,
        trust_classification=req.trust_classification,
        importance=req.importance,
        related_entities=req.related_entities,
        related_missions=req.related_missions,
        related_situations=req.related_situations,
        related_decisions=req.related_decisions,
        related_actions=req.related_actions,
        verification_references=req.verification_references,
        world_state_references=req.world_state_references,
        metadata=req.metadata,
        auto_consolidate=req.auto_consolidate,
    )
    return {
        "experience": exp.model_dump(),
        "candidate_memory": cand.model_dump() if cand else None,
    }


@router.post("/search", response_model=List[CognitiveMemoryItem])
async def search_memories(
    req: SearchMemoryRequest,
    service: CognitiveMemoryService = Depends(get_service),
) -> List[CognitiveMemoryItem]:
    """Performs scope-isolated multi-criteria memory retrieval."""
    return service.search(
        query=req.query,
        scope=req.scope,
        scope_id=req.scope_id,
        memory_types=req.memory_types,
        include_stale=req.include_stale,
        min_confidence=req.min_confidence,
        limit=req.limit,
    )


@router.post("/context-pack", response_model=MemoryContextPack)
async def assemble_context_pack(
    req: ContextPackRequest,
    service: CognitiveMemoryService = Depends(get_service),
) -> MemoryContextPack:
    """Assembles a bounded context pack with evidence, freshness, and conflict notices."""
    return service.assemble_context_pack(
        query=req.query,
        scope=req.scope,
        scope_id=req.scope_id,
        max_items=req.max_items,
    )


@router.get("/conflicts", response_model=List[MemoryConflict])
async def list_conflicts(
    service: CognitiveMemoryService = Depends(get_service),
) -> List[MemoryConflict]:
    """Returns all identified memory conflicts and active disagreements."""
    return service.list_conflicts()


@router.get("/patterns", response_model=List[MemoryPattern])
async def list_patterns(
    service: CognitiveMemoryService = Depends(get_service),
) -> List[MemoryPattern]:
    """Returns discovered recurring memory patterns and clustering summaries."""
    return service.list_patterns()


@router.get("/stale", response_model=List[CognitiveMemoryItem])
async def list_stale_memories(
    service: CognitiveMemoryService = Depends(get_service),
) -> List[CognitiveMemoryItem]:
    """Returns all memories marked as STALE requiring empirical revalidation."""
    return [
        m for m in service.list_memories(limit=200)
        if m.freshness == FreshnessState.STALE
    ]


@router.get("/{memory_id}", response_model=CognitiveMemoryItem)
async def get_memory(
    memory_id: str,
    service: CognitiveMemoryService = Depends(get_service),
) -> CognitiveMemoryItem:
    """Retrieves a single memory item by ID."""
    mem = service.get_memory(memory_id)
    if not mem:
        raise HTTPException(status_code=404, detail=f"Memory '{memory_id}' not found")
    return mem


@router.get("/{memory_id}/history")
async def get_memory_history(
    memory_id: str,
    service: CognitiveMemoryService = Depends(get_service),
) -> Dict[str, Any]:
    """Retrieves version lineage and provenance trail for a memory."""
    mem = service.get_memory(memory_id)
    if not mem:
        raise HTTPException(status_code=404, detail=f"Memory '{memory_id}' not found")
    return {
        "memory_id": mem.memory_id,
        "version": mem.version,
        "superseded_by": mem.superseded_by,
        "predecessor_id": mem.predecessor_id,
        "lineage_ids": mem.lineage_ids,
        "observed_at": mem.observed_at,
        "last_verified_at": mem.last_verified_at,
        "lifecycle_state": mem.lifecycle_state.value,
        "provenance_trail": mem.provenance_trail,
    }


@router.get("/{memory_id}/evidence")
async def get_memory_evidence(
    memory_id: str,
    service: CognitiveMemoryService = Depends(get_service),
) -> Dict[str, Any]:
    """Retrieves underlying empirical evidence, verifications, and experience references."""
    mem = service.get_memory(memory_id)
    if not mem:
        raise HTTPException(status_code=404, detail=f"Memory '{memory_id}' not found")
    return {
        "memory_id": mem.memory_id,
        "confidence": mem.confidence,
        "confidence_evidence": mem.confidence_evidence,
        "evidence_experience_ids": mem.evidence_experience_ids,
        "verification_references": mem.verification_references,
        "useful_count": mem.useful_count,
        "error_count": mem.error_count,
    }


@router.post("/{memory_id}/revalidate", response_model=CognitiveMemoryItem)
async def revalidate_memory(
    memory_id: str,
    service: CognitiveMemoryService = Depends(get_service),
) -> CognitiveMemoryItem:
    """Empirically revalidates a memory item, resetting freshness to CURRENT."""
    mem = service.revalidate_memory(memory_id)
    if not mem:
        raise HTTPException(status_code=404, detail=f"Memory '{memory_id}' not found")
    return mem


@router.post("/{memory_id}/invalidate", response_model=CognitiveMemoryItem)
async def invalidate_memory(
    memory_id: str,
    req: Optional[InvalidationRequest] = None,
    service: CognitiveMemoryService = Depends(get_service),
) -> CognitiveMemoryItem:
    """Marks a memory as retired/invalidated while preserving the audit record."""
    reason = req.reason if req else "MANUAL_INVALIDATION"
    mem = service.invalidate_memory(memory_id, reason=reason)
    if not mem:
        raise HTTPException(status_code=404, detail=f"Memory '{memory_id}' not found")
    return mem


@router.post("/{memory_id}/supersede", response_model=CognitiveMemoryItem)
async def supersede_memory(
    memory_id: str,
    req: UserCorrectionRequest,
    service: CognitiveMemoryService = Depends(get_service),
) -> CognitiveMemoryItem:
    """Applies a user correction: marks old memory as SUPERSEDED and creates V+1."""
    new_mem = service.apply_user_correction(
        old_memory_id=memory_id,
        new_content=req.new_content,
        new_facts=req.new_facts,
    )
    if not new_mem:
        raise HTTPException(status_code=404, detail=f"Memory '{memory_id}' not found")
    return new_mem


@router.post("/replay")
async def replay_memories(
    req: ReplayRequest,
    service: CognitiveMemoryService = Depends(get_service),
) -> Dict[str, Any]:
    """Deterministically simulates memory evolution without side-effects."""
    return service.replay_sequence(experience_ids=req.experience_ids)


@router.post("/snapshot", response_model=MemorySnapshot)
async def create_snapshot(
    service: CognitiveMemoryService = Depends(get_service),
) -> MemorySnapshot:
    """Generates an immutable point-in-time snapshot of the cognitive memory fabric."""
    return service.create_snapshot()
