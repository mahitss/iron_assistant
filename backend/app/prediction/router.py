"""FastAPI REST API Router for Kairo Predictive Intelligence & Anticipation Engine (Task 47)."""

from __future__ import annotations

import logging
from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.prediction.early_warning import WarningSeverity
from app.prediction.safety import PredictionSecurityViolation
from app.prediction.schemas import (
    BacktestConfig,
    BacktestResult,
    CalibrationMetricsResponse,
    CalibrationReport,
    CounterfactualRequest,
    CounterfactualResponse,
    DriftReport,
    EarlyWarningResponse,
    EarlyWarningSeverity,
    ForecastCreateRequest,
    ForecastHorizon,
    ForecastResponse,
    ForecastState,
    ForecastStrategyType,
    ForecastType,
    PredictedRiskResponse,
    PredictionCreateRequest,
    PredictionHealthResponse,
    PredictionResponse,
    ScenarioSchema,
    SimulationRequest,
    SimulationResponse,
)
from app.prediction.service import PredictionService

logger = logging.getLogger("kairo.prediction.router")

router = APIRouter(prefix="/prediction", tags=["prediction"])

_global_prediction_service: Optional[PredictionService] = None


def get_prediction_service() -> PredictionService:
    global _global_prediction_service
    if _global_prediction_service is None:
        _global_prediction_service = PredictionService()
    return _global_prediction_service


def get_current_user_id(x_user_id: Annotated[Optional[str], Header()] = None) -> str:
    return x_user_id or "default_user"


def get_current_project_id(x_project_id: Annotated[Optional[str], Header()] = None) -> str:
    return x_project_id or "default_project"


# ==================================================
# Predictions Endpoints (Spec 2-5, 138-145)
# ==================================================

@router.post("/predictions", response_model=PredictionResponse, status_code=status.HTTP_201_CREATED)
async def create_prediction(
    req: PredictionCreateRequest,
    service: Annotated[PredictionService, Depends(get_prediction_service)],
    user_id: Annotated[str, Depends(get_current_user_id)],
    project_id: Annotated[str, Depends(get_current_project_id)],
) -> PredictionResponse:
    try:
        pred = service.create_prediction(
            subject=req.subject,
            event=req.event,
            predicted_state=req.predicted_state,
            prediction_window=req.prediction_window,
            time_to_event_seconds=req.time_to_event_seconds,
            confidence=req.confidence,
            model_reference=req.model_reference,
            assumptions=req.assumptions,
            evidence_refs=req.evidence_refs,
            user_id=user_id,
            project_id=project_id,
            environment=req.environment,
        )
        return PredictionResponse(**pred.to_dict())
    except PredictionSecurityViolation as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.get("/predictions", response_model=List[PredictionResponse])
async def list_predictions(
    service: Annotated[PredictionService, Depends(get_prediction_service)],
    user_id: Annotated[str, Depends(get_current_user_id)],
    project_id: Annotated[str, Depends(get_current_project_id)],
    status: Optional[str] = Query(None),
) -> List[PredictionResponse]:
    preds = service.list_predictions(user_id=user_id, project_id=project_id, status=status)
    return [PredictionResponse(**p.to_dict()) for p in preds]


@router.get("/predictions/{prediction_id}", response_model=PredictionResponse)
async def get_prediction(
    prediction_id: str,
    service: Annotated[PredictionService, Depends(get_prediction_service)],
) -> PredictionResponse:
    pred = service.get_prediction(prediction_id)
    if not pred:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Prediction {prediction_id} not found")
    return PredictionResponse(**pred.to_dict())


@router.post("/predictions/{prediction_id}/evaluate", response_model=PredictionResponse)
async def evaluate_prediction_outcome(
    prediction_id: str,
    payload: Dict[str, Any],
    service: Annotated[PredictionService, Depends(get_prediction_service)],
) -> PredictionResponse:
    observed_state = payload.get("observed_state", {})
    action_influenced = payload.get("action_influenced", False)

    pred = service.evaluate_prediction_outcome(
        prediction_id=prediction_id,
        observed_state=observed_state,
        action_influenced=action_influenced,
    )
    if not pred:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Prediction {prediction_id} not found")
    return PredictionResponse(**pred.to_dict())


