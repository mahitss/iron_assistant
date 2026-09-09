"""Kairo Unified Notification, Communication, Delivery, Priority, and Alerting Layer (Task 34)."""

from app.notifications.models import (
    NotificationActionModel,
    NotificationDeliveryModel,
    NotificationModel,
    NotificationPreferenceModel,
)
from app.notifications.policy import DeliveryDecision, NotificationPolicy
from app.notifications.priority import PriorityResolver
from app.notifications.router import router as notifications_router
from app.notifications.schemas import (
    ActionStatus,
    ActionType,
    ChannelType,
    DeliveryStatus,
    NotificationActionExecuteRequest,
    NotificationActionExecuteResponse,
    NotificationCreateRequest,
    NotificationListResponse,
    NotificationPreferencesRequest,
    NotificationPreferencesResponse,
    NotificationPriority,
    NotificationResponse,
    NotificationState,
    NotificationType,
)
from app.notifications.service import UnifiedNotificationService, notification_service

__all__ = [
    "NotificationModel",
    "NotificationActionModel",
    "NotificationDeliveryModel",
    "NotificationPreferenceModel",
    "NotificationType",
    "NotificationPriority",
    "NotificationState",
    "ChannelType",
    "ActionType",
    "ActionStatus",
    "DeliveryStatus",
    "NotificationResponse",
    "NotificationListResponse",
    "NotificationCreateRequest",
    "NotificationActionExecuteRequest",
    "NotificationActionExecuteResponse",
    "NotificationPreferencesRequest",
    "NotificationPreferencesResponse",
    "DeliveryDecision",
    "NotificationPolicy",
    "PriorityResolver",
    "UnifiedNotificationService",
    "notification_service",
    "notifications_router",
]
