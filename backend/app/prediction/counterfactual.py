"""Counterfactual Engine, Hypothetical Modeling, and Reality Separation (Task 47)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional
import uuid

logger = logging.getLogger("kairo.prediction.counterfactual")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class CounterfactualResult:
    """Hypothetical counterfactual exploration strictly labeled as non-historical (Spec 11, 121-123)."""

    counterfactual_id: str
    subject: str
    label: str = "HYPOTHETICAL"  # Mandatory flag (Spec 122)
    is_hypothetical: bool = True
    is_historical_fact: bool = False  # Enforce Spec 123: Counterfactual must NEVER be stored as historical fact
    hypothesis: str = ""
    no_intervention_outcome: Dict[str, Any] = field(default_factory=dict)
    intervention_outcome: Optional[Dict[str, Any]] = None
    explanation: str = ""
    timestamp: datetime = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "counterfactual_id": self.counterfactual_id,
            "subject": self.subject,
            "label": self.label,
            "is_hypothetical": self.is_hypothetical,
            "is_historical_fact": self.is_historical_fact,
            "hypothesis": self.hypothesis,
            "no_intervention_outcome": self.no_intervention_outcome,
            "intervention_outcome": self.intervention_outcome,
            "explanation": self.explanation,
            "timestamp": self.timestamp.isoformat(),
        }


class CounterfactualEngine:
    """Explores alternative scenarios without corrupting historical or World Model facts (Spec 11, 121-123)."""

    @classmethod
    def evaluate_counterfactual(
        cls,
        subject: str,
        current_trend: Any,
        proposed_action: Optional[str] = None,
        hypothetical_action: Optional[str] = None,
        action_effect_delta: Optional[Dict[str, Any]] = None,
        horizon_hours: int = 24,
    ) -> CounterfactualResult:
        """Enforce Spec 121: Answer 'What happens if we don't intervene?' and 'What happens if we take action X?'"""
        cid = f"cf_{uuid.uuid4().hex[:8]}"
        action = proposed_action or hypothetical_action

        # Trend format handling
        trend_dict = current_trend if isinstance(current_trend, dict) else {"trend_description": str(current_trend)}

        no_action_outcome = dict(trend_dict)
        if "latency_ms" in no_action_outcome:
            no_action_outcome["projected_latency_ms"] = no_action_outcome["latency_ms"] * 1.5
            no_action_outcome["status"] = "DEGRADED"
        else:
            no_action_outcome["projected_exhaustion"] = f"Within {horizon_hours} hours under baseline trajectory"

        intv_outcome = None
        if action:
            intv_outcome = dict(trend_dict)
            if action_effect_delta:
                intv_outcome.update(action_effect_delta)
            else:
                intv_outcome["projected_status"] = "STABILIZED"
                intv_outcome["intervention_benefit"] = f"Action '{action}' arrests negative drift"
            hypothesis = f"Intervention scenario: if action '{action}' is executed over {horizon_hours}h horizon"
            explanation = f"Hypothetical evaluation: Applying '{action}' is projected to alleviate trend."
        else:
            hypothesis = f"Baseline counterfactual: No intervention occurs over {horizon_hours}h horizon"
            explanation = "Hypothetical evaluation: Without operational intervention, baseline trend persists."

        res = CounterfactualResult(
            counterfactual_id=cid,
            subject=subject,
            label="HYPOTHETICAL",
            is_hypothetical=True,
            is_historical_fact=False,
            hypothesis=hypothesis,
            no_intervention_outcome=no_action_outcome,
            intervention_outcome=intv_outcome,
            explanation=explanation,
        )
        logger.info("Computed counterfactual %s for %s: '%s'", cid, subject, hypothesis)
        return res
