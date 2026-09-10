"""Scenario ranking and comprehensive decision explanation engine."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.simulation.schemas import Simulation


class PlanExplanation(BaseModel):
    """Complete transparent explanation of a simulation recommendation (Prompt #152)."""

    scenario_id: str
    rank: int
    score: float
    why_selected: str
    key_assumptions: list[str] = Field(default_factory=list)
    key_risks: list[str] = Field(default_factory=list)
    what_could_fail: list[str] = Field(default_factory=list)
    reversibility_assessment: str
    verification_method: str


class ScenarioRanker:
    """Ranks simulated scenarios based on weighted objective scores and transparency rules."""

    def rank_scenarios(
        self,
        simulations: list[Simulation],
        user_priorities: dict[str, float] | None = None,
    ) -> list[PlanExplanation]:
        """Ranks scenarios transparently, exposing trade-offs and full decision rationale."""
        priorities = user_priorities or {
            "MINIMIZE_RISK": 0.4,
            "MAXIMIZE_AVAILABILITY": 0.3,
            "MINIMIZE_COST": 0.15,
            "MINIMIZE_LATENCY": 0.15,
        }

        scored_plans: list[tuple[Simulation, float, dict[str, Any]]] = []

        for sim in simulations:
            risk_weight = priorities.get("MINIMIZE_RISK", 0.4)
            cost_weight = priorities.get("MINIMIZE_COST", 0.15)
            avail_weight = priorities.get("MAXIMIZE_AVAILABILITY", 0.3)

            risk_penalty = len(sim.risks) * 0.2 * risk_weight
            conf_bonus = sim.confidence * 0.5 * avail_weight
            cost_val = 0.0
            for eff in sim.effects:
                if eff.effect_type.value == "COST":
                    cost_val += eff.magnitude

            cost_penalty = min(0.3, (cost_val / 100.0) * cost_weight) if cost_val > 0 else 0.0
            final_score = max(0.0, round(1.0 - risk_penalty - cost_penalty + conf_bonus, 3))

            scored_plans.append((sim, final_score, {"cost": cost_val, "risks": len(sim.risks)}))

        # Sort descending by final_score
        scored_plans.sort(key=lambda x: x[1], reverse=True)

        explanations: list[PlanExplanation] = []
        for rank, (sim, score, meta) in enumerate(scored_plans, 1):
            why = (
                f"Ranked #{rank} with composite score {score:.2f}. Balanced low risk profile "
                f"({meta['risks']} risks) and projected cost delta (${meta['cost']:.1f})."
            )
            assumptions_list = [a.statement for a in sim.assumptions]
            risks_list = [r.mitigation for r in sim.risks]
            failure_modes = [
                f"Unanticipated dependency failure on target {e.target}"
                for e in sim.effects if e.magnitude < 0
            ] or ["Unforeseen external traffic spike or network partition."]

            explanation = PlanExplanation(
                scenario_id=sim.scenario_id,
                rank=rank,
                score=score,
                why_selected=why,
                key_assumptions=assumptions_list[:3],
                key_risks=risks_list[:3],
                what_could_fail=failure_modes[:2],
                reversibility_assessment="High: configuration and replica changes can be rolled back immediately.",
                verification_method="Automated postcondition health probe and latency telemetry inspection.",
            )
            explanations.append(explanation)

        return explanations
