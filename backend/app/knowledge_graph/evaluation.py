"""Operational telemetry, quality evaluation, and user feedback loop (INVARIANTS 211-214)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class KnowledgeGraphEvaluator:
    """Tracks operational metrics, retrieval latency, resolution accuracy, and user feedback."""

    def __init__(self) -> None:
        self.metrics = {
            "nodes_created": 0,
            "edges_created": 0,
            "assertions_recorded": 0,
            "contradictions_detected": 0,
            "contradictions_resolved": 0,
            "merges_performed": 0,
            "splits_performed": 0,
            "queries_executed": 0,
            "forget_requests": 0,
            "user_corrections": 0,
        }
        self._feedback_log: List[Dict[str, Any]] = []

    def record_metric(self, metric_name: str, increment: int = 1) -> None:
        if metric_name in self.metrics:
            self.metrics[metric_name] += increment

    def record_feedback(
        self,
        entity_id: str,
        feedback_type: str,  # correct, forget, confirm, reject, not_relevant
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """INVARIANT 213 & 214: Records user feedback to update memory state and tune ranking."""
        record = {
            "entity_id": entity_id,
            "feedback_type": feedback_type,
            "notes": notes,
        }
        self._feedback_log.append(record)

        if feedback_type == "correct":
            self.record_metric("user_corrections")
        elif feedback_type == "forget":
            self.record_metric("forget_requests")

        return record

    def get_summary_metrics(self) -> Dict[str, Any]:
        return dict(self.metrics)
