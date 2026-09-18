"""Value-of-Waiting Engine for Task 114.
Assesses whether allowing natural state transitions or pending operations to converge is preferable to active probing.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("kairo.observation.waiting_engine")


class ValueOfWaitingEngine:
    """Evaluates the epistemic and cost benefits of waiting for natural telemetry arrival (Section 17)."""

    @classmethod
    def evaluate_waiting(
        cls,
        target_entity: str,
        expected_event_in_seconds: float = 5.0,
        deadline_seconds: Optional[float] = None,
        pending_operation_active: bool = True,
    ) -> Dict[str, Any]:
        """Determines if waiting is superior to initiating active queries."""
        # Check deadline constraint: Invariant: Deadline makes waiting invalid if wait > deadline (Section 45, Scenario J)
        if deadline_seconds is not None and expected_event_in_seconds >= deadline_seconds:
            return {
                "is_wait_advisable": False,
                "reason": f"Urgent deadline ({deadline_seconds:.1f}s) precludes waiting for natural convergence ({expected_event_in_seconds:.1f}s).",
                "recommended_wait_seconds": 0.0,
            }

        if pending_operation_active and expected_event_in_seconds <= 10.0:
            return {
                "is_wait_advisable": True,
                "reason": f"Natural telemetry for '{target_entity}' is expected within {expected_event_in_seconds:.1f}s from in-flight operation. Zero cost.",
                "recommended_wait_seconds": expected_event_in_seconds,
            }

        return {
            "is_wait_advisable": False,
            "reason": f"No imminent natural event detected for '{target_entity}'; active observation is warranted if VoI > cost.",
            "recommended_wait_seconds": 0.0,
        }
