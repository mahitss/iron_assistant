"""Core simulation engine orchestrating state cloning, interventions, propagation, and risk assessment."""

from __future__ import annotations

import copy
import uuid
from datetime import datetime, timezone

from app.simulation.audit import simulation_auditor
from app.simulation.constraints import ConstraintValidator
from app.simulation.dependencies import DependencyBridge
from app.simulation.effects import EffectCalculator
from app.simulation.propagation import EffectPropagator
from app.simulation.provenance import generate_provenance
from app.simulation.risks import RiskAssessor
from app.simulation.safety import (
    block_production_side_effects,
    tag_simulated_output,
)
from app.simulation.schemas import Scenario, Simulation, SimulationSnapshot, SimulationStatus
from app.simulation.states import SimulationStateManager
from app.simulation.uncertainty import UncertaintyQuantifier


class SimulationEngine:
    """Orchestrates hypothetical scenario simulations with strict sandboxing and bounds."""

    def __init__(self) -> None:
        self._state_manager = SimulationStateManager()
        self._dep_bridge = DependencyBridge()
        self._effect_calc = EffectCalculator()
        self._propagator = EffectPropagator(max_depth=4)
        self._constraint_validator = ConstraintValidator()
        self._risk_assessor = RiskAssessor()
        self._uncertainty_quantifier = UncertaintyQuantifier()

    def run_simulation(
        self,
        snapshot: SimulationSnapshot,
        scenario: Scenario,
        creator: str = "kairo_autonomous_supervisor",
    ) -> Simulation:
        """Executes a full sandboxed simulation run for a scenario against a snapshot baseline."""
        simulation_id = f"sim_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        # 1. Prepare composite initial state
        initial_state = {
            "world": copy.deepcopy(snapshot.world_state),
            "digital_twin": copy.deepcopy(snapshot.digital_twin_state),
            "telemetry": copy.deepcopy(snapshot.telemetry_state),
        }

        # 2. Extract topology from digital twin
        topology = self._dep_bridge.extract_topology(snapshot.digital_twin_state)

        # 3. Initialize state branch
        branch_id = self._state_manager.initialize_branch(
            base_snapshot_id=snapshot.snapshot_id,
            initial_data=initial_state,
        )

        primary_effects = []
        is_fatal_intervention = False
        origin_node = "system"

        # 4. Apply interventions sequentially
        for interv in scenario.interventions:
            # Firewall assertion
            block_production_side_effects(interv.operation, interv.target)
            origin_node = interv.target

            # Check if fatal
            if any(term in interv.operation.upper() for term in ("KILL", "FAIL", "TERMINATE")):
                is_fatal_intervention = True

            # Apply mutation to simulation state (in memory only)
            target = interv.target
            mutation_payload = {}
            if "." in target:
                parts = target.split(".")
                root = parts[0]
                curr = mutation_payload.setdefault(root, {})
                for part in parts[1:-1]:
                    curr = curr.setdefault(part, {})
                curr[parts[-1]] = interv.hypothetical_after
            else:
                mutation_payload[target] = interv.hypothetical_after

            self._state_manager.apply_transition(branch_id, mutation_payload)

            # Calculate primary effects
            effs = self._effect_calc.calculate_effects(
                intervention=interv,
                baseline_state=initial_state,
                topology=topology,
            )
            primary_effects.extend(effs)

        # 5. Propagate effects through dependency topology
        all_effects = self._propagator.propagate_effects(
            primary_effects=primary_effects,
            topology=topology,
            is_topology_incomplete=False,
        )

        # 6. Analyze blast radius and cascade failures
        blast_radius = self._dep_bridge.estimate_blast_radius(
            origin_node=origin_node,
            topology=topology,
            max_depth=4,
        )
        cascade = self._dep_bridge.detect_cascades(
            origin_node=origin_node,
            is_fatal_failure=is_fatal_intervention,
            topology=topology,
            max_depth=4,
        )

        # 7. Check resource constraints
        latest_state = self._state_manager.get_latest_state(branch_id)
        constraint_result = self._constraint_validator.validate_constraints(
            hypothetical_state=latest_state.data,
            scenario_constraints=scenario.constraints,
        )

        # 8. Assess risks
        risks = self._risk_assessor.assess_risks(
            scenario_id=scenario.scenario_id,
            effects=all_effects,
            violations=constraint_result.violations,
            unmapped_dependencies_count=0,
        )

        # 9. Quantify epistemic uncertainty
        uncertainty = self._uncertainty_quantifier.quantify_uncertainty(
            assumptions=scenario.assumptions,
            topology_completeness=blast_radius.topology_completeness,
        )

        # 10. Generate state diff
        from app.simulation.states import calculate_state_diff
        diff = calculate_state_diff(initial_state, latest_state.data)

        # 11. Create immutable provenance
        provenance = generate_provenance(
            simulation_id=simulation_id,
            source_snapshot_id=snapshot.snapshot_id,
            scenario_id=scenario.scenario_id,
            initial_state=initial_state,
            creator=creator,
        )

        # 12. Build Simulation entity
        sim = Simulation(
            simulation_id=simulation_id,
            source_snapshot_id=snapshot.snapshot_id,
            scenario_id=scenario.scenario_id,
            initial_state=tag_simulated_output(initial_state),
            future_state=tag_simulated_output(latest_state.data),
            diff=diff.model_dump(),
            effects=all_effects,
            risks=risks,
            assumptions=scenario.assumptions,
            model_version="1.0.0",
            status=SimulationStatus.COMPLETED,
            confidence=uncertainty.overall_confidence,
            environment_label="SIMULATION_ONLY",
            is_hypothetical=True,
            provenance=provenance.model_dump(),
            created_at=now,
            completed_at=datetime.now(timezone.utc),
        )

        # 13. Record audit event
        simulation_auditor.record_event(
            event_type="SIMULATION_COMPLETED",
            actor=creator,
            simulation_id=simulation_id,
            scenario_id=scenario.scenario_id,
            details={
                "effects_count": len(all_effects),
                "risks_count": len(risks),
                "confidence": uncertainty.overall_confidence,
                "blast_radius": blast_radius.blast_radius_level,
                "cascade_likely": cascade.is_cascade_likely,
                "failing_nodes": cascade.failing_nodes,
            },
        )

        return sim
