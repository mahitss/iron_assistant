"""Authentication Freshness and Step-up Verification for Kairo Governance (Task 36).

Enforces:
- Active session requirements.
- Step-up MFA verification for sensitive/critical operations.
- Authentication age thresholds (e.g., maximum 15 minutes for privileged actions).
- Blocking expired sessions.
"""

from datetime import UTC, datetime
from typing import Any

from app.policy.schemas import PolicyContext, PolicyDecisionType, RiskLevel


class AuthFreshnessChecker:
    """Evaluates session validity, authentication freshness, and step-up MFA requirements."""

    MAX_FRESH_AUTH_MINUTES = 15.0

    @classmethod
    def evaluate_authentication(cls, context: PolicyContext, risk_level: RiskLevel) -> tuple[PolicyDecisionType | None, str | None]:
        """Verify authentication freshness and session state against risk level."""
        session = context.session
        action = (context.action or "").strip().lower()

        # If action is anonymous read, session might be optional depending on user context
        if not session:
            if risk_level in (RiskLevel.R2_MODERATE, RiskLevel.R3_HIGH, RiskLevel.R4_CRITICAL):
                return PolicyDecisionType.DENY, "Privileged operation requires an active, authenticated security session"
            return None, None

        # 1. Expired Session Check (Section 127)
        if session.get("is_expired") is True or session.get("is_active") is False:
            return PolicyDecisionType.DENY, "Security session is expired or inactive. Re-authentication required"

        # 2. Authentication Age Check (Section 63)
        auth_time = session.get("authenticated_at")
        if auth_time:
            try:
                dt_auth = datetime.fromisoformat(auth_time) if isinstance(auth_time, str) else auth_time
                if dt_auth.tzinfo is None:
                    dt_auth = dt_auth.replace(tzinfo=UTC)
                age_minutes = (datetime.now(UTC) - dt_auth).total_seconds() / 60.0

                # If high risk or critical action, require fresh auth within 15 minutes
                if risk_level in (RiskLevel.R3_HIGH, RiskLevel.R4_CRITICAL) and age_minutes > cls.MAX_FRESH_AUTH_MINUTES:
                    return (
                        PolicyDecisionType.REQUIRE_STEP_UP_AUTH,
                        f"Authentication is {int(age_minutes)} minutes old. Sensitive operations require step-up authentication within {cls.MAX_FRESH_AUTH_MINUTES} minutes"
                    )
            except (ValueError, TypeError):
                pass

        # 3. MFA Requirement for Critical Operations
        if risk_level == RiskLevel.R4_CRITICAL or any(k in action for k in ("modify_security", "rotate_keys", "deploy_production")):
            if not session.get("mfa_verified"):
                return PolicyDecisionType.REQUIRE_STEP_UP_AUTH, "Critical operation strictly requires multi-factor authentication (MFA)"

        return None, None
