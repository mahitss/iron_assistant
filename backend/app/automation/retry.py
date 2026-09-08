"""Exponential backoff retry policy filtering non-retryable exceptions."""

NON_RETRYABLE_EXCEPTIONS: tuple[str, ...] = (
    "PermissionDeniedError",
    "PermissionDenied",
    "AuthenticationError",
    "GitHubAuthenticationError",
    "GitHubPermissionError",
    "GitHubNotFoundError",
    "PathSecurityError",
    "CommandPolicyViolation",
    "ValueError",
    "KeyError",
    "TypeError",
    "InvalidStateTransitionError",
)


class RetryPolicy:
    """Configures retry behavior for transient workflow step failures."""

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay_seconds: float = 1.0,
        max_delay_seconds: float = 30.0,
        backoff_multiplier: float = 2.0,
    ) -> None:
        self.max_attempts = max_attempts
        self.initial_delay_seconds = initial_delay_seconds
        self.max_delay_seconds = max_delay_seconds
        self.backoff_multiplier = backoff_multiplier

    def is_retryable(self, exc: Exception, attempt: int) -> bool:
        """Determine if an exception is eligible for retry."""
        if attempt >= self.max_attempts:
            return False

        exc_type = type(exc).__name__
        if exc_type in NON_RETRYABLE_EXCEPTIONS:
            return False

        # If message contains explicit authorization/permission keywords
        msg = str(exc).lower()
        if any(k in msg for k in ("permission denied", "not authorized", "forbidden", "invalid arguments")):
            return False

        return True

    def get_delay_seconds(self, attempt: int) -> float:
        """Calculate exponential backoff delay for current attempt."""
        delay = self.initial_delay_seconds * (self.backoff_multiplier ** max(0, attempt - 1))
        return min(delay, self.max_delay_seconds)
