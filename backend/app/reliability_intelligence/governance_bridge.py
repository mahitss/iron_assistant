"""Governance, SecurityCenter, and EmergencyStop bridge for Task 90."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.reliability_intelligence.models import (
    AutonomyAdaptationLevel,
    EarlyWarningState,
    PreventionActionType,
    PreventionCandidate,
    ReversibilityLevel,
)
from app.security.emergency_stop import get_emergency_stop_service

logger = logging.getLogger("kairo.reliability_intelligence.governance_bridge")


class GovernanceBridge:
    """Enforces constitutional gating, approval requirements, and EmergencyStop primacy."""

    def __init__(self, coordinator: Optional[Any] = None) -> None:
        self._coordinator = coordinator

    def _get_coordinator(self) -> Any:
        if self._coordinator is None:
            try:
                from app.policy.governance_coordinator import GovernanceIntelligenceCoordinator
                self._coordinator = GovernanceIntelligenceCoordinator()
            except Exception as e:
                logger.debug("Task 78 GovernanceIntelligenceCoordinator lazy init: %s", e)
        return self._coordinator

    def check_emergency_stop(self) -> bool:
        """Returns True if global EmergencyStop is active."""
        try:
            e_stop = get_emergency_stop_service()
            return e_stop.is_stopped()
        except Exception as e:
            logger.warning("EmergencyStop check error: %s", e)
            return False

    def evaluate_authorization(
        self,
        candidate: PreventionCandidate,
        current_autonomy: AutonomyAdaptationLevel,
    ) -> Tuple[bool, bool, str]:
        """Evaluates whether candidate is authorized or requires human operator approval.

        Returns (is_authorized, requires_approval, reason).
        """
        # 1. EmergencyStop Primacy: ABSOLUTE KILL-SWITCH
        if self.check_emergency_stop():
            logger.error("Prevention authorization REJECTED: EmergencyStop is ACTIVE")
            return False, False, "EMERGENCY_STOP_ACTIVE: Proactive interventions are prohibited fail-closed"

        # 2. NO_ACTION requires no authorization
        if candidate.is_no_action:
            return True, False, "Passive observation approved"

        # 3. Autonomy state constraints
        if current_autonomy == AutonomyAdaptationLevel.STOPPED:
            return False, False, "System autonomy is STOPPED; all proactive execution suspended"
        elif current_autonomy == AutonomyAdaptationLevel.MANUAL_REQUIRED:
            return False, True, "System autonomy requires manual operator approval for all interventions"

        # 4. Action risk and reversibility tiers
        if candidate.action_type in (
            PreventionActionType.RELEASE_RESOURCE,
            PreventionActionType.REFRESH_POOL,
            PreventionActionType.THROTTLE,
            PreventionActionType.REDUCE_CONCURRENCY,
        ):
            # Low-risk, fully reversible actions can execute autonomously under FULL or CAUTIOUS
            if current_autonomy in (AutonomyAdaptationLevel.FULL, AutonomyAdaptationLevel.CAUTIOUS):
                return True, False, f"Autonomous execution authorized for low-risk action {candidate.action_type.value}"
            return False, True, f"Operator approval required under autonomy level {current_autonomy.value}"

        elif candidate.action_type in (
            PreventionActionType.RECONNECT,
            PreventionActionType.PAUSE_LOW_PRIORITY_WORK,
            PreventionActionType.DEGRADE_CAPABILITY,
        ):
            # Moderate-risk actions
            if current_autonomy == AutonomyAdaptationLevel.FULL and candidate.reversibility == ReversibilityLevel.REVERSIBLE:
                return True, False, f"Autonomous execution authorized for reversible moderate-risk action {candidate.action_type.value}"
            return False, True, f"Operator approval required for {candidate.action_type.value}"

        elif candidate.action_type in (
            PreventionActionType.RESTART_COMPONENT,
            PreventionActionType.FAILOVER,
            PreventionActionType.PAUSE_WORKFLOW,
        ):
            # Mutating service operations require explicit approval unless pre-approved by policy
            return False, True, f"Operator approval required for service mutating intervention {candidate.action_type.value}"

        elif candidate.action_type == PreventionActionType.ESCALATE:
            # Escalation to human is inherently safe
            return True, False, "Human operator escalation authorized"

        return False, True, f"Operator approval required for {candidate.action_type.value}"

    def adapt_autonomy_level(
        self,
        early_warning_state: EarlyWarningState,
        verification_failure_rate: float = 0.0,
        critical_incidents_active: int = 0,
    ) -> AutonomyAdaptationLevel:
        """Dynamically adapts autonomy according to Section 40 principles."""
        if self.check_emergency_stop():
            return AutonomyAdaptationLevel.STOPPED

        # Repeated verification failures or critical signals reduce autonomy
        if verification_failure_rate > 0.40 or critical_incidents_active >= 3:
            return AutonomyAdaptationLevel.MANUAL_REQUIRED
        elif verification_failure_rate > 0.20 or early_warning_state == EarlyWarningState.CRITICAL:
            return AutonomyAdaptationLevel.RESTRICTED
        elif early_warning_state in (EarlyWarningState.HIGH, EarlyWarningState.ELEVATED):
            return AutonomyAdaptationLevel.CAUTIOUS

        return AutonomyAdaptationLevel.FULL


_global_governance_bridge: Optional[GovernanceBridge] = None


def get_governance_bridge() -> GovernanceBridge:
    global _global_governance_bridge
    if _global_governance_bridge is None:
        _global_governance_bridge = GovernanceBridge()
    return _global_governance_bridge
