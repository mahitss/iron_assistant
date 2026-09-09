"""Proactive Intelligence event subscriber.

Evaluates incoming signals such as CI failures, system state changes, and connected devices
to suggest proactive remediation and intelligent assistance.
"""

from __future__ import annotations

import logging
from typing import Any

from app.events.schemas import Event

logger = logging.getLogger(__name__)


async def handle_proactive_event(event: Event) -> None:
    """Evaluates incoming event signals for proactive assistance."""
    event_type = event.event_type
    payload = event.payload or {}
    user_id = event.user_id

    logger.info(
        "ProactiveHandler received event '%s' (ID: %s, User: %s)",
        event_type,
        event.event_id,
        user_id,
    )

    if event_type == "github.ci.failed":
        repo = payload.get("repo", "unknown")
        workflow = payload.get("workflow_name", "CI")
        logger.info(
            "Proactive Intelligence triggered: Analyzing CI failure on %s (%s) for automated fix recommendations.",
            repo,
            workflow,
        )

    elif event_type == "device.connected":
        device_name = payload.get("device_name", "Device")
        logger.info("Proactive Intelligence detected new companion device: %s", device_name)

    elif event_type == "security.blocked":
        reason = payload.get("reason", "policy violation")
        logger.warning("Proactive Intelligence noting security block event: %s", reason)
