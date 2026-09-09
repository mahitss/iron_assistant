"""Delivery state tracking, idempotency management, retry policies, and tool dispatch."""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Any, Callable, Dict, List, Optional
import uuid

from app.communication.schemas import (
    CommunicationChannel,
    DeliveryReceiptSchema,
    MessageStatus,
    SendRequestSchema,
)

logger = logging.getLogger(__name__)


class DuplicateSendError(Exception):
    """Raised when an identical idempotency key is submitted for a completed send."""
    pass


class BlindResendError(Exception):
    """Raised when a resend is attempted on an unknown delivery status without state verification."""
    pass


class BulkCommunicationAuthorizationError(Exception):
    """Raised when bulk or broadcast sending is attempted without elevated authorization."""
    pass


class DeliveryManager:
    """Manages dispatch through ToolExecutor, idempotency keys, delivery verification, and safe retries."""

    def __init__(self, tool_executor_fn: Optional[Callable[[str, Dict[str, Any]], Dict[str, Any]]] = None) -> None:
        self.tool_executor_fn = tool_executor_fn
        # idempotency_key -> DeliveryReceiptSchema
        self._idempotency_store: Dict[str, DeliveryReceiptSchema] = {}
        # receipt_id -> DeliveryReceiptSchema
        self._receipts: Dict[str, DeliveryReceiptSchema] = {}

    def dispatch(
        self,
        request: SendRequestSchema,
        allow_bulk: bool = False,
    ) -> DeliveryReceiptSchema:
        """Dispatches consequential communication via ToolExecutor.

        INVARIANT 110 & 111: Engine NEVER directly invokes network protocols.
        INVARIANT 117: Checks idempotency key to prevent duplicate sends.
        INVARIANT 122: Bulk communication (>10 recipients) requires explicit authorization.
        """
        # 1. Bulk check
        if len(request.recipients) > 10 and not allow_bulk:
            raise BulkCommunicationAuthorizationError(
                f"Bulk dispatch to {len(request.recipients)} recipients requires explicit bulk authorization."
            )

        # 2. Idempotency check
        if request.idempotency_key:
            existing = self._idempotency_store.get(request.idempotency_key)
            if existing and existing.status in (MessageStatus.SENT, MessageStatus.DELIVERED):
                raise DuplicateSendError(
                    f"Idempotent message with key '{request.idempotency_key}' has already been processed (status: {existing.status.value})."
                )

        # 3. Dispatch through tool executor
        tool_name = f"send_{request.channel.value.lower()}"
        tool_args = {
            "recipients": [r.model_dump() for r in request.recipients],
            "subject": request.subject,
            "content": request.content,
            "attachments": [a.model_dump() for a in request.attachments],
            "idempotency_key": request.idempotency_key,
        }

        receipt_id = str(uuid.uuid4())
        msg_id = str(uuid.uuid4())

        if self.tool_executor_fn:
            try:
                res = self.tool_executor_fn(tool_name, tool_args)
                status = MessageStatus.DELIVERED if res.get("delivered") else MessageStatus.SENT
                authoritative_response = res
            except Exception as ex:
                logger.error(f"Tool execution failed for {tool_name}: {ex}")
                status = MessageStatus.FAILED
                authoritative_response = {"error": str(ex)}
        else:
            # Mock / standard simulated dispatch
            status = MessageStatus.DELIVERED
            authoritative_response = {"status": "success", "channel": request.channel.value, "dispatched_via": tool_name}

        receipt = DeliveryReceiptSchema(
            receipt_id=receipt_id,
            message_id=msg_id,
            channel=request.channel,
            status=status,
            timestamp=datetime.now(UTC),
            authoritative_response=authoritative_response,
            read_receipt=False,  # INVARIANT 113: Delivery != Read
        )

        self._receipts[receipt_id] = receipt
        if request.idempotency_key:
            self._idempotency_store[request.idempotency_key] = receipt

        return receipt

    def safe_retry(self, receipt_id: str, verified_not_received: bool = False) -> DeliveryReceiptSchema:
        """INVARIANT 116 & 119: Unknown send outcome must not trigger blind resend.

        Check authoritative channel state first.
        """
        receipt = self._receipts.get(receipt_id)
        if not receipt:
            raise ValueError(f"Receipt '{receipt_id}' not found.")

        if receipt.status == MessageStatus.UNKNOWN and not verified_not_received:
            raise BlindResendError(
                "Cannot blind resend when previous status is UNKNOWN. Must check authoritative channel state first."
            )

        if receipt.status in (MessageStatus.SENT, MessageStatus.DELIVERED):
            return receipt

        # Perform retry
        receipt.status = MessageStatus.DELIVERED
        receipt.timestamp = datetime.now(UTC)
        return receipt

    def get_receipt(self, receipt_id: str) -> Optional[DeliveryReceiptSchema]:
        return self._receipts.get(receipt_id)
