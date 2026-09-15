"""REST API Router for Task 90 Reliability Intelligence & Predictive Prevention."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.reliability_intelligence.models import (
    PredictiveIncident,
    PreventionCandidate,
    PreventionStrategyScorecard,
    ReliabilitySignal,
)
from app.reliability_intelligence.service import get_reliability_intelligence_service

logger = logging.getLogger("kairo.reliability_intelligence.router")

router = APIRouter(prefix="/api/v1/reliability-intelligence", tags=["Reliability Intelligence"])


class EvaluateIncidentRequest(BaseModel):
    component: str
    metric_name: str
    current_value: float
    threshold_value: Optional[float] = None
    severity: str = "P2"


@router.get("/signals", response_model=List[ReliabilitySignal])
async def list_signals() -> List[ReliabilitySignal]:
    """Retrieves all active early warning reliability signals."""
    svc = get_reliability_intelligence_service()
    return svc.list_signals()


@router.get("/incidents", response_model=List[PredictiveIncident])
async def list_incidents() -> List[PredictiveIncident]:
    """Lists active and historical predictive reliability incidents."""
    svc = get_reliability_intelligence_service()
    return svc.list_incidents()


@router.get("/incidents/{incident_id}", response_model=PredictiveIncident)
async def get_incident(incident_id: str) -> PredictiveIncident:
    """Retrieves detailed predictive incident by ID including decision explanation."""
    svc = get_reliability_intelligence_service()
    inc = svc.get_incident(incident_id)
    if not inc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Predictive incident '{incident_id}' not found",
        )
    return inc


@router.get("/candidates/{candidate_id}", response_model=Dict[str, Any])
async def get_candidate(candidate_id: str) -> Dict[str, Any]:
    """Inspects details of an evaluated prevention candidate."""
    svc = get_reliability_intelligence_service()
    for inc in svc.list_incidents():
        for cand in inc.candidates:
            if cand.candidate_id == candidate_id:
                return cand.model_dump()
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Prevention candidate '{candidate_id}' not found",
    )


@router.get("/scorecards", response_model=List[PreventionStrategyScorecard])
async def get_scorecards() -> List[PreventionStrategyScorecard]:
    """Retrieves strategy effectiveness scorecards and degradation statuses."""
    svc = get_reliability_intelligence_service()
    return svc.calibration.get_scorecards()


@router.get("/calibration", response_model=Dict[str, Any])
async def get_calibration() -> Dict[str, Any]:
    """Returns macro prediction-vs-reality calibration metrics, Brier score, and FP/FN rates."""
    svc = get_reliability_intelligence_service()
    return svc.calibration.get_calibration_metrics()


@router.post("/evaluate", response_model=PredictiveIncident)
async def evaluate_telemetry(req: EvaluateIncidentRequest) -> PredictiveIncident:
    """Evaluates telemetry reading, establishes baselines, forecasts, and runs prevention loop."""
    svc = get_reliability_intelligence_service()
    sig = svc.ingest_telemetry_reading(
        component=req.component,
        metric_name=req.metric_name,
        current_value=req.current_value,
        threshold_value=req.threshold_value,
        severity=req.severity,
    )
    if not sig:
        raise HTTPException(
            status_code=status.HTTP_200_OK,
            detail="Telemetry reading is within healthy normal baseline. No incident generated.",
        )
    return await svc.evaluate_and_prevent(sig)
