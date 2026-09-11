"""Multi-Metric Progress Engine, Milestone Verification, and Sunk Cost Defense (Task 66)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.missions.schemas import (
    Goal,
)

logger = logging.getLogger("kairo.missions.progress")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class ProgressEngine:
    """Calculates multi-dimensional mission progress and defends against false completion."""

    @classmethod
    def calculate_progress(
        cls,
        total_tasks: int,
        completed_tasks: int,
        verified_milestones: int,
        total_milestones: int,
    ) -> float:
        """Calculate holistic progress percentage.

        Avoid simplistic single-metric percentage. Blends task execution (40%)
        with verified milestones (60%).
        """
        task_ratio = (completed_tasks / total_tasks) if total_tasks > 0 else 0.0
        milestone_ratio = (verified_milestones / total_milestones) if total_milestones > 0 else 0.0

        if total_milestones > 0:
            pct = (task_ratio * 0.4 + milestone_ratio * 0.6) * 100.0
        else:
            pct = task_ratio * 100.0

        return round(min(100.0, max(0.0, pct)), 1)

    @classmethod
    def verify_milestone(
        cls,
        milestone_id: str,
        completion_criteria: list[str],
        empirical_evidence: list[str],
    ) -> bool:
        """Verify milestone against empirical criteria (Spec 30).

        Invariant: Do not mark complete merely because a task reported 'done'.
        Requires at least one empirical evidence match per criterion.
        """
        if not completion_criteria:
            return False

        if not empirical_evidence:
            logger.warning("Milestone %s verification failed: No empirical evidence provided.", milestone_id)
            return False

        # Invariant: Each criterion must have corresponding empirical verification evidence
        matched_criteria = 0
        for crit in completion_criteria:
            crit_low = crit.lower()
            if any(crit_low in ev.lower() or "verified" in ev.lower() for ev in empirical_evidence):
                matched_criteria += 1

        return matched_criteria == len(completion_criteria)

    @classmethod
    def evaluate_goal_success(
        cls,
        goal: Goal,
        metric_readings: dict[str, Any],
    ) -> tuple[bool, list[str]]:
        """Evaluate whether goal success criteria are met (Spec 10, 75, 76).

        Invariant: PROGRESS != SUCCESS.
        TASK COMPLETION != GOAL COMPLETION.
        TOOL SUCCESS != GOAL SUCCESS.
        """
        if not goal.success_criteria:
            return False, ["No success criteria defined for goal."]

        reasons: list[str] = []
        all_passed = True

        for crit in goal.success_criteria:
            if crit.criteria_type == "metric_threshold":
                actual = metric_readings.get(crit.target_metric)
                if actual is None:
                    all_passed = False
                    reasons.append(f"Metric '{crit.target_metric}' not available in telemetry readings.")
                    continue

                target = float(crit.target_value) if crit.target_value is not None else 0.0
                actual_val = float(actual)
                crit.current_value = actual_val

                passed = False
                if crit.comparison_operator == "lte":
                    passed = actual_val <= target
                elif crit.comparison_operator == "lt":
                    passed = actual_val < target
                elif crit.comparison_operator == "gte":
                    passed = actual_val >= target
                elif crit.comparison_operator == "gt":
                    passed = actual_val > target
                elif crit.comparison_operator == "eq":
                    passed = actual_val == target

                crit.is_verified = passed
                if not passed:
                    all_passed = False
                    reasons.append(
                        f"Target metric '{crit.target_metric}' {actual_val} did not satisfy {crit.comparison_operator} {target}."
                    )
                else:
                    crit.verified_at = _now_utc()
                    crit.verification_evidence.append(f"Metric {actual_val} passed threshold {target}.")

            elif crit.criteria_type == "verification_result":
                if not crit.is_verified:
                    all_passed = False
                    reasons.append(f"Verification result for '{crit.description}' is still pending.")

        return all_passed, reasons

    @classmethod
    def evaluate_sunk_cost(
        cls,
        consecutive_failures: int,
        cost_incurred: float,
        expected_future_value: float,
    ) -> tuple[bool, str]:
        """Sunk Cost Defense (Spec 34).

        Kairo must not continue a failing strategy because 'we already spent time/money on it'.
        """
        if consecutive_failures >= 3 and expected_future_value < 0.3:
            return (
                True,
                f"SUNK COST ALERT: Strategy has failed {consecutive_failures} times and expected future value ({expected_future_value:.2f}) "
                f"is low. Halt continuation despite ${cost_incurred:.2f} already incurred.",
            )
        return False, "Strategy remains viable."
