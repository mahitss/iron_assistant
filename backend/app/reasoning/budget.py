"""Reasoning budget and stopping criteria coordinator for Kairo Reasoning (Task 71).

Monitors cognitive effort, enforcing bounded deliberation:
- Iteration, latency, and tool-call bounds
- Explicit stopping criteria (confidence reached, evidence sufficient, budget exhausted)
- Escalation triggering (NEEDS_MORE_EVIDENCE, NEEDS_TOOL, NEEDS_HUMAN_REVIEW)
"""

import logging
from datetime import UTC, datetime

from app.reasoning.schemas import (
    EscalationType,
    ReasoningBudget,
    ReasoningConfidence,
    ReasoningDepth,
    SubProblem,
)

logger = logging.getLogger(__name__)


class BudgetCoordinator:
    """Controls deliberation budget and decides stopping / escalation boundaries."""

    @staticmethod
    def initialize_budget(depth: ReasoningDepth) -> ReasoningBudget:
        """Derive resource bounds based on requested reasoning depth."""
        if depth == ReasoningDepth.QUICK:
            return ReasoningBudget(
                max_depth=1,
                max_subproblems=2,
                max_hypotheses=3,
                max_iterations=4,
                max_latency_sec=15.0,
                max_tool_calls=1,
            )
        elif depth == ReasoningDepth.DEEP:
            return ReasoningBudget(
                max_depth=3,
                max_subproblems=10,
                max_hypotheses=8,
                max_iterations=20,
                max_latency_sec=120.0,
                max_tool_calls=8,
            )
        elif depth == ReasoningDepth.CRITICAL:
            return ReasoningBudget(
                max_depth=4,
                max_subproblems=12,
                max_hypotheses=10,
                max_iterations=30,
                max_latency_sec=180.0,
                max_tool_calls=12,
            )
        # STANDARD
        return ReasoningBudget(
            max_depth=3,
            max_subproblems=6,
            max_hypotheses=5,
            max_iterations=10,
            max_latency_sec=60.0,
            max_tool_calls=4,
        )

    def record_iteration(self, budget: ReasoningBudget) -> bool:
        """Increment iteration count. Returns True if within budget, False if exhausted."""
        budget.iterations_used += 1
        if budget.iterations_used >= budget.max_iterations:
            logger.warning(
                f"Reasoning budget iteration limit reached ({budget.iterations_used}/{budget.max_iterations})"
            )
            return False
        return True

    def record_tool_call(self, budget: ReasoningBudget) -> bool:
        """Increment tool calls. Returns True if permitted, False if limit exceeded."""
        if budget.tool_calls_used >= budget.max_tool_calls:
            logger.warning(
                f"Reasoning tool budget exhausted ({budget.tool_calls_used}/{budget.max_tool_calls})"
            )
            return False
        budget.tool_calls_used += 1
        return True

    def should_stop(
        self,
        budget: ReasoningBudget,
        start_time: datetime,
        current_confidence: ReasoningConfidence,
        required_confidence: ReasoningConfidence,
        subproblems: list[SubProblem],
    ) -> tuple[bool, str]:
        """Evaluate if deliberation should stop.

        Returns (should_stop, reason).
        """
        # 1. Check time budget
        elapsed = (datetime.now(UTC) - start_time).total_seconds()
        if elapsed >= budget.max_latency_sec:
            return True, f"Time budget exhausted ({elapsed:.1f}s >= {budget.max_latency_sec}s)"

        # 2. Check iteration budget
        if budget.iterations_used >= budget.max_iterations:
            return True, f"Iteration budget exhausted ({budget.iterations_used}/{budget.max_iterations})"

        # 3. Check if all subproblems are resolved
        if subproblems and all(sp.status == "RESOLVED" for sp in subproblems):
            return True, "All sub-problems resolved"

        # 4. Check confidence sufficiency
        confidence_ranks = {
            ReasoningConfidence.VERY_LOW: 1,
            ReasoningConfidence.LOW: 2,
            ReasoningConfidence.MEDIUM: 3,
            ReasoningConfidence.HIGH: 4,
            ReasoningConfidence.VERY_HIGH: 5,
        }
        if confidence_ranks.get(current_confidence, 1) >= confidence_ranks.get(required_confidence, 3):
            return (
                True,
                f"Required confidence achieved ({current_confidence.value} >= {required_confidence.value})",
            )

        return False, "Deliberation continuing"

    def evaluate_escalation(
        self,
        budget: ReasoningBudget,
        current_confidence: ReasoningConfidence,
        has_contradictions: bool,
        risk_level: str,
    ) -> EscalationType | None:
        """Determine if deliberation should escalate to external review or specialist."""
        if risk_level == "CRITICAL" and (
            has_contradictions
            or current_confidence in (ReasoningConfidence.VERY_LOW, ReasoningConfidence.LOW)
        ):
            return EscalationType.NEEDS_HUMAN_REVIEW

        if budget.tool_calls_used >= budget.max_tool_calls and current_confidence == ReasoningConfidence.LOW:
            return EscalationType.NEEDS_TOOL

        if budget.iterations_used >= budget.max_iterations and current_confidence in (
            ReasoningConfidence.VERY_LOW,
            ReasoningConfidence.LOW,
        ):
            return EscalationType.NEEDS_MORE_EVIDENCE

        return None
