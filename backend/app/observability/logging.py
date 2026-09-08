"""Structured JSON logging with ArgumentSanitizer secret redaction."""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from app.api.middleware.request_id import get_request_id
from app.security.redaction import ArgumentSanitizer


class StructuredJsonFormatter(logging.Formatter):
    """Formats log records as structured JSON, redacting secrets and bounding lengths."""

    def format(self, record: logging.LogRecord) -> str:
        # 1. Base log record fields
        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": ArgumentSanitizer.redact_string(record.getMessage()),
            "request_id": getattr(record, "request_id", None) or get_request_id(),
        }

        # 2. Add structured extras if present
        for field in ("user_id", "session_id", "component", "event", "duration_ms", "status"):
            val = getattr(record, field, None)
            if val is not None:
                log_entry[field] = val

        # 3. Include exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def configure_structured_logging(log_level: str = "INFO") -> None:
    """Configure standard root logger with StructuredJsonFormatter."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredJsonFormatter())

    root = logging.getLogger()
    root.setLevel(log_level.upper())

    # Replace existing handlers with structured formatter
    root.handlers.clear()
    root.addHandler(handler)
