"""FastAPI endpoints for Task 92: KAIRO Knowledge Consolidation & Memory Evolution.

Prefixes: /api/v1/memory and /api/v1/knowledge.
Integrates with SecurityCenter and EmergencyStop.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.knowledge_consolidation.models import (
    ConflictResolutionRequest,
    MemoryEntity,
    MemoryIngestionRequest,
    MemoryReconstructionRequest,
    MemoryReconstructionResult,
    MemoryStatus,
    MemoryType,
)
from app.knowledge_consolidation.service import (
    KnowledgeConsolidationService,
    get_knowledge_consolidation_service,
)
from app.security.exceptions import EmergencyStopActiveError

router = APIRouter(tags=["Knowledge Consolidation & Memory Evolution (Task 92)"])


# ==============================================================================
# 1. Collection-Level & Operational Endpoints
# ==============================================================================


@router.get("/memory", response_model=list[dict[str, Any]])
def list_memories_endpoint(
    tenant_id: str = Query(default="default"),
    status: MemoryStatus | None = Query(default=None),
    type: MemoryType | None = Query(default=None),
    include_stale: bool = Query(default=False),
    service: KnowledgeConsolidationService = Depends(get_knowledge_consolidation_service),
) -> list[dict[str, Any]]:
    """List memories filtered by status, taxonomy type, and freshness."""
    mems = service.list_memories(
        tenant_id=tenant_id,
        status=status,
        type=type,
        include_stale=include_stale,
    )
    return [m.model_dump() for m in mems]


@router.post("/memory/ingest", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
def ingest_memory_endpoint(
    request: MemoryIngestionRequest,
    service: KnowledgeConsolidationService = Depends(get_knowledge_consolidation_service),
) -> dict[str, Any]:
    """Ingest new knowledge through normalization, deduplication, and conflict detection."""
    try:
        mem = service.ingest_memory(request)
        return mem.model_dump()
    except EmergencyStopActiveError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/memory/consolidate", response_model=dict[str, Any])
def consolidate_memories_endpoint(
    episode_ids: list[str] = Query(..., description="Episodic memory IDs to consolidate"),
    summary: str = Query(..., description="Consolidated semantic abstraction"),
    tenant_id: str = Query(default="default"),
    service: KnowledgeConsolidationService = Depends(get_knowledge_consolidation_service),
) -> dict[str, Any]:
    """Consolidate multiple episodic memories into a unified semantic memory."""
    try:
        return service.consolidate_explicit(episode_ids=episode_ids, summary=summary, tenant_id=tenant_id)
    except EmergencyStopActiveError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/memory/revalidate", response_model=list[dict[str, Any]])
def trigger_revalidation_endpoint(
    capability_changes: list[str] | None = Query(default=None),
    service: KnowledgeConsolidationService = Depends(get_knowledge_consolidation_service),
) -> list[dict[str, Any]]:
    """Scan and trigger bounded autonomous revalidation jobs for stale or evolved knowledge."""
    try:
        return service.run_revalidation_scan(capability_changes=capability_changes)
    except EmergencyStopActiveError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/memory/health", response_model=dict[str, Any])
def get_memory_health_endpoint(
    tenant_id: str = Query(default="default"),
    service: KnowledgeConsolidationService = Depends(get_knowledge_consolidation_service),
) -> dict[str, Any]:
    """Retrieve operational telemetry and epistemological health metrics."""
    return service.get_health(tenant_id=tenant_id)


@router.post("/memory/context", response_model=dict[str, Any])
def assemble_context_endpoint(
    query: str = Query(..., min_length=1),
    tenant_id: str = Query(default="default"),
    token_budget: int = Query(default=2000, ge=100, le=8000),
    service: KnowledgeConsolidationService = Depends(get_knowledge_consolidation_service),
) -> dict[str, Any]:
    """Assemble bounded context explicitly exposing any relevant contradictions."""
    return service.assemble_context(query=query, tenant_id=tenant_id, token_budget=token_budget)


@router.post("/knowledge/reconstruct", response_model=dict[str, Any])
def reconstruct_knowledge_endpoint(
    request: MemoryReconstructionRequest,
    service: KnowledgeConsolidationService = Depends(get_knowledge_consolidation_service),
) -> dict[str, Any]:
    """Forensic memory reconstruction: historical timeline, key events, current state, and conflicts."""
    res = service.reconstruct(request)
    return res.model_dump()


# ==============================================================================
# 2. Individual Memory Inspection & Lifecycle Operations
# ==============================================================================


@router.get("/memory/{memory_id}", response_model=dict[str, Any])
def get_memory_endpoint(
    memory_id: str,
    service: KnowledgeConsolidationService = Depends(get_knowledge_consolidation_service),
) -> dict[str, Any]:
    """Retrieve memory entity details by ID."""
    mem = service.get_memory(memory_id)
    if not mem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Memory '{memory_id}' not found.")
    return mem.model_dump()


@router.get("/memory/{memory_id}/history", response_model=list[dict[str, Any]])
def get_memory_history_endpoint(
    memory_id: str,
    service: KnowledgeConsolidationService = Depends(get_knowledge_consolidation_service),
) -> list[dict[str, Any]]:
    """Retrieve immutable lifecycle audit trail for memory."""
    mem = service.get_memory(memory_id)
    if not mem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Memory '{memory_id}' not found.")
    return service.lifecycle.get_history(memory_id)


@router.get("/memory/{memory_id}/evidence", response_model=list[dict[str, Any]])
def get_memory_evidence_endpoint(
    memory_id: str,
    service: KnowledgeConsolidationService = Depends(get_knowledge_consolidation_service),
) -> list[dict[str, Any]]:
    """Retrieve all grounding evidence supporting or contradicting this memory."""
    mem = service.get_memory(memory_id)
    if not mem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Memory '{memory_id}' not found.")
    evs = service.evidence.get_evidence_for_memory(memory_id)
    return [e.model_dump() for e in evs]


@router.get("/memory/{memory_id}/conflicts", response_model=list[dict[str, Any]])
def get_memory_conflicts_endpoint(
    memory_id: str,
    service: KnowledgeConsolidationService = Depends(get_knowledge_consolidation_service),
) -> list[dict[str, Any]]:
    """Retrieve detected contradictions involving this memory."""
    mem = service.get_memory(memory_id)
    if not mem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Memory '{memory_id}' not found.")
    conflicts = [
        c.model_dump() for c in service.conflicts._conflicts.values()
        if c.memory_a_id == memory_id or c.memory_b_id == memory_id
    ]
    return conflicts


@router.get("/memory/{memory_id}/provenance", response_model=dict[str, Any])
def get_memory_provenance_endpoint(
    memory_id: str,
    service: KnowledgeConsolidationService = Depends(get_knowledge_consolidation_service),
) -> dict[str, Any]:
    """Retrieve auditable lineage provenance for this memory."""
    prov = service.provenance.get_by_memory_id(memory_id)
    if not prov:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Provenance for '{memory_id}' not found.")
    return prov.model_dump()


@router.get("/memory/{memory_id}/related", response_model=list[dict[str, Any]])
def get_memory_related_endpoint(
    memory_id: str,
    service: KnowledgeConsolidationService = Depends(get_knowledge_consolidation_service),
) -> list[dict[str, Any]]:
    """Retrieve related memories connected via derivation or graph edges."""
    mem = service.get_memory(memory_id)
    if not mem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Memory '{memory_id}' not found.")
    derived_deps = service.derived.get_dependencies(memory_id)
    related_mems = [service._memories[pid].model_dump() for pid in derived_deps if pid in service._memories]
    return related_mems


@router.post("/memory/{memory_id}/resolve-conflict", response_model=dict[str, Any])
def resolve_memory_conflict_endpoint(
    memory_id: str,
    request: ConflictResolutionRequest,
    service: KnowledgeConsolidationService = Depends(get_knowledge_consolidation_service),
) -> dict[str, Any]:
    """Resolve a contradiction involving this memory."""
    try:
        # Find conflict involving this memory
        target_conflict = None
        for c in service.conflicts._conflicts.values():
            if (c.memory_a_id == memory_id or c.memory_b_id == memory_id) and c.status == "CONFLICTED":
                target_conflict = c
                break

        if not target_conflict:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No active contradiction found for memory '{memory_id}'.",
            )

        return service.resolve_conflict(target_conflict.conflict_id, request)
    except EmergencyStopActiveError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/memory/{memory_id}/archive", response_model=dict[str, Any])
def archive_memory_endpoint(
    memory_id: str,
    reason: str = Query(default="Archived via API request"),
    service: KnowledgeConsolidationService = Depends(get_knowledge_consolidation_service),
) -> dict[str, Any]:
    """Archive memory entity."""
    try:
        mem = service.archive_memory(memory_id, reason=reason)
        return mem.model_dump()
    except EmergencyStopActiveError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/memory/{memory_id}/forget", response_model=dict[str, Any])
def forget_memory_endpoint(
    memory_id: str,
    reason: str = Query(default="Compliance forgetting request"),
    hard_delete: bool = Query(default=False),
    service: KnowledgeConsolidationService = Depends(get_knowledge_consolidation_service),
) -> dict[str, Any]:
    """Forget memory entity with compliance tombstone."""
    try:
        mem = service.forget_memory(memory_id, reason=reason, hard_delete=hard_delete)
        return mem.model_dump()
    except EmergencyStopActiveError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
