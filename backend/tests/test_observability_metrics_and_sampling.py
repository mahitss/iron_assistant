"""Tests for metrics cardinality defense, sampling, and backpressure (Task 38)."""

from app.observability.exporters import TelemetryExporter
from app.observability.metrics import MetricsCollector
from app.observability.sampling import TraceSampler
from app.observability.schemas import (
    Span,
    SpanStatus,
    Trace,
    TraceStatus,
)


def test_metrics_collector_counters_gauges_and_latencies():
    """MetricsCollector tracks counters, gauges, and latency summaries."""
    collector = MetricsCollector()
    collector.clear()

    collector.inc_counter("requests_total", 1.0, labels={"endpoint": "/chat"})
    collector.inc_counter("requests_total", 3.0, labels={"endpoint": "/chat"})
    collector.set_gauge("active_tasks_gauge", 7.0)
    collector.record_latency("tool_duration_seconds", 0.125, labels={"tool": "web_search"})

    prom = collector.generate_prometheus_text()
    assert 'requests_total{endpoint="/chat"} 4.0' in prom
    assert "active_tasks_gauge 7.0" in prom
    assert 'tool_duration_seconds_count{tool="web_search"} 1' in prom
    assert 'tool_duration_seconds_sum{tool="web_search"} 0.1250' in prom


def test_cardinality_defense_bounds_label_explosion():
    """Metrics collector truncates labels and falls back to overflow bucket to prevent memory leak."""
    collector = MetricsCollector(max_cardinality=5)
    collector.clear()

    # Generate 20 distinct label combinations (exceeding limit of 5)
    for i in range(20):
        collector.inc_counter("dynamic_events_total", 1.0, labels={"user_id": f"unique_user_{i}"})

    prom = collector.generate_prometheus_text()
    # Overflow bucket must be present
    assert 'overflow="true"' in prom


def test_trace_sampler_prioritizes_errors_and_security_events():
    """TraceSampler always retains errors and security events, but probabilistically samples routine successes."""
    sampler = TraceSampler(default_sample_rate=0.0)  # zero rate for routine traces

    # 1. Routine success trace with no errors
    routine_trace = Trace(
        trace_id="trc_routine",
        root_operation="routine_check",
        status=TraceStatus.SUCCESS,
        error_count=0,
    )
    assert sampler.should_sample(routine_trace) is False

    # 2. Trace with error status
    error_trace = Trace(
        trace_id="trc_error",
        root_operation="failing_task",
        status=TraceStatus.ERROR,
        error_count=1,
    )
    assert sampler.should_sample(error_trace) is True

    # 3. Trace with security event tag in metadata
    security_trace = Trace(
        trace_id="trc_security",
        root_operation="admin_grant",
        status=TraceStatus.SUCCESS,
        metadata={"is_security_event": True},
    )
    assert sampler.should_sample(security_trace) is True


def test_telemetry_exporter_backpressure_and_fail_safe_isolation():
    """Exporter sheds non-error traces when buffer is full and never crashes on internal errors."""
    exporter = TelemetryExporter(max_buffer_size=3)

    # Add 3 routine traces
    t1 = Trace(trace_id="trc_1", root_operation="op1", status=TraceStatus.SUCCESS)
    t2 = Trace(trace_id="trc_2", root_operation="op2", status=TraceStatus.SUCCESS)
    t3 = Trace(trace_id="trc_3", root_operation="op3", status=TraceStatus.SUCCESS)
    exporter.export_trace(t1)
    exporter.export_trace(t2)
    exporter.export_trace(t3)

    # 4th trace arrives (an error trace)
    t_err = Trace(trace_id="trc_err", root_operation="op_err", status=TraceStatus.ERROR, error_count=1)
    success = exporter.export_trace(t_err)

    assert success is True
    assert exporter.dropped_count == 1
    # Error trace must be preserved in buffer
    buffered = exporter.get_buffered_traces()
    assert any(t.trace_id == "trc_err" for t in buffered)
    assert len(buffered) == 3
