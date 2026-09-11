"""Error Taxonomy, Clustering, Pattern Recognition, and Rationalization Detection (Task 67)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.self_audit.schemas import (
    ErrorCategory,
    ErrorCluster,
    ErrorSeverity,
)

logger = logging.getLogger("kairo.self_audit.errors")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class ErrorManager:
    """Classifies operational failures across the 12-category taxonomy and detects clusters (Spec 27, 29, 31)."""

    def __init__(self) -> None:
        self._clusters: dict[str, ErrorCluster] = {}
        self._history: list[dict[str, Any]] = []

    def record_error(
        self,
        category: ErrorCategory,
        severity: ErrorSeverity,
        description: str,
        error_code: str = "",
        tenant_id: str = "default",
    ) -> dict[str, Any]:
        """Record an operational error and evaluate clustering / recurring patterns (Spec 27, 29)."""
        error_id = f"err_{uuid.uuid4().hex[:8]}"
        entry = {
            "error_id": error_id,
            "category": category.value,
            "severity": severity.value,
            "description": description,
            "error_code": error_code or category.value,
            "timestamp": _now_utc().isoformat(),
            "tenant_id": tenant_id,
        }
        self._history.append(entry)

        # Check for clustering / recurring failure patterns (Spec 29, 31)
        cluster_key = f"{category.value}_{error_code or 'general'}"
        cluster = self._clusters.get(cluster_key)
        if not cluster:
            cluster = ErrorCluster(
                cluster_id=f"cls_{uuid.uuid4().hex[:8]}",
                error_category=category,
                pattern_name=error_code or f"Recurring {category.value}",
                recurring_count=1,
                root_cause_hypothesis=f"Initial hypothesis: Systematic deficit in {category.value.lower()}.",
                is_verified=False,
                sample_error_ids=[error_id],
                first_detected_at=_now_utc(),
                last_detected_at=_now_utc(),
            )
            self._clusters[cluster_key] = cluster
        else:
            cluster.recurring_count += 1
            cluster.last_detected_at = _now_utc()
            if len(cluster.sample_error_ids) < 10:
                cluster.sample_error_ids.append(error_id)

            if cluster.recurring_count >= 3:
                logger.warning(
                    "RECURRING_FAILURE_PATTERN: pattern=%s count=%d category=%s",
                    cluster.pattern_name,
                    cluster.recurring_count,
                    category.value,
                )

        return entry

    def get_clusters(self) -> list[ErrorCluster]:
        return list(self._clusters.values())

    def get_error_heatmap(self) -> dict[str, int]:
        """Generate category distribution for dashboard visualization (Spec 61)."""
        heatmap: dict[str, int] = {cat.value: 0 for cat in ErrorCategory}
        for err in self._history:
            heatmap[err["category"]] = heatmap.get(err["category"], 0) + 1
        return heatmap


class RationalizationDetector:
    """Detects when Kairo repeatedly justifies failures without modifying underlying behavior (Spec 70, 71)."""

    def __init__(self) -> None:
        self._explanations: list[dict[str, Any]] = []

    def record_failure_explanation(
        self,
        failure_event: str,
        explanation_given: str,
        behavior_adjusted: bool,
    ) -> dict[str, Any]:
        """Record explanation and flag RATIONALIZATION_PATTERN if behavior remains static (Spec 71)."""
        entry = {
            "failure": failure_event,
            "explanation": explanation_given,
            "behavior_adjusted": behavior_adjusted,
            "timestamp": _now_utc().isoformat(),
        }
        self._explanations.append(entry)

        # Check last 4 failure explanations: if >= 3 were justified without adjusting behavior
        recent = self._explanations[-4:]
        unadjusted_count = sum(1 for e in recent if not e["behavior_adjusted"])

        is_rationalizing = len(recent) >= 3 and unadjusted_count >= 3
        if is_rationalizing:
            logger.warning(
                "RATIONALIZATION_PATTERN: System repeatedly justified failures without behavioral adjustment."
            )

        return {
            "is_rationalizing": is_rationalizing,
            "unadjusted_failure_count": unadjusted_count,
            "pattern_alert": "RATIONALIZATION_PATTERN" if is_rationalizing else None,
        }


class InterventionTracker:
    """Evaluates whether self-correction recommendations produced verified improvement (Spec 72, 73)."""

    @classmethod
    def evaluate_intervention(
        cls,
        intervention_name: str,
        expected_metric_delta_pct: float,
        actual_metric_delta_pct: float,
    ) -> dict[str, Any]:
        """Validate intervention efficacy against empirical outcomes.

        Invariant: Do not claim correction succeeded without evidence (Spec 73, 82).
        """
        is_effective = actual_metric_delta_pct >= (expected_metric_delta_pct * 0.7)
        return {
            "intervention": intervention_name,
            "expected_delta_pct": expected_metric_delta_pct,
            "actual_delta_pct": actual_metric_delta_pct,
            "is_effective": is_effective,
            "status": "VERIFIED_EFFECTIVE" if is_effective else "INEFFECTIVE_INTERVENTION",
        }
