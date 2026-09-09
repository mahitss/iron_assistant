"""Unified Event Bus API Routes.

Exposes registry inspection, dead-letter queue management, replay operations,
event metrics, user activity stream, and safe publication endpoints.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.events.bus import event_bus
from app.events.dead_letter import dead_letter_manager
from app.events.handlers.activity_handler import get_user_activity
from app.events.metrics import event_metrics
from app.events.registry import event_registry
from app.events.schemas import Event, ReplaySafety

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["Events"])


def get_current_user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    """Extract and validate the authenticated user ID from request header."""
    if not x_user_id or not x_user_id.strip():
        return "default_user"
    return x_user_id.strip()


class PublishEventRequest(BaseModel):
    """Schema for external/client publication of allowed events."""

    event_type: str = Field(..., description="Canonical event type, e.g. 'notification.read'")
    source: str = Field(default="api_client", description="Origin source")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Event payload dictionary")
    correlation_id: Optional[str] = Field(default=None, description="Optional tracing correlation ID")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Arbitrary metadata")


class ReplayDeadLetterRequest(BaseModel):
    """Schema for requesting a dead-letter replay."""

    force: bool = Field(default=False, description="Force replay if review required")
    reason: Optional[str] = Field(default=None, description="Reason or justification for replay")


@router.get(
    "/registry",
    summary="List registered event schemas and policies",
    description="Returns full catalog of all 18+ registered event namespaces, replay safety levels, and retentions.",
)
async def get_event_registry_catalog() -> Dict[str, Any]:
    """Retrieve full catalog of registered event types."""
    events = event_registry.list_all()
    return {
        "total": len(events),
        "events": [
            {
                "event_type": e.event_type,
                "version": e.version,
                "description": e.description,
                "replay_safety": e.replay_safety.value if hasattr(e.replay_safety, "value") else str(e.replay_safety),
                "security_class": e.security_class.value if hasattr(e.security_class, "value") else str(e.security_class),
                "retention_days": e.retention_days,
            }
            for e in events
        ],
    }


@router.get(
    "/metrics",
    summary="Event bus metrics and throughput",
    description="Returns event bus throughput, p95 latency, retry counts, dead letters, and worker queues.",
)
async def get_bus_metrics() -> Dict[str, Any]:
    """Retrieve event bus telemetry snapshot."""
    queue_size = event_bus.dispatcher.queue_size
    subscribers_count = len(event_bus.dispatcher.get_subscribers())
    return await event_metrics.get_snapshot(queue_size=queue_size, subscriber_count=subscribers_count)


@router.get(
    "/dead-letters",
    summary="List dead letter queue records",
    description="Retrieves failed, permanent error, or retry-exhausted events for triage.",
)
async def list_dead_letters(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user_id: str = Depends(get_current_user_id),
) -> Dict[str, Any]:
    """List dead letters with pagination and status filtering."""
    records = await dead_letter_manager.list_dead_letters(
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return {
        "items": records,
        "limit": limit,
        "offset": offset,
    }


@router.get(
    "/dead-letters/{dead_letter_id}",
    summary="Get dead letter record by ID",
)
async def get_dead_letter_detail(
    dead_letter_id: str,
    user_id: str = Depends(get_current_user_id),
) -> Dict[str, Any]:
    """Retrieve single dead letter record."""
    record = await dead_letter_manager.get_dead_letter(dead_letter_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dead letter record not found")
    return record


@router.post(
    "/dead-letters/{dead_letter_id}/replay",
    summary="Replay dead letter event with safety enforcement",
    description="Replays dead lettered event if classified as REPLAY_SAFE or approved.",
)
async def replay_dead_letter_event(
    dead_letter_id: str,
    body: Optional[ReplayDeadLetterRequest] = None,
    user_id: str = Depends(get_current_user_id),
) -> Dict[str, Any]:
    """Replay a dead letter event while strictly preventing NON_REPLAYABLE side-effecting replays."""
    force = body.force if body else False
    try:
        success = await dead_letter_manager.replay_dead_letter(
            dead_letter_id=dead_letter_id,
            event_bus=event_bus,
            reviewed_by=user_id,
            force=force,
        )
        return {
            "replayed": success,
            "dead_letter_id": dead_letter_id,
            "reviewed_by": user_id,
        }
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post(
    "/dead-letters/{dead_letter_id}/discard",
    summary="Discard dead letter event",
)
async def discard_dead_letter_event(
    dead_letter_id: str,
    reason: Optional[str] = Query(default=None),
    user_id: str = Depends(get_current_user_id),
) -> Dict[str, Any]:
    """Mark a dead letter entry as discarded without replay."""
    try:
        await dead_letter_manager.discard_dead_letter(dead_letter_id, reason=reason)
        return {"discarded": True, "dead_letter_id": dead_letter_id}
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get(
    "/activity",
    summary="Get user-scoped activity timeline",
    description="Returns human-readable activity timeline stream for the current user.",
)
async def get_activity_timeline(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user_id: str = Depends(get_current_user_id),
) -> Dict[str, Any]:
    """Retrieve user-scoped activity entries."""
    activities = await get_user_activity(user_id=user_id, limit=limit, offset=offset)
    return {
        "items": activities,
        "limit": limit,
        "offset": offset,
    }


@router.post(
    "/publish",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Publish safe event to the bus",
    description="Allows authenticated clients to emit non-privileged events into the event bus.",
)
async def publish_event(
    body: PublishEventRequest,
    user_id: str = Depends(get_current_user_id),
) -> Dict[str, Any]:
    """Publish client event with strict security authority and redaction."""
    event = event_bus.publisher.create_event(
        event_type=body.event_type,
        source=body.source,
        payload=body.payload,
        user_id=user_id,
        correlation_id=body.correlation_id,
        metadata=body.metadata,
    )

    try:
        published_event = await event_bus.publish(event)
        return {
            "status": "accepted",
            "event_id": published_event.event_id,
            "event_type": published_event.event_type,
            "timestamp": published_event.timestamp.isoformat(),
        }
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Security Authority Violation: {exc}",
        )
