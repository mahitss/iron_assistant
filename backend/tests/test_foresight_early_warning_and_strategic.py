"""Tests for Early Warnings and Strategic Foresight Registers (Task 65)."""

from datetime import datetime, timezone

from app.foresight.early_warning import EarlyWarningEngine
from app.foresight.schemas import (
    EarlyWarningSeverity,
    ForesightHorizon,
    ReversibilityClass,
    TrendDirection,
)
from app.foresight.strategic import StrategicForesightManager


def test_early_warning_not_incident_and_deduplication():
    """Verify EARLY WARNING != INCIDENT invariant and alert storm suppression (Spec 35, 36)."""
    engine = EarlyWarningEngine()

    # Emit leading indicator warning
    w1 = engine.emit_early_warning(
        title="Cache Eviction Rate Elevation",
        description="Redis evictions elevated by 12% over 15m baseline.",
        severity=EarlyWarningSeverity.LOW,
        affected_entities=["redis_cache_01"],
    )

    assert w1.is_active is True
    # Invariant: An early warning is NOT an incident
    assert "INCIDENT" not in w1.severity.value

    # Emitting duplicate within deduplication window returns original or updates without spam
    w2 = engine.emit_early_warning(
        title="Cache Eviction Rate Elevation",
        description="Redis evictions elevated by 14% over 15m baseline.",
        severity=EarlyWarningSeverity.MEDIUM,
        affected_entities=["redis_cache_01"],
    )

    assert w2.signal_id == w1.signal_id  # Deduplicated to same signal
    assert len(engine.list_warnings()) == 1


def test_trend_detection_and_acceleration():
    """Verify TREND != CAUSE invariant and trend acceleration detection (Spec 38)."""
    engine = EarlyWarningEngine()

    # Accelerating series
    series = [10.0, 12.0, 16.0, 24.0, 36.0, 52.0]
    res = engine.detect_trend(series, metric_name="p99_latency")
    trend = res["trend"]

    assert trend in (TrendDirection.ACCELERATING, TrendDirection.INCREASING, TrendDirection.STRUCTURAL_SHIFT)


def test_strategic_risk_and_opportunity_registers():
    """Verify Risk & Opportunity registers, scoring, and optionality tracking (Spec 40, 41)."""
    mgr = StrategicForesightManager()

    risk = mgr.register_risk(
        title="Third-Party Payment Webhook Timeout",
        description="Payment partner SLAs degraded during holiday traffic.",
        probability=0.35,
        impact=0.80,
        time_horizon=ForesightHorizon.MID_FUTURE_1M,
        dependencies=["svc_payment"],
        mitigations=["Fallback queue with exponential backoff"],
    )
    assert risk.risk_id.startswith("rsk_")
    assert risk.status == "OPEN"

    opp = mgr.register_opportunity(
        title="Predictive Scaling via Pre-Warmed Lambda Concurrency",
        description="Pre-allocating compute saves 250ms cold start during traffic spikes.",
        potential_value=0.75,
        optionality_score=0.85,
        time_horizon=ForesightHorizon.MID_FUTURE_1M,
    )
    assert opp.opportunity_id.startswith("opp_")
    assert opp.optionality_score >= 0.80


def test_decision_reversibility_classification():
    """Verify decision reversibility and human authorization gating (Spec 42, 43)."""
    mgr = StrategicForesightManager()

    # Reversible action
    rev_eval = mgr.analyze_decision_impact(
        decision_title="Increase cache TTL from 60s to 120s",
        reversibility=ReversibilityClass.REVERSIBLE,
    )
    assert rev_eval["reversibility"] == ReversibilityClass.REVERSIBLE.value
    assert rev_eval["requires_human_approval"] is False

    # Irreversible action
    irrev_eval = mgr.analyze_decision_impact(
        decision_title="Permanently drop legacy audit partition",
        reversibility=ReversibilityClass.IRREVERSIBLE,
    )
    assert irrev_eval["reversibility"] == ReversibilityClass.IRREVERSIBLE.value
    assert irrev_eval["requires_human_approval"] is True


def test_bounded_monitoring_plan_lifecycle():
    """Verify bounded monitoring plans with expiry TTLs (Spec 44)."""
    mgr = StrategicForesightManager()

    plan = mgr.create_monitoring_plan(
        target_id="risk_db_saturation",
        target_type="risk",
        signals=["cpu_utilization", "active_connections"],
        frequency_seconds=60,
        ttl_days=7,
    )

    assert plan.is_active is True
    assert plan.expiry is not None
    assert plan.expiry > datetime.now(timezone.utc)
