"""Unit, integration, and safety tests for Task 90 Reliability Intelligence & Predictive Failure Prevention."""

from __future__ import annotations

import asyncio
import pytest
from datetime import datetime, timezone, timedelta

from app.reliability_intelligence.models import (
    AutonomyAdaptationLevel,
    EarlyWarningState,
    ForecastHorizon,
    PreventionActionType,
    PreventionCandidate,
    PreventionStatus,
    ReliabilitySignal,
    ReliabilitySignalType,
    ReversibilityLevel,
    TrendDirection,
)
from app.reliability_intelligence.baselines import BaselineTracker
from app.reliability_intelligence.signals import SignalStateMachine, SignalCorrelator
from app.reliability_intelligence.forecasting_bridge import ForecastingBridge
from app.reliability_intelligence.causal_bridge import CausalBridge
from app.reliability_intelligence.risk_bridge import RiskBridge
from app.reliability_intelligence.simulation_bridge import SimulationBridge
from app.reliability_intelligence.governance_bridge import GovernanceBridge
from app.reliability_intelligence.economy_bridge import EconomyBridge
from app.reliability_intelligence.execution_verifier import PreventionExecutorVerifier
from app.reliability_intelligence.calibration import CalibrationManager
from app.reliability_intelligence.service import ReliabilityIntelligenceService
from app.security.emergency_stop import get_emergency_stop_service


# ==============================================================================
# 1. BASELINES, RATE-OF-CHANGE & TREND DETECTION
# ==============================================================================

def test_baseline_tracker_and_trend_detection():
    tracker = BaselineTracker(max_samples_per_series=20)
    now = datetime.now(timezone.utc)

    # 1. Monotonically increasing samples
    for i in range(5):
        tracker.record_sample("native_runtime", "memory_rss_mb", 50.0 + (i * 10.0), now + timedelta(minutes=i))

    trend = tracker.detect_trend("native_runtime", "memory_rss_mb")
    assert trend == TrendDirection.INCREASING

    baseline = tracker.get_baseline("native_runtime", "memory_rss_mb")
    assert baseline.sample_count == 5
    assert baseline.baseline_value == 70.0  # (50+60+70+80+90)/5
    assert baseline.min_value == 50.0
    assert baseline.max_value == 90.0

    # 2. Rate of change and time-to-threshold estimation
    roc = tracker.compute_rate_of_change("native_runtime", "memory_rss_mb", threshold_value=120.0)
    assert roc.rate_per_minute > 0.0
    assert roc.estimated_time_to_threshold_minutes is not None
    assert roc.uncertainty_interval_minutes is not None
    assert "min" in roc.uncertainty_interval_minutes


def test_baseline_oscillating_and_stable_trends():
    tracker = BaselineTracker()
    now = datetime.now(timezone.utc)

    # Oscillating: up, down, up, down
    vals = [50.0, 70.0, 50.0, 70.0, 50.0]
    for i, v in enumerate(vals):
        tracker.record_sample("network", "active_conns", v, now + timedelta(seconds=i * 10))

    trend = tracker.detect_trend("network", "active_conns")
    assert trend == TrendDirection.OSCILLATING

    # Stable: flat
    tracker2 = BaselineTracker()
    for i in range(5):
        tracker2.record_sample("cpu", "usage", 25.0, now + timedelta(seconds=i * 10))

    trend_stable = tracker2.detect_trend("cpu", "usage")
    assert trend_stable == TrendDirection.STABLE


# ==============================================================================
# 2. STATE MACHINE, HYSTERESIS & SIGNAL DEDUPLICATION
# ==============================================================================

def test_early_warning_state_machine_hysteresis():
    sm = SignalStateMachine(escalation_consecutive_required=1, deescalation_consecutive_required=3)

    # Immediate escalation to ELEVATED
    state, transitioned = sm.transition("native_runtime", EarlyWarningState.ELEVATED)
    assert state == EarlyWarningState.ELEVATED
    assert transitioned is True

    # Immediate escalation to HIGH
    state, transitioned = sm.transition("native_runtime", EarlyWarningState.HIGH)
    assert state == EarlyWarningState.HIGH

    # De-escalation requires 3 consecutive readings (anti-flapping)
    state, transitioned = sm.transition("native_runtime", EarlyWarningState.NORMAL)
    assert state == EarlyWarningState.HIGH  # Reading 1: Held at HIGH
    assert transitioned is False

    state, transitioned = sm.transition("native_runtime", EarlyWarningState.NORMAL)
    assert state == EarlyWarningState.HIGH  # Reading 2: Still held

    state, transitioned = sm.transition("native_runtime", EarlyWarningState.NORMAL)
    assert state == EarlyWarningState.NORMAL  # Reading 3: Recovered!
    assert transitioned is True


