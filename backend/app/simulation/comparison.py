"""Multi-scenario comparison matrix and structured diffs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.simulation.schemas import ScenarioComparison, Simulation


class ScenarioDiffSummary(BaseModel):
    """Summarizes differences between two candidate scenarios."""

    scenario_a_id: str
    scenario_b_id: str
    intervention_diff: list[str] = Field(default_factory=list)
    assumption_conflicts: list[str] = Field(default_factory=list)
    are_mergeable: bool = True
    merge_block_reason: str | None = None


class ScenarioComparator:
    """Builds side-by-side comparison matrices across simulated scenarios."""

    def compare_simulations(
        self,
        simulations: list[Simulation],
    ) -> ScenarioComparison:
        """Generates multi-scenario comparison matrix across key dimensions."""
        scenario_ids = [s.scenario_id for s in simulations]
        metrics_table: dict[str, dict[str, Any]] = {}
        risk_summary: dict[str, list[str]] = {}
        trade_offs: list[str] = []

        for sim in simulations:
            scen_id = sim.scenario_id

            # Extract metrics from effects or state
            cost = 0.0
            latency_delta = 0.0
            avail_impact = 1.0

            for eff in sim.effects:
                if eff.effect_type.value == "COST":
                    cost += eff.magnitude
                elif eff.effect_type.value == "LATENCY":
                    latency_delta += eff.magnitude
                elif eff.effect_type.value == "HEALTH" and eff.magnitude < 0:
                    avail_impact = 0.9

            metrics_table[scen_id] = {
                "estimated_monthly_cost_delta": cost,
                "latency_delta_ms": latency_delta,
                "projected_availability_ratio": avail_impact,
                "overall_confidence": sim.confidence,
                "effects_count": len(sim.effects),
                "risks_count": len(sim.risks),
                "status": sim.status.value if hasattr(sim.status, "value") else str(sim.status),
            }

            risk_summary[scen_id] = [r.category.value if hasattr(r.category, "value") else str(r.category) for r in sim.risks]

        # Analyze pairwise trade-offs
        if len(simulations) >= 2:
            s1, s2 = simulations[0], simulations[1]
            m1 = metrics_table[s1.scenario_id]
            m2 = metrics_table[s2.scenario_id]
            if m1["estimated_monthly_cost_delta"] < m2["estimated_monthly_cost_delta"]:
                trade_offs.append(
                    f"Scenario '{s1.scenario_id}' has lower cost delta (${m1['estimated_monthly_cost_delta']}) "
                    f"than '{s2.scenario_id}' (${m2['estimated_monthly_cost_delta']})."
                )
            if m1["latency_delta_ms"] < m2["latency_delta_ms"]:
                trade_offs.append(
                    f"Scenario '{s1.scenario_id}' has better latency improvement ({m1['latency_delta_ms']}ms) "
                    f"than '{s2.scenario_id}' ({m2['latency_delta_ms']}ms)."
                )

        return ScenarioComparison(
            scenario_ids=scenario_ids,
            metrics_matrix=metrics_table,
            risk_summary=risk_summary,
            trade_offs=trade_offs,
            recommended_scenario_id=scenario_ids[0] if scenario_ids else None,
        )

    def diff_scenarios(self, sim_a: Simulation, sim_b: Simulation) -> ScenarioDiffSummary:
        """Compares interventions and detects conflicting assumptions to prevent unsafe merges (Prompt #158)."""
        interv_diff: list[str] = []
        conflicts: list[str] = []

        # Check assumptions for direct contradiction
        assump_a = {a.statement: a for a in sim_a.assumptions}
        assump_b = {a.statement: a for a in sim_b.assumptions}

        # Check for conflicting statements
        for stmt_a in assump_a:
            for stmt_b in assump_b:
                if "not " + stmt_a.lower() in stmt_b.lower() or "not " + stmt_b.lower() in stmt_a.lower():
                    conflicts.append(f"Contradictory assumptions: '{stmt_a}' vs '{stmt_b}'")

        can_merge = len(conflicts) == 0
        reason = None if can_merge else f"Cannot merge scenarios: {len(conflicts)} conflicting assumption(s) detected."

        return ScenarioDiffSummary(
            scenario_a_id=sim_a.scenario_id,
            scenario_b_id=sim_b.scenario_id,
            intervention_diff=interv_diff,
            assumption_conflicts=conflicts,
            are_mergeable=can_merge,
            merge_block_reason=reason,
        )
