"""Unified Notification Service coordinating ingestion, policy, delivery, and lifecycle (Task 34)."""

from datetime import UTC, datetime, timedelta
import logging
from typing import Any
import uuid

from sqlalchemy import and_, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.events.schemas import Event
from app.notifications.actions import NotificationActionDispatcher
from app.notifications.delivery import NotificationDeliveryCoordinator
from app.notifications.dedupe import NotificationDeduplicator
from app.notifications.grouping import NotificationGrouper
from app.notifications.models import (
    NotificationActionModel,
    NotificationDeliveryModel,
    NotificationModel,
    NotificationPreferenceModel,
)
from app.notifications.policy import DeliveryDecision, NotificationPolicy
from app.notifications.preferences import NotificationPreferencesManager
from app.notifications.priority import PriorityResolver
from app.notifications.schemas import (
    ActionStatus,
    ActionType,
    NotificationActionCreate,
    NotificationActionExecuteRequest,
    NotificationActionExecuteResponse,
    NotificationCreateRequest,
    NotificationPriority,
    NotificationResponse,
    NotificationState,
    NotificationType,
)
from app.notifications.templates import TemplateRenderer
from app.notifications.throttling import NotificationThrottler
from app.security.exceptions import TenantIsolationError

logger = logging.getLogger("kairo.notifications.service")


