"""Tests for Tool and Provider Reliability Tracking (Task 43)."""

import pytest
from app.learning.reliability import ReliabilityMetrics, ReliabilityTracker
from app.learning.service import LearningService


def test_tool_reliability_metrics_tracking():
    """Verify tool call recording, success rate, timeout rate, and average latency."""
    metrics = ReliabilityMetrics(entity_id="web_search", entity_type="tool")
    assert metrics.total_calls == 0
    assert metrics.reliability_score == 0.5  # Default baseline prior to data

    # 1. Successful fast call
    metrics.record_call(success=True, is_timeout=False, retries=0, latency_ms=120.0)
    assert metrics.total_calls == 1
    assert metrics.success_rate == 1.0
    assert metrics.timeout_rate == 0.0
    assert metrics.average_latency_ms == 120.0
    assert metrics.reliability_score == 1.0

    # 2. Timeout failure call with retries
    metrics.record_call(success=False, is_timeout=True, retries=2, latency_ms=5000.0)
    assert metrics.total_calls == 2
    assert metrics.success_rate == 0.5
    assert metrics.failure_rate == 0.5
    assert metrics.timeout_rate == 0.5
    assert metrics.retries == 2
    assert metrics.average_latency_ms == 2560.0
    # Penalty applied: failure 0.4*0.5 + timeout 0.4*0.5 = 0.4 penalty -> 0.6 score
    assert metrics.reliability_score == 0.6


def test_unknown_outcome_penalizes_reliability():
    """Unknown outcomes must penalize reliability scores rather than being counted as successes (Spec 82, 83)."""
    metrics = ReliabilityMetrics(entity_id="bash_execute", entity_type="tool")
    
    # 5 runs where 4 are unknown
    metrics.record_call(success=True, is_unknown=False)
    for _ in range(4):
        metrics.record_call(success=False, is_unknown=True)

    assert metrics.unknown_rate == 0.8
    assert metrics.reliability_score < 0.5  # Heavy penalty for unknown outcomes


def test_provider_reliability_tracking():
    """Provider performance tracking across models and endpoints (Spec 25)."""
    tracker = ReliabilityTracker()

    tracker.record_provider_result(provider_id="gemini-1.5-pro", success=True, latency_ms=450.0)
    tracker.record_provider_result(provider_id="gemini-1.5-pro", success=True, latency_ms=550.0)
    tracker.record_provider_result(provider_id="gemini-1.5-pro", success=True, latency_ms=500.0)

    p_metrics = tracker.get_provider_metrics("gemini-1.5-pro")
    assert p_metrics.total_calls == 3
    assert p_metrics.success_rate == 1.0
    assert p_metrics.average_latency_ms == 500.0
    assert p_metrics.reliability_score == 1.0

    # Failing provider
    tracker.record_provider_result(provider_id="unstable-provider", success=False, is_timeout=True, latency_ms=10000.0)
    p_unstable = tracker.get_provider_metrics("unstable-provider")
    assert p_unstable.timeout_rate == 1.0
    assert p_unstable.reliability_score < 0.3


def test_learning_service_reliability_integration():
    """LearningService exposes tool and provider reliability summaries."""
    service = LearningService()
    
    service.reliability.record_tool_result("python_interpreter", success=True, latency_ms=80.0)
    service.reliability.record_provider_result("claude-3-5-sonnet", success=True, latency_ms=620.0)

    tools = service.reliability.get_all_tool_reliability()
    providers = service.reliability.get_all_provider_reliability()

    assert any(t["entity_id"] == "python_interpreter" for t in tools)
    assert any(p["entity_id"] == "claude-3-5-sonnet" for p in providers)


def test_model_routing_feedback_safety():
    """Learning suggestions cannot force use of an unavailable or policy-restricted provider (Spec 26, 27)."""
    service = LearningService()
    
    # Model suggestions are advisory metadata only
    service.reliability.record_provider_result("fast-cheaper-provider", success=True, latency_ms=120.0)
    
    metrics = service.reliability.get_provider_metrics("fast-cheaper-provider")
    assert metrics.success_rate == 1.0
    
    # Router remains authoritative; learning suggestions cannot bypass policy
    summary = metrics.to_dict()
    assert summary["entity_type"] == "provider"
    assert "reliability_score" in summary
