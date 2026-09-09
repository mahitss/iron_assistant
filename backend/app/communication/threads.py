"""Threading engine, conversation grouping, cross-channel correlation, and anti-merging guards."""

from __future__ import annotations

from datetime import UTC, datetime
import re
from typing import Any, Dict, List, Optional
import uuid

from app.communication.schemas import (
    CommunicationChannel,
    MessageSchema,
    ParticipantSchema,
    ThreadSchema,
    ThreadState,
)


def clean_subject(subject: Optional[str]) -> str:
    """Strips Re:, Fwd:, and whitespace to find normalized root subject."""
    if not subject:
        return ""
    cleaned = re.sub(r"^(re|fwd|fw|aw|sv):\s*", "", subject, flags=re.IGNORECASE)
    return cleaned.strip().lower()


class ThreadEngine:
    """Manages thread state, message grouping, correlation, and rolling summaries."""

    def __init__(self) -> None:
        # thread_id -> ThreadSchema
        self._threads: Dict[str, ThreadSchema] = {}

    def get_thread(self, thread_id: str) -> Optional[ThreadSchema]:
        return self._threads.get(thread_id)

    def list_threads(
        self,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        state: Optional[ThreadState] = None,
    ) -> List[ThreadSchema]:
        results = list(self._threads.values())
        if user_id:
            results = [t for t in results if t.user_id == user_id]
        if project_id:
            results = [t for t in results if t.project_id == project_id]
        if state:
            results = [t for t in results if t.state == state]
        return sorted(results, key=lambda t: t.last_activity, reverse=True)

    def correlate_message(self, message: MessageSchema) -> ThreadSchema:
        """Assigns message to an existing thread or creates a new one.

        Strictly enforces NO FALSE THREAD MERGING: generic subjects or broad topics
        do not merge threads unless message IDs, references, or exact clean subjects match.
        """
        # 1. Direct thread_id match
        if message.thread_id and message.thread_id in self._threads:
            target_thread = self._threads[message.thread_id]
            self._add_message_to_thread(target_thread, message)
            return target_thread

        # 2. Check in-reply-to headers from message provenance
        prov = message.provenance or {}
        headers = prov.get("headers", {})
        in_reply_to = headers.get("in-reply-to") or headers.get("references")
        if in_reply_to:
            for thread in self._threads.values():
                for m in thread.messages:
                    if m.message_id == in_reply_to:
                        self._add_message_to_thread(thread, message)
                        return thread

        # 3. Cross-channel explicit correlation:
        # Only allowed with explicit correlation token (e.g. cross_channel_ref or ticket_id)
        cross_ref = prov.get("cross_channel_ref") or headers.get("x-kairo-thread-ref")
        if cross_ref and cross_ref in self._threads:
            target_thread = self._threads[cross_ref]
            self._add_message_to_thread(target_thread, message)
            return target_thread

        # 4. Clean subject and participant overlap (same channel only, unless explicit link)
        norm_subj = clean_subject(message.subject)
        # INVARIANT: Do not merge purely generic subjects like 'hello', 'hi', 'update', 'meeting'
        GENERIC_SUBJECTS = {"", "hello", "hi", "hey", "update", "meeting", "sync", "status", "notes", "question"}

        if norm_subj and norm_subj not in GENERIC_SUBJECTS:
            for thread in self._threads.values():
                # Cross-channel threads require strong evidence, so check channel match
                if thread.channel == message.channel and thread.project_id == message.project_id:
                    if clean_subject(thread.subject) == norm_subj:
                        # Check participant overlap
                        thread_senders = {p.identity for p in thread.participants}
                        if message.sender in thread_senders or any(r.identity in thread_senders for r in message.recipients):
                            # Check time proximity (e.g. within 30 days)
                            time_diff = abs((message.timestamp - thread.last_activity).total_seconds())
                            if time_diff < 30 * 86400:
                                self._add_message_to_thread(thread, message)
                                return thread

        # If no strict correlation matches, create new thread
        new_thread = self.create_thread(
            channel=message.channel,
            subject=message.subject or "Untitled Conversation",
            user_id=message.user_id,
            project_id=message.project_id,
            initial_message=message,
        )
        return new_thread

    def create_thread(
        self,
        channel: CommunicationChannel,
        subject: str,
        user_id: str = "default_user",
        project_id: Optional[str] = None,
        initial_message: Optional[MessageSchema] = None,
    ) -> ThreadSchema:
        t_id = str(uuid.uuid4())
        participants = []
        messages = []
        if initial_message:
            initial_message.thread_id = t_id
            messages.append(initial_message)
            participants.append(
                ParticipantSchema(
                    identity=initial_message.sender,
                    display_name=initial_message.sender.split("@")[0],
                )
            )
            for r in initial_message.recipients:
                participants.append(
                    ParticipantSchema(
                        identity=r.identity,
                        display_name=r.display_name or r.identity.split("@")[0],
                    )
                )

        thread = ThreadSchema(
            thread_id=t_id,
            channel=channel,
            participants=participants,
            subject=subject,
            messages=messages,
            state=ThreadState.ACTIVE,
            last_activity=initial_message.timestamp if initial_message else datetime.now(UTC),
            project_id=project_id,
            importance="NORMAL",
            user_id=user_id,
        )
        self._threads[t_id] = thread
        return thread

    def update_thread_state(self, thread_id: str, new_state: ThreadState) -> ThreadSchema:
        thread = self._threads.get(thread_id)
        if not thread:
            raise ValueError(f"Thread '{thread_id}' not found.")
        thread.state = new_state
        return thread

    def generate_rolling_summary(self, thread_id: str) -> Dict[str, Any]:
        """Generates structured summary of thread without omitting critical decisions."""
        thread = self._threads.get(thread_id)
        if not thread:
            raise ValueError(f"Thread '{thread_id}' not found.")

        msg_count = len(thread.messages)
        if msg_count == 0:
            return {
                "what_happened": "No messages in thread.",
                "decisions": [],
                "open_questions": [],
                "actions": [],
                "deadlines": [],
                "uncertainty_notes": [],
            }

        # Build rolling summary content
        what_happened = f"Thread discussing '{thread.subject}' with {len(thread.participants)} participants ({msg_count} messages)."
        decisions: List[str] = []
        open_questions: List[str] = []
        actions: List[Dict[str, Any]] = []

        for m in thread.messages:
            content = m.content_reference
            if "?" in content:
                for line in content.split("\n"):
                    if "?" in line and line.strip() not in open_questions:
                        open_questions.append(line.strip())
            if any(k in content.lower() for k in ["agreed", "decided", "decision:", "approved"]):
                decisions.append(f"Recorded in message {m.message_id[:8]}: {content[:100]}...")

        return {
            "what_happened": what_happened,
            "decisions": decisions,
            "open_questions": open_questions,
            "actions": actions,
            "deadlines": [],
            "uncertainty_notes": ["Summary automatically maintained from thread trajectory."],
        }

    def _add_message_to_thread(self, thread: ThreadSchema, message: MessageSchema) -> None:
        message.thread_id = thread.thread_id
        thread.messages.append(message)
        thread.last_activity = max(thread.last_activity, message.timestamp)

        # Update participants if new identity
        existing_ids = {p.identity for p in thread.participants}
        if message.sender not in existing_ids:
            thread.participants.append(
                ParticipantSchema(
                    identity=message.sender,
                    display_name=message.sender.split("@")[0],
                )
            )
            existing_ids.add(message.sender)
        for r in message.recipients:
            if r.identity not in existing_ids:
                thread.participants.append(
                    ParticipantSchema(
                        identity=r.identity,
                        display_name=r.display_name or r.identity.split("@")[0],
                    )
                )
                existing_ids.add(r.identity)
