"""FastAPI REST API endpoints for Task 68: Kairo Autonomous Knowledge & Memory Consolidation Engine.

Implements complete Spec 25 API specification with backward compatibility.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.routes.memory import get_memory_service
from app.db.session import get_db
from app.memory_consolidation.schemas import (
    CognitiveClassification,
    ContextAssemblyRequest,
    MemoryCaptureRequest,
    MemorySearchRequest,
    MemoryType,
    TrustLevel,
)
from app.memory_consolidation.service import (
    MemoryConsolidationService,
    memory_consolidation_service,
)

router = APIRouter(prefix="/memory", tags=["Autonomous Knowledge & Memory Consolidation Engine (Task 68)"])


def get_memory_consolidation_service(db: Session = Depends(get_db)) -> MemoryConsolidationService:
    if db is not None:
        memory_consolidation_service.db = db
    return memory_consolidation_service


def get_legacy_memory_service_optional(request: Request) -> Any:
    if get_memory_service in request.app.dependency_overrides:
        override = request.app.dependency_overrides[get_memory_service]
        return override()
    return None


# ==============================================================================
# 1. Operational Endpoints (Declared first to avoid /{memory_id} path shadowing)
# ==============================================================================


@router.post("/capture", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
def capture_memory(
    request: MemoryCaptureRequest,
    tenant_id: str = Query(default="default"),
    service: MemoryConsolidationService = Depends(get_memory_consolidation_service),
) -> dict[str, Any]:
    """Capture raw experience, observation, claim, or outcome (Spec 6, 25)."""
    try:
        effective_tenant = tenant_id if tenant_id != "default" else request.tenant_id
        mem = service.capture(request, tenant_id=effective_tenant)
        return mem.model_dump()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/search", response_model=list[dict[str, Any]])
def search_memories(
    q: str = Query(..., min_length=1, description="Semantic or keyword query"),
    top_k: int = Query(default=10, ge=1, le=100),
    memory_type: MemoryType | None = Query(default=None),
    cognitive_type: CognitiveClassification | None = Query(default=None),
    trust_level: TrustLevel | None = Query(default=None),
    min_confidence: float = Query(default=0.0, ge=0.0, le=1.0),
    min_importance: float = Query(default=0.0, ge=0.0, le=1.0),
    include_stale: bool = Query(default=False),
    tenant_id: str = Query(default="default"),
    goal_id: str | None = Query(default=None),
    project_id: str | None = Query(default=None),
    service: MemoryConsolidationService = Depends(get_memory_consolidation_service),
) -> list[dict[str, Any]]:
    """Explainable multi-factor memory search with scoring justifications (Spec 20, 21, 25)."""
    search_req = MemorySearchRequest(
        query=q,
        top_k=top_k,
        memory_type=memory_type,
        cognitive_type=cognitive_type,
        trust_level=trust_level,
        min_confidence=min_confidence,
        min_importance=min_importance,
        include_stale=include_stale,
        tenant_id=tenant_id,
        goal_id=goal_id,
        project_id=project_id,
    )
    results = service.search(search_req, tenant_id=tenant_id)
    return [r.model_dump() for r in results]


@router.get("/conflicts", response_model=list[dict[str, Any]])
def get_memory_conflicts(
    tenant_id: str = Query(default="default"),
    service: MemoryConsolidationService = Depends(get_memory_consolidation_service),
) -> list[dict[str, Any]]:
    """Retrieve active contradictions and competing claims (Spec 12, 25)."""
    conflicts = service.get_conflicts(tenant_id=tenant_id)
    return [c.model_dump() for c in conflicts]


@router.get("/stale", response_model=list[dict[str, Any]])
def get_stale_memories(
    tenant_id: str = Query(default="default"),
    service: MemoryConsolidationService = Depends(get_memory_consolidation_service),
) -> list[dict[str, Any]]:
    """Retrieve memories whose TTL has expired under type-specific policies (Spec 14, 25)."""
    stale = service.get_stale(tenant_id=tenant_id)
    return [m.model_dump() for m in stale]


@router.get("/expiring", response_model=list[dict[str, Any]])
def get_expiring_memories(
    within_hours: int = Query(default=24, ge=1, le=720),
    tenant_id: str = Query(default="default"),
    service: MemoryConsolidationService = Depends(get_memory_consolidation_service),
) -> list[dict[str, Any]]:
    """Retrieve memories expiring within specified hours (Spec 25)."""
    expiring = service.get_expiring(tenant_id=tenant_id, within_hours=within_hours)
    return [m.model_dump() for m in expiring]


@router.get("/health", response_model=dict[str, Any])
def get_memory_health(
    tenant_id: str = Query(default="default"),
    service: MemoryConsolidationService = Depends(get_memory_consolidation_service),
) -> dict[str, Any]:
    """Retrieve memory health metrics and operational telemetry (Spec 27, 25)."""
    metrics = service.get_health(tenant_id=tenant_id)
    return metrics.model_dump()


@router.post("/context", response_model=dict[str, Any])
def assemble_task_context(
    request: ContextAssemblyRequest,
    tenant_id: str = Query(default="default"),
    service: MemoryConsolidationService = Depends(get_memory_consolidation_service),
) -> dict[str, Any]:
    """Assemble token-bounded task context partitioned into cognitive blocks (Spec 22, 25)."""
    try:
        effective_tenant = tenant_id if tenant_id != "default" else request.tenant_id
        res = service.assemble_context(request, tenant_id=effective_tenant)
        return res.model_dump()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/sweep", response_model=dict[str, Any])
def trigger_consolidation_sweep(
    tenant_id: str = Query(default="default"),
    service: MemoryConsolidationService = Depends(get_memory_consolidation_service),
) -> dict[str, Any]:
    """Trigger background autonomous consolidation worker sweep (Spec 26)."""
    try:
        return service.run_sweep(tenant_id=tenant_id)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


# ==============================================================================
# 2. Individual Memory Inspection & Lifecycle Operations (Spec 25)
# ==============================================================================


@router.get("/{memory_id}/provenance", response_model=dict[str, Any])
def get_memory_provenance(
    memory_id: str,
    tenant_id: str = Query(default="default"),
    service: MemoryConsolidationService = Depends(get_memory_consolidation_service),
) -> dict[str, Any]:
    """Retrieve explainable lineage graph for memory (Spec 7, 25)."""
    try:
        return service.get_provenance(memory_id, tenant_id=tenant_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Memory '{memory_id}' not found.")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/{memory_id}/history", response_model=list[dict[str, Any]])
def get_memory_history(
    memory_id: str,
    tenant_id: str = Query(default="default"),
    service: MemoryConsolidationService = Depends(get_memory_consolidation_service),
) -> list[dict[str, Any]]:
    """Retrieve chronological audit trail of memory lifecycle operations (Spec 33, 25)."""
    try:
        return service.get_history(memory_id, tenant_id=tenant_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Memory '{memory_id}' not found.")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.post("/{memory_id}/validate", response_model=dict[str, Any])
def validate_memory_endpoint(
    memory_id: str,
    verified: bool = Query(default=True),
    evidence_ref: str = Query(..., description="Evidence reference verifying claim"),
    tenant_id: str = Query(default="default"),
    service: MemoryConsolidationService = Depends(get_memory_consolidation_service),
) -> dict[str, Any]:
    """Empirically validate candidate memory (Spec 24, 25)."""
    try:
        mem = service.validate_memory(
            memory_id, verified=verified, evidence_ref=evidence_ref, tenant_id=tenant_id
        )
        return mem.model_dump()
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Memory '{memory_id}' not found.")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{memory_id}/promote", response_model=dict[str, Any])
def promote_memory_endpoint(
    memory_id: str,
    reason: str = Query(..., description="Justification for executive promotion"),
    tenant_id: str = Query(default="default"),
    service: MemoryConsolidationService = Depends(get_memory_consolidation_service),
) -> dict[str, Any]:
    """Promote memory to executive tier (Spec 11, 25)."""
    try:
        mem = service.promote_memory(memory_id, reason=reason, tenant_id=tenant_id)
        return mem.model_dump()
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Memory '{memory_id}' not found.")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{memory_id}/consolidate", response_model=dict[str, Any])
def consolidate_memory_endpoint(
    memory_id: str,
    related_ids: list[str] = Query(default=[], description="Related memory IDs to consolidate with"),
    tenant_id: str = Query(default="default"),
    service: MemoryConsolidationService = Depends(get_memory_consolidation_service),
) -> dict[str, Any]:
    """Manually consolidate specified memories into higher-level abstraction (Spec 9, 25)."""
    try:
        cluster_ids = [memory_id] + [rid for rid in related_ids if rid != memory_id]
        cand, cons = service.consolidate_explicit(cluster_ids, tenant_id=tenant_id)
        return {
            "candidate": cand.model_dump(),
            "consolidated_memory": cons.model_dump(),
        }
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{memory_id}/quarantine", response_model=dict[str, Any])
def quarantine_memory_endpoint(
    memory_id: str,
    reason: str = Query(default="Suspicious content flagged by audit", description="Reason for quarantine"),
    tenant_id: str = Query(default="default"),
    service: MemoryConsolidationService = Depends(get_memory_consolidation_service),
) -> dict[str, Any]:
    """Quarantine suspicious or unverified memory (Spec 17, 25)."""
    try:
        mem = service.quarantine_memory(memory_id, reason=reason, tenant_id=tenant_id)
        return mem.model_dump()
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Memory '{memory_id}' not found.")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{memory_id}/forget", response_model=dict[str, Any])
def forget_memory_endpoint(
    memory_id: str,
    reason: str = Query(default="User-requested forgetting", description="Reason for memory deletion"),
    hard_delete: bool = Query(default=False, description="Whether to execute hard deletion"),
    tenant_id: str = Query(default="default"),
    service: MemoryConsolidationService = Depends(get_memory_consolidation_service),
) -> dict[str, Any]:
    """Safely forget/delete memory with compliance tombstone (Spec 16, 25)."""
    try:
        mem = service.forget_memory(memory_id, reason=reason, tenant_id=tenant_id, hard_delete=hard_delete)
        return mem.model_dump()
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Memory '{memory_id}' not found.")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{memory_id}", response_model=dict[str, Any])
async def get_durable_memory_by_id(
    memory_id: str,
    tenant_id: str = Query(default="default"),
    service: MemoryConsolidationService = Depends(get_memory_consolidation_service),
    legacy_service: Any = Depends(get_legacy_memory_service_optional),
) -> dict[str, Any]:
    """Retrieve durable memory details by primary identifier (Spec 25)."""
    if memory_id in service._memories:
        try:
            mem = service.get_memory(memory_id, tenant_id=tenant_id)
            return mem.model_dump()
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    if legacy_service is not None:
        try:
            legacy_mem = await legacy_service.get_memory(memory_id)
            if legacy_mem is not None:
                return legacy_mem.model_dump() if hasattr(legacy_mem, "model_dump") else dict(legacy_mem)
        except Exception:
            pass

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Memory '{memory_id}' not found.")
