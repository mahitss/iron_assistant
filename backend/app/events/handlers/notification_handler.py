"""Notification dispatch subscriber for Kairo Event Bus.

Routes alerts for CI failures, approval requests, and emergency stops to the user.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.events.schemas import Event

logger = logging.getLogger(__name__)

# In-memory buffer of recent notifications for testing and feed inspection
_recent_notifications: List[Dict[str, Any]] = []


def get_recent_notifications() -> List[Dict[str, Any]]:
    return list(_recent_notifications)


def clear_recent_notifications() -> None:
    _recent_notifications.clear()


async def handle_notification_event(event: Event) -> None:
    """Dispatches notification alerts based on event content."""
    event_type = event.event_type
    payload = event.payload or {}
    user_id = event.user_id

    title = "Kairo Alert"
    body = ""
    severity = "info"

    if event_type == "github.ci.failed":
        repo = payload.get("repo", "repo")
        workflow = payload.get("workflow_name", "Build")
        title = f"CI Build Failed: {repo}"
        body = f"Workflow '{workflow}' failed. Proactive diagnosis initiated."
        severity = "warning"

    elif event_type == "approval.requested":
        action = payload.get("action", "Action")
        title = "Action Requires Approval"
        body = f"Kairo requires your approval to proceed with: {action}"
        severity = "warning"

    elif event_type == "emergency_stop.activated":
        title = "EMERGENCY STOP ACTIVATED"
        body = f"System-wide emergency stop triggered: {payload.get('reason', 'Operator request')}"
        severity = "critical"

    elif event_type == "security.blocked":
        title = "Security Guard Blocked Action"
        body = f"Action blocked: {payload.get('reason', 'Security policy violation')}"
        severity = "warning"

    elif event_type == "notification.created":
        title = payload.get("title", "Notification")
        body = payload.get("body", "")
        severity = payload.get("severity", "info")

    notification_record = {
        "event_id": event.event_id,
        "event_type": event_type,
        "user_id": user_id,
        "title": title,
        "body": body,
        "severity": severity,
        "timestamp": event.timestamp.isoformat() if event.timestamp else None,
    }

    _recent_notifications.append(notification_record)
    if len(_recent_notifications) > 200:
        _recent_notifications.pop(0)

    logger.info(
        "Notification dispatched: [%s] %s - %s (User: %s)",
        severity.upper(),
        title,
        body,
        user_id,
    )
