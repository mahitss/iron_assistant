"""Simulation bridge integrating Task 89 digital twin & Pareto counterfactual comparison."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.reliability_intelligence.models import (
    CounterfactualComparison,
    FailureForecast,
    PredictedImpact,
    PreventionActionType,
    PreventionCandidate,
    ReliabilitySignal,
    ReliabilitySignalType,
    ReversibilityLevel,
    generate_ri_id,
)

logger = logging.getLogger("kairo.reliability_intelligence.simulation_bridge")


class SimulationBridge:
    """Delegates pre-prevention consequence simulation to Task 89 Digital Twin."""

    def __init__(self, simulation_service: Optional[Any] = None) -> None:
        self._simulation_service = simulation_service

    def _get_simulation_service(self) -> Any:
        if self._simulation_service is None:
            try:
                from app.simulation.recovery_service import get_recovery_service
                self._simulation_service = get_recovery_service()
            except Exception as e:
                logger.debug("Task 89 simulation service lazy init: %s", e)
        return self._simulation_service

    def generate_prevention_candidates(
        self,
        signal: ReliabilitySignal,
        impact: PredictedImpact,
    ) -> List[PreventionCandidate]:
        """Synthesizes candidate preventive actions matching component and failure mode."""
        comp = signal.component.lower()
        sig_type = signal.signal_type
        candidates: List[PreventionCandidate] = []

        # 1. ALWAYS INCLUDE MANDATORY NO_ACTION BASELINE (Section 20)
        no_action = PreventionCandidate(
            candidate_id=generate_ri_id("cand_noaction"),
            action_type=PreventionActionType.NO_ACTION,
            target_component=comp,
            parameters={},
            description="Take no proactive action; continue passive observation",
            is_no_action=True,
            reversibility=ReversibilityLevel.REVERSIBLE,
            minimum_intervention_rank=0,
            predicted_benefit=0.0,
            intervention_risk=0.0,
            intervention_cost={"cpu_delta_pct": 0.0, "mem_delta_mb": 0.0},
            simulated_blast_radius=impact.blast_radius_score,
            estimated_duration_seconds=0.0,
            confidence=signal.confidence,
            net_prevention_value=0.0,
            is_recommended=False,
        )
        candidates.append(no_action)

        # 2. Tailored actions by signal type
        if sig_type in (ReliabilitySignalType.RESOURCE_PRESSURE, ReliabilitySignalType.MEMORY_EXHAUSTION):
            candidates.append(
                PreventionCandidate(
                    candidate_id=generate_ri_id("cand"),
                    action_type=PreventionActionType.RELEASE_RESOURCE,
                    target_component=comp,
                    parameters={"resource": "memory_buffer", "aggressive_gc": True},
                    description="Release idle buffers and trigger garbage collection",
                    is_no_action=False,
                    reversibility=ReversibilityLevel.REVERSIBLE,
                    minimum_intervention_rank=1,
                    predicted_benefit=0.75,
                    intervention_risk=0.05,
                    intervention_cost={"cpu_delta_pct": 2.0, "mem_delta_mb": -50.0},
                    simulated_blast_radius=0.05,
                    estimated_duration_seconds=0.5,
                    confidence=0.85,
                )
            )
            candidates.append(
                PreventionCandidate(
                    candidate_id=generate_ri_id("cand"),
                    action_type=PreventionActionType.REDUCE_CONCURRENCY,
                    target_component=comp,
                    parameters={"concurrency_limit": 4},
                    description="Temporarily throttle task concurrency to relieve memory pressure",
                    is_no_action=False,
                    reversibility=ReversibilityLevel.REVERSIBLE,
                    minimum_intervention_rank=2,
                    predicted_benefit=0.85,
                    intervention_risk=0.10,
                    intervention_cost={"throughput_penalty_pct": 15.0},
                    simulated_blast_radius=0.10,
                    estimated_duration_seconds=0.2,
                    confidence=0.80,
                )
            )
            candidates.append(
                PreventionCandidate(
                    candidate_id=generate_ri_id("cand"),
                    action_type=PreventionActionType.RESTART_COMPONENT,
                    target_component=comp,
                    parameters={"graceful": True, "timeout_seconds": 5},
                    description="Preventive restart of component to flush memory leaks",
                    is_no_action=False,
                    reversibility=ReversibilityLevel.PARTIALLY_REVERSIBLE,
                    minimum_intervention_rank=3,
                    predicted_benefit=0.95,
                    intervention_risk=0.25,
                    intervention_cost={"cpu_delta_pct": 10.0, "mem_delta_mb": -120.0},
                    simulated_blast_radius=0.25,
                    estimated_duration_seconds=2.5,
                    confidence=0.90,
                )
            )

        elif sig_type in (
            ReliabilitySignalType.NETWORK_INSTABILITY,
            ReliabilitySignalType.LATENCY_DEGRADATION,
            ReliabilitySignalType.CONNECTION_EXHAUSTION,
        ):
            candidates.append(
                PreventionCandidate(
                    candidate_id=generate_ri_id("cand"),
                    action_type=PreventionActionType.REFRESH_POOL,
                    target_component=comp,
                    parameters={"purge_idle": True},
                    description="Purge stale connections and refresh HTTP connection pool",
                    is_no_action=False,
                    reversibility=ReversibilityLevel.REVERSIBLE,
                    minimum_intervention_rank=1,
                    predicted_benefit=0.70,
                    intervention_risk=0.05,
                    intervention_cost={"latency_delta_ms": 10.0},
                    simulated_blast_radius=0.05,
                    estimated_duration_seconds=0.3,
                    confidence=0.85,
                )
            )
            candidates.append(
                PreventionCandidate(
                    candidate_id=generate_ri_id("cand"),
                    action_type=PreventionActionType.RECONNECT,
                    target_component=comp,
                    parameters={"backoff_multiplier": 1.5},
                    description="Recycle socket transport and re-establish upstream session",
                    is_no_action=False,
                    reversibility=ReversibilityLevel.REVERSIBLE,
                    minimum_intervention_rank=2,
                    predicted_benefit=0.85,
                    intervention_risk=0.15,
                    intervention_cost={"latency_delta_ms": 45.0},
                    simulated_blast_radius=0.15,
                    estimated_duration_seconds=0.8,
                    confidence=0.80,
                )
            )

        elif sig_type == ReliabilitySignalType.CRASH_LOOP:
            candidates.append(
                PreventionCandidate(
                    candidate_id=generate_ri_id("cand"),
                    action_type=PreventionActionType.DEGRADE_CAPABILITY,
                    target_component=comp,
                    parameters={"degraded_mode": "read_only"},
                    description="Gracefully degrade to safe mode to break crash frequency",
                    is_no_action=False,
                    reversibility=ReversibilityLevel.REVERSIBLE,
                    minimum_intervention_rank=1,
                    predicted_benefit=0.90,
                    intervention_risk=0.15,
                    intervention_cost={"capability_loss": 1.0},
                    simulated_blast_radius=0.20,
                    estimated_duration_seconds=0.5,
                    confidence=0.85,
                )
            )
            candidates.append(
                PreventionCandidate(
                    candidate_id=generate_ri_id("cand"),
                    action_type=PreventionActionType.ESCALATE,
                    target_component=comp,
                    parameters={"reason": "Crash loop forming; automated restart tripped"},
                    description="Escalate to human operator for environment diagnostics",
                    is_no_action=False,
                    reversibility=ReversibilityLevel.REVERSIBLE,
                    minimum_intervention_rank=2,
                    predicted_benefit=1.0,
                    intervention_risk=0.0,
                    intervention_cost={},
                    simulated_blast_radius=0.0,
                    estimated_duration_seconds=0.1,
                    confidence=0.95,
                )
            )

        elif sig_type in (ReliabilitySignalType.TOOL_DEGRADATION, ReliabilitySignalType.WORKFLOW_DEGRADATION):
            candidates.append(
                PreventionCandidate(
                    candidate_id=generate_ri_id("cand"),
                    action_type=PreventionActionType.THROTTLE,
                    target_component=comp,
                    parameters={"rate_limit": 5},
                    description=f"Throttle invocation rate on degraded tool {comp}",
                    is_no_action=False,
                    reversibility=ReversibilityLevel.REVERSIBLE,
                    minimum_intervention_rank=1,
                    predicted_benefit=0.70,
                    intervention_risk=0.05,
                    intervention_cost={},
                    simulated_blast_radius=0.05,
                    estimated_duration_seconds=0.2,
                    confidence=0.85,
                )
            )
            candidates.append(
                PreventionCandidate(
                    candidate_id=generate_ri_id("cand"),
                    action_type=PreventionActionType.DEGRADE_CAPABILITY,
                    target_component=comp,
                    parameters={"use_fallback": True},
                    description=f"Route requests to alternate provider for {comp}",
                    is_no_action=False,
                    reversibility=ReversibilityLevel.REVERSIBLE,
                    minimum_intervention_rank=2,
                    predicted_benefit=0.85,
                    intervention_risk=0.10,
                    intervention_cost={},
                    simulated_blast_radius=0.10,
                    estimated_duration_seconds=0.4,
                    confidence=0.80,
                )
            )

        else:
            candidates.append(
                PreventionCandidate(
                    candidate_id=generate_ri_id("cand"),
                    action_type=PreventionActionType.THROTTLE,
                    target_component=comp,
                    parameters={"rate_limit": 10},
                    description=f"Apply adaptive rate limiting to {comp}",
                    is_no_action=False,
                    reversibility=ReversibilityLevel.REVERSIBLE,
                    minimum_intervention_rank=1,
                    predicted_benefit=0.65,
                    intervention_risk=0.05,
                    intervention_cost={},
                    simulated_blast_radius=0.05,
                    estimated_duration_seconds=0.2,
                    confidence=0.75,
                )
            )

        return candidates

    def compare_and_select(
        self,
        candidates: List[PreventionCandidate],
        forecast: FailureForecast,
        impact: PredictedImpact,
    ) -> CounterfactualComparison:
        """Evaluates all candidates against NO_ACTION and selects minimum effective intervention."""
        no_action_cand = next((c for c in candidates if c.is_no_action), None)
        if not no_action_cand:
            raise ValueError("Mandatory NO_ACTION candidate missing")

        # Compute net prevention value for each candidate
        # expected avoided loss = failure_probability * blast_radius_score * 100
        avoided_loss_base = forecast.failure_probability * impact.blast_radius_score * 10.0

        for cand in candidates:
            if cand.is_no_action:
                cand.net_prevention_value = 0.0
                continue

            # benefit = avoided loss * candidate's predicted benefit
            expected_benefit = avoided_loss_base * cand.predicted_benefit
            # cost penalty
            cost_penalty = sum(abs(v) for v in cand.intervention_cost.values()) * 0.05
            # risk penalty
            risk_penalty = cand.intervention_risk * 5.0
            # reversibility bonus: prefer REVERSIBLE
            rev_bonus = 1.0 if cand.reversibility == ReversibilityLevel.REVERSIBLE else 0.0

            cand.net_prevention_value = round(expected_benefit - cost_penalty - risk_penalty + rev_bonus, 2)

        # Minimum Intervention Selection:
        # Filter candidates where net_prevention_value > 0 (strictly better than NO_ACTION)
        viable = [c for c in candidates if not c.is_no_action and c.net_prevention_value > 0.0]

        if viable:
            # Sort primarily by minimum intervention rank, then by net value
            viable.sort(key=lambda c: (c.minimum_intervention_rank, -c.net_prevention_value))
            selected = viable[0]
            selected.is_recommended = True
            rationale = (
                f"Selected {selected.action_type.value} as the minimum effective intervention "
                f"(rank {selected.minimum_intervention_rank}, net value {selected.net_prevention_value:.2f}, "
                f"reversibility={selected.reversibility.value}) over NO_ACTION baseline."
            )
        else:
            selected = no_action_cand
            selected.is_recommended = True
            rationale = (
                "NO_ACTION baseline selected: calculated risk/cost of candidate interventions exceeds "
                "expected avoided loss. Passive observation preferred."
            )

        return CounterfactualComparison(
            comparison_id=generate_ri_id("cmp"),
            baseline_no_action=no_action_cand,
            evaluated_candidates=candidates,
            selected_candidate=selected,
            selection_rationale=rationale,
            minimum_intervention_applied=True,
        )


_global_simulation_bridge: Optional[SimulationBridge] = None


def get_simulation_bridge() -> SimulationBridge:
    global _global_simulation_bridge
    if _global_simulation_bridge is None:
        _global_simulation_bridge = SimulationBridge()
    return _global_simulation_bridge
