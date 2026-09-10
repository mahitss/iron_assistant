"""Policy state tracking and anti-self-policy-modification guards (INVARIANTS 42, 43, 127-129)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class PolicyTamperingError(Exception):
    """Raised when an attempt is made to weaken or modify system security/governance policies autonomously."""
    pass


class PolicyStateManager:
    """Tracks active system governance policies and protects security controls from autonomous modification."""

    def __init__(self) -> None:
        # policy_rule_name -> bool permitted
        self._governance_rules: Dict[str, bool] = {
            "allow_arbitrary_shell_execution": False,
            "require_approval_for_destructive_actions": True,
            "enforce_audit_logging": True,
            "prevent_security_center_disabling": True,
            "require_tls_on_external_calls": True,
        }

    def check_policy(self, rule_name: str) -> bool:
        return self._governance_rules.get(rule_name, False)

    def attempt_policy_update(self, rule_name: str, new_value: bool, authorized_by_governance: bool = False) -> None:
        """INVARIANT 127 & 128: Self-model cannot modify policy or disable SecurityCenter."""
        if not authorized_by_governance:
            raise PolicyTamperingError(
                f"Autonomous modification of policy rule '{rule_name}' is forbidden. Security controls immutable."
            )
        self._governance_rules[rule_name] = new_value

    def get_policy_summary(self) -> Dict[str, Any]:
        return dict(self._governance_rules)
