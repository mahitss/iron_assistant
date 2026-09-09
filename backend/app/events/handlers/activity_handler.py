"""Activity feed event subscriber and timeline formatter for Kairo.

Transforms low-level event streams into clear, human-readable timeline entries
for the user-facing Activity Feed.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.events.db import get_event_db_session
from app.events.models import EventRecord
from app.events.schemas import Event
from sqlalchemy import desc, select

logger = logging.getLogger(__name__)

# Recent in-memory activity buffer (per user or global fallback)
_recent_activities: List[Dict[str, Any]] = []


def format_activity_title(event_type: str, payload: Dict[str, Any]) -> str:
    """Format human-readable title for event type and payload."""
    if event_type == "github.ci.failed":
        return f"CI Workflow Failed: {payload.get('workflow_name', 'Build')} on {payload.get('repo', 'repo')}"
    elif event_type == "github.pr.merged":
        return f"PR #{payload.get('pr_number', '')} Merged: {payload.get('title', 'Pull Request')}"
    elif event_type == "chat.message.created":
        role = payload.get("role", "User")
        return f"New {role.capitalize()} Message"
    elif event_type == "chat.response.completed":
        tokens = payload.get("tokens_generated", 0)
        return f"Assistant Response Generated ({tokens} tokens)"
    elif event_type == "security.blocked":
        return f"Security Guard Blocked Action: {payload.get('tool_name', 'Action')}"
    elif event_type == "approval.requested":
        return f"Approval Required: {payload.get('action', 'Action')}"
    elif event_type == "approval.granted":
        return f"Approval Granted for {payload.get('action', 'Action')}"
    elif event_type == "device.connected":
        return f"Companion Device Connected: {payload.get('device_name', 'Device')}"
    elif event_type == "evaluation.completed":
        return f"Evaluation Run Completed: {payload.get('benchmark_name', 'Benchmark')}"
    elif event_type == "emergency_stop.activated":
        return "EMERGENCY STOP Triggered"
    elif event_type == "notification.created":
        return f"Alert: {payload.get('title', 'Notification')}"

    return f"Event: {event_type.replace('.', ' ').title()}"


async def handle_activity_event(event: Event) -> None:
    """Subscribed handler to format and buffer activity records."""
    title = format_activity_title(event.event_type, event.payload or {})
    activity_entry = {
        "id": event.event_id,
        "event_type": event.event_type,
        "user_id": event.user_id,
        "title": title,
        "source": event.source,
        "timestamp": event.timestamp.isoformat() if event.timestamp else None,
        "payload": event.payload or {},
        "metadata": event.metadata or {},
    }

    _recent_activities.insert(0, activity_entry)
    if len(_recent_activities) > 500:
        _recent_activities.pop()


async def get_user_activity(
    user_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """Retrieve activity feed entries for a given user from database or buffer."""
    try:
        async with get_event_db_session() as session:
            if session is not None:
                query = select(EventRecord)
                if user_id:
                    query = query.where(EventRecord.user_id == user_id)
                query = query.order_by(desc(EventRecord.timestamp)).limit(limit).offset(offset)
                res = await session.execute(query)
                records = res.scalars().all()
            if records:
                return [
                    {
                        "id": r.id,
                        "event_type": r.event_type,
                        "user_id": r.user_id,
                        "title": format_activity_title(r.event_type, r.payload or {}),
                        "source": r.source,
                        "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                        "payload": r.payload or {},
                    }
                    for r in records
                ]
    except Exception as db_err:
        logger.debug("Database activity fetch failed: %s", db_err)

    # Fallback to in-memory buffer
    activities = _recent_activities
    if user_id:
        activities = [a for a in activities if a.get("user_id") == user_id or a.get("user_id") is None]
    return activities[offset : offset + limit]


def clear_recent_activities() -> None:
    _recent_activities.clear()
