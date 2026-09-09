"""Exponential backoff calculation with jitter and server Retry-After support."""

from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
import random
from app.resilience.schemas import RetryPolicy


class BackoffCalculator:
    """Calculates sleep delays for retries with exponential backoff, jitter, and Retry-After."""

    @staticmethod
    def calculate_delay(
        attempt: int,
        policy: RetryPolicy,
        server_retry_after: str | int | float | None = None,
    ) -> float:
        """Calculates backoff delay in seconds for a given attempt index (0-based)."""
        # 1. Check if server specified a valid Retry-After header
        if policy.respect_retry_after and server_retry_after is not None:
            parsed_delay = BackoffCalculator.parse_retry_after(server_retry_after)
            if parsed_delay is not None and parsed_delay >= 0:
                # Bound by policy max_delay to prevent external DOS via huge Retry-After
                return min(parsed_delay, policy.max_delay)

        # 2. Exponential backoff: initial * (multiplier ** attempt)
        calculated = policy.initial_delay * (policy.multiplier ** max(0, attempt))
        capped = min(calculated, policy.max_delay)

        # 3. Full Jitter: uniform random between 0 and capped
        if policy.jitter:
            return random.uniform(capped * 0.5, capped)

        return capped

    @staticmethod
    def parse_retry_after(header_val: str | int | float) -> float | None:
        """Parses an HTTP Retry-After header which can be either seconds or an HTTP date."""
        if isinstance(header_val, (int, float)):
            return float(header_val)

        if not isinstance(header_val, str):
            return None

        val = header_val.strip()
        # Check if numeric seconds
        if val.isdigit():
            return float(val)

        # Try parsing RFC 2822 / 1123 date
        try:
            target_time = parsedate_to_datetime(val)
            now = datetime.now(UTC)
            if target_time.tzinfo is None:
                target_time = target_time.replace(tzinfo=UTC)
            diff = (target_time - now).total_seconds()
            return max(0.0, diff)
        except Exception:
            return None
