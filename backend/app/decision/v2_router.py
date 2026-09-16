"""FastAPI router for Task 94 Decision Intelligence & Decision Memory.

Prefixes: /api/v1/decisions and /api/decisions.
Respects SecurityCenter boundaries and EmergencyStop kill-switch.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.decision.domain import (
    AssumptionItem,
    DecisionExplanation,
    DecisionInput,
    DecisionOption,
    DecisionOutcomeRecord,
    DecisionV2Record,
)
from app.decision.intelligence_service import (
    DecisionIntelligenceService,
    get_decision_intelligence_service,
)
from app.security.exceptions import EmergencyStopActiveError

router = APIRouter(tags=["Decision Intelligence & Memory Engine (Task 94)"])


def get_service(db: Session = Depends(get_db)) -> DecisionIntelligenceService:
    return get_decision_intelligence_service(db=db)


class SelectRequest(BaseModel):
    chosen_option_id: str
    actor: str = "user"


class ApproveRequest(BaseModel):
    approver: str
    approval_id: str


class RejectRequest(BaseModel):
    actor: str = "operator"
    reason: str = "Rejected during review"


class ReEvaluateRequest(BaseModel):
    reason: str = "Context or assumption changed"


class DeferRequest(BaseModel):
    reason: str = "Deferred by operator"


# ==============================================================================
# 1. Deliberation & Evaluation
# ==============================================================================


@router.post("/decisions/evaluate", response_model=DecisionV2Record, status_code=status.HTTP_201_CREATED)
def evaluate_decision_endpoint(
    payload: DecisionInput,
    service: DecisionIntelligenceService = Depends(get_service),
) -> DecisionV2Record:
    """Evaluate candidate options across multi-criteria dimensions, constraints, and risks."""
    try:
        return service.evaluate_decision(payload)
    except EmergencyStopActiveError as ex:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(ex))


@router.get("/decisions", response_model=list[DecisionV2Record])
def list_decisions_endpoint(
    limit: int = Query(default=50, ge=1, le=100),
    service: DecisionIntelligenceService = Depends(get_service),
) -> list[DecisionV2Record]:
    """List recent decision records."""
    return service.list_decisions(limit=limit)


@router.get("/decisions/{decision_id}", response_model=DecisionV2Record)
def get_decision_endpoint(
    decision_id: str,
    service: DecisionIntelligenceService = Depends(get_service),
) -> DecisionV2Record:
    """Fetch complete decision record by identifier."""
    dec = service.get_decision(decision_id)
    if not dec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Decision '{decision_id}' not found")
    return dec


# ==============================================================================
# 2. Options, Assumptions, Evidence & Explanations
# ==============================================================================


@router.get("/decisions/{decision_id}/options", response_model=list[DecisionOption])
def get_decision_options_endpoint(
    decision_id: str,
    service: DecisionIntelligenceService = Depends(get_service),
) -> list[DecisionOption]:
    """Retrieve evaluated candidate options and Pareto dominance."""
    return service.get_options(decision_id)


@router.get("/decisions/{decision_id}/assumptions", response_model=list[AssumptionItem])
def get_decision_assumptions_endpoint(
    decision_id: str,
    service: DecisionIntelligenceService = Depends(get_service),
) -> list[AssumptionItem]:
    """Retrieve assumptions underpinning the decision."""
    return service.get_assumptions(decision_id)


@router.get("/decisions/{decision_id}/evidence")
def get_decision_evidence_endpoint(
    decision_id: str,
    service: DecisionIntelligenceService = Depends(get_service),
) -> list[dict[str, Any]]:
    """Retrieve grounded evidence supporting the decision."""
    dec = service.get_decision(decision_id)
    if not dec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Decision '{decision_id}' not found")
    return dec.evidence


@router.get("/decisions/{decision_id}/explanation", response_model=DecisionExplanation)
def get_decision_explanation_endpoint(
    decision_id: str,
    service: DecisionIntelligenceService = Depends(get_service),
) -> DecisionExplanation:
    """Generate structured 15-point evidence-based explanation."""
    try:
        return service.generate_explanation(decision_id)
    except KeyError as ex:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ex))


# ==============================================================================
# 3. Lifecycle Transitions
# ==============================================================================


@router.post("/decisions/{decision_id}/select", response_model=DecisionV2Record)
def select_option_endpoint(
    decision_id: str,
    payload: SelectRequest,
    service: DecisionIntelligenceService = Depends(get_service),
) -> DecisionV2Record:
    """Select a specific option from the candidate alternatives."""
    try:
        return service.select_option(decision_id, payload.chosen_option_id, actor=payload.actor)
    except KeyError as ex:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ex))
    except ValueError as ex:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ex))


@router.post("/decisions/{decision_id}/approve", response_model=DecisionV2Record)
def approve_decision_endpoint(
    decision_id: str,
    payload: ApproveRequest,
    service: DecisionIntelligenceService = Depends(get_service),
) -> DecisionV2Record:
    """Record formal human or institutional approval."""
    try:
        return service.approve_decision(decision_id, approver=payload.approver, approval_id=payload.approval_id)
    except KeyError as ex:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ex))
    except ValueError as ex:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ex))


@router.post("/decisions/{decision_id}/reject", response_model=DecisionV2Record)
def reject_decision_endpoint(
    decision_id: str,
    payload: RejectRequest,
    service: DecisionIntelligenceService = Depends(get_service),
) -> DecisionV2Record:
    """Reject a proposed decision."""
    try:
        return service.reject_decision(decision_id, actor=payload.actor, reason=payload.reason)
    except KeyError as ex:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ex))


@router.post("/decisions/{decision_id}/re-evaluate", response_model=DecisionV2Record)
def re_evaluate_decision_endpoint(
    decision_id: str,
    payload: ReEvaluateRequest,
    service: DecisionIntelligenceService = Depends(get_service),
) -> DecisionV2Record:
    """Trigger re-evaluation following environment drift or assumption invalidation."""
    try:
        return service.re_evaluate_decision(decision_id, reason=payload.reason)
    except KeyError as ex:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ex))


@router.post("/decisions/{decision_id}/defer", response_model=DecisionV2Record)
def defer_decision_endpoint(
    decision_id: str,
    payload: DeferRequest,
    service: DecisionIntelligenceService = Depends(get_service),
) -> DecisionV2Record:
    """Defer a decision."""
    try:
        return service.defer_decision(decision_id, reason=payload.reason)
    except KeyError as ex:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ex))


# ==============================================================================
# 4. Outcome & Memory Tracking
# ==============================================================================


@router.post("/decisions/{decision_id}/outcome", response_model=DecisionOutcomeRecord)
def record_outcome_endpoint(
    decision_id: str,
    payload: DecisionOutcomeRecord,
    service: DecisionIntelligenceService = Depends(get_service),
) -> DecisionOutcomeRecord:
    """Record verified post-execution outcome and consolidate into decision memory."""
    payload.decision_id = decision_id
    return service.record_outcome(payload)


@router.get("/decisions/{decision_id}/outcome", response_model=DecisionOutcomeRecord | None)
def get_decision_outcome_endpoint(
    decision_id: str,
    service: DecisionIntelligenceService = Depends(get_service),
) -> DecisionOutcomeRecord | None:
    """Retrieve verified outcome data."""
    return service.get_outcome(decision_id)
