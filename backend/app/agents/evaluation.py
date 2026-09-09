"""Team Quality Evaluation, Risk-Based Sizing, and Minimal Team Selection (Task 44)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.agents.agent import AgentRole

logger = logging.getLogger("kairo.agents.evaluation")


@dataclass
class TeamCompositionRecommendation:
    """Recommended specialist team roster based on task risk and domain (Specs 195-198)."""

    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    required_roles: list[AgentRole]
    requires_independent_reviewer: bool
    requires_independent_verifier: bool
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_level": self.risk_level,
            "required_roles": [r.value for r in self.required_roles],
            "requires_independent_reviewer": self.requires_independent_reviewer,
            "requires_independent_verifier": self.requires_independent_verifier,
            "rationale": self.rationale,
        }


class TeamEvaluator:
    """Recommends minimal viable team compositions based on verified risk (Specs 195-198).
    
    PRINCIPLE: Minimal Team Principle (Spec 198).
    Do not spawn agents unnecessarily. Low-risk operations should not spawn complex teams.
    """

    @classmethod
    def recommend_team_composition(
        cls,
        task_objective: str,
        risk_level: str = "LOW",
    ) -> TeamCompositionRecommendation:
        risk = risk_level.upper()

        if risk in ["HIGH", "CRITICAL"]:
            # High-risk: specialist + independent reviewer + verifier (Spec 196)
            return TeamCompositionRecommendation(
                risk_level=risk,
                required_roles=[
                    AgentRole.CODER,
                    AgentRole.SECURITY_ANALYST,
                    AgentRole.REVIEWER,
                    AgentRole.VERIFIER,
                ],
                requires_independent_reviewer=True,
                requires_independent_verifier=True,
                rationale="High-risk task requires strict separation of authoring, security review, and empirical verification.",
            )

        elif risk == "MEDIUM":
            return TeamCompositionRecommendation(
                risk_level=risk,
                required_roles=[AgentRole.CODER, AgentRole.TESTER],
                requires_independent_reviewer=False,
                requires_independent_verifier=True,
                rationale="Medium-risk task requires authoring specialist and automated test verification.",
            )

        # Low risk: 1 agent suffices (Spec 196, 198)
        return TeamCompositionRecommendation(
            risk_level="LOW",
            required_roles=[AgentRole.RESEARCHER],
            requires_independent_reviewer=False,
            requires_independent_verifier=False,
            rationale="Low-risk read-only operation: single specialist satisfies quality without redundant overhead.",
        )
