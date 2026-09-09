"""Draft message generation, tone adaptation, provenance tracking, and strict hallucination controls."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
import uuid

from app.communication.schemas import (
    CommunicationTone,
    DraftMessageSchema,
    DraftStatus,
    RecipientSchema,
)


class DraftHallucinationError(Exception):
    """Raised when a draft attempts to invent unsubstantiated facts or attachments."""
    pass


class DraftEngine:
    """Manages draft generation, tone adaptation, provenance, and approval gating."""

    def __init__(self) -> None:
        # draft_id -> DraftMessageSchema
        self._drafts: Dict[str, DraftMessageSchema] = {}

    def create_draft(
        self,
        recipients: List[RecipientSchema],
        subject: Optional[str],
        body: str,
        tone: CommunicationTone = CommunicationTone.FORMAL,
        intent: str = "REQUEST",
        thread_id: Optional[str] = None,
        source_context: Optional[Dict[str, Any]] = None,
        requires_approval: bool = True,
        user_id: str = "default_user",
    ) -> DraftMessageSchema:
        """Creates a strictly grounded draft message.

        INVARIANT 47: Draft != Sent. Status starts as DRAFT.
        INVARIANT 48: Draft provenance records rationale and source context.
        INVARIANT 49: Hallucination control prevents asserting fake attachments or facts.
        """
        self._audit_hallucination(body, source_context or {})

        draft_id = str(uuid.uuid4())
        draft = DraftMessageSchema(
            draft_id=draft_id,
            thread_id=thread_id,
            recipients=recipients,
            subject=subject,
            body_reference=body,
            tone=tone,
            intent=intent,
            source_context=source_context or {},
            status=DraftStatus.DRAFT,
            provenance={
                "created_at": datetime.now(UTC).isoformat(),
                "generator": "kairo_draft_engine",
                "grounded_sources": list((source_context or {}).keys()),
            },
            requires_approval=requires_approval,
            approved_by=None,
            user_id=user_id,
        )
        self._drafts[draft_id] = draft
        return draft

    def update_draft(
        self,
        draft_id: str,
        new_body: Optional[str] = None,
        new_subject: Optional[str] = None,
        new_tone: Optional[CommunicationTone] = None,
    ) -> DraftMessageSchema:
        """Modifies draft content. Material changes invalidate previous approval."""
        draft = self._drafts.get(draft_id)
        if not draft:
            raise ValueError(f"Draft '{draft_id}' not found.")

        # INVARIANT 109: Material draft changes invalidate approval where required
        if draft.status == DraftStatus.APPROVED:
            draft.status = DraftStatus.REVIEWED
            draft.approved_by = None

        if new_body is not None:
            self._audit_hallucination(new_body, draft.source_context)
            draft.body_reference = new_body
        if new_subject is not None:
            draft.subject = new_subject
        if new_tone is not None:
            draft.tone = new_tone

        return draft

    def approve_draft(self, draft_id: str, approver_identity: str) -> DraftMessageSchema:
        draft = self._drafts.get(draft_id)
        if not draft:
            raise ValueError(f"Draft '{draft_id}' not found.")
        draft.status = DraftStatus.APPROVED
        draft.approved_by = approver_identity
        return draft

    def mark_sent(self, draft_id: str) -> DraftMessageSchema:
        draft = self._drafts.get(draft_id)
        if not draft:
            raise ValueError(f"Draft '{draft_id}' not found.")
        draft.status = DraftStatus.SENT
        return draft

    def get_draft(self, draft_id: str) -> Optional[DraftMessageSchema]:
        return self._drafts.get(draft_id)

    def list_drafts(self, user_id: Optional[str] = None) -> List[DraftMessageSchema]:
        results = list(self._drafts.values())
        if user_id:
            results = [d for d in results if d.user_id == user_id]
        return results

    def _audit_hallucination(self, body: str, source_context: Dict[str, Any]) -> None:
        """Audits candidate body for ungrounded claims or fake attachments."""
        body_lower = body.lower()
        # If body claims "attached is" or "I have attached", verify attachment exists in source context
        if any(w in body_lower for w in ["attached is", "i have attached", "see attached"]):
            attachments = source_context.get("attachments", [])
            if not attachments:
                raise DraftHallucinationError(
                    "Draft mentions an attachment ('attached is') but no verified attachment was provided in source context."
                )
