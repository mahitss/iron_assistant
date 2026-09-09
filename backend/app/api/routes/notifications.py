"""REST API endpoints for user notification center (Re-exported from unified notifications layer)."""

from app.notifications.router import (
    get_current_user_id,
    router,
)
from app.notifications.schemas import (
    NotificationActionExecuteRequest,
    NotificationActionExecuteResponse,
    NotificationListResponse,
    NotificationPreferencesRequest,
    NotificationPreferencesResponse,
    NotificationResponse,
)

__all__ = [
    "router",
    "get_current_user_id",
    "NotificationListResponse",
    "NotificationResponse",
    "NotificationPreferencesRequest",
    "NotificationPreferencesResponse",
    "NotificationActionExecuteRequest",
    "NotificationActionExecuteResponse",
]
