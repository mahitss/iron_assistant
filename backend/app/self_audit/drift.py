"""Behavioral Baseline Tracking, Drift Detection, and Goal/Proxy Alignment Audit (Task 67)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.self_audit.schemas import (
    BehaviorBaseline,
    ErrorCategory,
    ErrorSeverity,
)

logger = logging.getLogger("kairo.self_audit.drift")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class BehaviorDriftDetector:
    """Detects systematic operational and behavioral drift against historical baselines (Spec 32, 33, 34)."""

    def __init__(self) -> None:
        self._baselines: dict[str, BehaviorBaseline] = {
            "verification_frequency": BehaviorBaseline(
                baseline_id="bsl_verif",
                metric_name="verification_frequency",
                normal_mean=0.90,
                normal_std=0.05,
                drift_threshold_pct=30.0,
                current_value=0.90,
            ),
            "tool_call_rate": BehaviorBaseline(
                baseline_id="bsl_tools",
                metric_name="tool_call_rate",
                normal_mean=5.2,
                normal_std=1.2,
                drift_threshold_pct=50.0,
                current_value=5.2,
            ),
            "retry_frequency": BehaviorBaseline(
                baseline_id="bsl_retries",
                metric_name="retry_frequency",
                normal_mean=0.10,
                normal_std=0.04,
                drift_threshold_pct=60.0,
                current_value=0.10,
            ),
            "reported_confidence": BehaviorBaseline(
                baseline_id="bsl_conf",
                metric_name="reported_confidence",
                normal_mean=0.75,
                normal_std=0.10,
                drift_threshold_pct=35.0,
                current_value=0.75,
            ),
        }

    def update_metric(self, metric_name: str, current_value: float) -> BehaviorBaseline:
        """Update current operational reading and evaluate drift against threshold (Spec 34)."""
        baseline = self._baselines.get(metric_name)
        if not baseline:
            baseline = BehaviorBaseline(
                baseline_id=f"bsl_{uuid.uuid4().hex[:8]}",
                metric_name=metric_name,
                normal_mean=current_value,
                current_value=current_value,
            )
            self._baselines[metric_name] = baseline
            return baseline

        baseline.current_value = current_value
        baseline.updated_at = _now_utc()

        # Check percentage deviation from baseline mean
        if baseline.normal_mean > 0:
            diff_pct = abs(current_value - baseline.normal_mean) / baseline.normal_mean * 100.0
            if diff_pct >= baseline.drift_threshold_pct:
                baseline.is_drifting = True
                direction = "dropped" if current_value < baseline.normal_mean else "increased"
                baseline.drift_reason = (
                    f"BEHAVIOR_DRIFT: {metric_name} {direction} by {diff_pct:.1f}% "
                    f"(current={current_value:.2f}, baseline={baseline.normal_mean:.2f})."
                )
                logger.warning(baseline.drift_reason)
            else:
                baseline.is_drifting = False
                baseline.drift_reason = ""

        return baseline

    def get_active_drifts(self) -> list[dict[str, Any]]:
        """Retrieve all currently active behavioral drift alerts."""
        drifts: list[dict[str, Any]] = []
        for name, b in self._baselines.items():
            if b.is_drifting:
                drifts.append(
                    {
                        "metric_name": name,
                        "baseline_mean": b.normal_mean,
                        "current_value": b.current_value,
                        "drift_reason": b.drift_reason,
                        "alert_code": f"{name.upper()}_BEHAVIOR_DRIFT",
                    }
                )
        return drifts

    def list_baselines(self) -> list[BehaviorBaseline]:
        return list(self._baselines.values())


class GoalAlignmentAuditor:
    """Audits purpose alignment and defends against proxy metric manipulation (Spec 35, 36, 37)."""

    @classmethod
    def audit_goal_alignment(
        cls,
        original_goal_description: str,
        recent_actions: list[str],
        optimization_metrics: list[str] | None = None,
    ) -> dict[str, Any]:
        """Verify ongoing action stream remains aligned with authorized goal (Spec 35)."""
        goal_keywords = set(original_goal_description.lower().split())
        actions_text = " ".join(recent_actions).lower()

        overlap = sum(1 for w in goal_keywords if len(w) > 4 and w in actions_text)
        divergence = 1.0 - (overlap / max(1, len(goal_keywords)))

        is_drifting = divergence > 0.70 and len(recent_actions) >= 3
        return {
            "original_goal": original_goal_description,
            "actions_analyzed": len(recent_actions),
            "divergence_score": round(divergence, 2),
            "is_goal_drifting": is_drifting,
            "status": "GOAL_DRIFT_DETECTED" if is_drifting else "ALIGNED",
        }

    @classmethod
    def detect_proxy_gaming(
        cls,
        true_objective_metric: str,
        proxy_metric: str,
        true_metric_delta_pct: float,
        proxy_metric_delta_pct: float,
    ) -> dict[str, Any]:
        """Detect proxy gaming / Goodhart's law where metric improves but reality degrades (Spec 37).

        Example: Incident count drops by 40% (proxy) while failure rate rises by 15% (reality).
        """
        is_gaming = proxy_metric_delta_pct > 20.0 and true_metric_delta_pct < -5.0
        details = ""
        if is_gaming:
            details = (
                f"METRIC_GAMING_RISK: Proxy metric '{proxy_metric}' improved by +{proxy_metric_delta_pct:.1f}%, "
                f"while true objective '{true_objective_metric}' degraded by {true_metric_delta_pct:.1f}%."
            )
            logger.error(details)

        return {
            "true_objective_metric": true_objective_metric,
            "proxy_metric": proxy_metric,
            "is_proxy_gaming": is_gaming,
            "alert": details if is_gaming else None,
            "category": ErrorCategory.GOAL_ERROR.value if is_gaming else None,
            "severity": ErrorSeverity.HIGH.value if is_gaming else ErrorSeverity.INFO.value,
        }
