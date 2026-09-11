"""Novelty Detection and Change Magnitude Engine for Kairo Attention (Task 70).

A completely normal event should not consume excessive attention (e.g. CPU = 45% is baseline normal).
A sudden deviation (CPU = 98%, sudden traffic spike, schema change) may be novel.
CRITICAL INVARIANT:
Novelty != Danger. Novelty alone does not equate to importance.
"""

from typing import Any


class NoveltyDetector:
    """Evaluates novelty and change magnitude against baselines."""

    # Threshold above which an item is considered novel enough to influence attention
    NOVELTY_THRESHOLD = 0.50

    @classmethod
    def evaluate(
        cls,
        *,
        observed_value: float | None = None,
        baseline_mean: float = 50.0,
        baseline_std: float = 10.0,
        historical_frequency: int = 10,
        event_type: str = "general",
        changes: dict[str, Any] | None = None,
        explicit_novelty: float | None = None,
        explicit_change_magnitude: float | None = None,
    ) -> tuple[float, float, bool, dict[str, float]]:
        """Evaluate novelty score and change magnitude.

        Returns:
            (novelty_score [0.0 - 1.0], change_magnitude [0.0 - 1.0], is_novel, breakdown)
        """
        # 1. Statistical anomaly deviation if metric provided
        stat_novelty = 0.0
        if observed_value is not None and baseline_std > 0:
            z_score = abs(observed_value - baseline_mean) / baseline_std
            # Map z-score: z=0 -> 0.0, z=2 -> 0.5, z>=4 -> 1.0
            stat_novelty = min(1.0, z_score / 4.0)

        # 2. Historical frequency penalty (frequent events are not novel)
        freq_factor = 1.0 / (1.0 + (historical_frequency * 0.1))

        # 3. Change magnitude evaluation
        change_mag = 0.0
        if changes:
            # Significant change categories
            critical_change_keys = {
                "config",
                "deployment",
                "traffic",
                "security_policy",
                "database_schema",
                "goal",
            }
            detected_keys = set(changes.keys())
            overlap = detected_keys.intersection(critical_change_keys)
            if overlap:
                change_mag = min(1.0, 0.4 + (len(overlap) * 0.2))
            else:
                change_mag = min(1.0, len(changes) * 0.1)

        if explicit_change_magnitude is not None:
            change_mag = max(change_mag, max(0.0, min(1.0, explicit_change_magnitude)))

        # 4. Composite novelty
        computed_novelty = max(stat_novelty, freq_factor * 0.8)
        if change_mag > 0.6:
            computed_novelty = max(computed_novelty, change_mag * 0.8)

        if explicit_novelty is not None:
            final_novelty = max(computed_novelty, max(0.0, min(1.0, explicit_novelty)))
        else:
            final_novelty = computed_novelty

        final_novelty = round(max(0.0, min(1.0, final_novelty)), 3)
        final_change_mag = round(max(0.0, min(1.0, change_mag)), 3)
        is_novel = final_novelty >= cls.NOVELTY_THRESHOLD

        breakdown = {
            "statistical_novelty": round(stat_novelty, 3),
            "historical_frequency_factor": round(freq_factor, 3),
            "change_magnitude": final_change_mag,
            "computed_novelty": final_novelty,
        }

        return final_novelty, final_change_mag, is_novel, breakdown
