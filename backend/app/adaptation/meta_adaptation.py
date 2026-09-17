"""Meta-Adaptation Engine and Control-Loop Safety Safeguards for Task 105.
Monitors the adaptation system's own health and prevents infinite loops,
diminishing-return cycling, and unconstrained branching.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import logging
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger("kairo.adaptation.meta")


class MetaAdaptationEngine:
    """Monitors adaptation performance and enforces control-loop safety constraints."""

    def __init__(
        self,
        max_generations: int = 5,
        cooldown_seconds: float = 60.0,
        diminishing_return_threshold: float = 0.005,
    ) -> None:
        self.max_generations = max_generations
        self.cooldown_seconds = cooldown_seconds
        self.diminishing_return_threshold = diminishing_return_threshold
        # capability -> list of timestamps of recent experiments
        self._recent_experiment_times: dict[str, list[datetime]] = {}
        # capability -> list of recent metric deltas
        self._recent_deltas: dict[str, list[float]] = {}
        # seen hypothesis hashes
        self._seen_hypotheses: set[str] = set()

    def check_loop_safety(
        self,
        capability: str,
        current_generation: int,
        hypothesis_hash: str,
    ) -> tuple[bool, list[str]]:
        """Validates that a new experiment cycle satisfies all control-loop safety rules."""
        violations: list[str] = []

        # 1. Max generation check (prevents unbounded branching)
        if current_generation >= self.max_generations:
            violations.append(
                f"MAX_GENERATIONS_EXCEEDED: Capability '{capability}' reached generation {current_generation} >= {self.max_generations}."
            )

        # 2. Cooldown check
        now = datetime.now(UTC)
        recent_times = self._recent_experiment_times.get(capability, [])
        if recent_times:
            last_run = recent_times[-1]
            elapsed = (now - last_run).total_seconds()
            if elapsed < self.cooldown_seconds:
                violations.append(
                    f"COOLDOWN_ACTIVE: Must wait {self.cooldown_seconds - elapsed:.1f}s before another experiment on '{capability}'."
                )

        # 3. Repeated hypothesis detection
        if hypothesis_hash in self._seen_hypotheses:
            violations.append("REPEATED_HYPOTHESIS: Identical hypothesis was already evaluated recently.")

        # 4. Diminishing returns check
        deltas = self._recent_deltas.get(capability, [])
        if len(deltas) >= 3:
            recent_3 = deltas[-3:]
            if all(abs(d) < self.diminishing_return_threshold for d in recent_3):
                violations.append(
                    f"DIMINISHING_RETURNS: Last 3 experiments achieved deltas < {self.diminishing_return_threshold}. Halting adaptation loop."
                )

        passed = len(violations) == 0
        if not passed:
            logger.warning("Control loop safety blocked adaptation for %s: %s", capability, "; ".join(violations))
        return passed, violations

    def record_experiment_outcome(
        self,
        capability: str,
        hypothesis_hash: str,
        metric_delta: float,
    ) -> None:
        """Records an experiment completion to maintain history for cooldown and diminishing returns."""
        now = datetime.now(UTC)
        if capability not in self._recent_experiment_times:
            self._recent_experiment_times[capability] = []
        self._recent_experiment_times[capability].append(now)

        if capability not in self._recent_deltas:
            self._recent_deltas[capability] = []
        self._recent_deltas[capability].append(metric_delta)

        self._seen_hypotheses.add(hypothesis_hash)

    def calculate_meta_health(
        self,
        total_experiments: int,
        successful_experiments: int,
        failed_experiments: int,
        inconclusive_experiments: int,
        rollback_count: int,
    ) -> dict[str, Any]:
        """Evaluates whether the adaptation system itself is functioning reliably."""
        if total_experiments == 0:
            return {
                "adaptation_health": "NOMINAL",
                "success_rate": 0.0,
                "failure_rate": 0.0,
                "inconclusive_rate": 0.0,
                "rollback_rate": 0.0,
                "needs_meta_evaluation": False,
            }

        success_rate = successful_experiments / total_experiments
        failure_rate = failed_experiments / total_experiments
        inconclusive_rate = inconclusive_experiments / total_experiments
        rollback_rate = rollback_count / max(1, successful_experiments)

        # Detect degradation
        is_degraded = (
            (total_experiments >= 5 and inconclusive_rate > 0.60) or
            (total_experiments >= 5 and failure_rate > 0.50) or
            (rollback_count >= 2 and rollback_rate > 0.30)
        )

        health = "DEGRADED" if is_degraded else "NOMINAL"
        if is_degraded:
            logger.warning("Meta-Adaptation Health is DEGRADED! Emitting evaluation finding.")

        return {
            "adaptation_health": health,
            "total_experiments": total_experiments,
            "success_rate": round(success_rate, 3),
            "failure_rate": round(failure_rate, 3),
            "inconclusive_rate": round(inconclusive_rate, 3),
            "rollback_rate": round(rollback_rate, 3),
            "needs_meta_evaluation": is_degraded,
            "recommendation": "Review evaluation benchmarks and hypothesis generation parameters" if is_degraded else "Adaptation engine operating normally",
        }
