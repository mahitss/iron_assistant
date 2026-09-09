"""Tests for Change Detection, Significance Classification, Change Bursts, and Anomaly Detection (Task 46)."""

from datetime import datetime, timezone
import pytest

from app.perception.changes import (
    ChangeDetector,
    ChangeEvent,
    ChangeType,
)
from app.perception.events import EventType, PerceptionEvent
from app.perception.observations import Observation
from app.perception.significance import ChangeSignificance, SignificanceClassifier
from app.perception.situation import Anomaly, SituationalAwarenessManager
from app.perception.sources import PerceptionSource, SourceType


def utc_now():
    return datetime.now(timezone.utc)


def test_8_change_types():
    types = [
        "STATE_CHANGE", "CONFIG_CHANGE", "CODE_CHANGE", "HEALTH_CHANGE",
        "VERSION_CHANGE", "PERMISSION_CHANGE", "RESOURCE_CHANGE", "BEHAVIOR_CHANGE",
    ]
    for t in types:
        assert ChangeType(t) is not None


def test_change_detection_and_structural_diff():
    detector = ChangeDetector()
    source = PerceptionSource("src_1", SourceType.SERVICE, "Auth Service")

    # First observation establishes baseline
    obs1 = Observation.from_event(
        PerceptionEvent("e1", EventType.UPDATED, "src_1", "service:auth:health", payload={"status": "HEALTHY"}),
        source,
    )
    chg1 = detector.detect_change(obs1)
    assert chg1 is not None
    assert chg1.before is None
    assert chg1.after == {"status": "HEALTHY"}

    # Second identical observation detects NO change
    obs2 = Observation.from_event(
        PerceptionEvent("e2", EventType.UPDATED, "src_1", "service:auth:health", payload={"status": "HEALTHY"}),
        source,
    )
    chg2 = detector.detect_change(obs2)
    assert chg2 is None

    # Third mutated observation detects state change with before vs after diff (Spec 81)
    obs3 = Observation.from_event(
        PerceptionEvent("e3", EventType.HEALTH_CHANGED, "src_1", "service:auth:health", payload={"status": "DEGRADED"}),
        source,
    )
    chg3 = detector.detect_change(obs3)
    assert chg3 is not None
    assert chg3.before == {"status": "HEALTHY"}
    assert chg3.after == {"status": "DEGRADED"}
    assert chg3.change_type == ChangeType.HEALTH_CHANGE


def test_significance_rules_security_and_production():
    """Enforce Spec 84, 85: Security/permission changes and production changes receive elevated significance."""
    # Security change in development
    sig_sec = SignificanceClassifier.evaluate_significance(
        change_type_str="PERMISSION_CHANGE",
        subject="auth:roles",
        environment="DEVELOPMENT",
        before={"role": "user"},
        after={"role": "admin"},
        is_security_sensitive=True,
    )
    assert sig_sec in [ChangeSignificance.HIGH, ChangeSignificance.CRITICAL]

    # Change in production
    sig_prod = SignificanceClassifier.evaluate_significance(
        change_type_str="VERSION_CHANGE",
        subject="deployment:api",
        environment="PRODUCTION",
        before={"version": "1.0"},
        after={"version": "2.0"},
    )
    assert sig_prod in [ChangeSignificance.HIGH, ChangeSignificance.CRITICAL]

    # Trivial state change in test
    sig_triv = SignificanceClassifier.evaluate_significance(
        change_type_str="STATE_CHANGE",
        subject="test:runner",
        environment="TEST",
        before={"ping": 1},
        after={"ping": 2},
    )
    assert sig_triv in [ChangeSignificance.TRIVIAL, ChangeSignificance.LOW]


def test_change_burst_aggregation():
    """Enforce Spec 88: Correlate bursts (e.g. 100 file changes -> one logical change set)."""
    detector = ChangeDetector()
    changes = []
    for i in range(10):
        changes.append(
            ChangeEvent(
                change_id=f"chg_f_{i}",
                subject=f"file:backend/app/module_{i}.py",
                change_type=ChangeType.CODE_CHANGE,
                before=None,
                after={"size": 100 + i},
                source_id="src_fs",
                significance=ChangeSignificance.LOW,
            )
        )

    aggregated = detector.aggregate_change_bursts(changes)
    # 10 individual changes under 'file' prefix aggregated into 1 burst
    assert len(aggregated) == 1
    assert "burst_aggregate" in aggregated[0].subject
    assert aggregated[0].evidence["burst_count"] == 10


def test_anomaly_detection_and_planned_maintenance_suppression():
    """Enforce Spec 89-95: Anomaly is a signal, not confirmed incident.
    Planned maintenance suppresses false alarms.
    """
    sit_mgr = SituationalAwarenessManager()

    # Unplanned anomaly
    anom1 = sit_mgr.detect_anomaly(
        subject="service:redis",
        expected="HEALTHY",
        observed="UNHEALTHY",
        confidence=0.95,
    )
    assert anom1 is not None
    assert anom1.subject == "service:redis"
    assert anom1.is_suppressed_by_plan is False

    # Planned maintenance window registered (Spec 93, 94)
    sit_mgr.register_maintenance_window("service:database", "Scheduled OS upgrade")

    anom2 = sit_mgr.detect_anomaly(
        subject="service:database",
        expected="ONLINE",
        observed="OFFLINE",
        confidence=0.99,
    )
    assert anom2 is not None
    assert anom2.is_suppressed_by_plan is True
    assert anom2.evidence["maintenance_reason"] == "Scheduled OS upgrade"
