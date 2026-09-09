"""Backward compatibility re-export for logging (Task 38)."""

from app.observability.logs import StructuredJsonFormatter, configure_structured_logging

__all__ = ["StructuredJsonFormatter", "configure_structured_logging"]
