"""ContextQualityEvaluator: Multi-dimensional context quality scoring (Task 69)."""

import logging

from app.context.universal_schemas import ContextQualityScore, UniversalContextItem

logger = logging.getLogger("kairo.context.quality")


class ContextQualityEvaluator:
    """Evaluates context packages across relevance, coverage, freshness, trust, noise, and redundancy."""

    @classmethod
    def evaluate_quality(
        cls,
        selected_items: list[UniversalContextItem],
        total_candidates: int,
        build_latency_ms: float = 12.5,
    ) -> ContextQualityScore:
        """Compute comprehensive quality metrics for assembled context."""
        if not selected_items:
            return ContextQualityScore(
                relevance=0.0,
                coverage=0.0,
                freshness=1.0,
                trust=1.0,
                confidence=0.5,
                redundancy=0.0,
                noise=0.0,
                latency_ms=build_latency_ms,
                overall_score=0.2,
            )

        n = len(selected_items)
        avg_relevance = sum(it.relevance_score for it in selected_items) / n
        avg_freshness = sum(it.freshness_score for it in selected_items) / n
        avg_confidence = sum(it.confidence for it in selected_items) / n

        # Trust score based on verified vs unverified items
        trust_vals = [1.0 if it.trust_level in {"VERIFIED", "TRUSTED"} else 0.7 for it in selected_items]
        avg_trust = sum(trust_vals) / n

        # Coverage factor (selected items / candidates, or variety of types)
        distinct_types = len({it.context_type for it in selected_items})
        coverage = min(1.0, (distinct_types / 3.0) * 0.6 + min(1.0, n / 5.0) * 0.4)

        # Noise: items with low relevance (< 0.4)
        noise_items = sum(1 for it in selected_items if it.relevance_score < 0.4)
        noise_ratio = noise_items / n

        # Redundancy: title token repetition
        all_titles = [it.title.lower() for it in selected_items]
        unique_titles = set(all_titles)
        redundancy_ratio = 1.0 - (len(unique_titles) / n) if n > 1 else 0.0

        overall = (
            avg_relevance * 0.35
            + coverage * 0.20
            + avg_freshness * 0.15
            + avg_trust * 0.15
            + avg_confidence * 0.15
        ) - (redundancy_ratio * 0.15 + noise_ratio * 0.15)

        overall_clamped = round(max(0.05, min(1.0, overall)), 4)

        return ContextQualityScore(
            relevance=round(avg_relevance, 4),
            coverage=round(coverage, 4),
            freshness=round(avg_freshness, 4),
            trust=round(avg_trust, 4),
            confidence=round(avg_confidence, 4),
            redundancy=round(redundancy_ratio, 4),
            noise=round(noise_ratio, 4),
            latency_ms=round(build_latency_ms, 2),
            overall_score=overall_clamped,
        )
