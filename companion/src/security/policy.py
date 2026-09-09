"""Local Policy Engine enforcing independent defense-in-depth security checks."""

import logging
from typing import Any

from companion.src.device.state import CompanionState, DeviceStateManager
from companion.src.permissions.registry import ActionDefinition, ActionRegistry
from companion.src.permissions.risk import RiskLevel
from companion.src.security.emergency_stop import LocalEmergencyStop

logger = logging.getLogger("kairo.companion.security.policy")


class LocalPolicyEngine:
    """Independent local gatekeeper verifying device state, capabilities, and safety rules."""

    def __init__(
        self,
        registry: ActionRegistry | None = None,
        state_manager: DeviceStateManager | None = None,
        emergency_stop: LocalEmergencyStop | None = None,
        allowed_filesystem_paths: list[str] | None = None,
    ) -> None:
        self.registry = registry or ActionRegistry()
        self.state_manager = state_manager or DeviceStateManager()
        self.emergency_stop = emergency_stop or LocalEmergencyStop()
        self.allowed_filesystem_paths = allowed_filesystem_paths or []

    def evaluate_action_request(
        self,
        action_name: str,
        parameters: dict[str, Any],
        has_verified_approval: bool = False,
    ) -> tuple[bool, str, ActionDefinition]:
        """Evaluate if an action is permitted by local policy.

        Returns: (allowed: bool, reason: str, action_def: ActionDefinition)
        """
        # 1. Action Allowlist Check
        try:
            action_def = self.registry.get_action(action_name)
        except Exception as exc:
            return False, f"Action rejected: {exc}", None

        # 2. Local Emergency Stop Check (Layer 1)
        if self.emergency_stop.is_stopped:
            return False, "Action blocked: Local Emergency Stop is ACTIVE.", action_def

        # 3. Companion Lifecycle State Check
        current_state = self.state_manager.current_state
        if current_state == CompanionState.REVOKED:
            return False, "Action blocked: Companion is REVOKED.", action_def

        if current_state == CompanionState.STOPPED:
            return False, "Action blocked: Companion is in STOPPED state.", action_def

        # Read-only actions (like screen.capture) can be armed in READY state;
        # Active mutating actions require ARMED or ACTIVE state
        if action_def.risk_level != RiskLevel.READ_ONLY:
            if current_state not in (CompanionState.ARMED, CompanionState.ACTIVE):
                return (
                    False,
                    f"Action blocked: Computer control is {current_state.value}. Must be ARMED or ACTIVE.",
                    action_def,
                )

        # 4. Capability Toggle Check
        required_cap = action_def.capability
        if not self.state_manager.is_capability_enabled(required_cap):
            return (
                False,
                f"Action blocked: Required capability '{required_cap}' is disabled locally.",
                action_def,
            )

        # 5. Local Approval Requirement Check
        if action_def.requires_approval and not has_verified_approval:
            return (
                False,
                "Action requires explicit user approval artifact before local execution.",
                action_def,
            )

        return True, "Action approved by local policy.", action_def