# ==================================================
# Forecasts Endpoints (Spec 6-11, 63, 64)
# ==================================================

# ==================================================
# Forecasts Endpoints (Task 74, Spec 6-11, 49, 63, 64)
# ==================================================

@router.post("/forecasts", response_model=ForecastResponse, status_code=status.HTTP_201_CREATED)
@router.post("/forecast", response_model=ForecastResponse, status_code=status.HTTP_201_CREATED)
async def create_forecast(
    req: ForecastCreateRequest,
    service: Annotated[PredictionService, Depends(get_prediction_service)],
    user_id: Annotated[str, Depends(get_current_user_id)],
    project_id: Annotated[str, Depends(get_current_project_id)],
) -> ForecastResponse:
    obs = req.observations or req.historical_series or req.series
    pe = req.predicted_value if req.predicted_value is not None else req.point_estimate
    fc = service.create_forecast(
        target=req.target,
        current_trend=req.evidence.get("current_trend", {}) if isinstance(req.evidence, dict) else {},
        interventions=[s.model_dump() for s in req.scenarios if s.is_counterfactual],
        likelihood=req.likelihood,
        timeframe=req.timeframe,
        assumptions=req.assumptions,
        user_id=user_id,
        project_id=project_id,
        target_type=req.target_type,
        target_metric=req.target_metric,
        horizon=req.horizon,
        forecast_type=req.forecast_type,
        strategy=req.strategy,
        observations=obs,
        point_estimate=pe,
        interval=req.interval,
        baseline=req.baseline,
    )
    return ForecastResponse(**fc.to_dict())


@router.get("/forecasts", response_model=List[ForecastResponse])
async def list_forecasts(
    service: Annotated[PredictionService, Depends(get_prediction_service)],
    target: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    horizon: Optional[str] = Query(None),
) -> List[ForecastResponse]:
    st = None
    if state:
        try:
            from app.prediction.schemas import ForecastState
            st = ForecastState(state.upper())
        except ValueError:
            pass
    hz = None
    if horizon:
        try:
            from app.prediction.schemas import ForecastHorizon
            hz = ForecastHorizon(horizon.upper())
        except ValueError:
            pass
    fcs = service.list_forecasts(target=target, state=st, horizon=hz)
    return [ForecastResponse(**f.to_dict()) for f in fcs]


@router.get("/forecasts/active", response_model=List[ForecastResponse])
async def list_active_forecasts(
    service: Annotated[PredictionService, Depends(get_prediction_service)],
) -> List[ForecastResponse]:
    from app.prediction.schemas import ForecastState
    fcs = service.list_forecasts(state=ForecastState.PUBLISHED)
    return [ForecastResponse(**f.to_dict()) for f in fcs if not f.is_stale()]


@router.get("/forecasts/{forecast_id}", response_model=ForecastResponse)
async def get_forecast(
    forecast_id: str,
    service: Annotated[PredictionService, Depends(get_prediction_service)],
) -> ForecastResponse:
    fc = service.get_forecast(forecast_id)
    if not fc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Forecast '{forecast_id}' not found")
    return ForecastResponse(**fc.to_dict())


@router.post("/forecasts/{forecast_id}/refresh", response_model=ForecastResponse)
async def refresh_forecast(
    forecast_id: str,
    payload: Dict[str, Any],
    service: Annotated[PredictionService, Depends(get_prediction_service)],
) -> ForecastResponse:
    new_evidence = payload.get("new_evidence")
    changed_assumptions = payload.get("changed_assumptions")
    reason = payload.get("reason", "Periodic refresh")
    updated_series = payload.get("updated_series") or payload.get("series")
    try:
        revised = service.refresh_forecast(
            forecast_id=forecast_id,
            new_evidence=new_evidence,
            changed_assumptions=changed_assumptions,
            reason=reason,
            updated_series=updated_series,
        )
        return ForecastResponse(**revised.to_dict())
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Forecast '{forecast_id}' not found")


