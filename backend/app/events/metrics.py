"""Metrics collection and observability for Kairo Unified Event Bus.

Tracks throughput, latency, failure rates, queue depth, and dead letters.
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional


class EventMetricsTracker:
    """Thread-safe / async-safe in-memory metrics store for event bus telemetry."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self.published_count: int = 0
        self.delivered_count: int = 0
        self.processed_count: int = 0
        self.failed_count: int = 0
        self.retried_count: int = 0
        self.dead_lettered_count: int = 0

        # Breakdown dictionaries
        self.by_event_type: Dict[str, int] = defaultdict(int)
        self.by_source: Dict[str, int] = defaultdict(int)
        self.by_subscriber: Dict[str, int] = defaultdict(int)
        self.errors_by_subscriber: Dict[str, int] = defaultdict(int)

        # Latency tracking (sliding window of recent handler run durations in ms)
        self._latencies: List[float] = []
        self._max_latency_samples: int = 1000

    async def record_published(self, event_type: str, source: str) -> None:
        async with self._lock:
            self.published_count += 1
            self.by_event_type[event_type] += 1
            self.by_source[source] += 1

    async def record_delivered(self, subscriber_name: str) -> None:
        async with self._lock:
            self.delivered_count += 1
            self.by_subscriber[subscriber_name] += 1

    async def record_processed(self, subscriber_name: str, duration_seconds: float) -> None:
        duration_ms = duration_seconds * 1000.0
        async with self._lock:
            self.processed_count += 1
            self._latencies.append(duration_ms)
            if len(self._latencies) > self._max_latency_samples:
                self._latencies.pop(0)

    async def record_failed(self, subscriber_name: str) -> None:
        async with self._lock:
            self.failed_count += 1
            self.errors_by_subscriber[subscriber_name] += 1

    async def record_retry(self) -> None:
        async with self._lock:
            self.retried_count += 1

    async def record_dead_letter(self) -> None:
        async with self._lock:
            self.dead_lettered_count += 1

    async def get_snapshot(self, queue_size: int = 0, subscriber_count: int = 0) -> Dict[str, Any]:
        """Returns consolidated metrics snapshot."""
        async with self._lock:
            avg_latency = (
                sum(self._latencies) / len(self._latencies) if self._latencies else 0.0
            )
            p95_latency = 0.0
            if self._latencies:
                sorted_l = sorted(self._latencies)
                p95_idx = int(len(sorted_l) * 0.95)
                p95_latency = sorted_l[min(p95_idx, len(sorted_l) - 1)]

            return {
                "published_total": self.published_count,
                "delivered_total": self.delivered_count,
                "processed_total": self.processed_count,
                "failed_total": self.failed_count,
                "retried_total": self.retried_count,
                "dead_lettered_total": self.dead_lettered_count,
                "queue_size": queue_size,
                "active_subscribers": subscriber_count,
                "latency_ms": {
                    "avg": round(avg_latency, 2),
                    "p95": round(p95_latency, 2),
                    "samples_count": len(self._latencies),
                },
                "by_event_type": dict(self.by_event_type),
                "by_source": dict(self.by_source),
                "by_subscriber": dict(self.by_subscriber),
                "errors_by_subscriber": dict(self.errors_by_subscriber),
            }

    async def reset(self) -> None:
        """Reset all metric counters."""
        async with self._lock:
            self.published_count = 0
            self.delivered_count = 0
            self.processed_count = 0
            self.failed_count = 0
            self.retried_count = 0
            self.dead_lettered_count = 0
            self.by_event_type.clear()
            self.by_source.clear()
            self.by_subscriber.clear()
            self.errors_by_subscriber.clear()
            self._latencies.clear()


event_metrics = EventMetricsTracker()
