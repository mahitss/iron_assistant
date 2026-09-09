"""Central approval manager handling requests, expiration, and deterministic binding."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.security.exceptions import (
    ApprovalExpiredError,
    ApprovalInvalidError,
    TenantIsolationError,
)
from app.security.models import SecurityApprovalRequest
from app.security.redaction import ArgumentSanitizer

logger = logging.getLogger("kairo.security.approvals")

DEFAULT_APPROVAL_TIMEOUT_SECONDS = 30


class ApprovalManager:
    """Manages the full lifecycle of human-in-the-loop approval requests."""

    @classmethod
    async def create_request(
        cls,
        db_session: AsyncSession,
        user_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        session_id: str | None = None,
        workflow_run_id: str | None = None,
        risk_level: str = "HIGH",
        action_description: str | None = None,
        timeout_seconds: int = DEFAULT_APPROVAL_TIMEOUT_SECONDS,
    ) -> SecurityApprovalRequest:
        """Create and persist a new pending ApprovalRequest bound to exact action fingerprint."""
        now = datetime.now(UTC)
        fingerprint = ArgumentSanitizer.compute_action_fingerprint(
            tool_name=tool_name,
            user_id=user_id,
            session_id=session_id,
            arguments=arguments,
        )
        desc_text = action_description or ArgumentSanitizer.describe_action(tool_name, arguments)
        clean_args = ArgumentSanitizer.sanitize(arguments)

        req = SecurityApprovalRequest(
            user_id=user_id,
            session_id=session_id,
            workflow_run_id=workflow_run_id,
            tool_name=tool_name,
            action_description=desc_text,
            risk_level=risk_level,
            arguments_summary=clean_args,
            action_fingerprint=fingerprint,
            status="pending",
            created_at=now,
            expires_at=now + timedelta(seconds=timeout_seconds),
        )
        db_session.add(req)
        await db_session.commit()
        await db_session.refresh(req)

        logger.info(
            "Created ApprovalRequest '%s' for tool '%s' (user=%s, risk=%s, fingerprint=%s)",
            req.id,
            tool_name,
            user_id,
            risk_level,
            fingerprint[:12],
        )
        try:
            from app.proactive.service import ProactiveService
            from app.proactive.state import SourceType

            await ProactiveService.process_event(
                db_session=db_session,
                user_id=user_id,
                source_type=SourceType.APPROVAL,
                category="approval.required",
                payload={
                    "approval_id": req.id,
                    "tool_name": tool_name,
                    "risk_level": risk_level,
                    "action_description": desc_text,
                },
                source_id=req.id,
            )
        except Exception as exc:
            logger.debug("Proactive approval notification skipped: %s", exc)

        # Emit approval.requested to Unified Event Bus
        try:
            from app.events import event_bus

            await event_bus.publish(
                event_bus.publisher.create_event(
                    event_type="approval.requested",
                    source="security_center",
                    payload={
                        "approval_id": req.id,
                        "action": desc_text,
                        "tool_name": tool_name,
                        "risk_level": risk_level,
                        "action_fingerprint": fingerprint,
                        "arguments": clean_args,
                    },
                    user_id=user_id,
                )
            )
        except Exception as eb_err:
            logger.debug("EventBus approval.requested publication skipped: %s", eb_err)

        return req

    @classmethod
    async def find_active_approval(
        cls,
        db_session: AsyncSession,
        user_id: str,
        action_fingerprint: str,
    ) -> SecurityApprovalRequest | None:
        """Find an approved, non-expired approval request matching exact fingerprint."""
        now = datetime.now(UTC)
        stmt = (
            select(SecurityApprovalRequest)
            .where(
                SecurityApprovalRequest.user_id == user_id,
                SecurityApprovalRequest.action_fingerprint == action_fingerprint,
                SecurityApprovalRequest.status == "approved",
                SecurityApprovalRequest.expires_at > now,
            )
            .order_by(desc(SecurityApprovalRequest.created_at))
        )
        res = await db_session.execute(stmt)
        return res.scalars().first()

    @classmethod
    async def list_pending_approvals(
        cls,
        db_session: AsyncSession,
        user_id: str,
    ) -> list[SecurityApprovalRequest]:
        """List active pending approval requests for user, expiring any that passed deadline."""
        now = datetime.now(UTC)
        stmt = (
            select(SecurityApprovalRequest)
            .where(
                SecurityApprovalRequest.user_id == user_id,
                SecurityApprovalRequest.status == "pending",
            )
            .order_by(desc(SecurityApprovalRequest.created_at))
        )
        res = await db_session.execute(stmt)
        requests = list(res.scalars().all())

        active_pending = []
        for req in requests:
            req_expires = (
                req.expires_at if req.expires_at.tzinfo is not None else req.expires_at.replace(tzinfo=UTC)
            )
            if req_expires <= now:
                req.status = "expired"
            else:
                active_pending.append(req)

        await db_session.commit()
        return active_pending

    @classmethod
    async def apply_decision(
        cls,
        db_session: AsyncSession,
        approval_id: str,
        user_id: str,
        decision: str,  # "approve" | "deny"
        reason: str | None = None,
    ) -> SecurityApprovalRequest:
        """Apply user decision to a pending approval request, strictly checking ownership and expiration."""
        stmt = select(SecurityApprovalRequest).where(SecurityApprovalRequest.id == approval_id)
        res = await db_session.execute(stmt)
        req = res.scalar_one_or_none()

        if not req:
            raise ApprovalInvalidError(f"Approval request '{approval_id}' not found.")

        # Enforce tenant isolation
        if req.user_id != user_id:
            raise TenantIsolationError("Unauthorized: You cannot approve or deny another user's action.")

        # Check existing status
        if req.status != "pending":
            raise ApprovalInvalidError(
                f"Approval request '{approval_id}' is already in '{req.status}' state."
            )

        now = datetime.now(UTC)
        req_expires = (
            req.expires_at if req.expires_at.tzinfo is not None else req.expires_at.replace(tzinfo=UTC)
        )
        if req_expires <= now:
            req.status = "expired"
            await db_session.commit()
            raise ApprovalExpiredError(f"Approval request '{approval_id}' has expired.")

        if decision == "approve":
            req.status = "approved"
            # Give approved request extended validity window so execution can complete
            req.expires_at = now + timedelta(seconds=60)
        elif decision == "deny":
            req.status = "denied"
        else:
            raise ApprovalInvalidError(f"Invalid approval decision: '{decision}'")

        req.decided_at = now
        req.decision_reason = reason
        await db_session.commit()
        await db_session.refresh(req)

        logger.info("ApprovalRequest '%s' marked '%s' by user '%s'.", req.id, req.status, user_id)

        # Emit approval.granted or security.blocked event
        try:
            from app.events import event_bus

            if decision == "approve":
                await event_bus.publish(
                    event_bus.publisher.create_event(
                        event_type="approval.granted",
                        source="security_center",
                        payload={
                            "approval_id": req.id,
                            "action": req.action_description,
                            "tool_name": req.tool_name,
                            "action_fingerprint": req.action_fingerprint,
                        },
                        user_id=user_id,
                    )
                )
            else:
                await event_bus.publish(
                    event_bus.publisher.create_event(
                        event_type="security.blocked",
                        source="security_center",
                        payload={
                            "approval_id": req.id,
                            "tool_name": req.tool_name,
                            "reason": reason or "Approval rejected by user",
                        },
                        user_id=user_id,
                    )
                )
        except Exception as eb_err:
            logger.debug("EventBus decision event skipped: %s", eb_err)

        return req
