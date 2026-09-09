"""Scenario Simulation, Simulated State Isolation, and World Model Safeguards (Task 47)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger("kairo.prediction.simulation")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SimulationIsolationError(Exception):
    """Raised when simulation attempts to write or update authoritative World Model state (Spec 120)."""


@dataclass
class SimulationResult:
    """Multi-step simulated state projection explicitly marked as SIMULATED (Spec 118-120)."""

    simulation_id: str
    target: str
    label: str = "SIMULATED"  # Mandatory flag (Spec 119)
    is_simulated: bool = True
    simulated_steps: List[Dict[str, Any]] = field(default_factory=list)
    trajectory: List[Dict[str, Any]] = field(default_factory=list)
    final_state: Dict[str, Any] = field(default_factory=dict)
    assumptions: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "target": self.target,
            "label": self.label,
            "is_simulated": self.is_simulated,
            "simulated_steps": self.simulated_steps,
            "trajectory": self.trajectory,
            "final_state": self.final_state,
            "assumptions": self.assumptions,
            "timestamp": self.timestamp.isoformat(),
        }


class ScenarioSimulator:
    """Simulates system evolution under candidate actions with zero World Model contamination (Spec 118-120)."""

    @classmethod
    def simulate(
        cls,
        target: str,
        initial_state: Dict[str, Any],
        interventions: Optional[List[Dict[str, Any]]] = None,
        time_steps: int = 5,
    ) -> SimulationResult:
        """Run bounded multi-step synthetic simulation (Spec 118).
        
        CRITICAL: Simulation output cannot update authoritative World Model state! (Spec 120)
        """
        sid = f"sim_{uuid.uuid4().hex[:8]}"
        state = dict(initial_state)
        trajectory = []

        for step in range(1, time_steps + 1):
            # Apply intervention if scheduled for this step
            if interventions:
                for intv in interventions:
                    if intv.get("step") == step:
                        state.update(intv.get("state_delta", {}))
                        if "action" in intv and "instances" in state:
                            state["instances"] += intv.get("count", 1)

            step_record = {
                "step": step,
                "projected_state": dict(state),
                "source": "SIMULATION_ENGINE",
                "is_authoritative": False,  # Mandatory reality separation (Spec 120)
            }
            trajectory.append(step_record)

        res = SimulationResult(
            simulation_id=sid,
            target=target,
            label="SIMULATED",
            is_simulated=True,
            simulated_steps=trajectory,
            trajectory=trajectory,
            final_state=dict(state),
            assumptions=["Synthetic workload simulation with fixed step physics"],
        )
        logger.info("Executed scenario simulation %s for %s (%d steps)", sid, target, time_steps)
        return res

    @classmethod
    def simulate_scenario(
        cls,
        scenario_name: str,
        initial_state: Dict[str, Any],
        steps: int = 5,
        interventions: Optional[List[Dict[str, Any]]] = None,
    ) -> SimulationResult:
        return cls.simulate(
            target=scenario_name,
            initial_state=initial_state,
            interventions=interventions,
            time_steps=steps,
        )
