"""FastAPI REST API routes for Autonomous World Model & Long-Horizon Foresight Engine (Task 65, Spec 74, 75)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

from app.foresight.schemas import (
    EarlyWarningSignal,
    ForecastCreateRequest,
    ForecastRecord,
    ForesightEntity,
    ForesightHorizon,
    ForesightRelationship,
    ReassessRequest,
    ScenarioBranch,
    ScenarioCreateRequest,
    ScenarioType,
    StrategicOpportunity,
    StrategicRisk,
    WorldDiff,
    WorldModelOverview,
    WorldModelQueryRequest,
    WorldModelQueryResponse,
    WorldScope,
)
from app.foresight.service import foresight_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/foresight", tags=["Autonomous World Model & Foresight Engine"])
world_model_router = APIRouter(
    prefix="/api/v1/world-model", tags=["Autonomous World Model & Foresight Engine"]
)


@router.get("/health", summary="Foresight Engine Health Probe")
@world_model_router.get("/health", summary="World Model Health Probe")
async def get_foresight_health() -> dict[str, Any]:
    """Health probe for World Model and Long-Horizon Foresight Engine."""
    return {
        "status": "healthy",
        "subsystem": "kairo_autonomous_world_model_and_foresight_engine",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "audit_integrity": foresight_service.verify_audit_integrity(),
    }


# =====================================================================
# World Model Endpoints (Spec 74)
# =====================================================================


@router.post("/query", response_model=WorldModelQueryResponse, summary="Query the world model")
@world_model_router.post("/query", response_model=WorldModelQueryResponse, summary="Query the world model")
async def query_world_model(req: WorldModelQueryRequest) -> WorldModelQueryResponse:
    """Reason across entities, causal relationships, forecasts, and risks."""
    return foresight_service.query_world_model(req)


@router.get("", response_model=WorldModelOverview, summary="Get world model overview")
@router.get("/", response_model=WorldModelOverview, include_in_schema=False)
@world_model_router.get("", response_model=WorldModelOverview, summary="Get world model overview")
@world_model_router.get("/", response_model=WorldModelOverview, include_in_schema=False)
async def get_world_overview() -> WorldModelOverview:
    """Retrieve high-level overview of live world model state and foresight metrics."""
    return foresight_service.get_overview()


@router.get("/entities", response_model=list[ForesightEntity], summary="List entities")
@world_model_router.get("/entities", response_model=list[ForesightEntity], summary="List entities")
async def list_entities(
    entity_type: str | None = Query(None, description="Filter by entity type"),
    scope: WorldScope | None = Query(None, description="Filter by scope"),
    state: str | None = Query(None, description="Filter by state"),
) -> list[ForesightEntity]:
    """Retrieve list of world entities with freshness evaluation."""
    return foresight_service.list_entities(entity_type=entity_type, scope=scope, state=state)


@router.get("/entities/{entity_id}", response_model=ForesightEntity, summary="Get single entity")
@world_model_router.get("/entities/{entity_id}", response_model=ForesightEntity, summary="Get single entity")
async def get_entity(entity_id: str) -> ForesightEntity:
    """Retrieve full details and freshness for a specific entity."""
    ent = foresight_service.get_entity(entity_id)
    if not ent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity_id}' not found in World Model.",
        )
    return ent


@router.get("/relationships", response_model=list[ForesightRelationship], summary="List relationships")
@world_model_router.get(
    "/relationships", response_model=list[ForesightRelationship], summary="List relationships"
)
async def list_relationships(
    source_id: str | None = Query(None),
    target_id: str | None = Query(None),
) -> list[ForesightRelationship]:
    """Retrieve semantic and causal relationships."""
    return foresight_service.list_relationships(source_id=source_id, target_id=target_id)


@router.get("/diff", response_model=WorldDiff, summary="Compute world model difference")
@world_model_router.get("/diff", response_model=WorldDiff, summary="Compute world model difference")
async def get_world_diff(
    historical_timestamp: str | None = Query(
        None, description="ISO timestamp for historical comparison. Defaults to 1 hour ago."
    ),
) -> WorldDiff:
    """Compare current world state with historical snapshot at time T."""
    if historical_timestamp:
        try:
            t = datetime.fromisoformat(historical_timestamp)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid ISO timestamp format for historical_timestamp.",
            )
    else:
        t = datetime.now(timezone.utc)
    return foresight_service.compute_diff(t)


@router.post("/reassess", summary="Trigger world model reassessment")
@world_model_router.post("/reassess", summary="Trigger world model reassessment")
async def reassess_world(req: ReassessRequest) -> dict[str, Any]:
    """Trigger proactive reassessment of assumptions and propagate staleness."""
    return foresight_service.reassess_world_model(
        changed_entity_id=req.changed_entity_id,
        reason=req.reason,
        invalidate_stale_forecasts=req.invalidate_stale_forecasts,
    )


# =====================================================================
# Forecasting Endpoints (Spec 75)
# =====================================================================


@router.post("/forecast", response_model=ForecastRecord, summary="Generate a temporal forecast")
@world_model_router.post("/forecast", response_model=ForecastRecord, summary="Generate a temporal forecast")
async def create_forecast(req: ForecastCreateRequest) -> ForecastRecord:
    """Generate a multi-horizon range forecast (Invariant: FORECAST != FACT)."""
    return foresight_service.create_forecast(req)


@router.get("/forecasts", response_model=list[ForecastRecord], summary="List forecasts")
@world_model_router.get("/forecasts", response_model=list[ForecastRecord], summary="List forecasts")
async def list_forecasts(
    horizon: ForesightHorizon | None = Query(None),
) -> list[ForecastRecord]:
    """Retrieve list of active forecasts."""
    return foresight_service.list_forecasts(horizon=horizon)


@router.get("/forecast/{forecast_id}", response_model=ForecastRecord, summary="Get forecast details")
@world_model_router.get(
    "/forecast/{forecast_id}", response_model=ForecastRecord, summary="Get forecast details"
)
async def get_forecast(forecast_id: str) -> ForecastRecord:
    """Retrieve details of a specific forecast."""
    fct = foresight_service.get_forecast(forecast_id)
    if not fct:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Forecast '{forecast_id}' not found.",
        )
    return fct


@router.get("/forecast/{forecast_id}/evidence", summary="Get forecast evidence")
@world_model_router.get("/forecast/{forecast_id}/evidence", summary="Get forecast evidence")
async def get_forecast_evidence(forecast_id: str) -> dict[str, Any]:
    """Retrieve evidence backing a forecast."""
    fct = foresight_service.get_forecast(forecast_id)
    if not fct:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Forecast not found.")
    return {"forecast_id": forecast_id, "evidence": fct.evidence, "model": fct.model_name}


@router.get("/forecast/{forecast_id}/assumptions", summary="Get forecast assumptions")
@world_model_router.get("/forecast/{forecast_id}/assumptions", summary="Get forecast assumptions")
async def get_forecast_assumptions(forecast_id: str) -> dict[str, Any]:
    """Retrieve explicit assumptions supporting a forecast."""
    fct = foresight_service.get_forecast(forecast_id)
    if not fct:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Forecast not found.")
    return {"forecast_id": forecast_id, "assumptions": fct.assumptions, "status": fct.status.value}


@router.get("/forecast/{forecast_id}/scenarios", summary="Get scenarios associated with forecast")
@world_model_router.get("/forecast/{forecast_id}/scenarios", summary="Get scenarios associated with forecast")
async def get_forecast_scenarios(forecast_id: str) -> dict[str, Any]:
    """Retrieve scenario branches associated with the forecast topic."""
    scns = foresight_service.list_scenarios()
    return {"forecast_id": forecast_id, "scenarios": scns}


@router.get("/forecast/{forecast_id}/outcomes", summary="Get realized outcome & calibration")
@world_model_router.get("/forecast/{forecast_id}/outcomes", summary="Get realized outcome & calibration")
async def get_forecast_outcomes(forecast_id: str) -> dict[str, Any]:
    """Retrieve actual outcome and calibration accuracy score."""
    fct = foresight_service.get_forecast(forecast_id)
    if not fct:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Forecast not found.")
    return {
        "forecast_id": forecast_id,
        "actual_outcome": fct.actual_outcome,
        "calibration_score": fct.calibration_score,
        "status": fct.status.value,
    }


# =====================================================================
# Scenarios, Risks, Opportunities & Early Warnings
# =====================================================================


@router.post("/scenario", response_model=ScenarioBranch, summary="Create an isolated scenario branch")
@world_model_router.post(
    "/scenario", response_model=ScenarioBranch, summary="Create an isolated scenario branch"
)
async def create_scenario(req: ScenarioCreateRequest) -> ScenarioBranch:
    """Generate an isolated scenario sandbox (Invariant: SIMULATION != PRODUCTION)."""
    return foresight_service.create_scenario(req)


@router.get("/scenarios", response_model=list[ScenarioBranch], summary="List scenarios")
@world_model_router.get("/scenarios", response_model=list[ScenarioBranch], summary="List scenarios")
async def list_scenarios(
    scenario_type: ScenarioType | None = Query(None),
) -> list[ScenarioBranch]:
    """List scenario sandbox branches."""
    return foresight_service.list_scenarios(scenario_type=scenario_type)


@router.get("/risks", response_model=list[StrategicRisk], summary="List strategic risks")
@world_model_router.get("/risks", response_model=list[StrategicRisk], summary="List strategic risks")
async def list_risks() -> list[StrategicRisk]:
    """Retrieve active entries from the Strategic Risk Register."""
    return foresight_service.list_risks()


@router.get(
    "/opportunities", response_model=list[StrategicOpportunity], summary="List strategic opportunities"
)
@world_model_router.get(
    "/opportunities", response_model=list[StrategicOpportunity], summary="List strategic opportunities"
)
async def list_opportunities() -> list[StrategicOpportunity]:
    """Retrieve active entries from the Strategic Opportunity Register."""
    return foresight_service.list_opportunities()


@router.get("/early-warnings", response_model=list[EarlyWarningSignal], summary="List early warnings")
@world_model_router.get(
    "/early-warnings", response_model=list[EarlyWarningSignal], summary="List early warnings"
)
async def list_early_warnings() -> list[EarlyWarningSignal]:
    """Retrieve active early warning signals (Invariant: EARLY WARNING != INCIDENT)."""
    return foresight_service.list_early_warnings(active_only=True)


@router.get("/audit/trail", summary="Get audit trail")
@world_model_router.get("/audit/trail", summary="Get audit trail")
async def get_audit_trail(limit: int = Query(default=50, ge=1, le=200)) -> dict[str, Any]:
    """Retrieve recent cryptographic SHA-256 hash-chained audit records."""
    records = foresight_service.get_audit_trail(limit=limit)
    is_valid = foresight_service.verify_audit_integrity()
    return {
        "status": "success",
        "chain_intact": is_valid,
        "count": len(records),
        "records": [r.model_dump() for r in records],
    }