@router.post("/forecasts/{forecast_id}/invalidate", response_model=ForecastResponse)
async def invalidate_forecast(
    forecast_id: str,
    payload: Dict[str, Any],
    service: Annotated[PredictionService, Depends(get_prediction_service)],
) -> ForecastResponse:
    reason = payload.get("reason", "Operator or regime invalidation")
    try:
        inv = service.invalidate_forecast(forecast_id=forecast_id, reason=reason)
        return ForecastResponse(**inv.to_dict())
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Forecast '{forecast_id}' not found")


@router.post("/forecasts/{forecast_id}/evaluate", response_model=ForecastResponse)
async def evaluate_forecast_outcome(
    forecast_id: str,
    payload: Dict[str, Any],
    service: Annotated[PredictionService, Depends(get_prediction_service)],
) -> ForecastResponse:
    actual_val = float(payload.get("actual_value", 0.0))
    action_inf = bool(payload.get("action_influenced", False))
    try:
        fc = service.evaluate_forecast_outcome(
            forecast_id=forecast_id,
            actual_value=actual_val,
            action_influenced=action_inf,
        )
        return ForecastResponse(**fc.to_dict())
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Forecast '{forecast_id}' not found")


@router.get("/forecasts/{forecast_id}/history", response_model=List[ForecastResponse])
async def get_forecast_history(
    forecast_id: str,
    service: Annotated[PredictionService, Depends(get_prediction_service)],
) -> List[ForecastResponse]:
    fc = service.get_forecast(forecast_id)
    if not fc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Forecast '{forecast_id}' not found")
    history = service.get_forecast_history(fc.target)
    return [ForecastResponse(**h.to_dict()) for h in history]


@router.get("/forecasts/{forecast_id}/outcome")
async def get_forecast_outcome(
    forecast_id: str,
    service: Annotated[PredictionService, Depends(get_prediction_service)],
) -> Dict[str, Any]:
    fc = service.get_forecast(forecast_id)
    if not fc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Forecast '{forecast_id}' not found")
    return {"forecast_id": forecast_id, "actual_outcome": fc.actual_outcome, "state": fc.state.value}


