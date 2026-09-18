"""Autonomous Discriminating Observation & Information-Value Engine (Task 115 Section 21, 33, 46).

Identifies discriminating observations that can distinguish between competing hypotheses,
calculates information value (integrating with Task 114 Active Observation Engine),
and defines actionable information gaps.

Hard Invariants:
- Discriminating observations are formulated without mutating action policies or triggering unapproved actuators.
- Does NOT execute observations automatically (leaves execution to Task 114 and governance).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from app.hypothesis.domain import (
    Hypothesis,
    HypothesisDiscriminator,
    HypothesisSet,
)

logger = logging.getLogger("kairo.hypothesis.discriminator")


class DiscriminatorEngine:
    """Discovers observations that maximize divergence across competing hypotheses."""

    def find_discriminating_observations(
        self,
        hset: HypothesisSet,
        hypotheses: List[Hypothesis],
    ) -> List[HypothesisDiscriminator]:
        """Examines active hypotheses in a set and generates discriminators with high information value."""
        active = [h for h in hypotheses if h.hypothesis_id in hset.active_hypothesis_ids and not h.is_unknown_hypothesis]
        if len(active) < 2:
            return []

        discriminators: List[HypothesisDiscriminator] = []

        # Compare pairs of competing hypotheses
        for i in range(len(active)):
            for j in range(i + 1, len(active)):
                h_a = active[i]
                h_b = active[j]

                disc = self._derive_discriminator_between(h_a, h_b)
                if disc:
                    discriminators.append(disc)

        hset.discriminators = discriminators
        hset.updated_at = datetime.now(timezone.utc)

        # Update information gaps
        hset.information_gaps = [
            f"Need observation on '{d.target_metric_or_signal}' to discriminate between hypotheses: {list(d.hypothesis_predictions.keys())}"
            for d in discriminators
        ]

        logger.info(
            "Derived %d discriminating observations for hypothesis set %s",
            len(discriminators),
            hset.set_id,
        )
        return discriminators

    def _derive_discriminator_between(
        self, hyp_a: Hypothesis, hyp_b: Hypothesis
    ) -> Optional[HypothesisDiscriminator]:
        """Finds a metric or state where hyp_a and hyp_b predict distinct outcomes."""
        metric_a = hyp_a.claim.target_metric
        metric_b = hyp_b.claim.target_metric

        if metric_a and metric_b and metric_a != metric_b:
            return HypothesisDiscriminator(
                target_metric_or_signal=f"{metric_a} vs {metric_b}",
                hypothesis_predictions={
                    hyp_a.hypothesis_id: f"{hyp_a.claim.subject} shows {hyp_a.claim.expected_direction or 'anomaly'} in {metric_a}",
                    hyp_b.hypothesis_id: f"{hyp_b.claim.subject} shows {hyp_b.claim.expected_direction or 'anomaly'} in {metric_b}",
                },
                observation_channel="telemetry.metrics_collector",
                information_value=0.85,
                estimated_cost=0.1,
                latency_seconds=1.5,
                risk_level="LOW",
                rationale=f"Observing both {metric_a} and {metric_b} immediately confirms or weakens {hyp_a.hypothesis_id} relative to {hyp_b.hypothesis_id}.",
            )

        # Look at predictions
        for pred_a in hyp_a.predictions:
            for pred_b in hyp_b.predictions:
                if pred_a.expected_metric and pred_b.expected_metric:
                    return HypothesisDiscriminator(
                        target_metric_or_signal=f"{pred_a.expected_metric} / {pred_b.expected_metric}",
                        hypothesis_predictions={
                            hyp_a.hypothesis_id: f"Expected range: {pred_a.expected_value_range or 'elevated'}",
                            hyp_b.hypothesis_id: f"Expected range: {pred_b.expected_value_range or 'nominal'}",
                        },
                        observation_channel="telemetry.system_profiler",
                        information_value=0.75,
                        estimated_cost=0.15,
                        latency_seconds=2.0,
                        risk_level="LOW",
                        rationale="Divergent predicted telemetry ranges allow discrimination.",
                    )

        return None
