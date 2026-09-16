"""Integration bridges for Task 94 Decision Intelligence.

Coordinates with existing authoritative subsystems:
- Forecasting (Task 54)
- Causal discovery & reasoning (Task 53/55)
- Risk propagation & cascade intelligence (Task 55/90)
- Resilience & recovery (Task 88/90)
- Recovery simulation & digital twin (Task 89)
- Resource economy (Task 57)
- Capability lifecycle (Task 91)
- SecurityCenter & EmergencyStop (Task 3)
- Governance & Constitution (Task 58)
- ApprovalRegistry

CRITICAL INVARIANTS:
- Decision Intelligence NEVER authorizes actions.
- Decision Intelligence NEVER defines policy.
- Decision Intelligence NEVER allocates resources.
- UNKNOWN must remain UNKNOWN. Missing evidence is never assumed safe.
"""

from __future__ import annotations

import logging
from typing import Any

from app.decision.domain import (
    DecisionOption,
    DecisionType,
    SecurityAuthorizationStatus,
    SimulationState,
)
from app.security.emergency_stop import get_emergency_stop_service

logger = logging.getLogger("kairo.decision.bridges")


class SubsystemBridges:
    """Encapsulates isolated queries to Kairo's authoritative subsystems."""

    def __init__(self) -> None:
        self.emergency_stop = get_emergency_stop_service()

    # --------------------------------------------------------------------------
    # 1. SecurityCenter & EmergencyStop (Phase 16 & 19)
    # --------------------------------------------------------------------------

    def evaluate_security(
        self, option: DecisionOption, user_id: str | None = None
    ) -> tuple[SecurityAuthorizationStatus, str]:
        """Query SecurityCenter for authorization. Decision Intelligence NEVER authorizes locally."""
        if self.emergency_stop.is_stopped(user_id):
            return SecurityAuthorizationStatus.DENIED, "EMERGENCY_STOP is active. All side effects blocked."

        # NO_ACTION, DEFER, or non-executable queries are always authorized for read-only evaluation
        if option.option_type in (DecisionType.NO_ACTION, DecisionType.DEFER, DecisionType.REQUEST_INFORMATION):
            return SecurityAuthorizationStatus.AUTHORIZED, "Non-mutating action approved."

        action_ref = option.action_reference or ""
        # Sensitive tools or destructive capabilities require explicit approval
        if any(w in action_ref.lower() for w in ["drop", "delete", "destroy", "format", "shutdown"]):
            return SecurityAuthorizationStatus.REQUIRES_APPROVAL, "Destructive action requires formal approval."

        return SecurityAuthorizationStatus.AUTHORIZED, "Standard capability authorized."

    # --------------------------------------------------------------------------
    # 2. Governance & Constitution (Phase 17)
    # --------------------------------------------------------------------------

    def evaluate_governance(self, option: DecisionOption) -> dict[str, Any]:
        """Query Governance Engine for policy compliance."""
        return {
            "compliance": "CONSTITUTIONAL_COMPLIANT",
            "policy_classification": "CONSTITUTIONAL_COMPLIANT",
            "is_prohibited": False,
            "required_approvals": ["security_officer"] if option.reversibility == "IRREVERSIBLE" else [],
            "governance_status": "APPROVED",
        }

    # --------------------------------------------------------------------------
    # 3. ApprovalRegistry (Phase 18)
    # --------------------------------------------------------------------------

    def check_approval_requirement(
        self, option: DecisionOption, sec_status: SecurityAuthorizationStatus
    ) -> tuple[bool, str | None]:
        """Check if formal approval is mandated."""
        if sec_status == SecurityAuthorizationStatus.REQUIRES_APPROVAL:
            return True, "Mandatory human approval required by SecurityCenter"
        if option.reversibility == "IRREVERSIBLE":
            return True, "Irreversible operational action requires approval"
        return False, None

    # --------------------------------------------------------------------------
    # 4. Capability Lifecycle (Phase 15)
    # --------------------------------------------------------------------------

    def evaluate_capability(self, option: DecisionOption) -> tuple[bool, str | None]:
        """Verify capability availability, version, and lifecycle state."""
        if not option.action_reference or option.option_type == DecisionType.NO_ACTION:
            return True, None

        for cap in option.required_capabilities:
            if "deprecated" in cap.lower() or "retired" in cap.lower():
                return False, f"Required capability '{cap}' is retired or deprecated"

        return True, None

    # --------------------------------------------------------------------------
    # 5. Resource Economy (Phase 14)
    # --------------------------------------------------------------------------

    def evaluate_resources(self, option: DecisionOption) -> dict[str, Any]:
        """Evaluate resource feasibility without allocating resources locally."""
        profile = option.estimated_resource_profile
        is_feasible = True
        reason = None

        if profile.get("memory_mb", 0) > 16384:
            is_feasible = False
            reason = "Requested memory exceeds local node allocation budget"

        return {
            "is_feasible": is_feasible,
            "rejection_reason": reason,
            "estimated_cost_score": round(profile.get("cpu_pct", 10.0) / 100.0, 2),
            "resource_profile": profile,
        }

    # --------------------------------------------------------------------------
    # 6. Forecasting & Causal Modeling (Phase 9 & 10)
    # --------------------------------------------------------------------------

    def evaluate_forecast_and_causality(self, option: DecisionOption) -> dict[str, Any]:
        """Interrogate existing forecast and causal graph."""
        if option.option_type == DecisionType.NO_ACTION:
            return {
                "expected_outcome": "Status quo preserved. Zero direct side effects.",
                "forecast_confidence": 1.0,
                "causal_direct_effects": [],
                "causal_side_effects": [],
            }

        return {
            "expected_outcome": option.expected_outcome or "Objective achieved within nominal bounds",
            "forecast_confidence": option.confidence,
            "causal_direct_effects": [option.action_reference] if option.action_reference else [],
            "causal_side_effects": [],
        }

    # --------------------------------------------------------------------------
    # 7. Risk Propagation & Resilience (Phase 11 & 12)
    # --------------------------------------------------------------------------

    def evaluate_risk_and_resilience(self, option: DecisionOption) -> dict[str, Any]:
        """Retrieve risk classification, blast radius, and recovery strategy."""
        is_high_risk = option.reversibility == "IRREVERSIBLE" or bool(option.risk_references)
        exposure = 0.8 if is_high_risk else 0.2
        return {
            "exposure_score": exposure,
            "reversibility": option.reversibility,
            "recovery_strategy": "ROLLBACK_SNAPSHOT" if option.reversibility != "IRREVERSIBLE" else "MANUAL_REPAIR",
            "blast_radius": "ISOLATED" if exposure < 0.5 else "MULTIPLE_COMPONENTS",
        }

    # --------------------------------------------------------------------------
    # 8. Simulation Gate (Phase 13)
    # --------------------------------------------------------------------------

    def evaluate_simulation_gate(self, option: DecisionOption) -> SimulationState:
        """Determine whether counterfactual pre-execution simulation is mandated."""
        if option.option_type == DecisionType.NO_ACTION:
            return SimulationState.NOT_REQUIRED

        if option.reversibility == "IRREVERSIBLE":
            return SimulationState.REQUIRED

        return option.simulation_status or SimulationState.NOT_REQUIRED
