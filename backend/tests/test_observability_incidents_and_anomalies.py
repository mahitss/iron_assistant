"""Tests for anomaly detection, incident correlation, and evidence-backed resolution (Task 38)."""

import pytest

from app.observability.anomalies import AnomalyDetector
from app.observability.incidents import IncidentManager
from app.observability.schemas import (
    IncidentSeverity,
    IncidentStatus,
)


def test_anomaly_detector_identifies_latency_and_error_spikes():
    """AnomalyDetector compares metrics against baseline thresholds."""
    detector = AnomalyDetector()

    # Normal latency (40ms vs 45ms baseline) -> None
    assert detector.evaluate_latency("api", 40.0) is None

    # Anomaly latency spike (350ms vs 45ms baseline, >7x) -> AnomalyReport
    spike_report = detector.evaluate_latency("api", 350.0)
    assert spike_report is not None
    assert spike_report.metric_name == "latency_ms"
    assert spike_report.component == "api"
    assert spike_report.deviation_factor >= 2.5
    assert "spiked" in spike_report.evidence

    # Error rate surge (20% vs 1% baseline) -> AnomalyReport
    err_report = detector.evaluate_error_rate("api", 0.20)
    assert err_report is not None
    assert err_report.metric_name == "error_rate"
    assert err_report.severity == IncidentSeverity.HIGH


def test_incident_grouping_aggregates_multiple_failures():
    """IncidentManager correlates multiple failures on the same component into a single incident."""
    mgr = IncidentManager()

    # 1. First failure creates the incident
    inc1 = mgr.report_failure(
        component="github",
        title="GitHub API Connectivity Failure",
        evidence={"status_code": 503, "detail": "Service Unavailable"},
        severity=IncidentSeverity.HIGH,
    )
    assert inc1.status == IncidentStatus.OPEN
    assert len(inc1.evidence) == 1

    # 2. Second failure on the same component is grouped
    inc2 = mgr.report_failure(
        component="github",
        title="GitHub Secondary Timeout",
        evidence={"status_code": 504, "detail": "Gateway Timeout"},
        severity=IncidentSeverity.CRITICAL,
    )
    assert inc1.id == inc2.id  # Same correlated incident!
    assert len(inc2.evidence) == 2
    assert inc2.severity == IncidentSeverity.CRITICAL  # Escalated to higher severity


def test_incident_acknowledgment_and_evidence_backed_resolution():
    """Incident resolution requires verifiable evidence of recovery."""
    mgr = IncidentManager()
    inc = mgr.report_failure(
        component="database",
        title="Database Connection Pool Exhaustion",
        evidence={"pool_size": 20, "waiting_threads": 45},
    )

    # 1. Acknowledge
    acked = mgr.acknowledge_incident(inc.id, acknowledged_by="operator_bob")
    assert acked.status == IncidentStatus.ACKNOWLEDGED
    assert acked.acknowledged_by == "operator_bob"

    # 2. Rejection of blank evidence
    with pytest.raises(ValueError, match="verifiable evidence"):
        mgr.resolve_incident(inc.id, recovery_evidence="   ")

    # 3. Successful resolution with evidence
    resolved = mgr.resolve_incident(
        inc.id,
        recovery_evidence="Database connection pool expanded to 100 connections. Active pool usage dropped to 12%. SELECT 1 probe latency 2.1ms.",
    )
    assert resolved.status == IncidentStatus.RESOLVED
    assert resolved.resolved_at is not None
    assert any(e.get("event") == "resolution_verification" for e in resolved.evidence)
