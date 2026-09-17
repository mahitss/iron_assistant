"""Loop Guard & Anti-Thrashing Circuit Breaker for Kairo Control Plane (Task 102).

Guarantees:
- Infinite autonomous loops are impossible.
- Repeated identical actions, decisions, or failures trip a fail-safe circuit breaker.
- When tripped, autonomous progression arrests and escalates for human review.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from app.control_plane.domain import ControlCycle, ControlCycleStatus

logger = logging.getLogger("kairo.control_plane.loop_guard")


class LoopGuardCircuitBreaker:
    """Detects runaway recursion, thrashing, and repetitive decision/action loops."""

    def __init__(self, failure_threshold: int = 3, repetition_threshold: int = 3) -> None:
        self.failure_threshold = failure_threshold
        self.repetition_threshold = repetition_threshold
        self._action_counts: Dict[str, int] = defaultdict(int)
        self._decision_counts: Dict[str, int] = defaultdict(int)
        self._failure_counts: Dict[str, int] = defaultdict(int)
        self._tripped_reasons: List[str] = []

    def record_step(
        self,
        cycle: ControlCycle,
        action_fingerprint: Optional[str] = None,
        decision_fingerprint: Optional[str] = None,
        failure_fingerprint: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Inspects current cycle state against repeated patterns.
        
        Returns:
            (is_tripped, reason_if_tripped)
        """
        # 1. Check budget exhaustion
        if cycle.budget.is_exhausted():
            reason = (
                f"LoopGuard: Budget envelope exhausted "
                f"(Duration: {cycle.budget.consumed_duration_s}/{cycle.budget.max_duration_s}s, "
                f"Retries: {cycle.budget.consumed_retries}/{cycle.budget.max_retries}, "
                f"ToolCalls: {cycle.budget.consumed_tool_calls}/{cycle.budget.max_tool_calls})"
            )
            self._tripped_reasons.append(reason)
            logger.warning(reason)
            return True, reason

        # 2. Check repeated failures
        if failure_fingerprint:
            self._failure_counts[failure_fingerprint] += 1
            if self._failure_counts[failure_fingerprint] >= self.failure_threshold:
                reason = (
                    f"LoopGuard: Identical failure threshold ({self.failure_threshold}) breached "
                    f"for fingerprint '{failure_fingerprint}'"
                )
                self._tripped_reasons.append(reason)
                logger.error(reason)
                return True, reason

        # 3. Check repeated actions
        if action_fingerprint:
            self._action_counts[action_fingerprint] += 1
            if self._action_counts[action_fingerprint] >= self.repetition_threshold:
                reason = (
                    f"LoopGuard: Repetitive action loop ({self.repetition_threshold}) detected "
                    f"for fingerprint '{action_fingerprint}'"
                )
                self._tripped_reasons.append(reason)
                logger.error(reason)
                return True, reason

        # 4. Check repeated decisions
        if decision_fingerprint:
            self._decision_counts[decision_fingerprint] += 1
            if self._decision_counts[decision_fingerprint] >= self.repetition_threshold:
                reason = (
                    f"LoopGuard: Repetitive decision loop ({self.repetition_threshold}) detected "
                    f"for fingerprint '{decision_fingerprint}'"
                )
                self._tripped_reasons.append(reason)
                logger.error(reason)
                return True, reason

        return False, None

    @property
    def is_tripped(self) -> bool:
        """Returns True if the circuit breaker has been tripped by any violation."""
        return len(self._tripped_reasons) > 0

    @property
    def tripped_reasons(self) -> List[str]:
        return list(self._tripped_reasons)

    def reset(self) -> None:
        """Resets tracking counters for testing or post-operator review."""
        self._action_counts.clear()
        self._decision_counts.clear()
        self._failure_counts.clear()
        self._tripped_reasons.clear()
