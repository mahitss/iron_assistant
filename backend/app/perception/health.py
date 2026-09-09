"""Perception Subsystem Health Monitoring, Telemetry Metrics, and Resync (Task 46)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Dict

logger = logging.getLogger("kairo.perception.health")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class PerceptionHealthMetrics:
    """Live observability metrics across environmental ingestion and processing (Spec 184, 185)."""

    events_received: int = 0
    events_processed: int = 0
    events_deduplicated: int = 0
    events_dropped: int = 0
    stale_events_rejected: int = 0
    out_of_order_events: int = 0
    changes_detected: int = 0
    anomalies_detected: int = 0
    avg_latency_ms: float = 0.0
    last_event_at: Optional[datetime] = None

    def record_ingestion(self, latency_ms: float = 0.0) -> None:
        self.events_received += 1
        self.events_processed += 1
        self.last_event_at = utc_now()
        # Exponential moving average
        self.avg_latency_ms = (self.avg_latency_ms * 0.9) + (latency_ms * 0.1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "events_received": self.events_received,
            "events_processed": self.events_processed,
            "events_deduplicated": self.events_deduplicated,
            "events_dropped": self.events_dropped,
            "stale_events_rejected": self.stale_events_rejected,
            "out_of_order_events": self.out_of_order_events,
            "changes_detected": self.changes_detected,
            "anomalies_detected": self.anomalies_detected,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "last_event_at": self.last_event_at.isoformat() if self.last_event_at else None,
        }
