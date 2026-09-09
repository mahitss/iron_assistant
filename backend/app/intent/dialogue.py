"""Dialogue State Tracking, Session Continuity, Goal Switching, and User Correction Loop (Task 48)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger("kairo.intent.dialogue")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class DialogueTurn:
    turn_id: str
    user_input: str
    intent_id: str
    goal_id: Optional[str] = None
    was_corrected: bool = False
    correction_text: Optional[str] = None
    timestamp: datetime = field(default_factory=utc_now)


@dataclass
class DialogueSession:
    session_id: str
    turns: List[DialogueTurn] = field(default_factory=list)
    active_goal_id: Optional[str] = None
    interrupted_goals: List[str] = field(default_factory=list)



class DialogueStateManager:
    """Manages multi-turn intent tracking, goal switching, and non-defensive user corrections (Spec 67-73, 86-96).
    
    CRITICAL INVARIANTS:
    1. No defensive behavior (Spec 69): Do NOT argue with user about their own intent.
    2. Explicit override (Spec 96): Current user statement strictly overrides inferred previous intent.
    3. Goal switch (Spec 93): Detect abrupt topic changes; do NOT carry stale context across goal switches.
    """

    def __init__(self) -> None:
        # session_id -> list of DialogueTurn
        self._sessions: Dict[str, List[DialogueTurn]] = {}
        # session_id -> current active goal_id
        self._active_goals: Dict[str, str] = {}
        # session_id -> interrupted goal_ids stack
        self._interrupted_goals: Dict[str, List[str]] = {}

    def record_turn(
        self,
        session_id: str,
        user_input: str,
        intent_id: str,
        goal_id: Optional[str] = None,
    ) -> DialogueTurn:
        tid = f"turn_{uuid.uuid4().hex[:8]}"
        turn = DialogueTurn(
            turn_id=tid,
            user_input=user_input,
            intent_id=intent_id,
            goal_id=goal_id,
        )
        self._sessions.setdefault(session_id, []).append(turn)

        if goal_id:
            # Check if this is a topic switch (Spec 93)
            current = self._active_goals.get(session_id)
            if current and current != goal_id:
                # Push previous goal to interrupted stack (Spec 94)
                self._interrupted_goals.setdefault(session_id, []).append(current)
                logger.info("Goal switch detected in session %s: %s -> %s (pushed to interrupted stack)", session_id, current, goal_id)
            self._active_goals[session_id] = goal_id

        return turn

    def handle_user_correction(
        self,
        session_id: str,
        correction_text: str,
        revised_intent_id: str,
    ) -> Dict[str, Any]:
        """Enforce Spec 67-69: Record user correction with zero defensiveness; update dialogue state."""
        turns = self._sessions.get(session_id, [])
        if turns:
            last_turn = turns[-1]
            last_turn.was_corrected = True
            last_turn.correction_text = correction_text

        logger.info("Non-defensively processed user correction in session %s: '%s'", session_id, correction_text)
        return {
            "status": "CORRECTION_ACCEPTED",
            "message": "Understood. Updating intent interpretation and revising plan.",
            "revised_intent_id": revised_intent_id,
            "session_id": session_id,
        }

    def resume_interrupted_goal(self, session_id: str) -> Optional[str]:
        """Enforce Spec 94, 95: Support returning to previously interrupted goal."""
        stack = self._interrupted_goals.get(session_id, [])
        if stack:
            resumed_goal_id = stack.pop()
            self._active_goals[session_id] = resumed_goal_id
            logger.info("Resumed interrupted goal %s in session %s", resumed_goal_id, session_id)
            return resumed_goal_id
        return None

    def reset_context(self, session_id: str) -> None:
        """Enforce Spec 92: Allow user to start a clean, new unrelated goal."""
        self._active_goals.pop(session_id, None)
        self._interrupted_goals.pop(session_id, None)
        logger.info("Reset dialogue context for session %s", session_id)