def test_signal_correlator_deduplication():
    correlator = SignalCorrelator(correlation_window_seconds=60.0)

    sig1 = ReliabilitySignal(
        signal_type=ReliabilitySignalType.RESOURCE_PRESSURE,
        component="native_runtime",
        current_value=85.0,
    )
    corr_id1, is_new1 = correlator.ingest_signal(sig1)
    assert is_new1 is True

    # Related signal on same component should reuse correlation_id
    sig2 = ReliabilitySignal(
        signal_type=ReliabilitySignalType.MEMORY_EXHAUSTION,
        component="native_runtime",
        current_value=92.0,
    )
    corr_id2, is_new2 = correlator.ingest_signal(sig2)
    assert is_new2 is False
    assert corr_id2 == corr_id1
    assert sig2.correlation_id == corr_id1


# ==============================================================================
# 3. FORECASTING, CAUSAL DRIVER & RISK PROPAGATION BRIDGES
# ==============================================================================

def test_forecasting_bridge_intervals_and_horizons():
    bridge = ForecastingBridge()
    tracker = BaselineTracker()
    now = datetime.now(timezone.utc)
    for i in range(4):
        tracker.record_sample("native_runtime", "memory_rss_mb", 70.0 + (i * 5.0), now + timedelta(minutes=i))
    roc = tracker.compute_rate_of_change("native_runtime", "memory_rss_mb", threshold_value=100.0)

    sig = ReliabilitySignal(
        signal_type=ReliabilitySignalType.MEMORY_EXHAUSTION,
        component="native_runtime",
        severity="P1",
        confidence=0.85,
        current_value=85.0,
    )

    fc = bridge.forecast_failure(sig, roc)
    assert fc.target_component == "native_runtime"
    assert fc.failure_probability >= 0.80
    assert fc.time_horizon in (ForecastHorizon.IMMEDIATE, ForecastHorizon.SHORT)
    assert fc.prevention_window_minutes is not None
    assert len(fc.evidence) >= 2


def test_causal_bridge_root_causes():
    bridge = CausalBridge()
    sig = ReliabilitySignal(
        signal_type=ReliabilitySignalType.CRASH_LOOP,
        component="native_runtime",
        current_value=3.0,
    )
    analysis = bridge.identify_causal_drivers(sig, "pinc_123")
    assert analysis.primary_trigger != ""
    assert analysis.mechanism != ""
    assert len(analysis.contributing_factors) >= 1
    assert analysis.causal_strength >= 0.80


def test_risk_bridge_downstream_impact():
    bridge = RiskBridge()
    sig = ReliabilitySignal(
        signal_type=ReliabilitySignalType.RESOURCE_PRESSURE,
        component="native_runtime",
        severity="P0",
    )
    impact = bridge.estimate_impact(sig)
    assert impact.blast_radius_score >= 0.70
    assert "sandbox" in impact.affected_components
    assert impact.operational_impact == "CRITICAL"


# ==============================================================================
# 4. SIMULATION, COUNTERFACTUAL COMPARISONS & MINIMUM INTERVENTION
# ==============================================================================

def test_simulation_bridge_mandatory_no_action_and_minimum_intervention():
    bridge = SimulationBridge()
    sig = ReliabilitySignal(
        signal_type=ReliabilitySignalType.MEMORY_EXHAUSTION,
        component="native_runtime",
        current_value=88.0,
    )
    impact = RiskBridge().estimate_impact(sig)
    fc = ForecastingBridge().forecast_failure(sig)

    candidates = bridge.generate_prevention_candidates(sig, impact)

    # 1. Verify mandatory NO_ACTION candidate is present
    no_action = next((c for c in candidates if c.is_no_action), None)
    assert no_action is not None
    assert no_action.action_type == PreventionActionType.NO_ACTION

    # 2. Run counterfactual comparison
    comparison = bridge.compare_and_select(candidates, fc, impact)
    assert comparison.selected_candidate is not None
    # Minimum intervention principle: prefers RELEASE_RESOURCE (rank 1) over heavy RESTART_COMPONENT (rank 3)
    assert comparison.selected_candidate.action_type in (
        PreventionActionType.RELEASE_RESOURCE,
        PreventionActionType.REDUCE_CONCURRENCY,
    )
    assert comparison.selected_candidate.reversibility == ReversibilityLevel.REVERSIBLE
    assert comparison.minimum_intervention_applied is True


# ==============================================================================
# 5. GOVERNANCE, APPROVAL & EMERGENCY STOP PRIMACY
# ==============================================================================

def test_governance_bridge_emergency_stop_primacy():
    gov = GovernanceBridge()
    e_stop = get_emergency_stop_service()
    cand = PreventionCandidate(
        action_type=PreventionActionType.RELEASE_RESOURCE,
        target_component="native_runtime",
    )

    # Active Emergency Stop must unconditionally block all prevention fail-closed
    e_stop.trigger_emergency_stop(reason="Drill active kill-switch test")
    try:
        authorized, requires_approval, reason = gov.evaluate_authorization(cand, AutonomyAdaptationLevel.FULL)
        assert authorized is False
        assert requires_approval is False
        assert "EMERGENCY_STOP_ACTIVE" in reason

        autonomy = gov.adapt_autonomy_level(EarlyWarningState.WATCH)
        assert autonomy == AutonomyAdaptationLevel.STOPPED
    finally:
        e_stop.reset_emergency_stop(is_human_user=True)


