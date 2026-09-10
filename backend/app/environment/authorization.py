"""Environment Action Authorization and Approval Revalidation (Task 54, Prompts #115-#117, #131, #132)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.environment.safety import ProductionSafetyViolationError
from app.environment.temporal import parse_utc, utc_now


class EnvironmentAuthorizationEngine:
    """Enforces policy, verifies approvals, and detects stale authorization/approval tokens."""

    @staticmethod
    def validate_action_authorization(
        actor: str,
        action: str,
        target_environment: str,
        auth_issued_at: datetime | str,
        max_auth_age_seconds: int = 1800,  # 30 mins
    ) -> bool:
        """Prompt #131: Revalidate authorization for long-running workflows."""
        now = utc_now()
        issued = parse_utc(auth_issued_at)
        age = (now - issued).total_seconds()

        if age > max_auth_age_seconds:
            raise ProductionSafetyViolationError(
                f"Authorization expired for actor '{actor}' executing '{action}'. Issued {int(age)}s ago; max allowed is {max_auth_age_seconds}s."
            )
        return True

    @staticmethod
    def validate_approval_freshness(
        approval_token: dict[str, Any],
        target_resource_current_state: dict[str, Any],
    ) -> bool:
        """Prompt #132: Revalidate approval when target state materially changes."""
        approved_target_state = approval_token.get("approved_state_baseline", {})
        for k, v in approved_target_state.items():
            if target_resource_current_state.get(k) != v:
                raise ProductionSafetyViolationError(
                    f"Approval invalidated: Target baseline changed for attribute '{k}' since approval was granted."
                )
        return True
