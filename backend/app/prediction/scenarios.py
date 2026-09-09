"""Scenario Generation, Plausible Alternative Futures, and Intervention Modeling (Task 47)."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger("kairo.prediction.scenarios")


@dataclass
class Scenario:
    """Distinct plausible future state with explicit prerequisites and likelihood (Spec 7-11)."""

    description: str
    scenario_id: str = field(default_factory=lambda: f"scen_{uuid.uuid4().hex[:8]}")
    prerequisites: List[str] = field(default_factory=list)
    expected_state: Dict[str, Any] = field(default_factory=dict)
    likelihood: float = 0.5
    impact: float = 0.5
    evidence: Any = field(default_factory=list)
    is_counterfactual: bool = False
    is_baseline: bool = False
    intervention: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "description": self.description,
            "prerequisites": self.prerequisites,
            "expected_state": self.expected_state,
            "likelihood": round(self.likelihood, 3),
            "impact": round(self.impact, 3),
            "evidence": self.evidence,
            "is_counterfactual": self.is_counterfactual,
            "is_baseline": self.is_baseline,
            "intervention": self.intervention,
        }


class ScenarioGenerator:
    """Generates plausible alternative futures, baseline trajectories, and intervention scenarios (Spec 8-11)."""

    @classmethod
    def create_baseline(
        cls,
        description: str,
        expected_state: Dict[str, Any],
        likelihood: float = 0.7,
        impact: float = 0.5,
        evidence: Optional[List[str]] = None,
    ) -> Scenario:
        """Create baseline future when no intervention occurs."""
        return Scenario(
            description=description,
            expected_state=expected_state,
            likelihood=likelihood,
            impact=impact,
            evidence=evidence or [],
            is_baseline=True,
            is_counterfactual=False,
        )

    @classmethod
    def create_intervention(
        cls,
        description: str,
        intervention_action: str,
        expected_state: Dict[str, Any],
        likelihood: float = 0.8,
        impact: float = 0.4,
        prerequisites: Optional[List[str]] = None,
        evidence: Optional[List[str]] = None,
    ) -> Scenario:
        """Create conditional intervention scenario: 'If action X occurs, expected outcome may be Y'."""
        return Scenario(
            description=description,
            expected_state=expected_state,
            likelihood=likelihood,
            impact=impact,
            prerequisites=prerequisites or [f"execute:{intervention_action}"],
            evidence=evidence or [f"action:{intervention_action}"],
            is_baseline=False,
            intervention=intervention_action,
            is_counterfactual=True,
        )

    @classmethod
    def generate_baseline(cls, target: str, current_trend: Dict[str, Any]) -> Scenario:
        """Enforce Spec 9: Generate baseline future when no intervention occurs."""
        sid = f"scen_base_{uuid.uuid4().hex[:8]}"
        return Scenario(
            scenario_id=sid,
            description=f"Baseline trajectory for {target}: no operational intervention applied.",
            prerequisites=["no_manual_or_autonomous_intervention"],
            expected_state=current_trend,
            likelihood=0.7,
            impact=0.5,
            evidence={"trend_basis": current_trend},
            is_counterfactual=False,
            is_baseline=True,
        )

    @classmethod
    def generate_intervention(
        cls,
        target: str,
        intervention_action: str,
        expected_consequence: Dict[str, Any],
        likelihood: float = 0.8,
    ) -> Scenario:
        """Enforce Spec 10: 'If action X occurs, expected outcome may be Y.' Explicitly labeled conditional."""
        sid = f"scen_int_{uuid.uuid4().hex[:8]}"
        return Scenario(
            scenario_id=sid,
            description=f"Conditional intervention on {target}: Action '{intervention_action}'.",
            prerequisites=[f"execute:{intervention_action}"],
            expected_state=expected_consequence,
            likelihood=likelihood,
            impact=0.4,
            evidence={"action": intervention_action},
            is_counterfactual=True,
            is_baseline=False,
            intervention=intervention_action,
        )

    @classmethod
    def generate_alternatives(
        cls,
        target: str,
        current_state: Dict[str, Any],
        interventions: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Scenario]:
        """Enforce Spec 8: Do not assume one inevitable future; represent plausible alternatives."""
        results = [cls.generate_baseline(target, current_state)]
        if interventions:
            for item in interventions:
                act = item.get("action", "unknown_action")
                exp = item.get("expected_consequence", {})
                prob = item.get("likelihood", 0.75)
                results.append(cls.generate_intervention(target, act, exp, prob))
        return results
