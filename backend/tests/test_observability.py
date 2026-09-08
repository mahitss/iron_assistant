"""Tests for structured JSON logging, Prometheus metrics, and distributed tracing."""

import json
import logging

from app.observability.logging import StructuredJsonFormatter
from app.observability.metrics import MetricsCollector
from app.observability.tracing import trace_span


def test_structured_json_formatter_masks_secrets():
    """StructuredJsonFormatter produces valid JSON and redacts sensitive tokens."""
    formatter = StructuredJsonFormatter()

    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Authenticated with token sk-or-v1-abcdef1234567890123456 and Bearer eyJhbGciOiJIUzI1NiJ9.test",
        args=(),
        exc_info=None,
    )
    record.request_id = "req_test_123"
    record.user_id = "user_alice"
    record.duration_ms = 42.5

    output = formatter.format(record)
    data = json.loads(output)

    assert data["level"] == "INFO"
    assert data["request_id"] == "req_test_123"
    assert data["user_id"] == "user_alice"
    assert data["duration_ms"] == 42.5
    # Secrets must be redacted
    assert "sk-or-v1-" not in data["message"]
    assert "[REDACTED_SECRET]" in data["message"]


def test_metrics_collector_and_prometheus_output():
    """MetricsCollector increments counters, measures latencies, and renders Prometheus text."""
    collector = MetricsCollector()
    collector.clear()

    collector.inc_counter("http_requests_total", value=1, labels={"method": "GET", "status": "200"})
    collector.inc_counter("http_requests_total", value=2, labels={"method": "GET", "status": "200"})
    collector.record_latency(
        "http_request_duration_seconds", duration_seconds=0.045, labels={"path": "/chat"}
    )

    prom_text = collector.generate_prometheus_text()

    assert 'http_requests_total{method="GET",status="200"} 3.0' in prom_text
    assert 'http_request_duration_seconds_count{path="/chat"} 1' in prom_text
    assert 'http_request_duration_seconds_sum{path="/chat"} 0.0450' in prom_text


def test_trace_span_measures_duration_and_redacts_attributes():
    """trace_span records execution duration, trace ID, and scrubs secrets from attributes."""
    with trace_span(
        "test_operation",
        attributes={"query": "hello", "api_key": "sk-123456789012345678"},
    ) as span:
        assert span.name == "test_operation"
        assert span.trace_id.startswith("trc_")
        assert span.status == "RUNNING"
        # Secret in attributes must be redacted
        assert span.attributes["api_key"] != "sk-123456789012345678"

    assert span.status == "OK"
    assert span.duration_ms is not None
    assert span.duration_ms >= 0
