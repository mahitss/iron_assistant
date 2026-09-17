"""Goal and Outcome Inference Engine for Task 108.

Infers likely desired goals from structured intent while preserving:
- GoalHypothesis != Authoritative Goal (Goal Management in Task 100 remains authoritative).
- Explicit command vs Inferred hypothesis (explicit has higher confidence and fewer unproven assumptions).
- Missing targets remain UNKNOWN; zero hallucination of certainty.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.intent.domain import (
    EpistemicStatus,
    GoalHypothesis,
    Intent,
    generate_id,
    utc_now,
)

logger = logging.getLogger("kairo.intent.goal_inference")


class GoalInferenceEngine:
    """Infers goal hypotheses from intent representations without assuming authority."""

    @classmethod
    def infer_goal(cls, intent: Intent, context: Optional[Dict[str, Any]] = None) -> GoalHypothesis:
        """Infers candidate goal hypothesis from an intent node."""
        is_explicit = intent.target_epistemic == EpistemicStatus.EXPLICIT
        epistemic = EpistemicStatus.EXPLICIT if is_explicit and intent.overall_confidence > 0.8 else EpistemicStatus.INFERRED

        # Formulate title
        action = intent.action_class or intent.category.value.lower()
        target = intent.target if intent.target != "UNKNOWN" else "unspecified target"
        title = f"{action.capitalize()} {target}".strip()

        description = f"User desires to {action} {target} within scope {intent.scope}."

        target_state = {
            "action": action,
            "target": intent.target,
            "status": "COMPLETED",
            "scope": intent.scope,
        }

        assumptions: List[str] = []
        if intent.target == "UNKNOWN":
            assumptions.append("Target is currently unknown; requires resolution or clarification before execution.")
            confidence = 0.4
        elif is_explicit:
            confidence = 0.95
        else:
            assumptions.append(f"Inferred intent category '{intent.category.value}' matches user objective.")
            confidence = 0.75

        evidence = [f"Derived directly from user instruction: '{intent.summary}'"]

        hypothesis = GoalHypothesis(
            hypothesis_id=generate_id("ghyp"),
            intent_id=intent.intent_id,
            title=title,
            description=description,
            target_state=target_state,
            confidence=confidence,
            evidence_ids=evidence,
            assumptions=assumptions,
            epistemic_status=epistemic,
            created_at=utc_now(),
        )

        logger.info("Inferred goal hypothesis %s ('%s', confidence=%.2f, epistemic=%s)",
                    hypothesis.hypothesis_id, hypothesis.title, confidence, epistemic.value)
        return hypothesis
