"""Evaluation and Accuracy Metrics for Environmental Intelligence (Task 54, Prompts #195-#200)."""

from __future__ import annotations

from typing import Any

from app.environment.schemas import DigitalTwin, FreshnessState, HealthStatus
from app.environment.temporal import calculate_freshness


class EnvironmentEvaluationEngine:
    """Computes precision, freshness, and accuracy metrics for digital twins."""

    @staticmethod
    def evaluate_twin_metrics(twin: DigitalTwin) -> dict[str, Any]:
        """Calculates topological and telemetry quality metrics for a digital twin."""
        total_nodes = len(twin.nodes)
        total_edges = len(twin.edges)

        fresh_count = 0
        stale_count = 0
        expired_count = 0
        unknown_health_count = 0

        for n in twin.nodes.values():
            freshness = calculate_freshness(n.last_seen)
            if freshness == FreshnessState.FRESH:
                fresh_count += 1
            elif freshness == FreshnessState.STALE:
                stale_count += 1
            elif freshness == FreshnessState.EXPIRED:
                expired_count += 1

            rec = twin.health.get(n.node_id)
            if not rec or rec.status == HealthStatus.UNKNOWN:
                unknown_health_count += 1

        freshness_ratio = (fresh_count / total_nodes) if total_nodes > 0 else 1.0
        health_coverage = ((total_nodes - unknown_health_count) / total_nodes) if total_nodes > 0 else 0.0

        # False dependency indicator: edges marked with low confidence or no verified provenance
        unverified_edges = sum(
            1 for e in twin.edges.values()
            if e.confidence.value in ("INFERRED", "UNKNOWN")
        )

        return {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "fresh_nodes": fresh_count,
            "stale_nodes": stale_count,
            "expired_nodes": expired_count,
            "freshness_ratio": round(freshness_ratio, 2),
            "health_coverage_ratio": round(health_coverage, 2),
            "unverified_edges": unverified_edges,
            "aggregate_confidence": twin.confidence,
        }
