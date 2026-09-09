"""Cross-interface context handoff manager with replay protection and bounded context (Spec 28-32, 85, 97, 98)."""

from datetime import UTC, datetime, timedelta
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.identity.models import HandoffContextModel, IdentitySessionModel
from app.identity.policies import IdentityPolicyEnforcer
from app.identity.schemas import (
    HandoffCompleteRequest,
    HandoffContextPacket,
    HandoffCreateRequest,
    HandoffResponse,
    IdentityErrorCode,
    SessionStatus,
)
from app.identity.tokens import generate_handoff_token, hash_token, verify_token
from app.security.exceptions import SecurityPolicyViolationError, TenantIsolationError

logger = logging.getLogger("kairo.identity.handoff")


class HandoffManager:
    """Coordinates secure, single-use, bounded context handoff between authorized interfaces."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.settings = get_settings()
        self.handoff_ttl = getattr(self.settings, "KAIRO_IDENTITY_HANDOFF_TTL_SECONDS", 300)

    async def create_handoff(self, user_id: str, request: HandoffCreateRequest) -> HandoffResponse:
        """Create a short-lived single-use handoff ticket with bounded context (Spec 28, 30, 97)."""
        # 1. Require explicit user consent (Spec 30)
        if not request.explicit_consent:
            raise SecurityPolicyViolationError("Cross-interface handoff requires explicit user consent.")

        # 2. Validate source session
        source_sess = await self.db.get(IdentitySessionModel, request.source_session_id)
        if not source_sess:
            raise KeyError(f"Source session '{request.source_session_id}' not found.")

        if source_sess.user_id != user_id:
            raise TenantIsolationError("Source session belongs to another user.")

        IdentityPolicyEnforcer.enforce_session_active(source_sess)

        # 3. Assemble bounded context (never copy entire database or entire memory, Spec 97)
        bounded_context: dict[str, Any] = {
            "source_client_type": source_sess.client_type,
            "source_device_id": source_sess.device_id,
            "conversation_id": request.conversation_id,
            "task_id": request.task_id,
            "project_id": request.project_id,
            "transferred_at": datetime.now(UTC).isoformat(),
        }

        # If task_id provided, verify task exists and belongs to user (Spec 98)
        if request.task_id:
            try:
                from app.tasks.models import TaskModel
                task = await self.db.get(TaskModel, request.task_id)
                if task:
                    if task.user_id != user_id:
                        raise TenantIsolationError(f"Task '{request.task_id}' belongs to another user.")
                    bounded_context["task_objective"] = task.objective[:200]
                    bounded_context["task_status"] = task.status
            except ImportError:
                pass

        # 4. Generate single-use cryptographic token and hash
        raw_token = generate_handoff_token()
        token_hash = hash_token(raw_token)
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=self.handoff_ttl)

        handoff_record = HandoffContextModel(
            user_id=user_id,
            source_session_id=request.source_session_id,
            target_device_id=request.target_device_id,
            conversation_id=request.conversation_id,
            task_id=request.task_id,
            project_id=request.project_id,
            relevant_context=bounded_context,
            token_hash=token_hash,
            consumed_at=None,
            expires_at=expires_at,
            created_at=now,
        )
        self.db.add(handoff_record)
        await self.db.commit()
        await self.db.refresh(handoff_record)

        logger.info(
            "Created context handoff '%s' for user '%s' (expires: %s)",
            handoff_record.id,
            user_id,
            expires_at,
        )

        # Emit handoff.created event
        try:
            from app.events import event_bus
            await event_bus.publish(
                event_bus.publisher.create_event(
                    event_type="handoff.created",
                    source="identity",
                    payload={
                        "handoff_id": handoff_record.id,
                        "source_session_id": handoff_record.source_session_id,
                        "target_device_id": handoff_record.target_device_id,
                        "task_id": handoff_record.task_id,
                    },
                    user_id=user_id,
                )
            )
        except Exception:
            pass

        return HandoffResponse(
            handoff_id=handoff_record.id,
            handoff_token=raw_token,
            expires_at=expires_at,
            target_device_id=request.target_device_id,
        )

    async def complete_handoff(
        self, user_id: str, handoff_id: str, request: HandoffCompleteRequest
    ) -> HandoffContextPacket:
        """Complete handoff by consuming single-use token with replay and cross-user defenses (Spec 31, 32, 85)."""
        record = await self.db.get(HandoffContextModel, handoff_id)
        if not record:
            raise KeyError(f"Handoff '{handoff_id}' not found.")

        # Defense 1: Cross-user handoff attempt rejected (Spec 85, 147)
        if record.user_id != user_id:
            logger.critical("Cross-user handoff attack detected: user '%s' attempted to claim handoff '%s' of user '%s'.", user_id, handoff_id, record.user_id)
            raise TenantIsolationError("Access denied: Handoff context belongs to another user.")

        # Defense 2: Replay attack prevention: consumed token cannot be reused (Spec 85, 150)
        if record.consumed_at is not None:
            logger.warning("Handoff replay attack blocked: handoff '%s' was already consumed at %s.", handoff_id, record.consumed_at)
            raise SecurityPolicyViolationError(IdentityErrorCode.HANDOFF_INVALID.value)

        # Defense 3: Expiration check (Spec 31, 85)
        now = datetime.now(UTC)
        h_exp = record.expires_at if record.expires_at.tzinfo is not None else record.expires_at.replace(tzinfo=UTC)
        if now > h_exp:
            logger.warning("Handoff expired for '%s' (expired at %s).", handoff_id, record.expires_at)
            raise SecurityPolicyViolationError(IdentityErrorCode.HANDOFF_EXPIRED.value)

        # Defense 4: Timing-safe token verification (Spec 32)
        if not verify_token(request.handoff_token, record.token_hash):
            logger.warning("Invalid handoff token provided for handoff '%s'.", handoff_id)
            raise SecurityPolicyViolationError(IdentityErrorCode.HANDOFF_INVALID.value)

        # Defense 5: Validate target session
        target_sess = await self.db.get(IdentitySessionModel, request.target_session_id)
        if not target_sess:
            raise KeyError(f"Target session '{request.target_session_id}' not found.")
        if target_sess.user_id != user_id:
            raise TenantIsolationError("Target session belongs to another user.")
        IdentityPolicyEnforcer.enforce_session_active(target_sess)

        # Immediately consume the ticket (Single-use enforcement)
        record.consumed_at = now
        record.target_session_id = request.target_session_id
        await self.db.commit()
        await self.db.refresh(record)

        logger.info("Context handoff '%s' completed successfully into session '%s'.", handoff_id, request.target_session_id)

        # Emit handoff.completed event
        try:
            from app.events import event_bus
            await event_bus.publish(
                event_bus.publisher.create_event(
                    event_type="handoff.completed",
                    source="identity",
                    payload={
                        "handoff_id": record.id,
                        "source_session_id": record.source_session_id,
                        "target_session_id": record.target_session_id,
                        "task_id": record.task_id,
                    },
                    user_id=user_id,
                )
            )
        except Exception:
            pass

        return HandoffContextPacket(
            handoff_id=record.id,
            user_id=record.user_id,
            source_session_id=record.source_session_id,
            target_session_id=record.target_session_id,
            conversation_id=record.conversation_id,
            task_id=record.task_id,
            project_id=record.project_id,
            relevant_context=record.relevant_context or {},
        )
