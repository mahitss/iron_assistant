"""Action modeling, intent reference, authority tracking, and self-checks (INVARIANTS 39-41, 47-49)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.metacognition.schemas import (
    ActionAuthority,
    ActionReadinessSchema,
    ExecutionReadiness,
)


class ActionGuardError(Exception):
    """Raised when an action is executed without required preconditions or authority."""
    pass


class ActionEngine:
    """Manages action intent references, authority validation, and pre/post-condition checks."""

    @staticmethod
    def assess_readiness(
        action_name: str,
        required_capabilities: List[str],
        available_capabilities: List[str],
        is_authorized: bool,
        is_policy_permitted: bool,
        requires_approval: bool = False,
        is_approved: bool = False,
        preconditions: Optional[Dict[str, bool]] = None,
        risk_level: str = "LOW",
    ) -> ActionReadinessSchema:
        """INVARIANT 45 & 47: Comprehensive structured readiness assessment before action."""
        missing_caps = [c for c in required_capabilities if c not in available_capabilities]
        blocking_reasons: List[str] = []

        if missing_caps:
            blocking_reasons.append(f"Missing required capabilities: {', '.join(missing_caps)}")

        if not is_authorized:
            blocking_reasons.append("Unauthorized action execution.")

        if not is_policy_permitted:
            blocking_reasons.append("Action is prohibited by system policy.")

        if requires_approval and not is_approved:
            blocking_reasons.append("Human approval required before execution.")

        # Check preconditions (INVARIANT 48)
        preconditions_met = True
        if preconditions:
            failed_preconditions = [k for k, v in preconditions.items() if not v]
            if failed_preconditions:
                preconditions_met = False
                blocking_reasons.append(f"Unmet preconditions: {', '.join(failed_preconditions)}")

        # Determine readiness state
        if missing_caps:
            readiness = ExecutionReadiness.BLOCKED
        elif not is_authorized:
            readiness = ExecutionReadiness.NEEDS_AUTHORIZATION
        elif not is_policy_permitted:
            readiness = ExecutionReadiness.BLOCKED
        elif requires_approval and not is_approved:
            readiness = ExecutionReadiness.NEEDS_APPROVAL
        elif not preconditions_met:
            readiness = ExecutionReadiness.BLOCKED
        else:
            readiness = ExecutionReadiness.READY

        # Determine authority state
        if not is_authorized:
            auth_state = ActionAuthority.UNAUTHORIZED
        elif requires_approval and not is_approved:
            auth_state = ActionAuthority.APPROVAL_REQUIRED
        elif requires_approval and is_approved:
            auth_state = ActionAuthority.APPROVED
        elif not is_policy_permitted:
            auth_state = ActionAuthority.BLOCKED
        else:
            auth_state = ActionAuthority.AUTHORIZED

        return ActionReadinessSchema(
            action_name=action_name,
            readiness=readiness,
            required_capabilities=required_capabilities,
            missing_capabilities=missing_caps,
            authority_state=auth_state,
            policy_permitted=is_policy_permitted,
            preconditions_met=preconditions_met,
            blocking_reasons=blocking_reasons,
            risk_level=risk_level,
        )

    @staticmethod
    def verify_postcondition(expected_keys: List[str], execution_result: Dict[str, Any]) -> bool:
        """INVARIANT 49: After execution, verify that expected postconditions were achieved."""
        return all(k in execution_result for k in expected_keys)
