"""Distributed tracing engine, span hierarchy, and context propagation (Task 38)."""

import time
import uuid
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager
from datetime import UTC, datetime
from typing import Any

from app.observability.correlation import (
    get_current_span_id,
    get_current_trace_id,
    set_correlation_context,
)
from app.observability.sanitization import TelemetrySanitizer
from app.observability.schemas import (
    Span as SpanSchema,
    SpanStatus,
    Trace as TraceSchema,
    TraceStatus,
)
from app.observability.spans import ActiveSpan


class ActiveTrace:
    """Manages an active trace execution tree."""

    def __init__(
        self,
        trace_id: str,
        root_operation: str,
        user_id: str | None = None,
        session_id: str | None = None,
        task_id: str | None = None,
        project_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.trace_id = trace_id
        self.root_operation = root_operation
        self.user_id = user_id
        self.session_id = session_id
        self.task_id = task_id
        self.project_id = project_id
        self.started_at = datetime.now(UTC)
        self.completed_at: datetime | None = None
        self._start_perf = time.perf_counter()
        self.duration_ms: float | None = None
        self.status = TraceStatus.RUNNING
        self.error_count: int = 0
        self.spans: list[ActiveSpan] = []
        self.metadata: dict[str, Any] = TelemetrySanitizer.sanitize_dict(metadata or {})

    def add_span(self, span: ActiveSpan) -> None:
        self.spans.append(span)
        if span.status == SpanStatus.ERROR:
            self.error_count += 1

    def finish(self, status: TraceStatus = TraceStatus.SUCCESS) -> None:
        self.completed_at = datetime.now(UTC)
        self.duration_ms = (time.perf_counter() - self._start_perf) * 1000.0
        self.status = status if self.error_count == 0 else TraceStatus.ERROR

    def to_schema(self) -> TraceSchema:
        return TraceSchema(
            trace_id=self.trace_id,
            root_operation=self.root_operation,
            user_id=self.user_id,
            session_id=self.session_id,
            task_id=self.task_id,
            project_id=self.project_id,
            started_at=self.started_at,
            completed_at=self.completed_at,
            duration_ms=self.duration_ms,
            status=self.status,
            error_count=self.error_count,
            spans=[s.to_schema() for s in self.spans],
            metadata=self.metadata,
        )


class DistributedTracer:
    """Singleton engine for distributed tracing across Kairo subsystems."""

    def __init__(self, max_retained_traces: int = 2000) -> None:
        self.max_retained_traces = max_retained_traces
        self._traces: dict[str, ActiveTrace] = {}
        self._task_trace_map: dict[str, str] = {}  # task_id -> trace_id

    def start_trace(
        self,
        root_operation: str,
        user_id: str | None = None,
        session_id: str | None = None,
        task_id: str | None = None,
        project_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ActiveTrace:
        """Starts a new root trace and sets the active correlation context."""
        trace_id = f"trc_{uuid.uuid4().hex[:16]}"
        trace = ActiveTrace(
            trace_id=trace_id,
            root_operation=root_operation,
            user_id=user_id,
            session_id=session_id,
            task_id=task_id,
            project_id=project_id,
            metadata=metadata,
        )
        self._traces[trace_id] = trace
        if task_id:
            self._task_trace_map[task_id] = trace_id

        # Maintain bounded in-memory buffer
        if len(self._traces) > self.max_retained_traces:
            oldest_key = next(iter(self._traces))
            del self._traces[oldest_key]

        set_correlation_context(
            trace_id=trace_id,
            task_id=task_id,
            user_id=user_id,
            project_id=project_id,
            session_id=session_id,
        )
        return trace

    @contextmanager
    def span(
        self,
        operation: str,
        component: str = "core",
        attributes: dict[str, Any] | None = None,
        parent_span_id: str | None = None,
    ) -> Generator[ActiveSpan, None, None]:
        """Synchronous context manager creating a child span under the active trace."""
        trace_id = get_current_trace_id()
        if not trace_id or trace_id not in self._traces:
            # Auto-create root trace if none active
            auto_trace = self.start_trace(root_operation=operation)
            trace_id = auto_trace.trace_id

        parent_id = parent_span_id or get_current_span_id()
        active_span = ActiveSpan(
            operation=operation,
            component=component,
            trace_id=trace_id,
            parent_span_id=parent_id,
            attributes=attributes,
        )
        set_correlation_context(span_id=active_span.span_id)

        try:
            yield active_span
            if active_span.status == SpanStatus.RUNNING:
                active_span.finish(status=SpanStatus.SUCCESS)
        except Exception as exc:
            active_span.record_error(exc)
            active_span.finish(status=SpanStatus.ERROR)
            raise
        finally:
            if trace_id in self._traces:
                self._traces[trace_id].add_span(active_span)
            set_correlation_context(span_id=parent_id)

    @asynccontextmanager
    async def span_async(
        self,
        operation: str,
        component: str = "core",
        attributes: dict[str, Any] | None = None,
        parent_span_id: str | None = None,
    ) -> AsyncGenerator[ActiveSpan, None]:
        """Asynchronous context manager creating a child span under the active trace."""
        trace_id = get_current_trace_id()
        if not trace_id or trace_id not in self._traces:
            auto_trace = self.start_trace(root_operation=operation)
            trace_id = auto_trace.trace_id

        parent_id = parent_span_id or get_current_span_id()
        active_span = ActiveSpan(
            operation=operation,
            component=component,
            trace_id=trace_id,
            parent_span_id=parent_id,
            attributes=attributes,
        )
        set_correlation_context(span_id=active_span.span_id)

        try:
            yield active_span
            if active_span.status == SpanStatus.RUNNING:
                active_span.finish(status=SpanStatus.SUCCESS)
        except Exception as exc:
            active_span.record_error(exc)
            active_span.finish(status=SpanStatus.ERROR)
            raise
        finally:
            if trace_id in self._traces:
                self._traces[trace_id].add_span(active_span)
            set_correlation_context(span_id=parent_id)

    def get_trace(self, trace_id: str) -> TraceSchema | None:
        trace = self._traces.get(trace_id)
        return trace.to_schema() if trace else None

    def get_task_trace(self, task_id: str) -> TraceSchema | None:
        trace_id = self._task_trace_map.get(task_id)
        return self.get_trace(trace_id) if trace_id else None

    def list_traces(
        self,
        user_id: str | None = None,
        project_id: str | None = None,
        limit: int = 50,
    ) -> list[TraceSchema]:
        """Lists traces respecting user and project isolation."""
        results: list[TraceSchema] = []
        for trace in reversed(list(self._traces.values())):
            # Enforce user and project isolation
            if user_id and trace.user_id and trace.user_id != user_id:
                continue
            if project_id and trace.project_id and trace.project_id != project_id:
                continue
            results.append(trace.to_schema())
            if len(results) >= limit:
                break
        return results


# Global singleton tracer
tracer = DistributedTracer()


# ============================================================================
# Backward Compatibility Layer for existing code & tests
# ============================================================================


class Span:
    """Backward compatibility wrapper preserving existing Span interface."""

    def __init__(
        self, name: str, trace_id: str | None = None, attributes: dict[str, Any] | None = None
    ) -> None:
        self.name = name
        self.trace_id = trace_id or f"trc_{uuid.uuid4().hex[:16]}"
        self.attributes = TelemetrySanitizer.sanitize_dict(attributes or {})
        self.start_time: float = time.time()
        self.end_time: float | None = None
        self.duration_ms: float | None = None
        self.status: str = "RUNNING"
        self.error: str | None = None

    def finish(self, status: str = "OK", error: str | None = None) -> None:
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000.0
        self.status = status
        self.error = TelemetrySanitizer.sanitize_text(error) if error else None


@contextmanager
def trace_span(name: str, attributes: dict[str, Any] | None = None) -> Generator[Span, None, None]:
    """Backward compatibility helper preserving existing trace_span contextmanager."""
    span = Span(name=name, attributes=attributes)
    try:
        yield span
        span.finish(status="OK")
    except Exception as exc:
        span.finish(status="ERROR", error=str(exc))
        raise
