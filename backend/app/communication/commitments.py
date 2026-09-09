"""Commitment extraction, ownership tracking, and anti-fabrication guards."""

from __future__ import annotations

from datetime import UTC, datetime
import re
from typing import Any, Dict, List, Optional
import uuid

from app.communication.schemas import (
    CommitmentSchema,
    CommitmentStatus,
    MessageSchema,
)


class CommitmentFabricationError(Exception):
    """Raised when an attempt is made to create or impute a fabricated commitment."""
    pass


class CommitmentTracker:
    """Extracts, tracks, and audits commitments made by the user or external participants."""

    def __init__(self) -> None:
        # commitment_id -> CommitmentSchema
        self._commitments: Dict[str, CommitmentSchema] = {}

    def extract_commitments_from_message(
        self,
        message: MessageSchema,
        current_user_identity: str = "user@kairo.internal",
    ) -> List[CommitmentSchema]:
        """Extracts strictly grounded commitments from message text.

        INVARIANT 27: Never fabricate a commitment for the user!
        Only extract statements with explicit promises ("I will", "We commit to", "Assigned to X").
        """
        text = message.content_reference
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        commitments: List[CommitmentSchema] = []

        for line in lines:
            # 1. Check user commitment ("I will ...", "I'll ...", "I commit to ...")
            user_match = re.search(r"\b(?:i will|i'll|i commit to|i promise to)\s+([^.\n]+)", line, re.IGNORECASE)
            if user_match:
                stmt = user_match.group(0).strip()
                # Determine sender
                owner = current_user_identity if message.direction.value == "OUTBOUND" else message.sender
                c = CommitmentSchema(
                    statement=stmt,
                    owner=owner,
                    source_message_id=message.message_id,
                    thread_id=message.thread_id,
                    status=CommitmentStatus.OPEN,
                    confidence=0.92,
                    user_id=message.user_id,
                )
                commitments.append(c)
                self._commitments[c.commitment_id] = c
                continue

            # 2. Check third-party attributed commitment ("Alice will ...", "Bob promised to ...")
            third_match = re.search(r"\b([A-Z][a-zA-Z0-9_\-]+)\s+(?:will|committed to|is going to)\s+([^.\n]+)", line)
            if third_match:
                speaker_name = third_match.group(1)
                # Filter out generic pronouns
                if speaker_name.lower() not in ("it", "this", "that", "there", "what", "how", "who"):
                    stmt = third_match.group(0).strip()
                    c = CommitmentSchema(
                        statement=stmt,
                        owner=speaker_name,
                        source_message_id=message.message_id,
                        thread_id=message.thread_id,
                        status=CommitmentStatus.OPEN,
                        confidence=0.85,
                        user_id=message.user_id,
                    )
                    commitments.append(c)
                    self._commitments[c.commitment_id] = c

        return commitments

    def create_explicit_commitment(
        self,
        statement: str,
        owner: str,
        due_at: Optional[datetime] = None,
        source_message_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        user_id: str = "default_user",
    ) -> CommitmentSchema:
        if not statement or not statement.strip():
            raise CommitmentFabricationError("Cannot create a commitment with an empty statement.")
        if not owner or not owner.strip():
            raise CommitmentFabricationError("Cannot create a commitment without an explicit owner.")

        c = CommitmentSchema(
            statement=statement.strip(),
            owner=owner.strip(),
            due_at=due_at,
            source_message_id=source_message_id,
            thread_id=thread_id,
            status=CommitmentStatus.OPEN,
            confidence=1.0,
            user_id=user_id,
        )
        self._commitments[c.commitment_id] = c
        return c

    def update_status(self, commitment_id: str, status: CommitmentStatus) -> CommitmentSchema:
        c = self._commitments.get(commitment_id)
        if not c:
            raise ValueError(f"Commitment '{commitment_id}' not found.")
        c.status = status
        return c

    def list_commitments(
        self,
        user_id: Optional[str] = None,
        owner: Optional[str] = None,
        status: Optional[CommitmentStatus] = None,
    ) -> List[CommitmentSchema]:
        results = list(self._commitments.values())
        if user_id:
            results = [c for c in results if c.user_id == user_id]
        if owner:
            results = [c for c in results if c.owner.lower() == owner.lower()]
        if status:
            results = [c for c in results if c.status == status]
        return results
