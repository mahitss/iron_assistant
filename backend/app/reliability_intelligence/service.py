"""Master Reliability Intelligence & Predictive Prevention Service (Task 90).

Orchestrates the entire end-to-end prevention chain:
OBSERVE
 ↓
DETECT SIGNAL & ESTABLISH BASELINE
 ↓
FORECAST FAILURE (Task 74)
 ↓
IDENTIFY CAUSAL DRIVERS (Task 73)
 ↓
PROPAGATE SYSTEMIC RISK & BLAST RADIUS (Task 75)
 ↓
SIMULATE PREVENTIONS & NO-ACTION COUNTERFACTUAL (Task 89)
 ↓
SELECT SAFEST MINIMUM INTERVENTION
 ↓
GOVERN, AUTHORIZE & ADAPT AUTONOMY (Task 78, EmergencyStop)
 ↓
ALLOCATE COGNITIVE & RESOURCE BUDGET (Task 77)
 ↓
EXECUTE PREVENTIVE INTERVENTION (Task 88)
 ↓
DETERMINISTIC NON-LLM VERIFICATION PROBE & STABILITY WINDOW
 ↓
METACOGNITIVE CALIBRATION & LEARNING
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple

from app.reliability_intelligence.baselines import (
    BaselineTracker,
    get_baseline_tracker,
)
from app.reliability_intelligence.calibration import (
    CalibrationManager,
    get_calibration_manager,
)
from app.reliability_intelligence.causal_bridge import (
    CausalBridge,
    get_causal_bridge,
)
from app.reliability_intelligence.economy_bridge import (
    EconomyBridge,
    get_economy_bridge,
)
from app.reliability_intelligence.execution_verifier import (
    PreventionExecutorVerifier,
    get_executor_verifier,
)
from app.reliability_intelligence.forecasting_bridge import (
    ForecastingBridge,
    get_forecasting_bridge,
)
from app.reliability_intelligence.governance_bridge import (
    GovernanceBridge,
    get_governance_bridge,
)
from app.reliability_intelligence.models import (
    AutonomyAdaptationLevel,
    DecisionExplanation,
    EarlyWarningState,
    PredictiveIncident,
    PreventionActionType,
    PreventionCandidate,
    PreventionStatus,
    ReliabilitySignal,
    ReliabilitySignalType,
    generate_ri_id,
    _now_utc,
)
from app.reliability_intelligence.risk_bridge import (
    RiskBridge,
    get_risk_bridge,
)
from app.reliability_intelligence.signals import (
    SignalCorrelator,
    SignalStateMachine,
    get_signal_correlator,
    get_signal_state_machine,
)
from app.reliability_intelligence.simulation_bridge import (
    SimulationBridge,
    get_simulation_bridge,
)

logger = logging.getLogger("kairo.reliability_intelligence.service")


class ReliabilityIntelligenceService:
    """Master orchestrator integrating all 10 subsystems into an autonomous prevention loop."""

    def __init__(
        self,
        baseline_tracker: Optional[BaselineTracker] = None,
        signal_state_machine: Optional[SignalStateMachine] = None,
        signal_correlator: Optional[SignalCorrelator] = None,
        forecasting_bridge: Optional[ForecastingBridge] = None,
        causal_bridge: Optional[CausalBridge] = None,
        risk_bridge: Optional[RiskBridge] = None,
        simulation_bridge: Optional[SimulationBridge] = None,
        governance_bridge: Optional[GovernanceBridge] = None,
        economy_bridge: Optional[EconomyBridge] = None,
        executor_verifier: Optional[PreventionExecutorVerifier] = None,
        calibration_manager: Optional[CalibrationManager] = None,
    ) -> None:
        self.baselines = baseline_tracker or get_baseline_tracker()
        self.state_machine = signal_state_machine or get_signal_state_machine()
        self.correlator = signal_correlator or get_signal_correlator()
        self.forecasting = forecasting_bridge or get_forecasting_bridge()
        self.causal = causal_bridge or get_causal_bridge()
        self.risk = risk_bridge or get_risk_bridge()
        self.simulation = simulation_bridge or get_simulation_bridge()
        self.governance = governance_bridge or get_governance_bridge()
        self.economy = economy_bridge or get_economy_bridge()
        self.executor = executor_verifier or get_executor_verifier()
        self.calibration = calibration_manager or get_calibration_manager()

        # In-memory storage for active signals and predictive incidents
        self._signals: Dict[str, ReliabilitySignal] = {}
        self._incidents: Dict[str, PredictiveIncident] = {}
        self._current_autonomy: AutonomyAdaptationLevel = AutonomyAdaptationLevel.FULL

    @property
    def current_autonomy(self) -> AutonomyAdaptationLevel:
        return self._current_autonomy

    def ingest_telemetry_reading(
        self,
        component: str,
        metric_name: str,
        current_value: float,
        threshold_value: Optional[float] = None,
        signal_type: ReliabilitySignalType = ReliabilitySignalType.RESOURCE_PRESSURE,
        severity: str = "P2",
    ) -> Optional[ReliabilitySignal]:
        """Ingests a live telemetry sample, updates dynamic baselines, and detects early signals."""
        self.baselines.record_sample(component, metric_name, current_value)
        rate_info = self.baselines.compute_rate_of_change(component, metric_name, threshold_value)
        base_info = self.baselines.get_baseline(component, metric_name)

        # Determine early warning state
        cand_state = EarlyWarningState.NORMAL
        if threshold_value is not None and current_value >= threshold_value * 0.95:
            cand_state = EarlyWarningState.CRITICAL
        elif threshold_value is not None and current_value >= threshold_value * 0.85:
            cand_state = EarlyWarningState.HIGH
        elif threshold_value is not None and current_value >= threshold_value * 0.70:
            cand_state = EarlyWarningState.ELEVATED
        elif rate_info.rate_per_minute > 0 and rate_info.estimated_time_to_threshold_minutes and rate_info.estimated_time_to_threshold_minutes < 30.0:
            cand_state = EarlyWarningState.WATCH

        state, transitioned = self.state_machine.transition(component, cand_state)

        if state == EarlyWarningState.NORMAL:
            return None  # All healthy within normal baseline

        # Construct typed signal
        sig = ReliabilitySignal(
            signal_id=generate_ri_id("sig"),
            signal_type=signal_type,
            component=component,
            metric_name=metric_name,
            severity=severity,
            confidence=rate_info.confidence,
            trend=rate_info.trend,
            baseline=base_info.baseline_value,
            current_value=current_value,
            forecast=rate_info.uncertainty_interval_minutes,
            evidence={
                "metric_name": metric_name,
                "rate_per_minute": rate_info.rate_per_minute,
                "time_to_threshold": rate_info.estimated_time_to_threshold_minutes,
                "baseline_mean": base_info.baseline_value,
                "sample_count": base_info.sample_count,
            },
            state=state,
        )

        corr_id, is_new = self.correlator.ingest_signal(sig)
        self._signals[sig.signal_id] = sig
        return sig

    async def evaluate_and_prevent(
        self,
        signal: ReliabilitySignal,
    ) -> PredictiveIncident:
        """Executes the complete end-to-end prevention intelligence pipeline."""
        comp = signal.component
        metric_name = signal.metric_name or signal.evidence.get("metric_name", "value")

        # 1. FORECAST FAILURE (Task 74)
        rate_info = self.baselines.compute_rate_of_change(comp, metric_name)
        forecast = self.forecasting.forecast_failure(signal, rate_info)

        # 2. IDENTIFY CAUSAL DRIVERS (Task 73)
        inc_id = generate_ri_id("pinc")
        causal_analysis = self.causal.identify_causal_drivers(signal, inc_id)

        # 3. ESTIMATE IMPACT & BLAST RADIUS (Task 75)
        impact = self.risk.estimate_impact(signal)

        # 4. SIMULATE PREVENTIONS & NO-ACTION COUNTERFACTUAL (Task 89)
        candidates = self.simulation.generate_prevention_candidates(signal, impact)
        comparison = self.simulation.compare_and_select(candidates, forecast, impact)
        selected = comparison.selected_candidate

        # 5. SYNTHESIZE STRUCTURED DECISION EXPLANATION (Section 47)
        explanation = DecisionExplanation(
            problem=f"Predicted {signal.signal_type.value} on {comp} ({forecast.uncertainty_interval})",
            evidence=forecast.evidence + causal_analysis.evidence,
            expected_impact=f"Blast radius score {impact.blast_radius_score:.2f} affecting {impact.affected_components}",
            options=[c.action_type.value for c in candidates],
            selected_action=selected.action_type.value if selected else "NONE",
            why=comparison.selection_rationale,
            confidence=round((forecast.confidence + causal_analysis.confidence) / 2.0, 2),
            uncertainty=forecast.uncertainty_interval,
            verification="Non-LLM synthetic health probe probe and stability monitoring",
        )

        # 6. ADAPT OPERATIONAL AUTONOMY (Task 78)
        self._current_autonomy = self.governance.adapt_autonomy_level(signal.state)

        # 7. GOVERNANCE & SECURITY AUTHORIZATION
        authorized, requires_approval, auth_reason = self.governance.evaluate_authorization(
            selected, self._current_autonomy
        )

        init_status = PreventionStatus.AUTHORIZING if requires_approval else (
            PreventionStatus.CANCELLED if not authorized else PreventionStatus.RECOMMENDED
        )

        incident = PredictiveIncident(
            incident_id=inc_id,
            title=f"Proactive Incident: {signal.signal_type.value} on {comp}",
            target_component=comp,
            early_warning_state=signal.state,
            signals=[signal],
            forecast=forecast,
            causal_drivers=causal_analysis,
            predicted_impact=impact,
            candidates=candidates,
            selected_prevention=selected,
            decision_explanation=explanation,
            status=init_status,
            autonomy_level=self._current_autonomy,
            authorization_granted=authorized,
            requires_approval=requires_approval,
        )
        self._incidents[inc_id] = incident

        # Emit incident creation
        await self.executor.emit_observability_event(
            "PREDICTIVE_INCIDENT_CREATED",
            {
                "incident_id": inc_id,
                "component": comp,
                "early_warning_state": signal.state.value,
                "selected_action": selected.action_type.value if selected else None,
            },
            correlation_id=signal.correlation_id,
        )

        # 8. RESOURCE ECONOMY BUDGET ALLOCATION (Task 77)
        if authorized and not requires_approval and not selected.is_no_action:
            budget_ok, budget_reason = self.economy.allocate_prevention_budget(selected)
            if not budget_ok:
                logger.warn("Prevention postponed by resource economy: %s", budget_reason)
                incident.status = PreventionStatus.FAILED
                return incident

            incident.resource_budget_allocated = True

            # 9. EXECUTE & VERIFY
            incident.status = PreventionStatus.EXECUTING
            status, exec_result = await self.executor.execute_prevention(
                selected, correlation_id=signal.correlation_id
            )
            incident.status = status
            incident.verification_passed = (status == PreventionStatus.VERIFIED)

            # Release budget
            self.economy.release_prevention_budget(selected)

            # 10. CALIBRATE & LEARN (Section 48-52)
            self.calibration.record_strategy_execution(
                selected.action_type,
                success=(status == PreventionStatus.VERIFIED),
                duration_seconds=selected.estimated_duration_seconds,
            )
            self.calibration.record_calibration(
                incident_id=inc_id,
                predicted_failure=signal.signal_type.value,
                actual_failure_occurred=False,  # Successfully prevented!
                predicted_horizon=forecast.time_horizon.value,
                predicted_confidence=forecast.confidence,
                intervention_executed=True,
            )
        elif requires_approval:
            incident.status = PreventionStatus.AUTHORIZING
            logger.info("Incident %s requires human operator authorization: %s", inc_id, auth_reason)
        elif selected.is_no_action:
            incident.status = PreventionStatus.VERIFIED
            incident.verification_passed = True

        incident.updated_at = _now_utc()
        return incident

    def get_incident(self, incident_id: str) -> Optional[PredictiveIncident]:
        return self._incidents.get(incident_id)

    def list_incidents(self) -> List[PredictiveIncident]:
        return list(self._incidents.values())

    def list_signals(self) -> List[ReliabilitySignal]:
        return list(self._signals.values())

    def get_calibration_summary(self) -> Dict[str, Any]:
        metrics = self.calibration.get_calibration_metrics()
        scorecards = {
            s.strategy.value: {
                "total_attempts": s.total_attempts,
                "successes": s.successes,
                "failures": s.failures,
                "verification_rate": s.verification_rate,
                "success_rate_percent": round(s.verification_rate * 100, 1),
                "is_degraded": s.health_status == "DEGRADED",
            }
            for s in self.calibration.get_scorecards()
            if s.total_attempts > 0
        }
        return {
            **metrics,
            "total_forecasts_tracked": metrics["total_evaluations"],
            "scorecards": scorecards,
        }


_global_service: Optional[ReliabilityIntelligenceService] = None


def get_reliability_intelligence_service() -> ReliabilityIntelligenceService:
    global _global_service
    if _global_service is None:
        _global_service = ReliabilityIntelligenceService()
    return _global_service
