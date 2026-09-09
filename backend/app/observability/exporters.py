"""Telemetry exporters with backpressure protection and non-blocking fail-safe isolation (Task 38)."""

import logging
from typing import Any

from app.observability.metrics import get_metrics_collector
from app.observability.schemas import MetricRecord, Trace, TraceStatus

logger = logging.getLogger("kairo.observability.exporters")


class TelemetryExporter:
    """Manages asynchronous, non-blocking telemetry export with backpressure shedding."""

    def __init__(self, max_buffer_size: int = 1000) -> None:
        self.max_buffer_size = max_buffer_size
        self._buffer: list[Trace] = []
        self.exported_count: int = 0
        self.dropped_count: int = 0
        self.failure_count: int = 0
        self.is_healthy: bool = True

    def export_trace(self, trace: Trace) -> bool:
        """Buffers or exports a trace safely.

        Never raises an exception to the caller, preventing telemetry from crashing the application.
        """
        try:
            # Backpressure handling
            if len(self._buffer) >= self.max_buffer_size:
                # Discard oldest non-error trace to make room
                dropped_idx = None
                for idx, item in enumerate(self._buffer):
                    if item.status == TraceStatus.SUCCESS and item.error_count == 0:
                        dropped_idx = idx
                        break

                if dropped_idx is not None:
                    self._buffer.pop(dropped_idx)
                    self.dropped_count += 1
                else:
                    # All items in buffer are errors; drop new non-error item if incoming is success
                    if trace.status == TraceStatus.SUCCESS:
                        self.dropped_count += 1
                        return False
                    # Incoming is error; drop oldest item unconditionally
                    self._buffer.pop(0)
                    self.dropped_count += 1

            self._buffer.append(trace)
            self.exported_count += 1
            get_metrics_collector().inc_counter("telemetry_traces_exported_total", 1.0)
            return True
        except Exception as exc:
            self.failure_count += 1
            self.is_healthy = False
            logger.warning("Telemetry exporter failed silently to protect application core: %s", exc)
            return False

    def get_buffered_traces(self) -> list[Trace]:
        return list(self._buffer)

    def clear(self) -> None:
        self._buffer.clear()

    def get_health(self) -> dict[str, Any]:
        """Returns health status of the telemetry exporter."""
        return {
            "healthy": self.is_healthy,
            "buffer_depth": len(self._buffer),
            "max_buffer_size": self.max_buffer_size,
            "exported_count": self.exported_count,
            "dropped_count": self.dropped_count,
            "failure_count": self.failure_count,
        }
