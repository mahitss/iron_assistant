"""FastAPI REST API router for Kairo Executive Decision Engine (Task 57)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.decision.safety import DecisionExecutionBoundaryError
from app.decision.schemas import (
    CandidateOption,
    DecisionOutcome,
    DecisionRecord,
    DecisionRequest,
    EvidenceItem,
)
from app.decision.service import decision_service

router = APIRouter(prefix="/api/v1/decision", tags=["decision"])


# Request payload schemas
class AnalyzeDecisionRequest(BaseModel):
    request: DecisionRequest
    candidate_options: list[CandidateOption] | None = None
    additional_evidence: list[EvidenceItem] | None = None
    simulations: list[dict[str, Any]] | None = None
    causal_context: dict[str, Any] | None = None
    memory_context: dict[str, Any] | None = None
    is_production: bool = False
    is_authorized: bool = True


class SelectOptionRequest(BaseModel):
    chosen_option_id: str
    actor: str = "user"


class ApproveDecisionRequest(BaseModel):
    approver: str
    approval_id: str


class RecordOutcomeRequest(BaseModel):
    actual_benefit: float
    actual_cost: float
    actual_duration: float
    success: bool = True
    unexpected_side_effects: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


@router.post("/analyze", response_model=DecisionRecord)
async def analyze_decision(payload: AnalyzeDecisionRequest) -> DecisionRecord:
    """Deliberates on a decision request and produces a ranked, traceable recommendation."""
    try:
        record = decision_service.analyze_and_recommend(
            request=payload.request,
            candidate_options=payload.candidate_options,
            additional_evidence=payload.additional_evidence,
            simulations=payload.simulations,
            causal_context=payload.causal_context,
            memory_context=payload.memory_context,
            is_production=payload.is_production,
            is_authorized=payload.is_authorized,
        )
        return record
    except DecisionExecutionBoundaryError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[DecisionRecord])
async def list_decisions(limit: int = Query(50, ge=1, le=200)) -> list[DecisionRecord]:
    """Lists recently evaluated decision records."""
    return decision_service.list_decisions(limit=limit)


@router.get("/analytics/calibration", response_model=dict[str, Any])
async def get_calibration_analytics() -> dict[str, Any]:
    """Retrieves decision calibration, override rate, and quality metrics."""
    return decision_service.get_analytics()


@router.get("/{decision_id}", response_model=DecisionRecord)
async def get_decision(decision_id: str) -> DecisionRecord:
    """Retrieves a specific decision record by its stable identifier."""
    record = decision_service.get_decision(decision_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Decision '{decision_id}' not found.")
    return record


@router.post("/{decision_id}/select", response_model=DecisionRecord)
async def select_option(decision_id: str, payload: SelectOptionRequest) -> DecisionRecord:
    """Records an authorized actor's selection, strictly distinguishing recommendation from decision."""
    try:
        return decision_service.select_option(
            decision_id=decision_id,
            chosen_option_id=payload.chosen_option_id,
            actor=payload.actor,
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{decision_id}/approve", response_model=DecisionRecord)
async def approve_decision(decision_id: str, payload: ApproveDecisionRequest) -> DecisionRecord:
    """Records explicit human or policy approval for guarded execution handoff."""
    try:
        return decision_service.approve_decision(
            decision_id=decision_id,
            approver=payload.approver,
            approval_id=payload.approval_id,
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{decision_id}/revalidate", response_model=DecisionRecord)
async def revalidate_decision(decision_id: str) -> DecisionRecord:
    """Revalidates a decision against current environment state, constraints, or policies."""
    try:
        return decision_service.revalidate_decision(decision_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{decision_id}/outcome", response_model=DecisionOutcome)
async def record_outcome(decision_id: str, payload: RecordOutcomeRequest) -> DecisionOutcome:
    """Records post-execution outcome and compares reality against original predictions."""
    try:
        return decision_service.record_outcome(
            decision_id=decision_id,
            actual_benefit=payload.actual_benefit,
            actual_cost=payload.actual_cost,
            actual_duration=payload.actual_duration,
            success=payload.success,
            unexpected_side_effects=payload.unexpected_side_effects,
            metadata=payload.metadata,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{decision_id}/outcome", response_model=DecisionOutcome)
async def get_outcome(decision_id: str) -> DecisionOutcome:
    """Retrieves verified execution outcome for a decision."""
    outcome = decision_service.get_outcome(decision_id)
    if not outcome:
        raise HTTPException(status_code=404, detail=f"No outcome recorded for decision '{decision_id}'.")
    return outcome


@router.get("/{decision_id}/explanation", response_model=dict[str, Any])
async def explain_decision(decision_id: str, query: str = Query("why this option")) -> dict[str, Any]:
    """Provides structured, faithful explanation for why an option was recommended or rejected."""
    result = decision_service.explain_decision(decision_id=decision_id, query=query)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/{decision_id}/as-of", response_model=dict[str, Any])
async def reconstruct_as_of(decision_id: str) -> dict[str, Any]:
    """Reconstructs historical decision context from its cryptographic snapshot."""
    result = decision_service.reconstruct_as_of(decision_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
