"""Tool and Model Provider Reliability Tracking for Kairo Learning Engine (Task 43)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("kairo.learning.reliability")


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class ReliabilityMetrics:
    """Empirical reliability metrics for a tool, provider, or strategy."""

    entity_id: str
    entity_type: str  # "tool", "provider", "strategy"
    total_calls: int = 0
    successes: int = 0
    failures: int = 0
    timeouts: int = 0
    retries: int = 0
    unknowns: int = 0
    total_latency_ms: float = 0.0
    last_updated: datetime = field(default_factory=utc_now)

    @property
    def success_rate(self) -> float:
        return (self.successes / self.total_calls) if self.total_calls > 0 else 0.0

    @property
    def failure_rate(self) -> float:
        return (self.failures / self.total_calls) if self.total_calls > 0 else 0.0

    @property
    def timeout_rate(self) -> float:
        return (self.timeouts / self.total_calls) if self.total_calls > 0 else 0.0

    @property
    def unknown_rate(self) -> float:
        return (self.unknowns / self.total_calls) if self.total_calls > 0 else 0.0

    @property
    def average_latency_ms(self) -> float:
        return (self.total_latency_ms / self.total_calls) if self.total_calls > 0 else 0.0

    @property
    def reliability_score(self) -> float:
        """Composite reliability score (Spec 22, 83). Unknowns penalize score."""
        if self.total_calls == 0:
            return 0.5
        penalty = (self.timeout_rate * 0.4) + (self.failure_rate * 0.4) + (self.unknown_rate * 0.3)
        return max(0.0, min(1.0, 1.0 - penalty))

    def record_call(
        self,
        success: bool,
        is_timeout: bool = False,
        is_unknown: bool = False,
        retries: int = 0,
        latency_ms: float = 0.0,
    ) -> None:
        self.total_calls += 1
        if success:
            self.successes += 1
        else:
            self.failures += 1

        if is_timeout:
            self.timeouts += 1
        if is_unknown:
            self.unknowns += 1

        self.retries += retries
        self.total_latency_ms += latency_ms
        self.last_updated = utc_now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "total_calls": self.total_calls,
            "successes": self.successes,
            "failures": self.failures,
            "timeouts": self.timeouts,
            "retries": self.retries,
            "unknowns": self.unknowns,
            "success_rate": round(self.success_rate, 3),
            "failure_rate": round(self.failure_rate, 3),
            "timeout_rate": round(self.timeout_rate, 3),
            "unknown_rate": round(self.unknown_rate, 3),
            "average_latency_ms": round(self.average_latency_ms, 2),
            "reliability_score": round(self.reliability_score, 3),
            "last_updated": self.last_updated.isoformat(),
        }


class ReliabilityTracker:
    """Manages empirical reliability profiles for tools, models, and providers."""

    def __init__(self) -> None:
        self._tools: dict[str, ReliabilityMetrics] = {}
        self._providers: dict[str, ReliabilityMetrics] = {}

    def get_tool_metrics(self, tool_name: str) -> ReliabilityMetrics:
        """Get or initialize tool metrics."""
        clean_name = tool_name.strip().lower()
        if clean_name not in self._tools:
            self._tools[clean_name] = ReliabilityMetrics(entity_id=clean_name, entity_type="tool")
        return self._tools[clean_name]

    def get_provider_metrics(self, provider_id: str) -> ReliabilityMetrics:
        """Get or initialize provider metrics."""
        clean_name = provider_id.strip().lower()
        if clean_name not in self._providers:
            self._providers[clean_name] = ReliabilityMetrics(entity_id=clean_name, entity_type="provider")
        return self._providers[clean_name]

    def record_tool_result(
        self,
        tool_name: str,
        success: bool,
        is_timeout: bool = False,
        is_unknown: bool = False,
        retries: int = 0,
        latency_ms: float = 0.0,
    ) -> None:
        metrics = self.get_tool_metrics(tool_name)
        metrics.record_call(
            success=success,
            is_timeout=is_timeout,
            is_unknown=is_unknown,
            retries=retries,
            latency_ms=latency_ms,
        )

    def record_provider_result(
        self,
        provider_id: str,
        success: bool,
        is_timeout: bool = False,
        latency_ms: float = 0.0,
    ) -> None:
        metrics = self.get_provider_metrics(provider_id)
        metrics.record_call(
            success=success,
            is_timeout=is_timeout,
            latency_ms=latency_ms,
        )

    def get_all_tool_reliability(self) -> list[dict[str, Any]]:
        return [m.to_dict() for m in self._tools.values()]

    def get_all_provider_reliability(self) -> list[dict[str, Any]]:
        return [m.to_dict() for m in self._providers.values()]
