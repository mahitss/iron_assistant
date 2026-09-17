"""FastAPI REST router for Kairo Autonomous Self-Model (Task 101).

Exposes typed introspective state without allowing unauthorized mutation.
All endpoints are safe, read-only or bounded reconciliation triggers.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.self_model.schemas import (
    CapabilityAwarenessItem,
    GroundingVerificationResult,
    LimitationItem,
    SelfModelAnswers,
    SelfModelDelta,
    SelfModelSnapshot,
    UncertaintyItem,
)
from app.self_model.service import SelfModelService, get_self_model_service

router = APIRouter(prefix="/api/v1/self-model", tags=["self-model"])


def get_service(
    session: Optional[AsyncSession] = Depends(get_db),
) -> SelfModelService:
    return get_self_model_service(db_session=session)


@router.get("/snapshot", response_model=SelfModelSnapshot)
async def get_current_snapshot(
    service: SelfModelService = Depends(get_service),
) -> SelfModelSnapshot:
    """Returns the current grounded operational state snapshot."""
    return service.get_current_snapshot()


@router.post("/reconcile", response_model=SelfModelSnapshot)
async def reconcile_self_state(
    service: SelfModelService = Depends(get_service),
) -> SelfModelSnapshot:
    """Triggers an empirical reconciliation pass and produces a new immutable snapshot."""
    return service.reconcile()


@router.get("/answers", response_model=SelfModelAnswers)
async def get_introspective_answers(
    service: SelfModelService = Depends(get_service),
) -> SelfModelAnswers:
    """Answers all 15 canonical introspective questions."""
    return service.get_answers()


@router.get("/capabilities", response_model=Dict[str, CapabilityAwarenessItem])
async def get_capabilities(
    service: SelfModelService = Depends(get_service),
) -> Dict[str, CapabilityAwarenessItem]:
    """Returns capability matrix with granular readiness dimensions."""
    return service.get_capabilities()


@router.get("/capabilities/{capability_id}", response_model=CapabilityAwarenessItem)
async def get_capability_detail(
    capability_id: str,
    service: SelfModelService = Depends(get_service),
) -> CapabilityAwarenessItem:
    """Returns readiness details and evidence for a specific capability."""
    cap = service.get_capability_readiness(capability_id)
    if not cap:
        raise HTTPException(status_code=404, detail=f"Capability '{capability_id}' not found")
    return cap


@router.get("/limitations", response_model=List[LimitationItem])
async def get_limitations(
    service: SelfModelService = Depends(get_service),
) -> List[LimitationItem]:
    """Returns factual, evidence-backed self-limitations."""
    return service.get_limitations()


@router.get("/uncertainties", response_model=List[UncertaintyItem])
async def get_uncertainties(
    service: SelfModelService = Depends(get_service),
) -> List[UncertaintyItem]:
    """Returns explicit epistemic uncertainties."""
    return service.get_uncertainties()


@router.get("/deltas", response_model=List[SelfModelDelta])
async def get_deltas(
    service: SelfModelService = Depends(get_service),
) -> List[SelfModelDelta]:
    """Returns state transition deltas between snapshots."""
    return service.get_recent_deltas()


@router.get("/history", response_model=List[SelfModelSnapshot])
async def get_snapshot_history(
    service: SelfModelService = Depends(get_service),
) -> List[SelfModelSnapshot]:
    """Returns the immutable timeline of captured snapshots."""
    return service.get_snapshot_history()


@router.get("/verify-grounding", response_model=GroundingVerificationResult)
async def verify_grounding(
    service: SelfModelService = Depends(get_service),
) -> GroundingVerificationResult:
    """Verifies that all self-model claims are strictly backed by empirical telemetry."""
    return service.verify_grounding()


@router.get("/summary")
async def get_summary(
    service: SelfModelService = Depends(get_service),
) -> Dict[str, Any]:
    """Returns a compact operational summary suitable for context injection."""
    snapshot = service.get_current_snapshot()
    ready_caps = [c.capability_id for c in snapshot.capabilities.values() if c.readiness_state.value == "READY"]
    degraded_caps = [c.capability_id for c in snapshot.capabilities.values() if c.readiness_state.value == "DEGRADED"]

    return {
        "snapshot_id": snapshot.snapshot_id,
        "runtime_version": snapshot.runtime_version,
        "autonomy_mode": snapshot.autonomy_mode.value,
        "emergency_stop_active": snapshot.emergency_stop_state,
        "ready_capabilities": ready_caps,
        "degraded_capabilities": degraded_caps,
        "limitation_count": len(snapshot.limitations),
        "uncertainty_count": len(snapshot.uncertainties),
        "saturation_pct": snapshot.resources.saturation_pct,
    }
