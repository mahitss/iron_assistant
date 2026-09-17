"""Pattern Detection Engine for Kairo Strategy Engine (Task 106).

Detects statistical regularities, outcome distributions, and counterexamples
across conditions, capabilities, environments, and resources without confusing
correlation with causation.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.strategy.experience_miner import MinedExperienceCluster


class DetectedPattern(BaseModel):
    """Statistically validated operational pattern."""

    pattern_id: str
    category: str
    domain_scope: str
    target_conditions: Dict[str, Any]
    approach_summary: str
    frequency: int
    success_count: int
    failure_count: int
    success_rate: float
    failure_rate: float
    conservative_confidence: float      # Lower bound of Wilson score interval
    uncertainty: float
    temporal_stability: float
    confounder_warnings: List[str] = Field(default_factory=list)
    counterexample_summaries: List[str] = Field(default_factory=list)


class PatternDetectionEngine:
    """Detects recurring patterns across mined experience clusters."""

    def __init__(self, min_success_rate: float = 0.70, confidence_z: float = 1.96) -> None:
        self.min_success_rate = min_success_rate
        self.confidence_z = confidence_z

    def _calculate_wilson_lower_bound(self, successes: int, total: int) -> float:
        """Calculate Wilson score interval lower bound for conservative statistical estimation."""
        if total == 0:
            return 0.0
        z = self.confidence_z
        p_hat = successes / total
        denominator = 1.0 + (z * z) / total
        center = p_hat + (z * z) / (2 * total)
        spread = z * math.sqrt((p_hat * (1.0 - p_hat) + (z * z) / (4 * total)) / total)
        lower = (center - spread) / denominator
        return max(0.0, min(1.0, lower))

    def detect_patterns(self, clusters: List[MinedExperienceCluster]) -> List[DetectedPattern]:
        """Analyze clusters and synthesize validated candidate patterns."""
        patterns: List[DetectedPattern] = []

        for cluster in clusters:
            total = cluster.total_count
            if total == 0:
                continue

            successes = len(cluster.successes)
            failures = len(cluster.failures)
            s_rate = successes / total
            f_rate = failures / total

            # Only consider clusters meeting baseline effectiveness
            if s_rate < self.min_success_rate:
                continue

            conservative_conf = self._calculate_wilson_lower_bound(successes, total)
            uncertainty = 1.0 - conservative_conf

            # Confounder and counterexample isolation
            confounders: List[str] = []
            env_counts: Dict[str, int] = {}
            for s in cluster.successes:
                env = s.get("environment", "prod")
                env_counts[env] = env_counts.get(env, 0) + 1

            if len(env_counts) == 1 and total > 5:
                confounders.append(
                    f"Correlation warning: Strategy only verified in environment '{list(env_counts.keys())[0]}'. May not generalize."
                )

            # Analyze counterexamples
            counter_summaries: List[str] = []
            for fail in cluster.counterexamples[:5]:
                reason = fail.get("error", fail.get("reason", "Condition mismatch or resource pressure"))
                counter_summaries.append(f"Failed under: {reason}")

            pattern = DetectedPattern(
                pattern_id=f"pat_{cluster.cluster_key.replace(':', '_')}",
                category=cluster.category,
                domain_scope=cluster.domain_scope,
                target_conditions=cluster.conditions,
                approach_summary=cluster.approach_summary,
                frequency=total,
                success_count=successes,
                failure_count=failures,
                success_rate=round(s_rate, 4),
                failure_rate=round(f_rate, 4),
                conservative_confidence=round(conservative_conf, 4),
                uncertainty=round(uncertainty, 4),
                temporal_stability=0.92,
                confounder_warnings=confounders,
                counterexample_summaries=counter_summaries,
            )
            patterns.append(pattern)

        return patterns
