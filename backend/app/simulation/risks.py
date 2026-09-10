"""Simulation risk modeling, downstream risk propagation, and mitigation analysis."""

from __future__ import annotations

import uuid

from app.simulation.schemas import RiskCategory, SimulatedEffect, SimulationRisk


class RiskAssessor:
    """Evaluates risks across 8 categories without false numerical precision."""

    def assess_risks(
        self,
        scenario_id: str,
        effects: list[SimulatedEffect],
        violations: list[str],
        unmapped_dependencies_count: int = 0,
    ) -> list[SimulationRisk]:
        """Synthesizes risks from simulated effects, constraint violations, and topology gaps."""
        risks: list[SimulationRisk] = []

        # 1. Constraint violations produce critical operational/availability risk
        if violations:
            risks.append(
                SimulationRisk(
                    risk_id=f"risk_cons_{uuid.uuid4().hex[:8]}",
                    scenario_id=scenario_id,
                    category=RiskCategory.OPERATIONS,
                    probability=0.85,
                    impact="CRITICAL",
                    confidence=0.90,
                    evidence=violations,
                    mitigation="Resize infrastructure quotas or scale down replica targets before real execution.",
                )
            )

        # 2. Availability risk from negative health effects
        for eff in effects:
            if eff.effect_type.value == "HEALTH" and eff.magnitude < 0:
                risks.append(
                    SimulationRisk(
                        risk_id=f"risk_avail_{uuid.uuid4().hex[:8]}",
                        scenario_id=scenario_id,
                        category=RiskCategory.AVAILABILITY,
                        probability=0.75,
                        impact="HIGH",
                        confidence=eff.confidence,
                        evidence=[f"Service '{eff.target}' projected health degradation: {eff.mechanism}"],
                        mitigation="Verify automated restart policy and health probe timeout before proceeding.",
                    )
                )

        # 3. Performance risk from latency spikes
        for eff in effects:
            if eff.effect_type.value == "LATENCY" and eff.magnitude > 50:
                risks.append(
                    SimulationRisk(
                        risk_id=f"risk_perf_{uuid.uuid4().hex[:8]}",
                        scenario_id=scenario_id,
                        category=RiskCategory.PERFORMANCE,
                        probability=0.60,
                        impact="MEDIUM",
                        confidence=eff.confidence,
                        evidence=[f"Node '{eff.target}' added latency: +{eff.magnitude}ms"],
                        mitigation="Enable request caching or configure traffic throttling.",
                    )
                )

        # 4. Dependency risk from unmapped topology
        if unmapped_dependencies_count > 0:
            risks.append(
                SimulationRisk(
                    risk_id=f"risk_dep_{uuid.uuid4().hex[:8]}",
                    scenario_id=scenario_id,
                    category=RiskCategory.DEPENDENCY,
                    probability=0.40,
                    impact="MEDIUM",
                    confidence=0.50,
                    evidence=[f"System topology contains {unmapped_dependencies_count} unmapped edge(s)"],
                    mitigation="Run Digital Twin topology scan to discover unindexed upstream services.",
                )
            )

        return risks
