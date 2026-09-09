"""Environment policy manager for Kairo Governance (Task 36).

Enforces production guardrails, change freezes, maintenance windows,
safe mode restrictions, and incident mode defenses.
"""

from datetime import UTC, datetime
from typing import Any

from app.policy.schemas import PolicyContext, PolicyDecisionType


class EnvironmentPolicyManager:
    """Manages environment classifications, change freezes, and production-specific constraints."""

    VALID_ENVIRONMENTS = {"development", "test", "staging", "production"}

    def __init__(self) -> None:
        self._change_freezes: dict[str, dict[str, Any]] = {}  # env -> metadata
        self._maintenance_windows: dict[str, dict[str, Any]] = {}
        self._safe_mode: bool = False
        self._incident_mode: bool = False

    def set_change_freeze(self, environment: str, active: bool, reason: str = "", authorized_by: str = "") -> None:
        """Activate or deactivate a change freeze on an environment."""
        env = environment.lower()
        if active:
            self._change_freezes[env] = {
                "active": True,
                "reason": reason or "Scheduled production change freeze",
                "authorized_by": authorized_by,
                "activated_at": datetime.now(UTC).isoformat(),
            }
        else:
            self._change_freezes.pop(env, None)

    def is_change_freeze_active(self, environment: str) -> tuple[bool, str]:
        """Check if a change freeze is active for the given environment."""
        info = self._change_freezes.get(environment.lower())
        if info and info.get("active"):
            return True, info.get("reason", "Change freeze active")
        return False, ""

    def get_frozen_environments(self) -> list[str]:
        """List all environments currently under change freeze."""
        return [env for env, info in self._change_freezes.items() if info.get("active")]

    def set_safe_mode(self, enabled: bool) -> None:
        """Set global system safe mode (read-only diagnostic mode)."""
        self._safe_mode = enabled

    @property
    def is_safe_mode(self) -> bool:
        return self._safe_mode

    def set_incident_mode(self, enabled: bool) -> None:
        """Set system incident response mode (restricts automated mutations)."""
        self._incident_mode = enabled

    @property
    def is_incident_mode(self) -> bool:
        return self._incident_mode

    def evaluate_environment_constraints(self, context: PolicyContext) -> tuple[PolicyDecisionType | None, str | None]:
        """Evaluate environment-specific baseline policies and invariants.

        Returns (Decision, Reason) if an environment-level invariant triggers, else (None, None).
        """
        env = (context.environment or "development").strip().lower()
        action = (context.action or "").strip().lower()
        world_state = context.world_state or {}

        # 1. Safe Mode Enforcement (Section 109, 110)
        safe_mode_active = self._safe_mode or world_state.get("safe_mode") is True
        if safe_mode_active:
            # Only read-only actions permitted in safe mode
            is_read = action in ("read", "get", "list", "search", "inspect", "status", "view", "diagnose")
            if not is_read:
                return PolicyDecisionType.DENY, "Safe mode is active: all mutations and executions are strictly prohibited"

        # 2. Incident Mode Enforcement (Section 111)
        incident_active = self._incident_mode or world_state.get("incident_mode") is True
        if incident_active:
            # Autonomous and automated actions are blocked during active incident
            if context.task is not None or (context.intent or {}).get("is_autonomous"):
                return PolicyDecisionType.DENY, "Incident mode is active: autonomous background mutations are suspended"

        # 3. Change Freeze Enforcement (Section 112)
        frozen, freeze_reason = self.is_change_freeze_active(env)
        if not frozen and world_state.get(f"change_freeze_{env}"):
            frozen = True
            freeze_reason = "Environment change freeze declared in system state"

        if frozen:
            if any(k in action for k in ("deploy", "modify_config", "patch", "delete", "upgrade", "restart")):
                # Unless explicit exception is provided in context constraints
                if not (context.task or {}).get("has_freeze_exception"):
                    return PolicyDecisionType.DENY, f"Action blocked: Change freeze active on '{env}'. Reason: {freeze_reason}"

        # 4. Production Specific Invariants (Sections 17, 46, 122)
        if env == "production":
            # Target must be explicitly specified (no wildcard or null target)
            if not context.target:
                return PolicyDecisionType.DENY, "Production operations strictly require an explicit, concrete target"

            # Production mutations require human approval
            if any(k in action for k in ("deploy", "delete", "drop", "terminate", "modify_config", "write", "patch", "reboot")):
                # Check if fresh state verification is missing
                target_dict = context.target if isinstance(context.target, dict) else {}
                if target_dict.get("state_is_stale") is True:
                    return PolicyDecisionType.DENY, "Production action blocked: Target state is stale and requires refresh"

                return PolicyDecisionType.REQUIRE_APPROVAL, "Production deployments, deletions, and configuration modifications require human approval"

        return None, None


# Global singleton instance
environment_policy_manager = EnvironmentPolicyManager()
