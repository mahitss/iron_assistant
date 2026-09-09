"""Master Predictive Intelligence & Anticipation Engine Service (Task 47)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from app.prediction.anticipation import ProactiveSuggestion, UserNeedAnticipator
from app.prediction.calibration import CalibrationMetrics, ProbabilityCalibrator
from app.prediction.counterfactual import CounterfactualEngine, CounterfactualResult
from app.prediction.dependencies import CascadeRiskScenario, DependencyCascadeModel
from app.prediction.early_warning import EarlyWarning, EarlyWarningManager, WarningSeverity, WarningStatus
from app.prediction.explanations import PredictionExplainer
from app.prediction.forecasts import Forecast, Prediction, PredictionStatus, PredictionWindow
from app.prediction.monitors import MonitorRegistry, PredictionMonitor
from app.prediction.provenance import ProvenanceLedger, ReviewAssessment
from app.prediction.risk import PredictedRisk, RiskAnticipator
from app.prediction.safety import PredictionSafetyGuard
from app.prediction.scenarios import Scenario, ScenarioGenerator
from app.prediction.signals import DetectedTrend, SignalDetector
from app.prediction.simulation import ScenarioSimulator, SimulationResult
from app.prediction.triggers import ActionClass, PredictionTrigger, TriggerType

logger = logging.getLogger("kairo.prediction.service")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PredictionService:
    """Canonical predictive intelligence service integrating multi-modal telemetry into live foresight."""

    def __init__(self) -> None:
        self.calibrator = ProbabilityCalibrator()
        self.warnings = EarlyWarningManager()
        self.monitors = MonitorRegistry()
        self.provenance = ProvenanceLedger()
        self.dependencies = DependencyCascadeModel()

        # In-memory stores: id -> model
        self._predictions: Dict[str, Prediction] = {}
        self._forecasts: Dict[str, Forecast] = {}
        self._risks: Dict[str, PredictedRisk] = {}
        self._triggers: Dict[str, PredictionTrigger] = {}

    def create_prediction(
        self,
        subject: str,
        event: str,
        predicted_state: Dict[str, Any],
        prediction_window: Any = "short-term",
        time_to_event_seconds: Optional[float] = None,
        confidence: float = 0.5,
        model_reference: str = "trend_linear_v1",
        model_version: str = "1.0.0",
        assumptions: Optional[List[str]] = None,
        evidence_refs: Optional[List[str]] = None,
        user_id: str = "default_user",
        project_id: str = "default_project",
        environment: str = "DEVELOPMENT",
    ) -> Prediction:
        """Create a bounded prediction with calibrated confidence and provenance (Spec 2-5, 17-21)."""
        pid = f"pred_{uuid.uuid4().hex[:10]}"

        # Parse window
        if isinstance(prediction_window, PredictionWindow):
            p_win = prediction_window
        else:
            try:
                p_win = PredictionWindow(str(prediction_window))
            except ValueError:
                p_win = PredictionWindow.SHORT_TERM

        # Compute expiration time
        if time_to_event_seconds is not None:
            expires_at = utc_now() + timedelta(seconds=time_to_event_seconds)
        elif p_win == PredictionWindow.NEAR_TERM:
            expires_at = utc_now() + timedelta(hours=1)
        elif p_win == PredictionWindow.SHORT_TERM:
            expires_at = utc_now() + timedelta(hours=24)
        elif p_win == PredictionWindow.MEDIUM_TERM:
            expires_at = utc_now() + timedelta(days=7)
        else:
            expires_at = utc_now() + timedelta(days=30)

        # Sanitize input features (Spec 186, 187)
        clean_state = PredictionSafetyGuard.sanitize_prediction_input(predicted_state)

        # Adjust confidence for small sample sizes (Spec 21)
        calibrated_conf = self.calibrator.adjust_confidence_for_sample_size(confidence, model_reference)

        pred = Prediction(
            prediction_id=pid,
            subject=subject,
            event=event,
            predicted_state=clean_state,
            prediction_window=p_win,
            confidence=calibrated_conf,
            model_reference=model_reference,
            created_at=utc_now(),
            expires_at=expires_at,
            assumptions=assumptions or [],
            evidence_refs=evidence_refs or [],
            status=PredictionStatus.ACTIVE,
            scope={"user_id": user_id, "project_id": project_id, "environment": environment},
        )

        self._predictions[pid] = pred

        # Record provenance (Spec 13, 180)
        self.provenance.record_provenance(
            prediction_id=pid,
            model_ref=model_reference,
            model_ver=model_version,
            features=clean_state,
            evidence_ids=evidence_refs or [],
        )

        # Start predictive monitoring probe (Spec 57, 58)
        self.monitors.register_monitor(prediction_id=pid, subject=subject)

        logger.info("Formulated prediction %s on %s: %s (conf=%.2f, window=%s)", pid, subject, event, calibrated_conf, p_win.value)
        return pred

    def generate_prediction(
        self,
        subject: str,
        event: str,
        predicted_state: Dict[str, Any],
        prediction_window: Any = "short-term",
        time_to_event_seconds: Optional[float] = None,
        confidence: float = 0.5,
        model_reference: str = "trend_linear_v1",
        model_version: str = "1.0.0",
        assumptions: Optional[List[str]] = None,
        evidence_refs: Optional[List[str]] = None,
        user_id: str = "default_user",
        project_id: str = "default_project",
        environment: str = "DEVELOPMENT",
    ) -> Prediction:
        return self.create_prediction(
            subject=subject,
            event=event,
            predicted_state=predicted_state,
            prediction_window=prediction_window,
            time_to_event_seconds=time_to_event_seconds,
            confidence=confidence,
            model_reference=model_reference,
            model_version=model_version,
            assumptions=assumptions,
            evidence_refs=evidence_refs,
            user_id=user_id,
            project_id=project_id,
            environment=environment,
        )

    def explain_prediction(self, prediction_id: str) -> str:
        pred = self._predictions.get(prediction_id)
        if not pred:
            raise KeyError(f"Prediction {prediction_id} not found")
        return PredictionExplainer.generate_explanation(pred)

    def review_prediction(
        self,
        prediction_id: str,
        reviewer_agent_id: str,
        assessment: str = "EVIDENCE_VALID",
        critique: str = "",
        is_supported: bool = True,
        evidence_quality: float = 0.85,
    ) -> ReviewAssessment:
        prov = self.provenance.get_provenance(prediction_id)
        if not prov:
            prov = self.provenance.record_provenance(
                prediction_id=prediction_id,
                model_ref="review_forecaster",
                model_ver="1.0.0",
                features={},
                evidence_ids=[],
            )
        return prov.add_review(
            reviewer_agent_id=reviewer_agent_id,
            is_supported=is_supported,
            evidence_quality=evidence_quality,
            assessment=assessment,
            critique=critique,
        )

    def anticipate_cascade_risk(
        self,
        root_service: str,
        event: str,
        downstream_services: Optional[List[str]] = None,
        probability: float = 0.8,
    ) -> CascadeRiskScenario:
        return self.dependencies.estimate_cascade_risk(
            failing_component=root_service,
            initial_confidence=probability,
            downstream_services=downstream_services,
        )

    def create_forecast(
        self,
        target: str,
        current_trend: Dict[str, Any],
        interventions: Optional[List[Dict[str, Any]]] = None,
        likelihood: float = 0.5,
        timeframe: str = "medium-term",
        assumptions: Optional[List[str]] = None,
        user_id: str = "default_user",
        project_id: str = "default_project",
    ) -> Forecast:
        """Create multi-scenario future projection with revision tracking (Spec 6-11, 63, 64)."""
        fc_id = f"fc_{uuid.uuid4().hex[:10]}"

        # Generate plausible alternative futures (Spec 8)
        scenarios = ScenarioGenerator.generate_alternatives(target, current_trend, interventions)
        scenario_dicts = [s.to_dict() for s in scenarios]

        # Check for previous version for diffing (Spec 63, 64)
        prev_fc = next((f for f in reversed(list(self._forecasts.values())) if f.target == target), None)
        version = (prev_fc.version + 1) if prev_fc else 1

        fc = Forecast(
            forecast_id=fc_id,
            target=target,
            scenarios=scenario_dicts,
            likelihood=likelihood,
            timeframe=timeframe,
            evidence={"baseline_trend": current_trend},
            assumptions=assumptions or ["Continuation of verified telemetry velocity"],
            uncertainty=0.15 if version > 1 else 0.3,
            version=version,
            previous_version_id=prev_fc.forecast_id if prev_fc else None,
            scope={"user_id": user_id, "project_id": project_id},
        )
        self._forecasts[fc_id] = fc

        if prev_fc:
            diff = fc.diff_from_previous(prev_fc)
            logger.info("Forecast revised for %s: v%d -> v%d (delta=%.2f)", target, prev_fc.version, fc.version, diff["likelihood_delta"])

        return fc

    def evaluate_prediction_outcome(
        self,
        prediction_id: str,
        observed_state: Dict[str, Any],
        action_influenced: bool = False,
    ) -> Optional[Prediction]:
        """Record empirical reality against active prediction and feed calibration (Spec 22-24, 110, 138-143)."""
        pred = self._predictions.get(prediction_id)
        if not pred:
            return None

        status = pred.evaluate_outcome(observed_state, was_action_influenced=action_influenced)

        # Feed probability calibrator (Spec 110)
        self.calibrator.record_outcome(
            model_reference=pred.model_reference,
            predicted_probability=pred.confidence,
            actual_occurred=(status == PredictionStatus.CONFIRMED),
            action_influenced=action_influenced,
        )

        # Clean up expired / closed monitors (Spec 158)
        self._cleanup_monitors()
        return pred

    def _cleanup_monitors(self) -> None:
        active_ids = {p.prediction_id for p in self._predictions.values() if p.status == PredictionStatus.ACTIVE and not p.is_expired()}
        self.monitors.cleanup_expired_monitors(active_ids)

    def list_predictions(
        self,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Prediction]:
        res = list(self._predictions.values())
        if user_id:
            res = [p for p in res if p.scope.get("user_id") in [user_id, "*"]]
        if project_id:
            res = [p for p in res if p.scope.get("project_id") in [project_id, "*"]]
        if status:
            res = [p for p in res if p.status.value == status.upper()]
        return res

    def get_prediction(self, prediction_id: str) -> Optional[Prediction]:
        return self._predictions.get(prediction_id)

    def get_health_metrics(self) -> Dict[str, Any]:
        """Aggregate health, calibration, and early warning stats."""
        self._cleanup_monitors()
        active = [p for p in self._predictions.values() if p.status == PredictionStatus.ACTIVE and not p.is_expired()]
        calib = self.calibrator.compute_calibration("trend_linear_v1")

        return {
            "predictions_active": len(active),
            "predictions_total": len(self._predictions),
            "warnings_open": len(self.warnings.get_active_warnings()),
            "monitors_running": len(self.monitors.get_active_monitors()),
            "avg_confidence": round(sum(p.confidence for p in active) / len(active), 3) if active else 0.5,
            "brier_score": calib.brier_score,
            "calibration_quality": "WELL_CALIBRATED" if calib.brier_score < 0.2 else "UNCALIBRATED",
        }
