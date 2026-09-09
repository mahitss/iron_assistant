"""Event Dispatcher with failure isolation, retry, deduplication, and dead-letter routing.

Guarantees that a failure in one subscriber handler never blocks or cancels
unrelated subscribers handling the same event.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, List, Optional

from app.config.settings import settings
from app.events.dead_letter import dead_letter_manager
from app.events.dedup import EventDeduplicator
from app.events.metrics import event_metrics
from app.events.retry import PermanentDeliveryError
from app.events.schemas import Event
from app.events.subscriber import EventSubscriber

logger = logging.getLogger(__name__)


class EventDispatcher:
    """Dispatches events to subscribers with bounded queue, failure isolation, and retry handling."""

    def __init__(
        self,
        deduplicator: Optional[EventDeduplicator] = None,
        max_queue_size: Optional[int] = None,
    ) -> None:
        self.deduplicator = deduplicator or EventDeduplicator()
        queue_size = (
            max_queue_size
            if max_queue_size is not None
            else getattr(settings, "KAIRO_EVENTS_MAX_IN_MEMORY_QUEUE", 2000)
        )
        self._queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=queue_size)
        self._subscribers: List[EventSubscriber] = []
        self._workers: List[asyncio.Task] = []
        self._running: bool = False
        self._lock = asyncio.Lock()

    @property
    def queue_size(self) -> int:
        return self._queue.qsize()

    @property
    def is_running(self) -> bool:
        return self._running

    def register_subscriber(self, subscriber: EventSubscriber) -> None:
        """Register subscriber and sort list by priority descending."""
        self._subscribers.append(subscriber)
        self._subscribers.sort(key=lambda s: s.priority, reverse=True)
        logger.info(
            "Registered subscriber '%s' (pattern: %s, priority: %d)",
            subscriber.name,
            subscriber.pattern,
            subscriber.priority,
        )

    def unregister_subscriber(self, subscriber_name: str) -> bool:
        """Unregister a subscriber by name."""
        orig_len = len(self._subscribers)
        self._subscribers = [s for s in self._subscribers if s.name != subscriber_name]
        return len(self._subscribers) < orig_len

    def get_subscribers(self) -> List[EventSubscriber]:
        return list(self._subscribers)

    async def enqueue(self, event: Event) -> None:
        """Enqueue event into bounded queue. Raises BufferError if queue is full."""
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.error(
                "Event queue full (%d items)! Dropping/rejecting event: %s",
                self._queue.maxsize,
                event.event_id,
            )
            await event_metrics.record_failed("queue_overflow")
            raise BufferError(f"Event bus queue capacity reached ({self._queue.maxsize} items)")

    async def _dispatch_to_subscriber(self, subscriber: EventSubscriber, event: Event) -> None:
        """Executes a single subscriber handler with metrics, retry, and dead letter capture."""
        start_time = time.time()
        await event_metrics.record_delivered(subscriber.name)

        try:
            await subscriber.retry_policy.execute_with_retry(
                handler=subscriber.handler,
                event=event,
                subscriber_name=subscriber.name,
            )
            duration = time.time() - start_time
            await event_metrics.record_processed(subscriber.name, duration)
        except Exception as exc:
            duration = time.time() - start_time
            await event_metrics.record_failed(subscriber.name)
            await event_metrics.record_dead_letter()

            logger.error(
                "Subscriber '%s' failed handling event '%s': %s",
                subscriber.name,
                event.event_id,
                exc,
            )
            # Route to dead letter manager
            try:
                await dead_letter_manager.record_failure(
                    event=event,
                    subscriber_name=subscriber.name,
                    error=exc,
                    retry_count=subscriber.retry_policy.max_retries,
                    first_attempt_at=event.timestamp,
                )
            except Exception as dl_err:
                logger.critical("Failed to write to Dead Letter Queue: %s", dl_err)

    async def dispatch_event_direct(self, event: Event) -> int:
        """Directly dispatch an event to all matching subscribers with failure isolation.

        Returns number of subscribers matched and executed.
        """
        # Deduplication check
        idempotency_key = (
            (event.metadata or {}).get("idempotency_key")
            or event.event_id
        )
        if await self.deduplicator.is_duplicate(idempotency_key):
            logger.info("Skipping duplicate event: %s (key: %s)", event.event_id, idempotency_key)
            return 0

        await self.deduplicator.mark_seen(idempotency_key)

        # Find matching subscribers
        matching = [s for s in self._subscribers if s.matches(event)]
        if not matching:
            logger.debug("No matching subscribers for event '%s' (type: %s)", event.event_id, event.event_type)
            return 0

        # FAILURE ISOLATION:
        # Group subscribers by priority or dispatch concurrently using gather(..., return_exceptions=True)
        tasks = [self._dispatch_to_subscriber(s, event) for s in matching]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for s, res in zip(matching, results):
            if isinstance(res, Exception):
                logger.error("Isolated handler error in '%s': %s", s.name, res)

        return len(matching)

    async def _worker_loop(self, worker_id: int) -> None:
        """Worker loop reading events from in-memory queue."""
        logger.info("Event dispatcher worker-%d started.", worker_id)
        while self._running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            try:
                await self.dispatch_event_direct(event)
            except Exception as exc:
                logger.error("Unhandled worker error processing event '%s': %s", event.event_id, exc)
            finally:
                self._queue.task_done()

        logger.info("Event dispatcher worker-%d stopped.", worker_id)

    async def start(self, worker_count: int = 2) -> None:
        """Start background worker tasks."""
        async with self._lock:
            if self._running:
                return
            self._running = True
            self._workers = [
                asyncio.create_task(self._worker_loop(i), name=f"event-worker-{i}")
                for i in range(worker_count)
            ]
            logger.info("Event dispatcher started with %d workers.", worker_count)

    async def stop(self, drain: bool = True, timeout: float = 5.0) -> None:
        """Gracefully stop dispatcher and optionally drain in-flight queue items."""
        async with self._lock:
            if not self._running:
                return
            logger.info("Stopping event dispatcher (drain=%s)...", drain)

            if drain and not self._queue.empty():
                try:
                    await asyncio.wait_for(self._queue.join(), timeout=timeout)
                except asyncio.TimeoutError:
                    logger.warning("Event dispatcher drain timed out after %.1fs.", timeout)

            self._running = False
            for w in self._workers:
                w.cancel()
            await asyncio.gather(*self._workers, return_exceptions=True)
            self._workers.clear()
            logger.info("Event dispatcher stopped.")
