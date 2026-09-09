"""Span execution unit, lifecycle management, and event recording (Task 38)."""

import time
import uuid
from datetime import UTC, datetime
from typing import Any

from app.observability.sanitization import TelemetrySanitizer
from app.observability.schemas import (
    ErrorEvent,
    Span as SpanSchema,
    SpanEvent,
    SpanStatus,
)


class ActiveSpan:
    """Represents an actively running or finished execution span."""

    def __init__(
        self,
        operation: str,
        component: str,
        trace_id: str,
        parent_span_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        self.span_id: str = f"spn_{uuid.uuid4().hex[:16]}"
        self.trace_id: str = trace_id
        self.parent_span_id: str | None = parent_span_id
        self.operation: str = operation
        self.component: str = component
        self.started_at: datetime = datetime.now(UTC)
        self.completed_at: datetime | None = None
        self._start_perf: float = time.perf_counter()
        self.duration_ms: float | None = None
        self.status: SpanStatus = SpanStatus.RUNNING
        self.error_code: str | None = None
        self.attributes: dict[str, Any] = TelemetrySanitizer.sanitize_dict(attributes or {})
        self.events: list[SpanEvent] = []

    def set_attribute(self, key: str, value: Any) -> None:
        """Sets a sanitized attribute on the active span."""
        if isinstance(value, dict):
            self.attributes[key] = TelemetrySanitizer.sanitize_dict(value)
        elif isinstance(value, str):
            self.attributes[key] = TelemetrySanitizer.sanitize_text(value)
        else:
            self.attributes[key] = value

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        """Records an event milestone during the span execution."""
        event = SpanEvent(
            name=name,
            timestamp=datetime.now(UTC),
            attributes=TelemetrySanitizer.sanitize_dict(attributes or {}),
        )
        self.events.append(event)

    def record_error(
        self,
        error: Exception | str,
        error_code: str = "ERROR",
        error_category: str = "EXECUTION",
        retryable: bool = False,
        attempt: int = 1,
        dependency: str | None = None,
    ) -> None:
        """Records a structured error event on the span without secrets."""
        msg = str(error) if isinstance(error, Exception) else str(error)
        clean_msg = TelemetrySanitizer.sanitize_text(msg)
        self.error_code = error_code
        self.status = SpanStatus.ERROR

        err_evt = ErrorEvent(
            error_code=error_code,
            error_category=error_category,
            message=clean_msg,
            retryable=retryable,
            attempt=attempt,
            dependency=dependency,
            timestamp=datetime.now(UTC),
        )
        self.add_event(name="error", attributes=err_evt.model_dump())

    def finish(self, status: SpanStatus = SpanStatus.SUCCESS, error_code: str | None = None) -> None:
        """Marks the span completed and records authoritative duration."""
        self.completed_at = datetime.now(UTC)
        self.duration_ms = (time.perf_counter() - self._start_perf) * 1000.0
        self.status = status
        if error_code:
            self.error_code = error_code

    def to_schema(self) -> SpanSchema:
        """Converts internal span representation to immutable Pydantic schema."""
        return SpanSchema(
            span_id=self.span_id,
            trace_id=self.trace_id,
            parent_span_id=self.parent_span_id,
            operation=self.operation,
            component=self.component,
            started_at=self.started_at,
            completed_at=self.completed_at,
            duration_ms=self.duration_ms,
            status=self.status,
            error_code=self.error_code,
            attributes=self.attributes,
            events=self.events,
        )
