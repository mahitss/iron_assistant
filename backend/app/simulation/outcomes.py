"""Simulation outcome synthesis, rollups, and structured summary formatting."""

from __future__ import annotations

from pydantic import BaseModel

from app.simulation.dependencies import BlastRadiusEstimate, CascadeFailureEstimate
from app.simulation.safety import tag_simulated_output
from app.simulation.schemas import SimulatedEffect, SimulationRisk
from app.simulation.uncertainty import UncertaintyProfile


class SimulationOutcomeSummary(BaseModel):
    """Unified rollup summary of all simulation dimensions."""

    simulation_id: str
    scenario_id: str
    status: str
    overall_confidence: float
    effects_count: int
    risks_count: int
    blast_radius: BlastRadiusEstimate
    cascade_estimate: CascadeFailureEstimate
    uncertainty: UncertaintyProfile
    is_hypothetical: bool = True
    environment_label: str = "SIMULATION_ONLY"
    summary_text: str


def summarize_outcome(
    simulation_id: str,
    scenario_id: str,
    status: str,
    effects: list[SimulatedEffect],
    risks: list[SimulationRisk],
    blast_radius: BlastRadiusEstimate,
    cascade: CascadeFailureEstimate,
    uncertainty: UncertaintyProfile,
) -> SimulationOutcomeSummary:
    """Combines simulation findings into a single structured outcome summary."""
    summary_lines = [
        f"Simulation '{simulation_id}' (Scenario: {scenario_id}) completed with status {status}.",
        f"Confidence: {uncertainty.overall_confidence:.2f} ({uncertainty.epistemic_uncertainty_level} uncertainty).",
        f"Blast Radius: {blast_radius.blast_radius_level} ({blast_radius.impacted_services_count} downstream services affected).",
    ]

    if cascade.is_cascade_likely:
        summary_lines.append(f"WARNING: Cascading failure detected across {len(cascade.failing_nodes)} nodes.")

    if risks:
        high_critical = [r for r in risks if r.impact in ("HIGH", "CRITICAL")]
        summary_lines.append(f"Identified {len(risks)} risk(s), including {len(high_critical)} high/critical risk items.")

    raw = {
        "simulation_id": simulation_id,
        "scenario_id": scenario_id,
        "status": status,
        "overall_confidence": uncertainty.overall_confidence,
        "effects_count": len(effects),
        "risks_count": len(risks),
        "blast_radius": blast_radius,
        "cascade_estimate": cascade,
        "uncertainty": uncertainty,
        "summary_text": " ".join(summary_lines),
    }

    return SimulationOutcomeSummary(**tag_simulated_output(raw))