def test_governance_bridge_approval_requirements():
    gov = GovernanceBridge()

    # Low-risk action under FULL autonomy: authorized
    low_cand = PreventionCandidate(
        action_type=PreventionActionType.RELEASE_RESOURCE,
        target_component="native_runtime",
    )
    auth_low, app_low, _ = gov.evaluate_authorization(low_cand, AutonomyAdaptationLevel.FULL)
    assert auth_low is True
    assert app_low is False

    # Heavy mutating restart requires human approval
    heavy_cand = PreventionCandidate(
        action_type=PreventionActionType.RESTART_COMPONENT,
        target_component="native_runtime",
    )
    auth_heavy, app_heavy, _ = gov.evaluate_authorization(heavy_cand, AutonomyAdaptationLevel.FULL)
    assert auth_heavy is False
    assert app_heavy is True


# ==============================================================================
# 6. RESOURCE ECONOMY & ACTIVE WORK PROTECTION
# ==============================================================================

def test_economy_bridge_active_work_protection():
    econ = EconomyBridge()
    cand = PreventionCandidate(
        action_type=PreventionActionType.RELEASE_RESOURCE,
        target_component="native_runtime",
    )

    allocated, msg = econ.allocate_prevention_budget(cand)
    assert allocated is True
    assert "reserved" in msg.lower() or "budget" in msg.lower()

    # Release budget
    econ.release_prevention_budget(cand)


# ==============================================================================
# 7. CALIBRATION, SCORECARDS & REGRESSION DETECTION
# ==============================================================================

def test_calibration_manager_scorecards_and_degradation():
    calib = CalibrationManager()

    # Record successful executions for RELEASE_RESOURCE
    for _ in range(3):
        calib.record_strategy_execution(PreventionActionType.RELEASE_RESOURCE, success=True, duration_seconds=0.4)

    card = calib._scorecards[PreventionActionType.RELEASE_RESOURCE]
    assert card.total_attempts == 3
    assert card.verification_rate == 1.0
    assert card.health_status == "HEALTHY"

    # Record repeated failures for RECONNECT -> should trip DEGRADED (< 80% SLA)
    for _ in range(3):
        calib.record_strategy_execution(PreventionActionType.RECONNECT, success=False, duration_seconds=1.2)

    card_reconnect = calib._scorecards[PreventionActionType.RECONNECT]
    assert card_reconnect.total_attempts == 3
    assert card_reconnect.verification_rate == 0.0
    assert card_reconnect.health_status == "DEGRADED"

    # Check macro calibration metrics
    calib.record_calibration("pinc_1", "MEMORY_EXHAUSTION", False, "SHORT", 0.85, intervention_executed=True)
    calib.record_false_positive("pinc_2", ReliabilitySignalType.LATENCY_DEGRADATION, 0.70, {})
    calib.record_false_negative("fail_1", "network", "Socket timeout", root_cause_of_miss="MODEL_BLIND_SPOT")

    metrics = calib.get_calibration_metrics()
    assert metrics["false_positives_count"] == 1
    assert metrics["false_negatives_count"] == 1
    assert "RECONNECT" in metrics["degraded_strategies"]


# ==============================================================================
# 8. MASTER SERVICE END-TO-END PIPELINE DRILL
# ==============================================================================

@pytest.mark.asyncio
async def test_reliability_intelligence_service_e2e_prevention():
    svc = ReliabilityIntelligenceService()

    # Ingest rising telemetry to establish baseline and trigger warning
    for val in [50.0, 60.0, 75.0, 88.0]:
        sig = svc.ingest_telemetry_reading(
            component="native_runtime",
            metric_name="memory_rss_mb",
            current_value=val,
            threshold_value=100.0,
            signal_type=ReliabilitySignalType.MEMORY_EXHAUSTION,
            severity="P1",
        )

    assert sig is not None
    assert sig.state in (EarlyWarningState.ELEVATED, EarlyWarningState.HIGH, EarlyWarningState.CRITICAL)

    # Run the complete autonomous prevention pipeline
    incident = await svc.evaluate_and_prevent(sig)

    assert incident.incident_id.startswith("pinc_")
    assert incident.forecast is not None
    assert incident.causal_drivers is not None
    assert incident.predicted_impact is not None
    assert len(incident.candidates) >= 3
    assert incident.selected_prevention is not None
    assert incident.decision_explanation is not None
    assert incident.decision_explanation.problem != ""
    assert incident.decision_explanation.why != ""

    # Check verified status
    assert incident.status in (PreventionStatus.VERIFIED, PreventionStatus.AUTHORIZING)
    if incident.status == PreventionStatus.VERIFIED:
        assert incident.verification_passed is True
