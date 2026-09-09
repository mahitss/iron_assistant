"""Structured JSON logging with trace correlation, secret redaction, and log injection defense (Task 38)."""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from app.api.middleware.request_id import get_request_id
from app.observability.correlation import (
    get_current_span_id,
    get_current_task_id,
    get_current_trace_id,
)
from app.observability.sanitization import TelemetrySanitizer


class StructuredJsonFormatter(logging.Formatter):
    """Formats log records as structured JSON, escaping injection characters and redacting secrets."""

    def format(self, record: logging.LogRecord) -> str:
        # 1. Base log record fields
        raw_msg = record.getMessage()
        sanitized_msg = TelemetrySanitizer.sanitize_log_message(raw_msg)

        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "service": "kairo",
            "logger": record.name,
            "message": sanitized_msg,
            "trace_id": getattr(record, "trace_id", None) or get_current_trace_id(),
            "span_id": getattr(record, "span_id", None) or get_current_span_id(),
            "task_id": getattr(record, "task_id", None) or get_current_task_id(),
            "request_id": getattr(record, "request_id", None) or get_request_id(),
        }

        # 2. Add contextual extras if present
        for field in (
            "component",
            "operation",
            "event_type",
            "status",
            "error_code",
            "duration_ms",
            "user_id",
            "project_id",
        ):
            val = getattr(record, field, None)
            if val is not None:
                if isinstance(val, (dict, list)):
                    log_entry[field] = TelemetrySanitizer.sanitize_dict(val if isinstance(val, dict) else {"items": val})
                elif isinstance(val, str):
                    log_entry[field] = TelemetrySanitizer.sanitize_text(val)
                else:
                    log_entry[field] = val

        # 3. Include exception info if present
        if record.exc_info:
            log_entry["exception"] = TelemetrySanitizer.sanitize_text(self.formatException(record.exc_info))

        return json.dumps(log_entry)


def configure_structured_logging(log_level: str = "INFO") -> None:
    """Configures the root logger with StructuredJsonFormatter."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredJsonFormatter())

    root = logging.getLogger()
    root.setLevel(log_level.upper())
    root.handlers.clear()
    root.addHandler(handler)
