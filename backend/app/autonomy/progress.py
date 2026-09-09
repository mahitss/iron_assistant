"""Verified Progress Tracking and No-Progress Loop Detection (Task 45)."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any, Dict, List

logger = logging.getLogger("kairo.autonomy.progress")


class NoProgressLoopError(Exception):
    """Raised when an autonomous run executes repeated cycles without achieving verified progress."""


@dataclass
class ProgressSnapshot:
    """Accurate progress report grounded in verified criteria and artifacts (Spec 57-61)."""

    total_steps: int
    completed_steps: int
    verified_criteria_count: int
    total_criteria_count: int
    verified_artifacts_count: int
    percentage: float
    summary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "verified_criteria_count": self.verified_criteria_count,
            "total_criteria_count": self.total_criteria_count,
            "verified_artifacts_count": self.verified_artifacts_count,
            "percentage": round(self.percentage, 1),
            "summary": self.summary,
        }


class ProgressTracker:
    """Calculates objective progress and halts stagnant or oscillating loops (Spec 57-61, 148-152)."""

    def __init__(self, max_stagnant_cycles: int = 4) -> None:
        self.max_stagnant_cycles = max_stagnant_cycles
        self._stagnant_cycles_count: int = 0
        self._last_completed_count: int = 0
        self._recent_step_history: List[str] = []

    def calculate_progress(
        self,
        total_steps: int,
        completed_steps: int,
        total_criteria: int,
        verified_criteria: int,
        verified_artifacts: int,
    ) -> ProgressSnapshot:
        """Compute verified progress percentage without inflating based on model calls (Spec 58, 61)."""
        if total_steps == 0:
            pct = 100.0 if total_criteria == 0 else 0.0
        else:
            step_ratio = completed_steps / total_steps
            crit_ratio = (verified_criteria / total_criteria) if total_criteria > 0 else step_ratio
            # 60% weight on verified criteria, 40% on completed steps
            pct = (crit_ratio * 60.0) + (step_ratio * 40.0)

        summary = f"{completed_steps}/{total_steps} steps finished; {verified_criteria}/{total_criteria} criteria verified"
        return ProgressSnapshot(
            total_steps=total_steps,
            completed_steps=completed_steps,
            verified_criteria_count=verified_criteria,
            total_criteria_count=total_criteria,
            verified_artifacts_count=verified_artifacts,
            percentage=round(min(100.0, max(0.0, pct)), 1),
            summary=summary,
        )

    def record_step_execution(self, step_id: str, completed_count: int) -> None:
        """Track progress and detect oscillating loops (e.g., A -> B -> A -> B) (Spec 150-152)."""
        # 1. Stagnation check: If no new step completed over multiple cycles
        if completed_count <= self._last_completed_count:
            self._stagnant_cycles_count += 1
            if self._stagnant_cycles_count >= self.max_stagnant_cycles:
                logger.error("No-progress loop detected: %d cycles without new verified completion.", self._stagnant_cycles_count)
                raise NoProgressLoopError(
                    f"Autonomous run halted: No verified progress made across {self._stagnant_cycles_count} consecutive execution cycles."
                )
        else:
            self._stagnant_cycles_count = 0
            self._last_completed_count = completed_count

        # 2. Oscillation check: Detect repeating sequence
        self._recent_step_history.append(step_id)
        if len(self._recent_step_history) >= 6:
            h = self._recent_step_history[-6:]
            if h[0] == h[2] == h[4] and h[1] == h[3] == h[5]:
                logger.critical("Oscillating step loop detected: %s -> %s repeating", h[0], h[1])
                raise NoProgressLoopError(f"Autonomous loop detected: Repeating execution pattern between {h[0]} and {h[1]}.")
