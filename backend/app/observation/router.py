"""FastAPI router for Task 114:
Autonomous Active Observation, Value-of-Information, Information Acquisition & Uncertainty Reduction Engine.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.observation.domain import (
    InformationGap,
    ObservationCandidate,
    ObservationPlan,
    UncertaintyState,
)
from app.observation.schemas import (
    InformationGapsResponse,
    ObservationCandidatesResponse,
    ObservationExecuteRequest,
    ObservationPlanCreateRequest,
    ObservationPlanDetailResponse,
    ObservationPlanResponse,
    UncertaintyResponse,
)
from app.observation.service import get_observation_service

router = APIRouter(prefix="/observations", tags=["Active Observation & VoI"])


def _to_plan_response(plan: ObservationPlan) -> ObservationPlanResponse:
    return ObservationPlanResponse(
        plan_id=plan.plan_id,
        version=plan.version,
        objective=plan.objective,
        target_entity=plan.target_entity,
        status=plan.status,
        recommended_stance=plan.recommended_stance,
        gaps_count=len(plan.gaps),
        candidates_count=len(plan.candidates),
        outcomes_count=len(plan.outcomes),
        budget_allocated=plan.budget.allocated_units,
        budget_spent=plan.budget.spent_units,
        stop_reason=plan.stop_reason.value if plan.stop_reason else None,
        is_stale=plan.is_stale,
        overall_confidence_before=plan.uncertainty_before.overall_confidence if plan.uncertainty_before else None,
        overall_confidence_after=plan.uncertainty_after.overall_confidence if plan.uncertainty_after else None,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


@router.post("/plans", response_model=ObservationPlanResponse, status_code=status.HTTP_201_CREATED)
def create_plan(req: ObservationPlanCreateRequest) -> ObservationPlanResponse:
    svc = get_observation_service()
    plan = svc.create_observation_plan(req)
    return _to_plan_response(plan)


@router.get("/plans", response_model=List[ObservationPlanResponse])
def list_plans(limit: int = Query(default=50, ge=1, le=100)) -> List[ObservationPlanResponse]:
    svc = get_observation_service()
    plans = svc.list_plans(limit=limit)
    return [_to_plan_response(p) for p in plans]


@router.get("/plans/{plan_id}", response_model=ObservationPlanDetailResponse)
def get_plan(plan_id: str) -> ObservationPlanDetailResponse:
    svc = get_observation_service()
    plan = svc.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Observation plan '{plan_id}' not found.")
    return ObservationPlanDetailResponse(plan=plan)


@router.get("/plans/{plan_id}/gaps", response_model=InformationGapsResponse)
def get_plan_gaps(plan_id: str) -> InformationGapsResponse:
    svc = get_observation_service()
    plan = svc.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Observation plan '{plan_id}' not found.")
    return InformationGapsResponse(
        plan_id=plan.plan_id,
        target_entity=plan.target_entity,
        gaps=plan.gaps,
    )


@router.get("/plans/{plan_id}/candidates", response_model=ObservationCandidatesResponse)
def get_plan_candidates(plan_id: str) -> ObservationCandidatesResponse:
    svc = get_observation_service()
    plan = svc.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Observation plan '{plan_id}' not found.")
    return ObservationCandidatesResponse(
        plan_id=plan.plan_id,
        target_entity=plan.target_entity,
        candidates=plan.candidates,
    )


@router.get("/plans/{plan_id}/value")
def get_plan_value(plan_id: str) -> Dict[str, Any]:
    svc = get_observation_service()
    plan = svc.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Observation plan '{plan_id}' not found.")
    return {
        "plan_id": plan.plan_id,
        "target_entity": plan.target_entity,
        "estimates": [
            {
                "candidate_id": c.candidate_id,
                "name": c.name,
                "method": c.method.value,
                "value_estimate": c.value_estimate.model_dump() if c.value_estimate else None,
            }
            for c in plan.candidates
        ],
    }


@router.get("/plans/{plan_id}/cost")
def get_plan_cost(plan_id: str) -> Dict[str, Any]:
    svc = get_observation_service()
    plan = svc.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Observation plan '{plan_id}' not found.")
    return {
        "plan_id": plan.plan_id,
        "budget": plan.budget.model_dump(),
        "candidate_costs": [
            {"candidate_id": c.candidate_id, "name": c.name, "cost": c.cost.model_dump()}
            for c in plan.candidates
        ],
    }


@router.get("/plans/{plan_id}/risk")
def get_plan_risk(plan_id: str) -> Dict[str, Any]:
    svc = get_observation_service()
    plan = svc.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Observation plan '{plan_id}' not found.")
    return {
        "plan_id": plan.plan_id,
        "candidate_risks": [
            {"candidate_id": c.candidate_id, "name": c.name, "risk": c.risk.model_dump()}
            for c in plan.candidates
        ],
    }


@router.get("/plans/{plan_id}/uncertainty")
def get_plan_uncertainty(plan_id: str) -> Dict[str, Any]:
    svc = get_observation_service()
    plan = svc.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Observation plan '{plan_id}' not found.")
    return {
        "plan_id": plan.plan_id,
        "target_entity": plan.target_entity,
        "before": plan.uncertainty_before.model_dump() if plan.uncertainty_before else None,
        "after": plan.uncertainty_after.model_dump() if plan.uncertainty_after else None,
    }


@router.post("/plans/{plan_id}/execute", response_model=ObservationPlanDetailResponse)
def execute_plan(
    plan_id: str,
    req: Optional[ObservationExecuteRequest] = None,
) -> ObservationPlanDetailResponse:
    svc = get_observation_service()
    try:
        updated_plan = svc.execute_observation(plan_id, req)
        return ObservationPlanDetailResponse(plan=updated_plan)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/plans/{plan_id}/cancel", response_model=ObservationPlanResponse)
def cancel_plan(plan_id: str, reason: str = Query(default="User cancelled")) -> ObservationPlanResponse:
    svc = get_observation_service()
    plan = svc.cancel_plan(plan_id, reason)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Observation plan '{plan_id}' not found.")
    return _to_plan_response(plan)


@router.post("/plans/{plan_id}/refresh", response_model=ObservationPlanResponse)
def refresh_plan(plan_id: str) -> ObservationPlanResponse:
    svc = get_observation_service()
    plan = svc.refresh_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Observation plan '{plan_id}' not found.")
    return _to_plan_response(plan)


@router.get("/gaps", response_model=List[InformationGap])
def list_gaps(plan_id: Optional[str] = None) -> List[InformationGap]:
    svc = get_observation_service()
    return svc.get_gaps(plan_id)


@router.get("/uncertainty", response_model=UncertaintyResponse)
def get_uncertainty(target: str = Query(default="system_core")) -> UncertaintyResponse:
    svc = get_observation_service()
    unc = svc.get_uncertainty(target)
    return UncertaintyResponse(
        target_entity=unc.target_entity,
        overall_confidence=unc.overall_confidence,
        dimensions={k: v.model_dump() for k, v in unc.dimensions.items()},
        missing_data_count=unc.missing_data_count,
        stale_signals_count=unc.stale_signals_count,
        assessed_at=unc.assessed_at,
    )


@router.get("/history")
def get_history(limit: int = Query(default=50, ge=1, le=100)) -> List[ObservationPlanResponse]:
    svc = get_observation_service()
    plans = svc.list_plans(limit=limit)
    return [_to_plan_response(p) for p in plans]
