"""Lineage tracking, audit trails, and immutable communication history."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
import uuid

from app.communication.schemas import MessageSchema


class ImmutableHistoryViolationError(Exception):
    """Raised when an attempt is made to mutate or silently rewrite sent communication history."""
    pass


class ProvenanceTracker:
    """Maintains an append-only audit trail for communication lifecycle events."""

    def __init__(self) -> None:
        # log_id -> audit record
        self._audit_trail: List[Dict[str, Any]] = []
        # immutable sent messages: message_id -> snapshot
        self._immutable_sent_messages: Dict[str, MessageSchema] = {}

    def record_event(
        self,
        event_type: str,
        entity_id: str,
        details: Dict[str, Any],
        user_id: str = "default_user",
    ) -> Dict[str, Any]:
        """INVARIANT 169: Audit access, draft, approval, send, failure, recipient, policy decision."""
        record = {
            "audit_id": str(uuid.uuid4()),
            "timestamp": datetime.now(UTC).isoformat(),
            "event_type": event_type,
            "entity_id": entity_id,
            "user_id": user_id,
            "details": details,
        }
        self._audit_trail.append(record)
        return record

    def commit_sent_message(self, message: MessageSchema) -> None:
        """INVARIANT 170: Immutable history — sent messages are sealed and cannot be modified."""
        if message.message_id in self._immutable_sent_messages:
            raise ImmutableHistoryViolationError(
                f"Message '{message.message_id}' is already committed to immutable history and cannot be rewritten."
            )
        self._immutable_sent_messages[message.message_id] = message.model_copy(deep=True)
        self.record_event(
            event_type="MESSAGE_COMMITTED",
            entity_id=message.message_id,
            details={"channel": message.channel.value, "sender": message.sender},
            user_id=message.user_id,
        )

    def verify_message_integrity(self, message_id: str, current_content: str) -> bool:
        committed = self._immutable_sent_messages.get(message_id)
        if not committed:
            return True
        if committed.content_reference != current_content:
            raise ImmutableHistoryViolationError(
                f"Integrity check failed: Message '{message_id}' content was modified after send."
            )
        return True

    def get_audit_trail(
        self,
        entity_id: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        results = self._audit_trail
        if entity_id:
            results = [r for r in results if r["entity_id"] == entity_id]
        if event_type:
            results = [r for r in results if r["event_type"] == event_type]
        return results
