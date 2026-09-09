"""Safe Policy Explanation and Decision Trace Generator (Task 36).

Produces concise, user-friendly explanations without leaking internal
security secrets, regex patterns, or bypassable implementation details.
"""

from typing import Any

from app.policy.schemas import PolicyDecisionType, PolicyRule, RiskLevel


class PolicyExplainer:
    """Generates sanitized user-facing explanations and safe debugging traces."""

    SAFE_REASON_MAP: dict[str, str] = {
        "PRODUCTION_REQUIRES_APPROVAL": "Production operations require formal human approval.",
        "EMERGENCY_STOP_ACTIVE": "System Emergency Stop is currently active. Action blocked.",
        "SAFE_MODE_ACTIVE": "System is running in Safe Mode (read-only diagnostic). Mutations are prohibited.",
        "CHANGE_FREEZE_ACTIVE": "Environment is currently under an active change freeze.",
        "STEP_UP_AUTH_REQUIRED": "This action requires recent multi-factor or step-up authentication.",
        "UNTRUSTED_DEVICE": "Operation is restricted to verified, trusted hardware devices.",
        "DEVICE_REVOKED": "Access denied: The requesting device is not authorized or has been revoked.",
        "CROSS_PROJECT_DENIED": "Cross-project resource modification is restricted.",
        "CROSS_USER_DENIED": "Access to another user's private resources is restricted.",
        "SECRETS_PROTECTED": "Sensitive credentials and raw secrets cannot be processed directly.",
        "UNAPPROVED_PROVIDER": "Data classification policy restricts processing to approved model enclaves.",
        "BUDGET_EXCEEDED": "Autonomous execution budget reached. Action paused for review.",
        "AUTOMATION_LIMIT_REACHED": "Maximum automation executions reached for this schedule.",
    }

    @classmethod
    def get_safe_explanation(
        cls,
        decision: PolicyDecisionType,
        rule: PolicyRule | None = None,
        reason_code: str | None = None,
        fallback_msg: str | None = None
    ) -> str:
        """Return a user-safe explanation that avoids leaking sensitive rules."""
        if rule and rule.safe_explanation:
            return rule.safe_explanation

        if reason_code and reason_code in cls.SAFE_REASON_MAP:
            return cls.SAFE_REASON_MAP[reason_code]

        if fallback_msg:
            # Strip internal paths or code snippets
            clean = fallback_msg.split("\n")[0]
            if len(clean) > 160:
                clean = clean[:157] + "..."
            return clean

        default_map = {
            PolicyDecisionType.ALLOW: "Action permitted under current governance policy.",
            PolicyDecisionType.DENY: "Action blocked by security governance policy.",
            PolicyDecisionType.REQUIRE_APPROVAL: "Action requires human approval prior to execution.",
            PolicyDecisionType.REQUIRE_CONFIRMATION: "Action requires explicit user confirmation.",
            PolicyDecisionType.REQUIRE_STEP_UP_AUTH: "Action requires step-up authentication.",
            PolicyDecisionType.ALLOW_WITH_LIMITS: "Action permitted within specific operational limits.",
            PolicyDecisionType.DEFER: "Action deferred pending operational resource review.",
        }
        return default_map.get(decision, "Policy evaluation complete.")

    @classmethod
    def build_denial_guidance(
        cls,
        reason_code: str | None,
        safe_explanation: str,
        next_path: str | None = None
    ) -> dict[str, Any]:
        """Construct structured user guidance on denial with safe next steps."""
        suggested_next = next_path
        if not suggested_next:
            if "approval" in safe_explanation.lower() or reason_code == "PRODUCTION_REQUIRES_APPROVAL":
                suggested_next = "Request formal approval from a project administrator"
            elif "step_up" in str(reason_code).lower() or "authentication" in safe_explanation.lower():
                suggested_next = "Perform step-up verification via MFA"
            elif "freeze" in safe_explanation.lower():
                suggested_next = "Wait until the change freeze window concludes or request an emergency freeze exception"
            else:
                suggested_next = "Contact your system security administrator"

        return {
            "status": "DENIED",
            "reason_code": reason_code or "POLICY_DENIED",
            "explanation": safe_explanation,
            "next_step": suggested_next,
        }
