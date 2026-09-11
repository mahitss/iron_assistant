"""Isolated scenario generation, sandbox branching, assumption tracking, and convergence/divergence analysis (Task 65, Spec 23-27, 65-68, 89)."""

from __future__ import annotations

import copy
import logging
from typing import Any

from app.foresight.safety import ForesightComputationLimiter
from app.foresight.schemas import (
    ForesightEntity,
    ForesightHorizon,
    ScenarioBranch,
    ScenarioType,
)

logger = logging.getLogger(__name__)


class ScenarioEngine:
    """Generates and manages isolated counterfactual scenario branches (Spec 23, 25, 89)."""

    def __init__(self, limiter: ForesightComputationLimiter | None = None) -> None:
        self._scenarios: dict[str, ScenarioBranch] = {}
        self.limiter = limiter or ForesightComputationLimiter()

    def create_scenario_branch(
        self,
        name: str,
        scenario_type: ScenarioType = ScenarioType.BASELINE,
        horizon: ForesightHorizon = ForesightHorizon.MID_FUTURE_1M,
        current_entities: dict[str, ForesightEntity] | None = None,
        assumptions: list[str] | None = None,
        interventions: list[str] | None = None,
        tenant_id: str = "default",
    ) -> ScenarioBranch:
        """Create an isolated future scenario branch sandbox.

        Invariant: SIMULATION ISOLATION (Spec 89).
        Simulation runs in a deep-copied sandbox and CANNOT mutate production entities.
        Invariant: SCENARIO != FORECAST (Spec 24).
        A scenario explores 'What could happen under assumptions X?', not 'What is most likely?'.
        """
        self.limiter.check_scenario_addition(len(self._scenarios))

        # Deep-copy current entities to guarantee sandbox isolation
        isolated_snapshot = copy.deepcopy(current_entities or {})
        initial_summary = f"Isolated snapshot of {len(isolated_snapshot)} entities"

        assumptions_list = assumptions or ["Default operational parameters continue"]
        interventions_list = interventions or []

        # Derive expected changes, risks, and opportunities based on scenario archetype
        expected_changes: list[str] = []
        risks: list[str] = []
        opportunities: list[str] = []

        if scenario_type == ScenarioType.OPTIMISTIC:
            expected_changes.append("Resource throughput scales smoothly; latency decreases 20%")
            opportunities.append("Capacity surplus enables early feature rollout")
            confidence = 0.70
        elif scenario_type in (ScenarioType.PESSIMISTIC, ScenarioType.ADVERSE):
            expected_changes.append("Traffic spike of +50% stresses memory allocation and buffer pools")
            risks.append("Potential thread starvation under sustained peak concurrency")
            confidence = 0.65
        elif scenario_type == ScenarioType.DISRUPTION:
            expected_changes.append("Primary database gateway experiences degraded replication latency")
            risks.append("Secondary cascading failures in dependent analytics pipelines")
            confidence = 0.55
        elif scenario_type == ScenarioType.RECOVERY:
            expected_changes.append("Auto-healing mechanisms stabilize degraded nodes within 4 minutes")
            opportunities.append("Validated resilience checkpoints enhance system trust")
            confidence = 0.75
        else:  # BASELINE or CUSTOM
            expected_changes.append("Operational metrics track within standard historical variance")
            confidence = 0.80

        # Incorporate explicit interventions
        for itv in interventions_list:
            expected_changes.append(f"Intervention simulated: {itv}")

        branch = ScenarioBranch(
            name=name,
            type=scenario_type,
            horizon=horizon,
            initial_state_summary=initial_summary,
            assumptions=assumptions_list,
            interventions=interventions_list,
            expected_changes=expected_changes,
            risks=risks,
            opportunities=opportunities,
            confidence=confidence,
            is_stale=False,
            is_robust=False,
            sensitivity_score=0.5,
            tenant_id=tenant_id,
        )

        self._scenarios[branch.scenario_id] = branch
        logger.info(
            "SCENARIO_BRANCH_CREATED: id=%s name='%s' type=%s horizon=%s",
            branch.scenario_id,
            name,
            scenario_type.value,
            horizon.value,
        )
        return branch

    def evaluate_convergence_and_sensitivity(self) -> dict[str, Any]:
        """Analyze multi-scenario convergence (ROBUST_OUTCOME) versus divergence (HIGH_SENSITIVITY) (Spec 67, 68).

        Invariant: Convergence is an indicator of robustness across assumptions, but NOT certainty!
        """
        active = [s for s in self._scenarios.values() if not s.is_stale]
        if len(active) < 2:
            return {"status": "insufficient_scenarios", "robust_scenarios": [], "sensitive_scenarios": []}

        # Check for common outcomes/risks across distinct scenario types
        risk_frequency: dict[str, int] = {}
        for scn in active:
            for r in scn.risks:
                risk_frequency[r] = risk_frequency.get(r, 0) + 1

        robust_risks = [r for r, count in risk_frequency.items() if count >= len(active) * 0.6]

        for scn in active:
            if any(r in scn.risks for r in robust_risks):
                scn.is_robust = True

            # If scenario exhibits high risk divergence under minor assumption shifts
            if scn.type in (ScenarioType.ADVERSE, ScenarioType.DISRUPTION) and len(scn.risks) >= 2:
                scn.sensitivity_score = 0.85
            else:
                scn.sensitivity_score = 0.35

        return {
            "total_scenarios": len(active),
            "robust_findings": robust_risks,
            "has_high_sensitivity": any(s.sensitivity_score > 0.8 for s in active),
        }

    def invalidate_on_assumption_change(self, invalidated_assumption: str) -> list[str]:
        """Mark scenarios stale if their underlying assumptions are contradicted by reality (Spec 27)."""
        stale_ids: list[str] = []
        lowered = invalidated_assumption.lower()
        for scn in self._scenarios.values():
            if not scn.is_stale:
                for a in scn.assumptions:
                    if lowered in a.lower() or any(w in a.lower() for w in lowered.split()):
                        scn.is_stale = True
                        stale_ids.append(scn.scenario_id)
                        logger.warning(
                            "SCENARIO_MARKED_STALE: id=%s assumption_invalidated='%s'",
                            scn.scenario_id,
                            invalidated_assumption,
                        )
                        break
        return stale_ids

    def get_scenario(self, scenario_id: str) -> ScenarioBranch | None:
        """Retrieve scenario branch by ID."""
        return self._scenarios.get(scenario_id)

    def list_scenarios(
        self,
        scenario_type: ScenarioType | None = None,
        tenant_id: str = "default",
    ) -> list[ScenarioBranch]:
        """List active scenario branches."""
        results: list[ScenarioBranch] = []
        for s in self._scenarios.values():
            if tenant_id != "default" and s.tenant_id != tenant_id:
                continue
            if scenario_type and s.type != scenario_type:
                continue
            results.append(s)
        return results

    def clear(self) -> None:
        """Clear scenarios cache (for tests)."""
        self._scenarios.clear()


scenario_engine = ScenarioEngine()
