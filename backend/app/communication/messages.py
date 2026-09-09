"""Message normalization, parsing, and data representation across communication channels."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
import uuid

from app.communication.schemas import (
    AttachmentSchema,
    CommunicationChannel,
    MessageDirection,
    MessageSchema,
    MessageStatus,
    PrivacyScope,
    RecipientSchema,
    RecipientType,
)


class MessageNormalizer:
    """Normalizes unstructured raw communication events from email, chat, SMS, voice, meetings, etc."""

    @staticmethod
    def normalize_email(
        raw_email: Dict[str, Any],
        user_id: str = "default_user",
        project_id: Optional[str] = None,
    ) -> MessageSchema:
        """Normalizes an email payload."""
        message_id = raw_email.get("message_id") or str(uuid.uuid4())
        sender = raw_email.get("from") or raw_email.get("sender") or "unknown@domain.com"
        subject = raw_email.get("subject", "")
        body = raw_email.get("body") or raw_email.get("content") or ""
        timestamp = raw_email.get("timestamp") or datetime.now(UTC)

        recipients: List[RecipientSchema] = []
        for to_addr in raw_email.get("to", []):
            if isinstance(to_addr, str):
                recipients.append(RecipientSchema(identity=to_addr, address=to_addr, recipient_type=RecipientType.TO))
            elif isinstance(to_addr, dict):
                recipients.append(RecipientSchema(**to_addr))

        for cc_addr in raw_email.get("cc", []):
            if isinstance(cc_addr, str):
                recipients.append(RecipientSchema(identity=cc_addr, address=cc_addr, recipient_type=RecipientType.CC))
            elif isinstance(cc_addr, dict):
                recipients.append(RecipientSchema(**cc_addr))

        for bcc_addr in raw_email.get("bcc", []):
            if isinstance(bcc_addr, str):
                recipients.append(RecipientSchema(identity=bcc_addr, address=bcc_addr, recipient_type=RecipientType.BCC))
            elif isinstance(bcc_addr, dict):
                recipients.append(RecipientSchema(**bcc_addr))

        attachments: List[AttachmentSchema] = []
        for att in raw_email.get("attachments", []):
            if isinstance(att, dict):
                attachments.append(AttachmentSchema(**att))

        direction = MessageDirection(raw_email.get("direction", MessageDirection.INBOUND))
        status = MessageStatus(raw_email.get("status", MessageStatus.DELIVERED))

        # INVARIANT: Draft != Sent
        if direction == MessageDirection.DRAFT and status == MessageStatus.SENT:
            raise ValueError("Draft message cannot be marked as SENT.")

        privacy_scope = PrivacyScope.PRIVATE
        if any(r.is_external for r in recipients):
            privacy_scope = PrivacyScope.EXTERNAL
        elif len(recipients) > 2:
            privacy_scope = PrivacyScope.GROUP

        return MessageSchema(
            message_id=message_id,
            channel=CommunicationChannel.EMAIL,
            sender=sender,
            recipients=recipients,
            timestamp=timestamp,
            thread_id=raw_email.get("thread_id"),
            subject=subject,
            content_reference=body,
            attachments=attachments,
            direction=direction,
            status=status,
            provenance={"source": "email_ingestion", "headers": raw_email.get("headers", {})},
            privacy_scope=privacy_scope,
            user_id=user_id,
            project_id=project_id,
        )

    @staticmethod
    def normalize_chat(
        raw_chat: Dict[str, Any],
        user_id: str = "default_user",
        project_id: Optional[str] = None,
    ) -> MessageSchema:
        """Normalizes a chat / Slack / Teams message."""
        message_id = raw_chat.get("message_id") or str(uuid.uuid4())
        sender = raw_chat.get("user") or raw_chat.get("sender") or "unknown_user"
        content = raw_chat.get("text") or raw_chat.get("content") or ""
        timestamp = raw_chat.get("timestamp") or datetime.now(UTC)
        channel_name = raw_chat.get("channel_name", "")
        is_public = raw_chat.get("is_public", False)

        recipients: List[RecipientSchema] = []
        for r in raw_chat.get("recipients", []):
            if isinstance(r, str):
                recipients.append(RecipientSchema(identity=r, address=r, recipient_type=RecipientType.TO))
            elif isinstance(r, dict):
                recipients.append(RecipientSchema(**r))

        privacy_scope = PrivacyScope.PUBLIC if is_public else (PrivacyScope.GROUP if len(recipients) > 1 else PrivacyScope.PRIVATE)

        return MessageSchema(
            message_id=message_id,
            channel=CommunicationChannel.CHAT,
            sender=sender,
            recipients=recipients,
            timestamp=timestamp,
            thread_id=raw_chat.get("thread_id") or raw_chat.get("thread_ts"),
            subject=f"Chat in {channel_name}" if channel_name else None,
            content_reference=content,
            attachments=[AttachmentSchema(**a) if isinstance(a, dict) else a for a in raw_chat.get("attachments", [])],
            direction=MessageDirection(raw_chat.get("direction", MessageDirection.INBOUND)),
            status=MessageStatus(raw_chat.get("status", MessageStatus.DELIVERED)),
            provenance={"source": "chat_ingestion", "channel_name": channel_name},
            privacy_scope=privacy_scope,
            user_id=user_id,
            project_id=project_id,
        )

    @staticmethod
    def normalize_generic(
        channel: CommunicationChannel,
        sender: str,
        content: str,
        recipients: Optional[List[RecipientSchema]] = None,
        subject: Optional[str] = None,
        thread_id: Optional[str] = None,
        direction: MessageDirection = MessageDirection.INBOUND,
        status: MessageStatus = MessageStatus.DELIVERED,
        user_id: str = "default_user",
        project_id: Optional[str] = None,
        attachments: Optional[List[AttachmentSchema]] = None,
    ) -> MessageSchema:
        """Generic normalizer for meeting transcripts, SMS, voice, and comments."""
        if direction == MessageDirection.DRAFT and status == MessageStatus.SENT:
            raise ValueError("Draft message cannot be marked as SENT.")

        recs = recipients or []
        privacy = PrivacyScope.PRIVATE
        if any(r.is_external for r in recs):
            privacy = PrivacyScope.EXTERNAL
        elif len(recs) > 2:
            privacy = PrivacyScope.GROUP

        return MessageSchema(
            channel=channel,
            sender=sender,
            recipients=recs,
            subject=subject,
            content_reference=content,
            thread_id=thread_id,
            direction=direction,
            status=status,
            attachments=attachments or [],
            privacy_scope=privacy,
            user_id=user_id,
            project_id=project_id,
            provenance={"source": f"{channel.value.lower()}_normalizer"},
        )
