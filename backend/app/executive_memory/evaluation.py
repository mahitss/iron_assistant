"""Multi-dimensional evaluation metrics for executive memory and false continuity measurement (INVARIANTS 223-225)."""

from __future__ import annotations

from typing import Any
from app.executive_memory.schemas import ExecutiveMemoryMetricsSchema


class ExecutiveMemoryEvaluator:
    """Tracks operational quality, timeline integrity, and explicitly measures false continuity rates."""

    def __init__(self) -> None:
        self.metrics = ExecutiveMemoryMetricsSchema()
        self._total_queries: int = 0
        self._false_claims: int = 0
        self._user_corrections: int = 0

    def record_query_outcome(
        self,
        latency_ms: float,
        was_accurate: bool = True,
        had_false_claim: bool = False,
    ) -> None:
        """INVARIANT 223: Records retrieval latency and accuracy."""
        self._total_queries += 1
        if had_false_claim:
            self._false_claims += 1

        self.metrics.context_retrieval_latency_ms = round(latency_ms, 2)
        self.metrics.false_continuity_rate = round(self._false_claims / self._total_queries, 3)

    def record_user_correction(self) -> None:
        """INVARIANT 186 & 223: Tracks user corrections against executive summaries."""
        self._user_corrections += 1
        if self._total_queries > 0:
            self.metrics.user_correction_rate = round(self._user_corrections / self._total_queries, 3)

    def get_metrics(self) -> ExecutiveMemoryMetricsSchema:
        """INVARIANT 223: Returns current operational metrics schema."""
        return self.metrics

    def get_metrics_report(self) -> dict[str, Any]:
        return self.metrics.model_dump()
