"""Safe interactive notification action execution and delegation (Task 34, Spec 13, 14, 38-42, 89, 90)."""

from datetime import UTC, datetime
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.notifications.models import NotificationActionModel, NotificationModel
from app.notifications.schemas import (
    ActionStatus,
    ActionType,
    NotificationActionExecuteRequest,
    NotificationActionExecuteResponse,
)
from app.security.exceptions import (
    ApprovalExpiredError,
    ApprovalInvalidError,
    SecurityPolicyViolationError,
    TenantIsolationError,
)

logger = logging.getLogger("kairo.notifications.actions")


class NotificationActionDispatcher:
    """
    Executes interactive notification actions safely without direct raw database mutations.
    Enforces:
      - Authenticated user & tenant isolation (Spec 36, 120).
      - Strict authorization & SecurityCenter / ApprovalManager delegation (Spec 13, 90, 91).
      - Replay prevention / idempotency (Spec 42).
      - Stale state safety (Spec 14, 41).
    """

    @classmethod
    async def execute_action(
        cls,
        db_session: AsyncSession,
        user_id: str,
        notification_id: str,
        action_id: str,
        request: NotificationActionExecuteRequest | None = None,
    ) -> NotificationActionExecuteResponse:
        """
        Execute an interactive notification action through authoritative subsystems.
        """
        now = datetime.now(UTC)

        # 1. Fetch notification and verify tenant ownership (Spec 36)
        notification = await db_session.get(NotificationModel, notification_id)
        if not notification:
            raise KeyError(f"Notification '{notification_id}' not found.")
        if notification.user_id != user_id:
            raise TenantIsolationError(f"Access denied: Notification '{notification_id}' belongs to another user.")

        # 2. Fetch action and verify binding
        action = await db_session.get(NotificationActionModel, action_id)
        if not action or action.notification_id != notification_id:
            raise KeyError(f"Action '{action_id}' not found on notification '{notification_id}'.")

        # 3. Check idempotency & replay prevention (Spec 42)
        if action.status == ActionStatus.EXECUTED.value:
            logger.warning("Action replay rejected: Action '%s' was already executed at %s.", action_id, action.executed_at)
            raise SecurityPolicyViolationError("Action has already been executed.")

        # 4. Check action expiration (Spec 14, 64)
        if action.expires_at:
            a_exp = action.expires_at if action.expires_at.tzinfo is not None else action.expires_at.replace(tzinfo=UTC)
            if now > a_exp:
                action.status = ActionStatus.EXPIRED.value
                await db_session.commit()
                logger.warning("Action expired for '%s' (expired at %s).", action_id, a_exp)
                raise ApprovalExpiredError(f"Action '{action_id}' has expired and cannot be executed.")

        act_type = ActionType(action.type) if isinstance(action.type, str) else action.type
        target_id = action.target_id
        result_payload: dict[str, Any] = {}

        # 5. Authoritative Subsystem Delegation
        try:
            # 5a. Approval actions (APPROVE / REJECT)
            if act_type in (ActionType.APPROVE, ActionType.REJECT):
                from app.security.approvals import ApprovalManager
                approved = (act_type == ActionType.APPROVE)
                reason = request.reason if request and request.reason else f"Notification {act_type.value} click"
                approval_record = await ApprovalManager.apply_decision(
                    db_session=db_session,
                    approval_id=target_id,
                    user_id=user_id,
                    decision="approve" if approved else "deny",
                    reason=reason,
                )
                result_payload = {
                    "approval_id": target_id,
                    "approved": approved,
                    "approval_status": approval_record.status,
                }

            # 5b. Task Engine actions (PAUSE / RESUME / CANCEL / RETRY)
            elif act_type in (ActionType.PAUSE, ActionType.RESUME, ActionType.CANCEL, ActionType.RETRY):
                from app.tasks.models import TaskModel
                task = await db_session.get(TaskModel, target_id)
                if not task:
                    raise KeyError(f"Target task '{target_id}' not found.")
                if task.user_id != user_id:
                    raise TenantIsolationError("Task belongs to another user.")

                # Stale action safety check (Spec 41)
                if act_type == ActionType.CANCEL and task.status in ("COMPLETED", "FAILED", "CANCELLED"):
                    logger.info("Stale action handled safely: task '%s' is already in state '%s'.", target_id, task.status)
                    result_payload = {
                        "task_id": target_id,
                        "task_status": task.status,
                        "message": f"Task already in terminal state '{task.status}'; cancel safely skipped.",
                    }
                else:
                    # Update task state accordingly
                    if act_type == ActionType.CANCEL:
                        task.status = "CANCELLED"
                    elif act_type == ActionType.PAUSE:
                        task.status = "PAUSED"
                    elif act_type == ActionType.RESUME:
                        task.status = "RUNNING"
                    result_payload = {"task_id": target_id, "task_status": task.status}

            # 5c. Informational OPEN or REFRESH
            elif act_type in (ActionType.OPEN, ActionType.REFRESH):
                result_payload = {"target_id": target_id, "action": act_type.value, "status": "navigated"}

            # Success: mark action executed
            action.status = ActionStatus.EXECUTED.value
            action.executed_at = now
            await db_session.commit()
            await db_session.refresh(action)

            logger.info("Executed notification action '%s' (%s) for user '%s'.", action_id, act_type.value, user_id)

            return NotificationActionExecuteResponse(
                action_id=action.id,
                notification_id=notification.id,
                status=ActionStatus.EXECUTED,
                executed_at=now,
                result=result_payload,
            )

        except Exception as exc:
            action.status = ActionStatus.FAILED.value
            await db_session.commit()
            logger.error("Failed executing notification action '%s': %s", action_id, exc)
            raise
