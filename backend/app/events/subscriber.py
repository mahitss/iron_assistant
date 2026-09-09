"""Event Subscriber definition and matching logic for Kairo Event Bus.

Supports wildcard pattern matching, handler priorities, tenant isolation, and custom filters.
"""

from __future__ import annotations

import fnmatch
import logging
from typing import Any, Callable, Coroutine, Optional, Set

from app.events.retry import RetryPolicy
from app.events.schemas import Event

logger = logging.getLogger(__name__)

EventHandler = Callable[[Event], Coroutine[Any, Any, Any]]
EventFilter = Callable[[Event], bool]


class EventSubscriber:
    """Represents a registered event subscriber."""

    def __init__(
        self,
        name: str,
        pattern: str,
        handler: EventHandler,
        priority: int = 50,
        retry_policy: Optional[RetryPolicy] = None,
        system_wide: bool = False,
        allowed_user_ids: Optional[Set[str]] = None,
        filter_func: Optional[EventFilter] = None,
    ) -> None:
        self.name = name
        self.pattern = pattern
        self.handler = handler
        self.priority = priority  # Higher priority executes first
        self.retry_policy = retry_policy or RetryPolicy()
        self.system_wide = system_wide
        self.allowed_user_ids = set(allowed_user_ids) if allowed_user_ids is not None else None
        self.filter_func = filter_func

    def matches_pattern(self, event_type: str) -> bool:
        """Check if event_type matches the subscriber pattern."""
        if self.pattern == "*" or self.pattern == event_type:
            return True
        return fnmatch.fnmatch(event_type, self.pattern)

    def is_tenant_allowed(self, event: Event) -> bool:
        """Enforces tenant and user isolation boundaries.

        System-wide subscribers (e.g. Audit, Global Telemetry) can see events across users.
        Tenant-scoped subscribers can ONLY see events matching their allowed user IDs.
        """
        if self.system_wide:
            return True

        # If subscriber is restricted to specific users, enforce check
        if self.allowed_user_ids is not None:
            if event.user_id is None:
                # System event without user_id: allow if subscriber allows system events
                return False
            return event.user_id in self.allowed_user_ids

        return True

    def matches(self, event: Event) -> bool:
        """Evaluate pattern, tenant isolation, and custom filter."""
        if not self.matches_pattern(event.event_type):
            return False

        if not self.is_tenant_allowed(event):
            return False

        if self.filter_func is not None:
            try:
                return bool(self.filter_func(event))
            except Exception as e:
                logger.warning("Filter function failed on subscriber '%s': %s", self.name, e)
                return False

        return True

    def __repr__(self) -> str:
        return f"<EventSubscriber name={self.name} pattern={self.pattern} priority={self.priority}>"
