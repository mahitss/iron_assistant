"""Tests for distributed tracing, span hierarchy, and context propagation (Task 38)."""

import asyncio
import pytest

from app.observability.correlation import (
    get_current_span_id,
    get_current_task_id,
    get_current_trace_id,
)
from app.observability.schemas import SpanStatus, TraceStatus
from app.observability.tracing import DistributedTracer, tracer


def test_root_trace_creation_and_context_propagation():
    """Test creating a root trace sets trace context and correlation IDs."""
    test_tracer = DistributedTracer()
    trace = test_tracer.start_trace(
        root_operation="investigate_ci",
        user_id="user_alice",
        task_id="task_123",
        project_id="proj_alpha",
    )

    assert trace.trace_id.startswith("trc_")
    assert trace.root_operation == "investigate_ci"
    assert trace.user_id == "user_alice"
    assert trace.status == TraceStatus.RUNNING
    assert get_current_trace_id() == trace.trace_id
    assert get_current_task_id() == "task_123"


def test_span_hierarchy_parent_child_relationships():
    """Test full command -> intent -> policy -> task -> agent -> tool hierarchy."""
    test_tracer = DistributedTracer()
    trace = test_tracer.start_trace(root_operation="COMMAND:investigate_ci", task_id="task_ci")

    with test_tracer.span("INTENT:parse_command", component="intent") as intent_span:
        with test_tracer.span("POLICY:evaluate_risk", component="policy") as policy_span:
            with test_tracer.span("TASK:execute_steps", component="task_engine") as task_span:
                with test_tracer.span("AGENT:ci_diagnostician", component="agent") as agent_span:
                    with test_tracer.span("TOOL:fetch_workflow_run", component="tool") as tool_span:
                        tool_span.set_attribute("target_repo", "mahitss/iron_assistant")
                        assert tool_span.parent_span_id == agent_span.span_id

    trace_schema = test_tracer.get_trace(trace.trace_id)
    assert trace_schema is not None
    assert len(trace_schema.spans) == 5

    spans_by_op = {s.operation: s for s in trace_schema.spans}
    assert spans_by_op["TOOL:fetch_workflow_run"].parent_span_id == spans_by_op["AGENT:ci_diagnostician"].span_id
    assert spans_by_op["AGENT:ci_diagnostician"].parent_span_id == spans_by_op["TASK:execute_steps"].span_id
    assert spans_by_op["TASK:execute_steps"].parent_span_id == spans_by_op["POLICY:evaluate_risk"].span_id
    assert spans_by_op["POLICY:evaluate_risk"].parent_span_id == spans_by_op["INTENT:parse_command"].span_id


@pytest.mark.asyncio
async def test_async_span_propagation_across_coroutines():
    """Test async context managers preserve trace context across coroutine switches."""
    test_tracer = DistributedTracer()
    trace = test_tracer.start_trace(root_operation="async_orchestration")

    async def sub_task(name: str):
        async with test_tracer.span_async(f"sub_task_{name}", component="worker") as span:
            await asyncio.sleep(0.01)
            span.set_attribute("worker_status", "done")

    await asyncio.gather(sub_task("A"), sub_task("B"))

    trace_schema = test_tracer.get_trace(trace.trace_id)
    assert trace_schema is not None
    assert len(trace_schema.spans) == 2
    for s in trace_schema.spans:
        assert s.status == SpanStatus.SUCCESS
        assert s.duration_ms is not None
        assert s.duration_ms >= 5.0


def test_span_error_recording_and_trace_status():
    """Test span errors trigger error events and mark parent trace as ERROR."""
    test_tracer = DistributedTracer()
    trace = test_tracer.start_trace(root_operation="failing_task")

    try:
        with test_tracer.span("risky_operation", component="tool") as span:
            raise RuntimeError("External dependency dropped connection")
    except RuntimeError:
        pass

    trace.finish()
    trace_schema = test_tracer.get_trace(trace.trace_id)
    assert trace_schema.status == TraceStatus.ERROR
    assert trace_schema.error_count == 1
    assert len(trace_schema.spans) == 1

    err_span = trace_schema.spans[0]
    assert err_span.status == SpanStatus.ERROR
    assert any(e.name == "error" for e in err_span.events)
