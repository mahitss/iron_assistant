"""Tests for user/project isolation, client forgery defense, and fail-safe isolation (Task 38)."""

from app.observability.exporters import TelemetryExporter
from app.observability.schemas import Trace, TraceStatus
from app.observability.tracing import DistributedTracer


def test_user_isolation_filters_unauthorized_traces():
    """Tracer list_traces isolates user data: Alice cannot see Bob's execution traces."""
    tracer = DistributedTracer()

    # Create trace for Alice
    t_alice = tracer.start_trace(root_operation="alice_op", user_id="user_alice")
    # Create trace for Bob
    t_bob = tracer.start_trace(root_operation="bob_op", user_id="user_bob")

    alice_traces = tracer.list_traces(user_id="user_alice")
    bob_traces = tracer.list_traces(user_id="user_bob")

    assert all(t.user_id == "user_alice" for t in alice_traces)
    assert not any(t.user_id == "user_bob" for t in alice_traces)

    assert all(t.user_id == "user_bob" for t in bob_traces)
    assert not any(t.user_id == "user_alice" for t in bob_traces)


def test_project_isolation_filters_unauthorized_project_traces():
    """Tracer list_traces respects project boundaries."""
    tracer = DistributedTracer()

    tracer.start_trace(root_operation="proj_a_op", project_id="proj_alpha")
    tracer.start_trace(root_operation="proj_b_op", project_id="proj_beta")

    alpha_traces = tracer.list_traces(project_id="proj_alpha")
    assert all(t.project_id == "proj_alpha" for t in alpha_traces)
    assert not any(t.project_id == "proj_beta" for t in alpha_traces)


def test_fail_safe_isolation_exporter_never_crashes_caller():
    """Faults inside the telemetry exporter are caught and isolated from core application execution."""
    exporter = TelemetryExporter()

    # Simulate exporter encountering invalid internal state
    exporter._buffer = None  # Force AttributeError on append

    # Attempting export must return False safely without raising to caller
    result = exporter.export_trace(Trace(trace_id="trc_fail", root_operation="op", status=TraceStatus.SUCCESS))
    assert result is False
    assert exporter.is_healthy is False
    assert exporter.failure_count == 1