class UnifiedNotificationService:
    """
    Unified high-level facade for Kairo communication and alerting.
    Enforces that Events != Notifications (Section Core Principle).
    """

    def __init__(
        self,
        deduplicator: NotificationDeduplicator | None = None,
        grouper: NotificationGrouper | None = None,
        throttler: NotificationThrottler | None = None,
        delivery_coordinator: NotificationDeliveryCoordinator | None = None,
    ) -> None:
        self.deduplicator = deduplicator or NotificationDeduplicator()
        self.grouper = grouper or NotificationGrouper()
        self.throttler = throttler or NotificationThrottler()
        self.delivery_coordinator = delivery_coordinator or NotificationDeliveryCoordinator()

    async def handle_event(
        self,
        db_session: AsyncSession,
        event: Event,
    ) -> NotificationModel | None:
        """
        Process an event emitted on the Unified Event Bus into zero, one, or grouped notifications.
        """
        user_id = event.user_id
        if not user_id:
            logger.debug("Event '%s' dropped: no user_id associated.", event.event_type)
            return None

        payload = event.payload if isinstance(event.payload, dict) else {}
        event_type = event.event_type

        # 1. Fetch user preferences
        prefs = await NotificationPreferencesManager.get_or_create_preferences(db_session, user_id)

        # 2. Check noise filter early
        if NotificationPolicy.should_ignore_event(event_type):
            return None

        notif_type = NotificationPolicy.map_event_to_notification_type(event_type)
        priority = PriorityResolver.resolve_priority(event_type, notif_type, payload)

        # 3. Deduplication check
        dedupe_key = NotificationDeduplicator.compute_dedupe_key(
            user_id=user_id,
            event_type=event_type,
            notification_type=notif_type,
            resource_id=payload.get("task_id") or payload.get("approval_id") or payload.get("device_id"),
            state=payload.get("status") or payload.get("state"),
            payload=payload,
        )
        is_dup = await self.deduplicator.is_duplicate(dedupe_key, db_session)

        # 4. Throttling and Storm check
        is_allowed, is_storm, throttle_msg = self.throttler.check_throttle(user_id, notif_type, priority)

        # 5. Evaluate policy
        decision, final_type, final_priority, reason = NotificationPolicy.evaluate(
            event=event,
            preferences=prefs,
            is_duplicate=is_dup,
            is_rate_limited=not is_allowed,
            is_storm=is_storm,
        )

        if decision == DeliveryDecision.SUPPRESS:
            logger.debug("Notification suppressed for event '%s': %s", event_type, reason)
            return None

        now = datetime.now(UTC)

        # 6. Grouping check
        if decision == DeliveryDecision.GROUP or prefs.grouping_enabled:
            should_hold, batch = self.grouper.record_event(
                user_id=user_id,
                event_type=event_type,
                title=payload.get("title") or event_type,
                notification_type=final_type,
                priority=final_priority,
                project_id=payload.get("project_id"),
                incident_id=payload.get("incident_id"),
                metadata=payload,
            )
            if should_hold and batch:
                # Held within sliding grouping window
                return None

        # 7. Render title and body
        title, body = TemplateRenderer.render(
            event_type=event_type,
            notification_type=final_type,
            payload=payload,
            custom_title=payload.get("title"),
            custom_body=payload.get("body"),
        )

        # 8. Create Notification record
        notif_id = f"notif_{uuid.uuid4().hex[:16]}"
        correlation_id = event.correlation_id or f"corr_{uuid.uuid4().hex[:12]}"
        project_id = payload.get("project_id")
        task_id = payload.get("task_id")

        expires_at = None
        if final_type == NotificationType.APPROVAL:
            # Approvals expire in 15 minutes by default
            expires_at = now + timedelta(seconds=900)

        notif = NotificationModel(
            id=notif_id,
            user_id=user_id,
            project_id=project_id,
            task_id=task_id,
            type=final_type.value,
            priority=final_priority.value,
            title=title,
            body=body,
            status=NotificationState.PENDING.value,
            created_at=now,
            expires_at=expires_at,
            source_event_id=event.event_id,
            correlation_id=correlation_id,
            dedupe_key=dedupe_key,
            metadata_json=payload,
        )
        db_session.add(notif)

        # 9. Create typed interactive actions if applicable
        if final_type == NotificationType.APPROVAL and payload.get("approval_id"):
            app_id = str(payload["approval_id"])
            approve_act = NotificationActionModel(
                id=f"act_{uuid.uuid4().hex[:16]}",
                notification_id=notif_id,
                type=ActionType.APPROVE.value,
                label="Approve",
                target_id=app_id,
                status=ActionStatus.PENDING.value,
                expires_at=expires_at,
                created_at=now,
            )
            reject_act = NotificationActionModel(
                id=f"act_{uuid.uuid4().hex[:16]}",
                notification_id=notif_id,
                type=ActionType.REJECT.value,
                label="Reject",
                target_id=app_id,
                status=ActionStatus.PENDING.value,
                expires_at=expires_at,
                created_at=now,
            )
            db_session.add(approve_act)
            db_session.add(reject_act)

        elif final_type == NotificationType.TASK and task_id:
            open_act = NotificationActionModel(
                id=f"act_{uuid.uuid4().hex[:16]}",
                notification_id=notif_id,
                type=ActionType.OPEN.value,
                label="View Task",
                target_id=task_id,
                status=ActionStatus.PENDING.value,
                created_at=now,
            )
            db_session.add(open_act)

        await db_session.commit()
        await db_session.refresh(notif)
        self.deduplicator.record_seen(dedupe_key)

        # 10. Execute Delivery
        deliveries = await self.delivery_coordinator.deliver(
            db_session=db_session,
            notification=notif,
            preferences=prefs,
        )
        self.throttler.record_delivery_outcome(success=any(d.status == "DELIVERED" for d in deliveries))

        # 11. Emit notification.created event
        try:
            from app.events import event_bus
            await event_bus.publish(
                event_bus.publisher.create_event(
                    event_type="notification.created",
                    source="notification",
                    payload={
                        "notification_id": notif.id,
                        "type": notif.type,
                        "priority": notif.priority,
                        "title": notif.title,
                    },
                    user_id=user_id,
                )
            )
        except Exception:
            pass

        return notif

    async def create_notification(
        self,
        db_session: AsyncSession,
        request: NotificationCreateRequest,
    ) -> NotificationResponse:
        """Explicit programmatic notification creation."""
        now = datetime.now(UTC)
        prefs = await NotificationPreferencesManager.get_or_create_preferences(db_session, request.user_id)

        clean_title = TemplateRenderer.sanitize_text(request.title)
        clean_body = TemplateRenderer.sanitize_text(request.body)

        notif_id = f"notif_{uuid.uuid4().hex[:16]}"
        correlation_id = request.correlation_id or f"corr_{uuid.uuid4().hex[:12]}"

        notif = NotificationModel(
            id=notif_id,
            user_id=request.user_id,
            project_id=request.project_id,
            task_id=request.task_id,
            type=request.type.value,
            priority=request.priority.value,
            title=clean_title,
            body=clean_body,
            status=NotificationState.PENDING.value,
            created_at=now,
            expires_at=request.expires_at,
            source_event_id=request.source_event_id,
            correlation_id=correlation_id,
            dedupe_key=request.dedupe_key,
            metadata_json=request.metadata,
        )
        db_session.add(notif)

        # Add actions
        for act_req in request.actions:
            action = NotificationActionModel(
                id=f"act_{uuid.uuid4().hex[:16]}",
                notification_id=notif_id,
                type=act_req.type.value,
                label=TemplateRenderer.sanitize_text(act_req.label),
                target_id=act_req.target_id,
                payload_json=act_req.payload,
                status=ActionStatus.PENDING.value,
                expires_at=act_req.expires_at or request.expires_at,
                created_at=now,
            )
            db_session.add(action)

        await db_session.commit()
        await db_session.refresh(notif)

        # Deliver
        await self.delivery_coordinator.deliver(
            db_session=db_session,
            notification=notif,
            preferences=prefs,
        )

        return NotificationResponse.from_model(notif)

    async def list_notifications(
        self,
        db_session: AsyncSession,
        user_id: str,
        status_filter: str | None = None,
        type_filter: str | None = None,
        priority_filter: str | None = None,
        project_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[NotificationModel], int, int]:
        """Fetch user-scoped notification history with unread count and filters."""
        # Base query
        stmt = select(NotificationModel).where(NotificationModel.user_id == user_id)

        if status_filter:
            if status_filter.lower() == "unread":
                stmt = stmt.where(NotificationModel.status.in_([NotificationState.PENDING.value, NotificationState.DELIVERED.value]))
            else:
                stmt = stmt.where(NotificationModel.status == status_filter.upper())
        else:
            # By default exclude dismissed notifications unless requested
            stmt = stmt.where(NotificationModel.status != NotificationState.DISMISSED.value)

        if type_filter:
            stmt = stmt.where(NotificationModel.type == type_filter.upper())

        if priority_filter:
            stmt = stmt.where(NotificationModel.priority == priority_filter.upper())

        if project_id:
            stmt = stmt.where(NotificationModel.project_id == project_id)

        # Total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db_session.execute(count_stmt)).scalar() or 0

        # Unread count
        unread_stmt = select(func.count()).where(
            NotificationModel.user_id == user_id,
            NotificationModel.status.in_([NotificationState.PENDING.value, NotificationState.DELIVERED.value]),
        )
        unread_count = (await db_session.execute(unread_stmt)).scalar() or 0

        # Paginated results ordered newest first
        stmt = stmt.order_by(desc(NotificationModel.created_at)).limit(limit).offset(offset)
        res = await db_session.execute(stmt)
        items = list(res.scalars().all())

        return items, total, unread_count

    async def get_notification(
        self,
        db_session: AsyncSession,
        user_id: str,
        notification_id: str,
    ) -> NotificationModel:
        """Fetch a specific notification validating tenant ownership (Spec 36)."""
        notif = await db_session.get(NotificationModel, notification_id)
        if not notif:
            raise KeyError(f"Notification '{notification_id}' not found.")
        if notif.user_id != user_id:
            raise TenantIsolationError(f"Access denied: Notification '{notification_id}' belongs to another user.")
        return notif

    async def mark_read(
        self,
        db_session: AsyncSession,
        user_id: str,
        notification_id: str,
    ) -> NotificationModel:
        """Mark notification as READ."""
        notif = await self.get_notification(db_session, user_id, notification_id)
        now = datetime.now(UTC)
        notif.status = NotificationState.READ.value
        notif.read_at = now
        await db_session.commit()
        await db_session.refresh(notif)
        return notif

    async def dismiss(
        self,
        db_session: AsyncSession,
        user_id: str,
        notification_id: str,
    ) -> NotificationModel:
        """Dismiss notification from view."""
        notif = await self.get_notification(db_session, user_id, notification_id)
        now = datetime.now(UTC)
        notif.status = NotificationState.DISMISSED.value
        notif.dismissed_at = now
        await db_session.commit()
        await db_session.refresh(notif)
        return notif

    async def mark_all_read(
        self,
        db_session: AsyncSession,
        user_id: str,
    ) -> int:
        """Mark all unread notifications as READ for the authenticated user (Spec 78)."""
        now = datetime.now(UTC)
        stmt = (
            update(NotificationModel)
            .where(
                NotificationModel.user_id == user_id,
                NotificationModel.status.in_([NotificationState.PENDING.value, NotificationState.DELIVERED.value]),
            )
            .values(status=NotificationState.READ.value, read_at=now)
        )
        res = await db_session.execute(stmt)
        count = res.rowcount or 0
        await db_session.commit()
        return count

    async def execute_action(
        self,
        db_session: AsyncSession,
        user_id: str,
        notification_id: str,
        action_id: str,
        request: NotificationActionExecuteRequest | None = None,
    ) -> NotificationActionExecuteResponse:
        """Safely execute an interactive notification action."""
        return await NotificationActionDispatcher.execute_action(
            db_session=db_session,
            user_id=user_id,
            notification_id=notification_id,
            action_id=action_id,
            request=request,
        )


# Global singleton instance
notification_service = UnifiedNotificationService()
