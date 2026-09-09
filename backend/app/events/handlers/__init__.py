"""Default event handlers and subscribers registration."""

from __future__ import annotations

import logging
from typing import Any

from app.events.handlers.activity_handler import handle_activity_event
from app.events.handlers.knowledge_handler import handle_knowledge_ingestion
from app.events.handlers.notification_handler import handle_notification_event
from app.events.handlers.proactive_handler import handle_proactive_event
from app.events.handlers.security_handler import handle_security_event

logger = logging.getLogger(__name__)


def register_default_handlers(bus: Any) -> None:
    """Registers standard system subscribers onto the given Event Bus."""
    # 1. Security & Audit Handler (Priority 90)
    bus.subscribe(
        pattern="security.*",
        handler=handle_security_event,
        name="security_audit_subscriber_sec",
        priority=90,
        system_wide=True,
    )
    bus.subscribe(
        pattern="approval.*",
        handler=handle_security_event,
        name="security_audit_subscriber_app",
        priority=90,
        system_wide=True,
    )
    bus.subscribe(
        pattern="emergency_stop.*",
        handler=handle_security_event,
        name="security_audit_subscriber_es",
        priority=95,
        system_wide=True,
    )

    # 2. Notification Dispatcher (Priority 60)
    for pat in [
        "notification.created",
        "github.ci.failed",
        "approval.requested",
        "emergency_stop.activated",
        "security.blocked",
    ]:
        bus.subscribe(
            pattern=pat,
            handler=handle_notification_event,
            name=f"notification_subscriber_{pat}",
            priority=60,
            system_wide=True,
        )

    # 3. Proactive Intelligence (Priority 50)
    for pat in [
        "github.ci.failed",
        "device.connected",
        "browser.page.navigated",
        "security.blocked",
    ]:
        bus.subscribe(
            pattern=pat,
            handler=handle_proactive_event,
            name=f"proactive_subscriber_{pat}",
            priority=50,
            system_wide=True,
        )

    # 4. Knowledge & Memory Ingestion (Priority 40)
    for pat in [
        "chat.response.completed",
        "github.pr.merged",
        "evaluation.completed",
        "project.updated",
    ]:
        bus.subscribe(
            pattern=pat,
            handler=handle_knowledge_ingestion,
            name=f"knowledge_subscriber_{pat}",
            priority=40,
            system_wide=True,
        )

    # 5. User Activity Feed & Timeline (Priority 10)
    bus.subscribe(
        pattern="*",
        handler=handle_activity_event,
        name="activity_feed_subscriber",
        priority=10,
        system_wide=True,
    )

    logger.info("Default EventBus subscribers successfully registered.")
