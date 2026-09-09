"""Tests for Failure Pattern Clustering, Pre-Flight Warnings, and Recovery Learning (Task 43)."""

import pytest
from app.learning.failures import FailureManager, PreFlightWarning
from app.learning.patterns import FailurePattern, PatternClusterer
from app.learning.recovery import RecoveryLearner


def test_pattern_clusterer_normalization():
    """PatternClusterer normalizes UUIDs, IPs, and timestamps into deterministic signatures (Spec 35)."""
    raw_1 = "Connection timeout to 192.168.1.55 on node 4b8d76e2-1234-4567-890a-bcde12345678"
    raw_2 = "Connection timeout to 10.0.0.12 on node 99aa88bb-4321-7654-a098-123456789abc"

    sig_1 = PatternClusterer.extract_signature(raw_1)
    sig_2 = PatternClusterer.extract_signature(raw_2)

    assert sig_1 == sig_2
    assert "<ip>" in sig_1
    assert "<uuid>" in sig_1
    assert "connection timeout to <ip> on node <uuid>" == sig_1


def test_failure_pattern_occurrence_and_confidence():
    """FailurePattern increments frequency and upgrades confidence tier with frequency (Spec 34, 38)."""
    pat = FailurePattern(
        domain="github",
        signature="rate limit exceeded for github api",
        mitigation="Switch to secondary PAT or wait for quota reset",
    )
    assert pat.frequency == 1
    assert pat.confidence == "MEDIUM"

    # Add occurrences
    for i in range(4):
        pat.record_occurrence(component=f"worker-{i}", evidence_item={"status": 403})

    assert pat.frequency == 5
    assert pat.confidence == "HIGH"
    assert len(pat.affected_components) == 4
    d = pat.to_dict()
    assert d["confidence"] == "HIGH"
    assert d["frequency"] == 5


def test_failure_clustering_collapses_similar_errors():
    """FailureManager clusters 10 API timeouts into 1 dependency degradation pattern (Spec 35)."""
    mgr = FailureManager()

    for i in range(10):
        mgr.record_failure(
            domain="billing",
            error_message=f"HTTP 504 Gateway Timeout from payment gateway 192.168.0.{i} on request 1000{i}",
            component="payment_client",
            mitigation="Enable circuit breaker and use idempotency token retry.",
        )

    patterns = mgr.list_patterns(domain="billing")
    assert len(patterns) == 1
    assert patterns[0].frequency == 10
    assert "http 504 gateway timeout from payment gateway <ip>" in patterns[0].signature


def test_pre_flight_warning_generation_and_threshold():
    """Pre-flight warning surfaces only when evidence supports it (frequency >= 3) (Spec 71)."""
    mgr = FailureManager()

    # With only 1 failure, no warning should be triggered
    mgr.record_failure(
        domain="deploy",
        error_message="docker daemon socket permission denied",
        component="runner",
    )
    warn_none = mgr.check_pre_flight(workflow_name="docker", domain="deploy")
    assert warn_none is None

    # Record 2 more failures to reach threshold of 3
    mgr.record_failure(domain="deploy", error_message="docker daemon socket permission denied")
    mgr.record_failure(domain="deploy", error_message="docker daemon socket permission denied")

    warn = mgr.check_pre_flight(workflow_name="docker", domain="deploy")
    assert warn is not None
    assert isinstance(warn, PreFlightWarning)
    assert warn.frequency == 3
    assert "Kairo has seen this workflow fail" in warn.message
    assert "docker daemon socket permission denied" in warn.pattern_signature


def test_pre_flight_predictive_safety_non_blocking():
    """Prediction cannot block legitimate execution unless policy or risk rules mandate it (Spec 72)."""
    mgr = FailureManager()
    for _ in range(5):
        mgr.record_failure(
            domain="database",
            error_message="lock wait timeout exceeded on orders table",
            mitigation="Reduce transaction duration and retry with backoff",
        )

    warn = mgr.check_pre_flight(workflow_name="orders", domain="database")
    assert warn is not None
    # Must be advisory / non-blocking by default
    assert warn.is_blocking is False


def test_recovery_learner_remediation_recommendation():
    """RecoveryLearner tracks which recovery actions succeed and recommends the optimal one (Spec 80, 81)."""
    learner = RecoveryLearner()
    sig = "redis connection refused"

    # Action A: restart container - 1 success out of 4 attempts (25%)
    for _ in range(3):
        learner.record_recovery(sig, recovery_action="restart_container", succeeded=False)
    learner.record_recovery(sig, recovery_action="restart_container", succeeded=True)

    # Action B: flush stale dns and reconnect - 3 successes out of 3 attempts (100%)
    for _ in range(3):
        learner.record_recovery(sig, recovery_action="flush_dns_and_reconnect", succeeded=True, is_safe_for_auto_retry=True)

    best = learner.recommend_recovery(sig)
    assert best is not None
    assert best.recovery_action == "flush_dns_and_reconnect"
    assert best.success_rate == 1.0
    assert best.is_safe_for_auto_retry is True
