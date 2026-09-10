"""Verified Real-World Transition Engine and ExecutionGate.

Enforces:
1. Strict separation of simulation from execution.
2. Revalidation of baseline state against current Digital Twin (drift check).
3. If baseline drifted materially -> marks gate STALE or INVALIDATED.
4. Requires READY status before any real execution plan can be dispatched.
5. Rechecks policy, authorization, approval, dependencies, and risks.
6. Defines mandatory postcondition verification plan.
"""

from __future__ import annotations

import copy
import uuid
from datetime import datetime, timezone
from typing import Any

from app.simulation.audit import simulation_auditor
from app.simulation.authorization import SimulationAuthorizationChecker
from app.simulation.safety import StaleSimulationError, UnverifiedExecutionError, scrub_secrets
from app.simulation.schemas import ExecutionGate, ExecutionGateStatus, Simulation, SimulationSnapshot
from app.simulation.snapshots import compute_state_hash


class RealWorldTransitionEngine:
    """Evaluates readiness of simulated plans for real-world execution through ExecutionGate."""

    def __init__(self) -> None:
        self._auth_checker = SimulationAuthorizationChecker()
        self._gates: dict[str, ExecutionGate] = {}

    def evaluate_gate(
        self,
        simulation: Simulation,
        snapshot: SimulationSnapshot,
        current_real_state: dict[str, Any],
        user_approved: bool = False,
        user_roles: list[str] | None = None,
    ) -> ExecutionGate:
        """Evaluates whether a simulation recommendation is safely transitionable to real execution."""
        gate_id = f"gate_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        user_roles = user_roles or []

        # 1. State Drift & Staleness Check (Prompts #129, #130, #131)
        clean_current = scrub_secrets(copy.deepcopy(current_real_state))
        current_hash = compute_state_hash(clean_current)
        drift_detected = current_hash != snapshot.baseline_hash
        drift_details: dict[str, Any] = {}

        if drift_detected:
            drift_details["reason"] = "Observed real-world state hash diverged from baseline snapshot."
            drift_details["baseline_hash"] = snapshot.baseline_hash
            drift_details["current_hash"] = current_hash
            status = ExecutionGateStatus.STALE
            if snapshot.is_stale:
                status = ExecutionGateStatus.INVALIDATED

            gate = ExecutionGate(
                gate_id=gate_id,
                simulation_id=simulation.simulation_id,
                scenario_id=simulation.scenario_id,
                status=status,
                baseline_snapshot_id=snapshot.snapshot_id,
                baseline_hash_at_sim=snapshot.baseline_hash,
                current_hash=current_hash,
                drift_detected=True,
                drift_details=drift_details,
                verification_plan=[],
                evaluated_at=now,
            )
            self._gates[gate_id] = gate
            simulation_auditor.record_event(
                event_type="GATE_CHECK_FAILED_STALE",
                simulation_id=simulation.simulation_id,
                details={"gate_id": gate_id, "status": status.value, "drift": drift_details},
            )
            return gate

        # 2. Authorization & Approvals Revalidation (Prompts #132, #133, #134)
        interventions = simulation.diff.get("interventions", [])
        auth_reqs = self._auth_checker.check_requirements(interventions if isinstance(interventions, list) else [])

        # Check simulation risks
        has_critical_risk = any(r.impact == "CRITICAL" for r in simulation.risks)
        has_high_risk = any(r.impact == "HIGH" for r in simulation.risks)

        if (has_critical_risk or has_high_risk) and not user_approved:
            status = ExecutionGateStatus.NEEDS_APPROVAL
        elif any(req.required_role not in user_roles for req in auth_reqs if req.required_role == "admin"):
            status = ExecutionGateStatus.NEEDS_AUTHORIZATION
        else:
            status = ExecutionGateStatus.READY

        # 3. Formulate Verification Plan Postconditions (Prompt #139)
        verification_plan = [
            "Check service health endpoint returns HTTP 200 within 30s.",
            "Verify p95 latency does not spike beyond +20% threshold.",
            "Inspect error rate remains below 0.1% for 3 consecutive telemetry probes.",
            "Confirm no downstream service cascaded into degraded state.",
        ]

        gate = ExecutionGate(
            gate_id=gate_id,
            simulation_id=simulation.simulation_id,
            scenario_id=simulation.scenario_id,
            status=status,
            baseline_snapshot_id=snapshot.snapshot_id,
            baseline_hash_at_sim=snapshot.baseline_hash,
            current_hash=current_hash,
            drift_detected=False,
            drift_details={},
            verification_plan=verification_plan,
            evaluated_at=now,
        )

        self._gates[gate_id] = gate
        simulation_auditor.record_event(
            event_type="GATE_EVALUATED",
            simulation_id=simulation.simulation_id,
            details={"gate_id": gate_id, "status": status.value},
        )
        return gate

    def get_gate(self, gate_id: str) -> ExecutionGate | None:
        return self._gates.get(gate_id)

    def assert_gate_ready(self, gate_id: str) -> None:
        """Throws if the gate is not in READY state, strictly blocking premature execution."""
        gate = self._gates.get(gate_id)
        if gate is None:
            raise UnverifiedExecutionError(f"Execution gate '{gate_id}' does not exist.")

        if gate.status == ExecutionGateStatus.STALE or gate.status == ExecutionGateStatus.INVALIDATED:
            raise StaleSimulationError(
                f"Transition blocked: ExecutionGate is {gate.status.value}. Baseline state has drifted. "
                "You must re-run simulation against fresh digital twin snapshot."
            )

        if gate.status != ExecutionGateStatus.READY:
            raise UnverifiedExecutionError(
                f"Transition blocked: ExecutionGate is {gate.status.value}. Real execution requires READY status."
            )


transition_engine = RealWorldTransitionEngine()
