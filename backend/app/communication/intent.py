"""Communication intent understanding, goal mapping, and action extraction."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import re
from typing import Any, Dict, List, Optional
from app.communication.schemas import MessageSchema


class CommunicationIntentEngine:
    """Extracts communicative actions, owners, goals, and temporal deadlines without inventing dates."""

    def __init__(self) -> None:
        pass

    def extract_intent_and_actions(self, message: MessageSchema) -> Dict[str, Any]:
        text = f"{message.subject or ''} {message.content_reference}".strip()
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]

        actions: List[Dict[str, Any]] = []
        # Pattern matching for actionable clauses
        action_patterns = [
            r"(?:please|kindly|could you|can you|need to|must)\s+([^.\n]+)",
            r"(?:todo|action item|task):\s*([^.\n]+)",
            r"([a-zA-Z]+)\s+will\s+([^.\n]+)",
            r"let's\s+([^.\n]+)",
        ]

        for line in lines:
            for pat in action_patterns:
                match = re.search(pat, line, re.IGNORECASE)
                if match:
                    action_stmt = match.group(1).strip()
                    # Extract potential owner
                    owner = self._extract_owner(line, fallback=message.sender)
                    deadline = self._extract_deadline_text(line)
                    actions.append({
                        "action": action_stmt,
                        "owner": owner,
                        "deadline_text": deadline,
                        "dependency": None,
                        "status": "IDENTIFIED",
                    })

        # Determine communication goal
        goal = self._determine_communication_goal(text)

        return {
            "communication_goal": goal,
            "actions": actions,
            "has_unanswered_question": "?" in text,
        }

    def _extract_owner(self, line: str, fallback: str) -> str:
        line_lower = line.lower()
        if "i will" in line_lower or "i'll" in line_lower or "assigned to me" in line_lower:
            return fallback
        match = re.search(r"assigned to\s+([a-zA-Z0-9_\-\.]+)", line, re.IGNORECASE)
        if match:
            return match.group(1)
        match_will = re.search(r"([a-zA-Z]+)\s+will", line, re.IGNORECASE)
        if match_will and match_will.group(1).lower() not in ("we", "it", "this", "that", "i"):
            return match_will.group(1)
        return "unassigned"

    def _extract_deadline_text(self, line: str) -> Optional[str]:
        """INVARIANT 30: Preserves ambiguity rather than inventing dates. Returns raw text or None."""
        m = re.search(r"\b(?:by|before|due|deadline)\s+([a-zA-Z0-9\s,\-\/:]+?)(?:[\.\n]|$)", line, re.IGNORECASE)
        if m:
            raw_deadline = m.group(1).strip()
            # If the raw deadline has substance, return it exactly
            if len(raw_deadline) > 1 and raw_deadline.lower() not in ("then", "now", "it"):
                return raw_deadline
        return None

    def _determine_communication_goal(self, text: str) -> str:
        tl = text.lower()
        if any(w in tl for w in ["follow up", "following up", "checking in on"]):
            return "follow_up"
        if any(w in tl for w in ["please confirm", "confirming", "do you agree", "can we proceed"]):
            return "confirm"
        if any(w in tl for w in ["schedule", "meeting at", "let's meet", "calendar"]):
            return "schedule"
        if any(w in tl for w in ["escalate", "urgent attention", "blocker", "severity 1"]):
            return "escalate"
        if any(w in tl for w in ["resolved", "fixed", "closing this", "completed"]):
            return "resolve"
        if any(w in tl for w in ["please", "requesting", "could you", "need you to"]):
            return "request"
        if any(w in tl for w in ["coordinate", "sync", "collaborate"]):
            return "coordinate"
        return "inform"
