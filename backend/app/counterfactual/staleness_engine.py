"""Staleness detection and cache invalidation engine for Task 113.
Ensures counterfactual analyses whose underlying world states, causal models,
or assumptions have changed are explicitly marked STALE and rejected from silent reuse.
"""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Any

from app.counterfactual.domain import (
    CounterfactualAnalysis,
    CounterfactualLifecycleStage,
)

logger = logging.getLogger("kairo.counterfactual.staleness_engine")


class StalenessEngine:
    """Evaluates whether an existing counterfactual analysis has become stale."""

    @classmethod
    def check_staleness(
        cls,
        analysis: CounterfactualAnalysis,
        current_world_state: dict[str, Any] | None = None,
        active_causal_version: str = "v1.0",
        active_capabilities: set[str] | None = None,
        external_dependency_health: dict[str, str] | None = None,
    ) -> tuple[bool, str]:
        """Evaluates staleness conditions against current environment state."""
        # 1. Causal model version mismatch
        if analysis.causal_model_version != active_causal_version:
            return True, f"CAUSAL_MODEL_CHANGED: Analysis used {analysis.causal_model_version}, active model is {active_causal_version}"

        # 2. Material world-state divergence from baseline
        if current_world_state:
            baseline_status = analysis.baseline.state_snapshot.get("status")
            current_status = current_world_state.get("status")
            if baseline_status and current_status and baseline_status != current_status:
                return True, f"WORLD_STATE_DIVERGENCE: Entity status changed from {baseline_status} to {current_status}"

        # 3. External dependency degradation
        if external_dependency_health:
            for dep, health in external_dependency_health.items():
                if health in ("DEGRADED", "DOWN", "TIMEOUT"):
                    return True, f"EXTERNAL_DEPENDENCY_DEGRADED: Dependency {dep} is {health}"

        # 4. Age-based expiration (default 1 hour horizon)
        age_seconds = (datetime.now(UTC) - analysis.created_at).total_seconds()
        if age_seconds > 3600:
            return True, f"HORIZON_EXPIRED: Analysis age ({int(age_seconds)}s) exceeds 3600s validity window"

        return False, ""

    @classmethod
    def mark_stale_if_needed(
        cls,
        analysis: CounterfactualAnalysis,
        current_world_state: dict[str, Any] | None = None,
        active_causal_version: str = "v1.0",
        external_dependency_health: dict[str, str] | None = None,
    ) -> CounterfactualAnalysis:
        """Applies staleness update to analysis record if conditions are met."""
        is_stale, reason = cls.check_staleness(
            analysis=analysis,
            current_world_state=current_world_state,
            active_causal_version=active_causal_version,
            external_dependency_health=external_dependency_health,
        )
        if is_stale:
            analysis.is_stale = True
            analysis.stale_reason = reason
            analysis.lifecycle_stage = CounterfactualLifecycleStage.STALE
            analysis.updated_at = datetime.now(UTC)
            logger.info("Marked counterfactual %s as STALE: %s", analysis.analysis_id, reason)
        return analysis
