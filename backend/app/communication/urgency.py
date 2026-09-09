"""Urgency evaluation, deadline calculations, priority ranking, and authority gating."""

from __future__ import annotations

from datetime import datetime, timedelta
import re
from typing import Any, Dict, List, Optional
from app.communication.schemas import CommunicationUrgency, MessageSchema


class UrgencyEvaluator:
    """Evaluates message urgency and ranks priority without allowing urgency to bypass policy."""

    def evaluate_urgency(self, message: MessageSchema) -> Dict[str, Any]:
        text = f"{message.subject or ''} {message.content_reference}".strip().lower()

        urgency = CommunicationUrgency.NORMAL
        reasons: List[str] = []

        if any(w in text for w in ["p0", "sev1", "sev0", "production down", "outage in prod", "security breach", "data leak"]):
            urgency = CommunicationUrgency.CRITICAL
            reasons.append("Contains production outage or high-severity security incident keywords.")
        elif any(w in text for w in ["urgent", "asap", "immediately", "deadline today", "emergency", "blocker"]):
            urgency = CommunicationUrgency.HIGH
            reasons.append("Contains immediate operational turnaround keywords.")
        elif any(w in text for w in ["no rush", "whenever you can", "fyi only", "low priority", "when you have a moment"]):
            urgency = CommunicationUrgency.LOW
            reasons.append("Explicitly tagged as low priority or non-urgent FYI.")

        return {
            "urgency": urgency,
            "reasons": reasons,
            "urgency_does_not_confer_authority": True,  # INVARIANT 38
        }

    def compute_priority_score(
        self,
        urgency: CommunicationUrgency,
        relationship_confidence: float = 0.8,
        is_client_or_critical_contact: bool = False,
        has_approaching_deadline: bool = False,
    ) -> float:
        """Computes numeric priority score (0.0 to 100.0) based on multiple factors."""
        base_scores = {
            CommunicationUrgency.LOW: 20.0,
            CommunicationUrgency.NORMAL: 50.0,
            CommunicationUrgency.HIGH: 75.0,
            CommunicationUrgency.CRITICAL: 90.0,
        }
        score = base_scores.get(urgency, 50.0)
        if has_approaching_deadline:
            score += 10.0
        if is_client_or_critical_contact:
            score += 5.0
        score *= min(max(relationship_confidence, 0.5), 1.0)
        return round(min(score, 100.0), 2)
