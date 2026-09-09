"""Inter-agent messaging protocol, types, authorization, and deduplication (Task 44)."""

from __future__ import annotations

import enum
import hashlib
import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger("kairo.agents.messages")


def utc_now() -> datetime:
    return datetime.now(UTC)


class MessageType(str, enum.Enum):
    """Authoritative inter-agent message types (Spec 31)."""

    TASK = "TASK"
    RESULT = "RESULT"
    QUESTION = "QUESTION"
    EVIDENCE = "EVIDENCE"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"
    REQUEST = "REQUEST"
    REVIEW = "REVIEW"
    DISAGREEMENT = "DISAGREEMENT"
    HANDOFF = "HANDOFF"
    CANCEL = "CANCEL"
    HEARTBEAT = "HEARTBEAT"


class DuplicateMessageError(Exception):
    """Raised when an identical message is received in duplicate."""


class MessageAuthorizationError(Exception):
    """Raised when an agent attempts to message outside its authorized collaboration scope."""


class AgentMessage(BaseModel):
    """Scoped, typed inter-agent message payload (Spec 30, 33)."""

    model_config = ConfigDict(extra="ignore")

    message_id: str = Field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:10]}")
    collaboration_id: str = "default_collab"
    sender_id: str = ""
    recipient_id: str = ""
    message_type: MessageType = MessageType.TASK
    payload: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)
    contract_id: str | None = None
    priority: int = 0
    sequence_num: int = 0
    created_at: datetime = Field(default_factory=utc_now)

    def __init__(self, **data: Any):
        if "sender" in data and not data.get("sender_id"):
            data["sender_id"] = data["sender"]
        if "recipient" in data and not data.get("recipient_id"):
            data["recipient_id"] = data["recipient"]
        if "type" in data and not data.get("message_type"):
            data["message_type"] = data["type"]
        if "priority" in data:
            p = data["priority"]
            if isinstance(p, str):
                priority_map = {"LOW": 0, "NORMAL": 1, "HIGH": 5, "URGENT": 10}
                data["priority"] = priority_map.get(p.upper(), 1)
        super().__init__(**data)

    @property
    def sender(self) -> str:
        return self.sender_id

    @property
    def recipient(self) -> str:
        return self.recipient_id

    @property
    def type(self) -> MessageType:
        return self.message_type

    @property
    def timestamp(self) -> datetime:
        return self.created_at

    @property
    def deduplication_hash(self) -> str:
        """Compute message content hash for safe idempotency checking (Spec 34)."""
        raw = f"{self.sender_id}:{self.recipient_id}:{self.message_type.value}:{self.contract_id}:{json.dumps(self.payload, sort_keys=True)}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "collaboration_id": self.collaboration_id,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "message_type": self.message_type.value,
            "payload": self.payload,
            "evidence_refs": self.evidence_refs,
            "contract_id": self.contract_id,
            "priority": self.priority,
            "sequence_num": self.sequence_num,
            "created_at": self.created_at.isoformat(),
        }


class MessageBus:
    """Delivers messages within authorized collaboration sessions with deduplication (Spec 32-36)."""

    def __init__(self) -> None:
        # recipient_id -> list of messages
        self._mailbox: dict[str, list[AgentMessage]] = {}
        # deduplication_hash -> message_id
        self._seen_hashes: dict[str, str] = {}
        self._authorized_contracts: dict[str, list[str]] = {}
        self._sequence_counter: int = 0

    def register_authorized_contract(self, contract_id: str, agent_ids: list[str]) -> None:
        self._authorized_contracts[contract_id] = list(agent_ids)

    def send(self, message: AgentMessage) -> bool:
        """Send message with hash-based deduplication and priority queueing."""
        h = message.deduplication_hash
        if h in self._seen_hashes:
            logger.info("Deduplicated duplicate message %s from %s", message.message_id, message.sender_id)
            return False

        self._seen_hashes[h] = message.message_id
        self._sequence_counter += 1
        message.sequence_num = self._sequence_counter

        queue = self._mailbox.setdefault(message.recipient_id, [])
        queue.append(message)
        # Sort queue by priority descending, then sequence ascending
        queue.sort(key=lambda m: (-m.priority, m.sequence_num))
        return True

    def send_authenticated(self, message: AgentMessage) -> bool:
        """Send message validating that sender is authorized under contract."""
        if message.contract_id and message.contract_id in self._authorized_contracts:
            authorized = self._authorized_contracts[message.contract_id]
            if message.sender_id not in authorized:
                raise MessageAuthorizationError(
                    f"Agent '{message.sender_id}' is not authorized to message under contract '{message.contract_id}'"
                )
        return self.send(message)

    def post_message(
        self,
        message: AgentMessage,
        allowed_participants: set[str] | None = None,
    ) -> tuple[bool, str]:
        """Legacy helper for backward compatibility."""
        if allowed_participants:
            if message.sender_id not in allowed_participants:
                return False, f"Sender '{message.sender_id}' not authorized."
        delivered = self.send(message)
        if not delivered:
            return True, "Duplicate message ignored safely."
        return True, "Message delivered"

    def get_messages(
        self,
        recipient_id: str,
        collaboration_id: Optional[str] = None,
        since_sequence: int = 0,
    ) -> list[AgentMessage]:
        """Retrieve ordered messages for a participant."""
        messages = self._mailbox.get(recipient_id, [])
        filtered = [
            m for m in messages
            if m.sequence_num > since_sequence
            and (collaboration_id is None or m.collaboration_id == collaboration_id)
        ]
        return filtered
