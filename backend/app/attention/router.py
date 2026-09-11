"""FastAPI REST router for Kairo Autonomous Attention & Cognitive Resource Engine (Task 70)."""

from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.attention.schemas import (
    AttentionCandidate,
    AttentionCandidateCreate,
    AttentionHealthMetrics,
    AttentionSnapshot,
)
from app.attention.service import AttentionEngineService

router = APIRouter(prefix="/attention", tags=["Autonomous Attention Engine"])


def get_service() -> AttentionEngineService:
    return AttentionEngineService.get_instance()


def get_tenant_id(x_tenant_id: Annotated[str | None, Header()] = None) -> str:
    if not x_tenant_id or not x_tenant_id.strip():
        return "default"
    return x_tenant_id.strip()


class ActionReasonRequest(BaseModel):
    reason: str = ""


class DelegateRequest(BaseModel):
    target_agent_id: str
    reason: str = ""
    scope: str = "full_investigation"


class ScoreAdjustRequest(BaseModel):
    delta: float = Field(default=0.15, ge=0.01, le=1.0)
    reason: str = ""


@router.post("/evaluate", response_model=AttentionCandidate, status_code=status.HTTP_201_CREATED)
async def evaluate_candidate(
    payload: AttentionCandidateCreate,
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> AttentionCandidate:
    """Evaluate signals/tasks into an explainable, scored attention candidate."""
    payload.tenant_id = tenant_id or payload.tenant_id
    service = get_service()
    return service.evaluate_candidate(payload)


@router.get("/current", response_model=AttentionCandidate | None)
async def get_current_focus(
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> AttentionCandidate | None:
    """Retrieve the candidate currently in active ATTENDING focus."""
    service = get_service()
    return service.get_current_focus(tenant_id)


@router.get("/queue", response_model=list[AttentionCandidate])
async def get_attention_queue(
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> list[AttentionCandidate]:
    """Retrieve active prioritized queue of attention items."""
    service = get_service()
    return service.get_queue(tenant_id)


@router.get("/snapshot", response_model=AttentionSnapshot)
async def get_snapshot(
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> AttentionSnapshot:
    """Capture point-in-time snapshot of active attention focus, stack, and queue."""
    service = get_service()
    return service.create_snapshot(tenant_id)


@router.get("/health", response_model=AttentionHealthMetrics)
async def get_attention_health(
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> AttentionHealthMetrics:
    """Retrieve telemetry metrics on attention performance, preemption, and resource usage."""
    service = get_service()
    return service.get_health(tenant_id)


@router.get("/metrics")
async def get_raw_metrics(
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> dict[str, Any]:
    """Retrieve granular attention and cognitive resource metrics."""
    service = get_service()
    health = service.get_health(tenant_id)
    return {
        "health": health.model_dump(),
        "resource_budget": service.resource_mgr.budget.model_dump(),
        "total_evaluations": service.total_evaluations,
        "total_interruptions": service.total_interruptions,
        "mode": service.mode.value,
    }


@router.get("/{attention_id}", response_model=AttentionCandidate)
async def get_candidate(
    attention_id: str,
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> AttentionCandidate:
    """Retrieve a specific attention candidate by ID."""
    service = get_service()
    cand = service.get_candidate(attention_id, tenant_id)
    if not cand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Attention candidate '{attention_id}' not found.",
        )
    return cand


@router.post("/{attention_id}/focus")
async def focus_candidate(
    attention_id: str,
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> dict[str, Any]:
    """Allocate active focus to candidate, preempting current work if justified."""
    service = get_service()
    try:
        cand, preemption = service.focus_candidate(attention_id, tenant_id)
        return {
            "status": "focused",
            "candidate": cand,
            "preemption": preemption,
        }
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))


@router.post("/{attention_id}/pause", response_model=AttentionCandidate)
async def pause_candidate(
    attention_id: str,
    req: ActionReasonRequest | None = None,
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> AttentionCandidate:
    """Pause an attending candidate and release active cognitive resources."""
    service = get_service()
    reason = req.reason if req else ""
    try:
        return service.pause_candidate(attention_id, tenant_id, reason=reason)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))


@router.post("/{attention_id}/resume", response_model=AttentionCandidate)
async def resume_candidate(
    attention_id: str,
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> AttentionCandidate:
    """Resume attention on a paused candidate."""
    service = get_service()
    try:
        return service.resume_candidate(attention_id, tenant_id)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))


@router.post("/{attention_id}/defer", response_model=AttentionCandidate)
async def defer_candidate(
    attention_id: str,
    req: ActionReasonRequest | None = None,
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> AttentionCandidate:
    """Defer candidate for later scheduling."""
    service = get_service()
    reason = req.reason if req else ""
    try:
        return service.defer_candidate(attention_id, tenant_id, reason=reason)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))


@router.post("/{attention_id}/delegate", response_model=AttentionCandidate)
async def delegate_candidate(
    attention_id: str,
    req: DelegateRequest,
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> AttentionCandidate:
    """Delegate candidate to a specialized autonomous agent."""
    service = get_service()
    try:
        return service.delegate_candidate(
            attention_id,
            target_agent_id=req.target_agent_id,
            tenant_id=tenant_id,
            reason=req.reason,
        )
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))


@router.post("/{attention_id}/dismiss", response_model=AttentionCandidate)
async def dismiss_candidate(
    attention_id: str,
    req: ActionReasonRequest | None = None,
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> AttentionCandidate:
    """Dismiss candidate from active scheduling."""
    service = get_service()
    reason = req.reason if req else ""
    try:
        return service.dismiss_candidate(attention_id, tenant_id, reason=reason)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))


@router.post("/{attention_id}/escalate", response_model=AttentionCandidate)
async def escalate_candidate(
    attention_id: str,
    req: ScoreAdjustRequest | None = None,
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> AttentionCandidate:
    """Escalate attention score based on new evidence or risk increase."""
    service = get_service()
    boost = req.delta if req else 0.15
    reason = req.reason if req else ""
    try:
        return service.escalate_candidate(attention_id, boost=boost, tenant_id=tenant_id, reason=reason)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))


@router.post("/{attention_id}/deescalate", response_model=AttentionCandidate)
async def deescalate_candidate(
    attention_id: str,
    req: ScoreAdjustRequest | None = None,
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> AttentionCandidate:
    """De-escalate attention score when risk has been mitigated or verified."""
    service = get_service()
    reduction = req.delta if req else 0.15
    reason = req.reason if req else ""
    try:
        return service.deescalate_candidate(
            attention_id, reduction=reduction, tenant_id=tenant_id, reason=reason
        )
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))


@router.get("/{attention_id}/explanation")
async def get_candidate_explanation(
    attention_id: str,
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> dict[str, Any]:
    """Retrieve explainable scoring and focus justification ('Why is/isn't Kairo focusing on this?')."""
    service = get_service()
    try:
        return service.get_explanation(attention_id, tenant_id)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))


@router.get("/{attention_id}/history")
async def get_candidate_history(
    attention_id: str,
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> list[dict[str, Any]]:
    """Retrieve full audit history for candidate."""
    service = get_service()
    return service.get_history(attention_id, tenant_id)
