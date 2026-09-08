"""Permission levels and access control for Kairo tools."""

from app.security.permissions import PermissionDecision, PermissionLevel


class PermissionDeniedError(Exception):
    """Raised when a tool is not authorized for execution."""

    def __init__(self, tool_name: str, permission_level: PermissionLevel, reason: str = "Permission denied"):
        super().__init__(f"Execution of '{tool_name}' ({permission_level.value}) denied: {reason}")
        self.tool_name = tool_name
        self.permission_level = permission_level
        self.reason = reason


class PermissionManager:
    """Manages authorization policies for tool execution.

    Currently:
    - READ: automatically allowed.
    - WRITE, EXTERNAL, EXECUTE: requires approval (denied without explicit approval).
    - DESTRUCTIVE: denied.
    """

    def __init__(self, custom_policies: dict[PermissionLevel, PermissionDecision] | None = None):
        self._policies = {
            PermissionLevel.READ: PermissionDecision.AUTO_ALLOWED,
            PermissionLevel.WRITE: PermissionDecision.REQUIRES_APPROVAL,
            PermissionLevel.EXTERNAL: PermissionDecision.REQUIRES_APPROVAL,
            PermissionLevel.EXECUTE: PermissionDecision.REQUIRES_APPROVAL,
            PermissionLevel.DESTRUCTIVE: PermissionDecision.DENIED,
        }
        if custom_policies:
            self._policies.update(custom_policies)

    def evaluate(self, tool_name: str, permission_level: PermissionLevel) -> PermissionDecision:
        """Evaluate permission level against current security policy."""
        return self._policies.get(permission_level, PermissionDecision.DENIED)

    def check_permission(self, tool_name: str, permission_level: PermissionLevel) -> None:
        """Check permission and raise PermissionDeniedError if not AUTO_ALLOWED."""
        decision = self.evaluate(tool_name, permission_level)
        if decision != PermissionDecision.AUTO_ALLOWED:
            raise PermissionDeniedError(
                tool_name=tool_name,
                permission_level=permission_level,
                reason=f"Policy evaluated to {decision.value}. Autonomous execution is not permitted.",
            )
