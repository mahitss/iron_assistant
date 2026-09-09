"""Kairo Unified Event Bus and Event-Driven Runtime."""

from app.events.bus import EventBus, event_bus
from app.events.dead_letter import DeadLetterManager, dead_letter_manager
from app.events.dedup import EventDeduplicator
from app.events.dispatcher import EventDispatcher
from app.events.handlers import register_default_handlers
from app.events.metrics import EventMetricsTracker, event_metrics
from app.events.outbox import OutboxProcessor, TransactionalOutbox, outbox_processor, transactional_outbox
from app.events.publisher import EventPublisher
from app.events.registry import EventRegistry, event_registry
from app.events.retry import (
    EventBusError,
    PermanentDeliveryError,
    RetryPolicy,
    TransientDeliveryError,
)
from app.events.safety import EventSecurityGuard
from app.events.schemas import (
    Event,
    EventSource,
    EventStatus,
    ReplaySafety,
)

__all__ = [
    "EventBus",
    "event_bus",
    "Event",
    "EventSource",
    "EventStatus",
    "ReplaySafety",
    "EventPublisher",
    "EventSubscriber",
    "EventDispatcher",
    "EventDeduplicator",
    "RetryPolicy",
    "EventBusError",
    "TransientDeliveryError",
    "PermanentDeliveryError",
    "DeadLetterManager",
    "dead_letter_manager",
    "EventRegistry",
    "event_registry",
    "EventMetricsTracker",
    "event_metrics",
    "TransactionalOutbox",
    "OutboxProcessor",
    "transactional_outbox",
    "outbox_processor",
    "EventSecurityGuard",
    "register_default_handlers",
]
