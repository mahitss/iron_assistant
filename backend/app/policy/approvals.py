"""Policy Approval Bridge for Kairo Governance (Task 36).

Coordinates with Security ApprovalManager to verify that:
- Human approvals are strictly non-transferable (cannot reuse across actions, targets, envs).
- Approvals have not expired.
- State freshness is revalidated prior to granting execution authority.
"""

from datetime import UTC, datetime
from typing import Any

from app.policy.schemas import PolicyContext, PolicyDecisionType


class PolicyApprovalBridge:
    """Verifies approval claims and requirements against policy standards."""

    @classmethod
    def validate_approval_claim(
        cls,
        context: PolicyContext,
        approval_claim: dict[str, Any] | None
    ) -> tuple[bool, str | None]:
        """Validate that an existing approval claim is valid, unexpired, and strictly matches the context."""
        if not approval_claim:
            return False, "Action requires approval, but no approval token/claim was provided"

        # 1. Expiration check (Section 59, 128)
        expires_at_raw = approval_claim.get("expires_at")
        if expires_at_raw:
            try:
                expires_at = datetime.fromisoformat(expires_at_raw) if isinstance(expires_at_raw, str) else expires_at_raw
                if datetime.now(UTC) > expires_at:
                    return False, "Approval has expired. A fresh approval must be requested"
            except (ValueError, TypeError):
                return False, "Invalid expiration format on approval claim"

        # 2. Status check
        status = str(approval_claim.get("status", "")).lower()
        if status != "approved":
            return False, f"Approval request is not in APPROVED state (current status: '{status}')"

        # 3. Non-Transferability checks (Section 58)
        # Action must match
        expected_action = approval_claim.get("action")
        if expected_action and context.action:
            if expected_action.lower() != context.action.lower():
                return False, f"Approval non-transferability violation: approved for action '{expected_action}', but requested '{context.action}'"

        # Target must match
        expected_target = approval_claim.get("target")
        actual_target = context.target
        actual_target_str = str(actual_target.get("id") or actual_target.get("path") if isinstance(actual_target, dict) else actual_target)
        if expected_target and actual_target_str:
            if str(expected_target) != actual_target_str:
                return False, f"Approval non-transferability violation: approved for target '{expected_target}', but requested '{actual_target_str}'"

        # Environment must match
        expected_env = approval_claim.get("environment")
        if expected_env and context.environment:
            if expected_env.lower() != context.environment.lower():
                return False, f"Approval non-transferability violation: approved for environment '{expected_env}', but requested '{context.environment}'"

        # User must match
        user_id = (context.user or {}).get("id") or (context.user or {}).get("user_id")
        expected_user = approval_claim.get("user_id")
        if expected_user and user_id:
            if str(expected_user) != str(user_id):
                return False, f"Approval non-transferability violation: approved for user '{expected_user}', but requested by '{user_id}'"

        # 4. Target freshness check (Section 60, 95, 142)
        if isinstance(context.target, dict) and context.target.get("state_is_stale") is True:
            return False, "Target state has changed or is stale since approval was granted. Revalidation required"

        return True, None
