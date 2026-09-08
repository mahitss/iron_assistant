"""Lightweight distributed tracing abstraction with secret sanitization."""

import time
import uuid
from contextlib import contextmanager
from typing import Any, Generator

from app.api.middleware.request_id import get_request_id
from app.security.redaction import ArgumentSanitizer


class Span:
    """Represents a single traced execution span."""

    def __init__(
        self, name: str, trace_id: str | None = None, attributes: dict[str, Any] | None = None
    ) -> None:
        self.name = name
        self.trace_id = trace_id or f"trc_{uuid.uuid4().hex[:16]}"
        self.request_id = get_request_id()
        self.attributes = ArgumentSanitizer.sanitize(attributes or {})
        self.start_time: float = time.time()
        self.end_time: float | None = None
        self.duration_ms: float | None = None
        self.status: str = "RUNNING"
        self.error: str | None = None

    def finish(self, status: str = "OK", error: str | None = None) -> None:
        """Mark span as finished and calculate duration."""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000.0
        self.status = status
        self.error = ArgumentSanitizer.redact_string(error) if error else None


@contextmanager
def trace_span(name: str, attributes: dict[str, Any] | None = None) -> Generator[Span, None, None]:
    """Context manager for tracing blocks of code without leaking raw prompts or secrets."""
    span = Span(name=name, attributes=attributes)
    try:
        yield span
        span.finish(status="OK")
    except Exception as exc:
        span.finish(status="ERROR", error=str(exc))
        raise