@router.get("/forecasts/{forecast_id}/explanation")
async def get_forecast_explanation(
    forecast_id: str,
    service: Annotated[PredictionService, Depends(get_prediction_service)],
) -> Dict[str, Any]:
    try:
        return service.get_forecast_explanation(forecast_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Forecast '{forecast_id}' not found")


@router.get("/forecasts/{forecast_id}/provenance")
async def get_forecast_provenance(
    forecast_id: str,
    service: Annotated[PredictionService, Depends(get_prediction_service)],
) -> Dict[str, Any]:
    try:
        return service.get_forecast_provenance(forecast_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Forecast '{forecast_id}' not found")


@router.post("/forecasts/backtest", response_model=BacktestResult)
async def run_backtest(
    payload: Dict[str, Any],
    service: Annotated[PredictionService, Depends(get_prediction_service)],
) -> BacktestResult:
    target = payload.get("target", "system_metric")
    series = payload.get("series", [])
    strat_str = payload.get("strategy", "TREND_EXTRAPOLATION")
    h_steps = int(payload.get("horizon_steps", 5))

    cfg = BacktestConfig(
        target=target,
        strategy=ForecastStrategyType(strat_str),
        horizon_steps=h_steps,
        window_type=payload.get("window_type", "rolling"),
        min_train_size=int(payload.get("min_train_size", 10)),
        step_size=int(payload.get("step_size", 1)),
    )
    return service.run_backtest(target=target, series=series, config=cfg)


# ==================================================
# Early Warnings & Risks (Task 74 & 47, Spec 24-28, 65, 66)
# ==================================================

@router.post("/early-warnings", response_model=EarlyWarningResponse, status_code=status.HTTP_201_CREATED)
@router.post("/warnings", response_model=EarlyWarningResponse, status_code=status.HTTP_201_CREATED)
async def issue_early_warning(
    payload: Dict[str, Any],
    service: Annotated[PredictionService, Depends(get_prediction_service)],
) -> EarlyWarningResponse:
    target = payload.get("target", "system")
    signal = payload.get("signal", "metric_surge")
    predicted_event = payload.get("predicted_event", "outage")
    conf = float(payload.get("confidence", 0.7))
    sev_str = payload.get("severity", "MEDIUM").upper()

    try:
        sev = EarlyWarningSeverity(sev_str)
    except ValueError:
        sev = EarlyWarningSeverity.WARNING

    w = service.warnings.create_warning(
        target=target,
        signal=signal,
        predicted_event=predicted_event,
        confidence=conf,
        severity=sev,
        evidence=payload.get("evidence", {}),
        linked_forecast_ids=payload.get("linked_forecast_ids", []),
        leading_indicators=payload.get("leading_indicators", []),
        recommended_investigation=payload.get("recommended_investigation"),
    )
    return EarlyWarningResponse(**w.to_dict())


@router.get("/early-warnings", response_model=List[EarlyWarningResponse])
@router.get("/early-warning", response_model=List[EarlyWarningResponse])
@router.get("/warnings", response_model=List[EarlyWarningResponse])
async def list_active_warnings(
    service: Annotated[PredictionService, Depends(get_prediction_service)],
) -> List[EarlyWarningResponse]:
    warns = service.warnings.get_active_warnings()
    return [EarlyWarningResponse(**w.to_dict()) for w in warns]


@router.get("/early-warnings/{warning_id}", response_model=EarlyWarningResponse)
async def get_early_warning(
    warning_id: str,
    service: Annotated[PredictionService, Depends(get_prediction_service)],
) -> EarlyWarningResponse:
    w = service.warnings.get_warning(warning_id)
    if not w:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Early warning '{warning_id}' not found")
    return EarlyWarningResponse(**w.to_dict())


@router.post("/early-warnings/{warning_id}/acknowledge", response_model=EarlyWarningResponse)
async def acknowledge_early_warning(
    warning_id: str,
    service: Annotated[PredictionService, Depends(get_prediction_service)],
    user_id: Annotated[str, Depends(get_current_user_id)],
    payload: Optional[Dict[str, Any]] = None,
) -> EarlyWarningResponse:
    try:
        w = service.warnings.acknowledge_warning(warning_id=warning_id, actor=user_id)
        return EarlyWarningResponse(**w.to_dict())
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Early warning '{warning_id}' not found")


@router.post("/early-warnings/{warning_id}/dismiss", response_model=EarlyWarningResponse)
async def dismiss_early_warning(
    warning_id: str,
    service: Annotated[PredictionService, Depends(get_prediction_service)],
    payload: Optional[Dict[str, Any]] = None,
) -> EarlyWarningResponse:
    reason = (payload or {}).get("reason", "Operator manually dismissed")
    try:
        w = service.warnings.dismiss_warning(warning_id=warning_id, reason=reason)
        return EarlyWarningResponse(**w.to_dict())
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Early warning '{warning_id}' not found")


@router.post("/early-warnings/{warning_id}/escalate", response_model=EarlyWarningResponse)
async def escalate_early_warning(
    warning_id: str,
    payload: Dict[str, Any],
    service: Annotated[PredictionService, Depends(get_prediction_service)],
) -> EarlyWarningResponse:
    new_conf = float(payload.get("confidence", 0.9))
    sev_str = payload.get("severity", "CRITICAL").upper()
    try:
        sev = EarlyWarningSeverity(sev_str)
    except ValueError:
        sev = EarlyWarningSeverity.CRITICAL
    new_ev = payload.get("evidence")

    try:
        w = service.warnings.escalate_warning(
            warning_id=warning_id,
            new_confidence=new_conf,
            new_severity=sev,
            new_evidence=new_ev,
        )
        return EarlyWarningResponse(**w.to_dict())
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Early warning '{warning_id}' not found")



@router.post("/risks", response_model=PredictedRiskResponse, status_code=status.HTTP_201_CREATED)
async def evaluate_risk(
    payload: Dict[str, Any],
    service: Annotated[PredictionService, Depends(get_prediction_service)],
) -> PredictedRiskResponse:
    from app.prediction.risk import RiskAnticipator
    risk = RiskAnticipator.evaluate_risk(
        subject=payload.get("subject", "general"),
        event=payload.get("event", "capacity_exhaust"),
        likelihood=float(payload.get("likelihood", 0.6)),
        impact=float(payload.get("impact", 0.7)),
        timeframe=payload.get("timeframe", "short-term"),
        confidence=float(payload.get("confidence", 0.8)),
        evidence=payload.get("evidence", {}),
    )
    service._risks[risk.risk_id] = risk
    return PredictedRiskResponse(**risk.to_dict())


@router.get("/risks", response_model=List[PredictedRiskResponse])
async def list_predicted_risks(
    service: Annotated[PredictionService, Depends(get_prediction_service)],
) -> List[PredictedRiskResponse]:
    return [PredictedRiskResponse(**r.to_dict()) for r in service._risks.values()]


# ==================================================
# Triggers & Monitors (Spec 50-61)
# ==================================================

@router.post("/triggers", status_code=status.HTTP_201_CREATED)
async def register_prediction_trigger(
    payload: Dict[str, Any],
    service: Annotated[PredictionService, Depends(get_prediction_service)],
) -> Dict[str, Any]:
    from app.prediction.triggers import PredictionTrigger, TriggerType, ActionClass
    t_type = TriggerType(payload.get("trigger_type", "THRESHOLD"))
    a_class = ActionClass(payload.get("action_class", "SAFE_PREEMPTION"))
    trig = PredictionTrigger(
        condition=payload.get("condition", ""),
        trigger_type=t_type,
        action_class=a_class,
        action_name=payload.get("action_name", ""),
        scope=payload.get("scope", ""),
        required_evidence=payload.get("required_evidence", []),
        authorized=payload.get("authorized", False),
    )
    service._triggers[trig.trigger_id] = trig
    return trig.to_dict()


@router.get("/monitors")
async def list_active_monitors(
    service: Annotated[PredictionService, Depends(get_prediction_service)],
) -> List[Dict[str, Any]]:
    return [
        {
            "monitor_id": m.monitor_id,
            "prediction_id": m.prediction_id,
            "subject": m.subject,
            "poll_frequency_seconds": m.poll_frequency_seconds,
            "state": m.state.value if hasattr(m.state, "value") else str(m.state),
            "checks_performed": m.checks_performed,
            "created_at": m.created_at.isoformat(),
        }
        for m in service.monitors.get_active_monitors()
    ]


# ==================================================
# Simulation & Counterfactuals (Spec 118-123)
# ==================================================

@router.post("/simulation", response_model=SimulationResponse)
@router.post("/simulate", response_model=SimulationResponse)
async def simulate_scenarios(
    req: SimulationRequest,
) -> SimulationResponse:
    from app.prediction.simulation import ScenarioSimulator
    target = req.target or req.scenario_name or "simulation_target"
    steps = req.steps or req.time_steps or 5
    intvs = req.interventions or req.intervention_actions or []
    res = ScenarioSimulator.simulate(
        target=target,
        initial_state=req.initial_state,
        interventions=intvs,
        time_steps=steps,
    )
    return SimulationResponse(**res.to_dict())


@router.post("/counterfactual", response_model=CounterfactualResponse)
async def evaluate_counterfactual(
    req: CounterfactualRequest,
) -> CounterfactualResponse:
    from app.prediction.counterfactual import CounterfactualEngine
    trend = req.current_trend if req.current_trend is not None else (req.baseline_trend or {})
    action = req.proposed_action or req.hypothetical_intervention
    res = CounterfactualEngine.evaluate_counterfactual(
        subject=req.subject,
        current_trend=trend,
        proposed_action=action,
        horizon_hours=req.horizon_hours,
    )
    return CounterfactualResponse(**res.to_dict())


# ==================================================
# Calibration & Health (Spec 19-23, 110, 166)
# ==================================================

@router.get("/calibration", response_model=CalibrationMetricsResponse)
async def get_calibration_metrics(
    service: Annotated[PredictionService, Depends(get_prediction_service)],
    model_reference: str = Query("trend_linear_v1"),
) -> CalibrationMetricsResponse:
    m = service.calibrator.compute_calibration(model_reference)
    return CalibrationMetricsResponse(**m.to_dict())


@router.get("/health", response_model=PredictionHealthResponse)
async def get_prediction_health(
    service: Annotated[PredictionService, Depends(get_prediction_service)],
) -> PredictionHealthResponse:
    return PredictionHealthResponse(**service.get_health_metrics())

