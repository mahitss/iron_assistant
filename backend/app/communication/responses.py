"""Response necessity determination and priority ranking."""

from __future__ import annotations

from typing import Any, Dict
from app.communication.schemas import (
    CommunicationUrgency,
    MessageCategory,
    MessageSchema,
    ResponseNeed,
)


class ResponseNeedEvaluator:
    """Determines whether a message requires a response and calculates priority ranking."""

    def evaluate_response_need(
        self,
        message: MessageSchema,
        category: MessageCategory,
        urgency: CommunicationUrgency,
    ) -> Dict[str, Any]:
        text = message.content_reference.lower()

        # Questions and direct requests usually require response
        if category in (MessageCategory.QUESTION, MessageCategory.APPROVAL):
            need = ResponseNeed.REQUIRED
            rationale = "Direct question or explicit approval request requires formal response."
        elif category in (MessageCategory.REQUEST, MessageCategory.TASK):
            need = ResponseNeed.RECOMMENDED
            rationale = "Task or assistance requested."
        elif category in (MessageCategory.INVITATION, MessageCategory.REMINDER):
            need = ResponseNeed.RECOMMENDED
            rationale = "Meeting invitation or reminder suggests confirmation."
        elif category in (MessageCategory.INFORMATION, MessageCategory.UPDATE, MessageCategory.THANKS):
            need = ResponseNeed.NO_RESPONSE
            rationale = "FYI / informational update or acknowledgement; response not needed."
        else:
            need = ResponseNeed.OPTIONAL
            rationale = "Contextual conversational message."

        # Urgency adjustment
        if urgency in (CommunicationUrgency.HIGH, CommunicationUrgency.CRITICAL) and need != ResponseNeed.NO_RESPONSE:
            need = ResponseNeed.REQUIRED

        return {
            "response_need": need,
            "rationale": rationale,
        }
