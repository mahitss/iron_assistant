"""Security exception hierarchy for Kairo Security Center."""


class SecurityError(Exception):
    """Base exception for all security violations and authorization failures."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class CapabilityDisabledError(SecurityError):
    """Raised when an action is denied because its required capability is disabled."""


class ApprovalRequiredError(SecurityError):
    """Raised when an action requires human approval before proceeding."""

    def __init__(self, message: str, approval_id: str | None = None, details: dict | None = None) -> None:
        super().__init__(message, details)
        self.approval_id = approval_id


class ApprovalExpiredError(SecurityError):
    """Raised when an approval request has exceeded its expiration deadline."""


class ApprovalInvalidError(SecurityError):
    """Raised when an approval is invalid, mismatched, or cannot be decided."""


class EmergencyStopActiveError(SecurityError):
    """Raised when an action is blocked because Emergency Stop is active."""


class RateLimitExceededError(SecurityError):
    """Raised when security rate limits are exceeded."""


class TenantIsolationError(SecurityError):
    """Raised when a user attempts cross-tenant access to another user's security resources."""
