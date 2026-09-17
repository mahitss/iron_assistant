"""FastAPI REST router for KAIRO Strategy Engine (Task 106).

Exposes typed endpoints for strategy discovery, inspection, applicability checks,
decision candidate bundles, execution feedback, governance proposals, and dashboard metrics.
Enforces the fundamental architectural boundary: NO DIRECT STRATEGY EXECUTION API.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.strategy.domain import (
    ApplicabilityStatus,
    ProposalStatus,
    StrategyCategory,
    StrategyStatus,
)
from app.strategy.schemas import (
    StrategyApplicabilityCheckRequest,
    StrategyApplicabilityResponse,
    StrategyCandidateContract,
    StrategyCreateRequest,
    StrategyDashboardResponse,
    StrategyEvidenceCreateRequest,
    StrategyFeedbackRequest,
    StrategyProposalCreateRequest,
    StrategyProposalReviewRequest,
    StrategySearchRequest,
    StrategyUpdateRequest,
    StrategyVersionCreateRequest,
)
from app.strategy.service import StrategyService

router = APIRouter(prefix="/strategies", tags=["strategy-engine"])

# Global service instance singleton
_service_instance: Optional[StrategyService] = None


def get_strategy_service() -> StrategyService:
    global _service_instance
    if _service_instance is None:
        _service_instance = StrategyService()
    return _service_instance


# ------------------------------------------------------------------------------
# Dashboard & Overview
# ------------------------------------------------------------------------------

@router.get("/dashboard", response_model=StrategyDashboardResponse)
async def get_dashboard(service: StrategyService = Depends(get_strategy_service)):
    """Retrieve comprehensive KPI metrics and telemetry for the Strategy Engine."""
    return service.get_dashboard()


@router.get("/coverage")
async def get_coverage_summary(service: StrategyService = Depends(get_strategy_service)):
    """Retrieve domain and category coverage statistics."""
    dashboard = service.get_dashboard()
    return {
        "coverage_by_category": dashboard.coverage_by_category,
        "total_strategies": dashboard.total_strategies,
        "stale_count": dashboard.stale_count,
        "revalidation_queue_count": dashboard.revalidation_queue_count,
    }


# ------------------------------------------------------------------------------
# Strategy CRUD
# ------------------------------------------------------------------------------

@router.get("", response_model=List[Dict[str, Any]])
async def list_strategies(
    category: Optional[StrategyCategory] = None,
    status: Optional[StrategyStatus] = None,
    domain_scope: Optional[str] = None,
    is_stale: Optional[bool] = None,
    limit: int = Query(default=50, le=200),
    service: StrategyService = Depends(get_strategy_service),
):
    """List strategies with optional filtering."""
    strats = service.list_strategies(
        category=category,
        status=status,
        domain_scope=domain_scope,
        is_stale=is_stale,
        limit=limit,
    )
    return [s.model_dump() for s in strats]


@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_strategy(
    request: StrategyCreateRequest,
    service: StrategyService = Depends(get_strategy_service),
):
    """Explicitly create a new strategy candidate."""
    strat = service.create_strategy(request)
    return strat.model_dump()


@router.get("/{strategy_id}", response_model=Dict[str, Any])
async def get_strategy(
    strategy_id: str,
    service: StrategyService = Depends(get_strategy_service),
):
    """Retrieve full details of a specific strategy."""
    strat = service.get_strategy(strategy_id)
    if not strat:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found.")
    return strat.model_dump()


@router.patch("/{strategy_id}", response_model=Dict[str, Any])
async def update_strategy(
    strategy_id: str,
    request: StrategyUpdateRequest,
    service: StrategyService = Depends(get_strategy_service),
):
    """Update basic metadata or lifecycle status of a strategy."""
    strat = service.get_strategy(strategy_id)
    if not strat:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found.")

    if request.name is not None:
        strat.name = request.name
    if request.objective is not None:
        strat.objective = request.objective
    if request.recommended_approach is not None:
        strat.recommended_approach = request.recommended_approach
    if request.lifecycle_status is not None:
        strat.lifecycle_status = request.lifecycle_status
    if request.validity_window_seconds is not None:
        strat.validity_window_seconds = request.validity_window_seconds
    if request.is_safety_critical is not None:
        strat.is_safety_critical = request.is_safety_critical

    return strat.model_dump()


# ------------------------------------------------------------------------------
# Versions & Evidence
# ------------------------------------------------------------------------------

@router.get("/{strategy_id}/versions", response_model=List[Dict[str, Any]])
async def get_strategy_versions(
    strategy_id: str,
    service: StrategyService = Depends(get_strategy_service),
):
    """Retrieve immutable version history for a strategy."""
    strat = service.get_strategy(strategy_id)
    if not strat:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found.")
    return [v.model_dump() for v in strat.versions]


@router.post("/{strategy_id}/versions", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_strategy_version(
    strategy_id: str,
    request: StrategyVersionCreateRequest,
    service: StrategyService = Depends(get_strategy_service),
):
    """Mint a new immutable version of a strategy."""
    try:
        ver = service.create_new_version(
            strategy_id=strategy_id,
            change_reason=request.change_reason,
            change_description=request.change_description,
            parameters=request.parameters,
            rules=request.rules,
        )
        return ver.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{strategy_id}/evidence", response_model=Dict[str, Any])
async def get_strategy_evidence(
    strategy_id: str,
    service: StrategyService = Depends(get_strategy_service),
):
    """Retrieve supporting evidence and counterexamples for a strategy."""
    strat = service.get_strategy(strategy_id)
    if not strat:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found.")
    return {
        "strategy_id": strategy_id,
        "evidences": [e.model_dump() for e in strat.evidences],
        "counterexamples": [c.model_dump() for c in strat.counterexamples],
    }


# ------------------------------------------------------------------------------
# Applicability & Decision Candidates (Advisory Bridge)
# ------------------------------------------------------------------------------

@router.post("/{strategy_id}/applicability", response_model=StrategyApplicabilityResponse)
async def check_strategy_applicability(
    strategy_id: str,
    request: StrategyApplicabilityCheckRequest,
    service: StrategyService = Depends(get_strategy_service),
):
    """Evaluate applicability of a specific strategy against given operational context."""
    strat = service.get_strategy(strategy_id)
    if not strat:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found.")

    app = service.evaluate_strategy_applicability(strategy_id, request.context)
    return StrategyApplicabilityResponse(
        strategy_id=strategy_id,
        strategy_name=strat.name,
        applicability_status=app.applicability_status,
        applicability_score=app.applicability_score,
        blocking_reasons=app.blocking_reasons,
        uncertainty_reasons=app.uncertainty_reasons,
        conditions_met=len(strat.conditions),
        total_conditions=len(strat.conditions),
    )


@router.post("/candidates", response_model=Dict[str, Any])
async def get_decision_candidates(
    request: StrategyApplicabilityCheckRequest,
    service: StrategyService = Depends(get_strategy_service),
):
    """Retrieve ranked candidate strategies formatted for Task 94 Decision Intelligence."""
    bundle = service.get_candidates_for_decision(
        context=request.context,
        category=request.category,
    )
    return bundle.model_dump()


# ------------------------------------------------------------------------------
# Feedback & Revalidation
# ------------------------------------------------------------------------------

@router.post("/{strategy_id}/feedback", response_model=Dict[str, Any])
async def submit_strategy_feedback(
    strategy_id: str,
    request: StrategyFeedbackRequest,
    service: StrategyService = Depends(get_strategy_service),
):
    """Record operational execution feedback from an action transaction."""
    try:
        fb = service.record_feedback(strategy_id, request)
        return fb.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{strategy_id}/revalidate", response_model=Dict[str, Any])
async def revalidate_strategy(
    strategy_id: str,
    service: StrategyService = Depends(get_strategy_service),
):
    """Revalidate a stale or drifted strategy."""
    try:
        strat = service.revalidate_strategy(strategy_id)
        return strat.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ------------------------------------------------------------------------------
# Conflicts, Proposals & Governance
# ------------------------------------------------------------------------------

@router.get("/{strategy_id}/conflicts", response_model=List[Dict[str, Any]])
async def get_strategy_conflicts(
    strategy_id: str,
    service: StrategyService = Depends(get_strategy_service),
):
    """Retrieve active conflicts involving this strategy."""
    conflicts = [
        c.model_dump()
        for c in service._conflicts.values()
        if c.strategy_a_id == strategy_id or c.strategy_b_id == strategy_id
    ]
    return conflicts


@router.post("/proposals", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_strategy_proposal(
    request: StrategyProposalCreateRequest,
    service: StrategyService = Depends(get_strategy_service),
):
    """Submit a strategy candidate for governance review and promotion."""
    prop = service.create_proposal(request)
    return prop.model_dump()


@router.post("/proposals/{proposal_id}/review", response_model=Dict[str, Any])
async def review_strategy_proposal(
    proposal_id: str,
    request: StrategyProposalReviewRequest,
    service: StrategyService = Depends(get_strategy_service),
):
    """Submit a governance review decision for a strategy proposal."""
    try:
        rev = service.review_proposal(proposal_id, request)
        return rev.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
