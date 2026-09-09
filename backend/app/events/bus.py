"""Central EventBus for Kairo Event-Driven Runtime.

Provides high-level pub/sub, pattern routing, graceful startup/drain, and metrics.
"""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set

from app.config.settings import settings
from app.events.dedup import EventDeduplicator
from app.events.dispatcher import EventDispatcher
from app.events.publisher import EventPublisher
from app.events.retry import RetryPolicy
from app.events.schemas import Event
from app.events.subscriber import EventHandler, EventSubscriber

logger = logging.getLogger(__name__)


class EventBus:
    """The central unified Event Bus coordinating all Kairo asynchronous events."""

    def __init__(
        self,
        deduplicator: Optional[EventDeduplicator] = None,
        dispatcher: Optional[EventDispatcher] = None,
    ) -> None:
        self.deduplicator = deduplicator or EventDeduplicator()
        self.dispatcher = dispatcher or EventDispatcher(deduplicator=self.deduplicator)
        self.publisher = EventPublisher(bus=self)
        self._enabled: bool = getattr(settings, "KAIRO_EVENTS_ENABLED", True)

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    def subscribe(
        self,
        pattern: str,
        handler: EventHandler,
        name: Optional[str] = None,
        priority: int = 50,
        retry_policy: Optional[RetryPolicy] = None,
        system_wide: bool = False,
        allowed_user_ids: Optional[Set[str]] = None,
        filter_func: Optional[Callable[[Event], bool]] = None,
    ) -> EventSubscriber:
        """Register a subscriber handler with pattern matching and isolation."""
        sub_name = name or f"{handler.__name__}_{pattern}"
        subscriber = EventSubscriber(
            name=sub_name,
            pattern=pattern,
            handler=handler,
            priority=priority,
            retry_policy=retry_policy,
            system_wide=system_wide,
            allowed_user_ids=allowed_user_ids,
            filter_func=filter_func,
        )
        self.dispatcher.register_subscriber(subscriber)
        return subscriber

    def on(
        self,
        pattern: str,
        name: Optional[str] = None,
        priority: int = 50,
        retry_policy: Optional[RetryPolicy] = None,
        system_wide: bool = False,
        allowed_user_ids: Optional[Set[str]] = None,
        filter_func: Optional[Callable[[Event], bool]] = None,
    ) -> Callable[[EventHandler], EventHandler]:
        """Decorator for registering an event handler."""
        def decorator(handler: EventHandler) -> EventHandler:
            self.subscribe(
                pattern=pattern,
                handler=handler,
                name=name or f"{handler.__name__}_{pattern}",
                priority=priority,
                retry_policy=retry_policy,
                system_wide=system_wide,
                allowed_user_ids=allowed_user_ids,
                filter_func=filter_func,
            )
            return handler
        return decorator

    def unsubscribe(self, subscriber_name: str) -> bool:
        """Remove a subscriber by name."""
        return self.dispatcher.unregister_subscriber(subscriber_name)

    def get_subscribers(self) -> List[EventSubscriber]:
        """Return list of all registered subscribers."""
        return self.dispatcher.get_subscribers()

    async def publish(
        self,
        event: Event,
        persist_log: bool = True,
    ) -> Event:
        """Publish an event through the security guard and into the dispatch pipeline."""
        if not self._enabled:
            logger.debug("Event bus is disabled; ignoring event: %s", event.event_id)
            return event

        return await self.publisher.publish(event, persist_log=persist_log)

    async def dispatch(self, event: Event) -> int:
        """Dispatch event directly to matching subscribers or enqueue if running worker pool."""
        if not self._enabled:
            return 0

        if self.dispatcher.is_running:
            try:
                await self.dispatcher.enqueue(event)
                return 1
            except BufferError:
                # Fallback to direct synchronous execution if buffer overflow occurs
                return await self.dispatcher.dispatch_event_direct(event)
        else:
            # Direct synchronous dispatch
            return await self.dispatcher.dispatch_event_direct(event)

    async def start(self, worker_count: int = 2) -> None:
        """Start background dispatch worker loop."""
        await self.dispatcher.start(worker_count=worker_count)

    async def stop(self, drain: bool = True, timeout: float = 5.0) -> None:
        """Gracefully stop dispatchers."""
        await self.dispatcher.stop(drain=drain, timeout=timeout)

    async def clear(self) -> None:
        """Reset deduplicator and subscriber state (used for test isolation)."""
        await self.deduplicator.clear()
        self.dispatcher._subscribers.clear()


event_bus = EventBus()


def get_event_bus() -> EventBus:
    """Retrieve global EventBus instance."""
    return event_bus
