"""Message classification across 14 communication categories."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple
from app.communication.schemas import MessageCategory, MessageSchema


class MessageClassifier:
    """Classifies inbound and outbound messages into 14 standardized communication categories."""

    def __init__(self) -> None:
        pass

    def classify(self, message: MessageSchema) -> Dict[str, Any]:
        text = f"{message.subject or ''} {message.content_reference}".strip()
        text_lower = text.lower()

        scores: Dict[MessageCategory, float] = {cat: 0.05 for cat in MessageCategory}

        # Rule-based heuristics & feature matching
        if "?" in text or any(w in text_lower for w in ["what", "how", "when", "where", "why", "who", "could you", "can you"]):
            scores[MessageCategory.QUESTION] += 0.6

        if any(w in text_lower for w in ["please send", "could you provide", "requesting", "need you to", "can you help"]):
            scores[MessageCategory.REQUEST] += 0.55

        if any(w in text_lower for w in ["action item", "todo", "assigned to", "task:", "jira", "pr#"]):
            scores[MessageCategory.TASK] += 0.65

        if any(w in text_lower for w in ["approve", "approval", "approved", "lgtm", "sign off", "rejected"]):
            scores[MessageCategory.APPROVAL] += 0.7

        if any(w in text_lower for w in ["status update", "weekly update", "progress report", "deployment finished", "released"]):
            scores[MessageCategory.UPDATE] += 0.6

        if any(w in text_lower for w in ["urgent:", "alert:", "incident", "outage", "critical error", "pagerduty"]):
            scores[MessageCategory.ALERT] += 0.8

        if any(w in text_lower for w in ["invitation", "invited you to", "meeting request", "calendar event", "zoom link"]):
            scores[MessageCategory.INVITATION] += 0.7

        if any(w in text_lower for w in ["reminder:", "friendly reminder", "don't forget", "gentle reminder"]):
            scores[MessageCategory.REMINDER] += 0.75

        if any(w in text_lower for w in ["unacceptable", "broken again", "complaint", "frustrated with", "dissatisfied"]):
            scores[MessageCategory.COMPLAINT] += 0.6

        if any(w in text_lower for w in ["feedback on", "suggestions for", "review comments", "input on"]):
            scores[MessageCategory.FEEDBACK] += 0.5

        if any(w in text_lower for w in ["thank you", "thanks!", "appreciate your help", "many thanks", "kudos"]):
            scores[MessageCategory.THANKS] += 0.7

        if any(w in text_lower for w in ["how are you", "happy weekend", "have a great day", "cheers", "good morning"]):
            scores[MessageCategory.SOCIAL] += 0.45

        if any(w in text_lower for w in ["fyi", "for your information", "note that", "heads up", "announcement"]):
            scores[MessageCategory.INFORMATION] += 0.5

        # Determine primary category
        sorted_cats = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        primary_category, top_score = sorted_cats[0]
        if top_score < 0.2:
            primary_category = MessageCategory.OTHER
            top_score = 0.5

        return {
            "primary_category": primary_category.value,
            "confidence": min(top_score, 0.99),
            "secondary_categories": [c.value for c, s in sorted_cats[1:4] if s > 0.3],
            "scores": {c.value: round(s, 2) for c, s in scores.items()},
        }
