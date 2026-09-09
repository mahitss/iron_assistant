"""Context engine integration, project isolation, multi-tenant boundaries, and cross-thread leak defense."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from app.communication.schemas import MessageSchema, ThreadSchema


class ContextIsolationViolationError(Exception):
    """Raised when an attempt is made to breach project, user, or organization boundaries."""
    pass


class CommunicationContextManager:
    """Provides scoped context assembly with strict cross-project and cross-user isolation."""

    def __init__(self) -> None:
        pass

    def assemble_context(
        self,
        requesting_user_id: str,
        thread: ThreadSchema,
        active_project_id: Optional[str] = None,
        max_messages: int = 10,
    ) -> Dict[str, Any]:
        """Assembles conversational and environmental context while strictly enforcing privacy boundaries."""
        # 1. Verify user isolation
        if thread.user_id != requesting_user_id:
            raise ContextIsolationViolationError(
                f"Access denied: User '{requesting_user_id}' cannot access communication belonging to user '{thread.user_id}'."
            )

        # 2. Verify project isolation if thread is tied to a specific project
        if thread.project_id and active_project_id and thread.project_id != active_project_id:
            raise ContextIsolationViolationError(
                f"Cross-project isolation breach: Thread project '{thread.project_id}' does not match active project '{active_project_id}'."
            )

        # 3. Retrieve relevant message history within the thread (data minimization)
        recent_messages = thread.messages[-max_messages:] if thread.messages else []

        history_items = []
        for m in recent_messages:
            # Double check message user ownership
            if m.user_id != requesting_user_id:
                continue
            history_items.append({
                "sender": m.sender,
                "timestamp": m.timestamp.isoformat(),
                "content": m.content_reference,
                "direction": m.direction.value,
            })

        return {
            "thread_id": thread.thread_id,
            "subject": thread.subject,
            "channel": thread.channel.value,
            "project_id": thread.project_id,
            "participants": [p.model_dump() for p in thread.participants],
            "message_history": history_items,
            "state": thread.state.value,
        }

    def sanitize_cross_thread_leak(
        self,
        candidate_text: str,
        confidential_terms_by_thread: Dict[str, List[str]],
        current_thread_id: str,
    ) -> str:
        """Ensures secrets or confidential tokens from other threads do not leak into candidate_text."""
        sanitized = candidate_text
        for other_tid, terms in confidential_terms_by_thread.items():
            if other_tid == current_thread_id:
                continue
            for term in terms:
                if len(term) >= 4 and term.lower() in sanitized.lower():
                    sanitized = sanitized.replace(term, "[REDACTED_CONFIDENTIAL]")
        return sanitized
