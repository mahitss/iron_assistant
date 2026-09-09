"""Sentiment and tone analysis with strict anti-diagnosis and anti-manipulation boundaries."""

from __future__ import annotations

import re
from typing import Any, Dict
from app.communication.schemas import CommunicationTone


class PsychologicalDiagnosisViolationError(Exception):
    """Raised when an attempt is made to generate a psychological or clinical assessment from text."""
    pass


class SentimentAnalyzer:
    """Analyzes surface sentiment and communication tone as strictly uncertain operational signals."""

    # Disallowed psychiatric / clinical diagnosis terms
    FORBIDDEN_DIAGNOSTIC_TERMS = {
        "narcissist",
        "bipolar",
        "schizophrenic",
        "depressed",
        "clinically anxious",
        "sociopath",
        "psychopath",
        "personality disorder",
        "neurotic",
        "manic",
    }

    def analyze(self, text: str) -> Dict[str, Any]:
        """Performs non-diagnostic, bounded sentiment and tone evaluation."""
        self._audit_no_diagnosis(text)

        text_lower = text.lower()

        # Surface operational sentiment (positive, neutral, negative, frustrated, concerned)
        sentiment_label = "neutral"
        sentiment_confidence = 0.65

        if any(w in text_lower for w in ["frustrated", "annoying", "unacceptable", "terrible", "waste of time"]):
            sentiment_label = "frustrated"
            sentiment_confidence = 0.8
        elif any(w in text_lower for w in ["worried", "concerned", "risk", "delay", "behind schedule"]):
            sentiment_label = "concerned"
            sentiment_confidence = 0.75
        elif any(w in text_lower for w in ["bad", "wrong", "broken", "failed", "buggy", "disappointed"]):
            sentiment_label = "negative"
            sentiment_confidence = 0.7
        elif any(w in text_lower for w in ["great", "awesome", "excellent", "thank you", "kudos", "wonderful", "glad"]):
            sentiment_label = "positive"
            sentiment_confidence = 0.85

        # Tone analysis (formal, casual, technical, concise, friendly, urgent)
        tone = self._detect_tone(text, text_lower)

        return {
            "surface_sentiment": sentiment_label,
            "sentiment_confidence": sentiment_confidence,
            "is_uncertain_signal": True,  # INVARIANT 40: Never treated as emotional fact
            "detected_tone": tone.value,
            "disclaimer": "Sentiment is an automated heuristic signal and must never be treated as clinical fact or used to profile individuals.",
        }

    def _detect_tone(self, text: str, text_lower: str) -> CommunicationTone:
        words = text.split()
        if any(w in text_lower for w in ["urgent", "asap", "immediately", "critical", "emergency"]):
            return CommunicationTone.URGENT

        if any(w in text_lower for w in ["hey", "hiya", "cool", "yeah", "gonna", "wanna", "lol"]):
            return CommunicationTone.CASUAL

        if any(w in text_lower for w in ["api", "protocol", "architecture", "endpoint", "database", "latency", "schema"]):
            return CommunicationTone.TECHNICAL

        if len(words) < 15 and ("yes" in text_lower or "no" in text_lower or "ack" in text_lower or "done" in text_lower):
            return CommunicationTone.CONCISE

        if any(w in text_lower for w in ["warm regards", "hope you are well", "thanks a lot", "cheers", "best wishes"]):
            return CommunicationTone.FRIENDLY

        return CommunicationTone.FORMAL

    def _audit_no_diagnosis(self, candidate_text: str) -> None:
        """INVARIANT 41: Never diagnose people from communication."""
        lower = candidate_text.lower()
        for term in self.FORBIDDEN_DIAGNOSTIC_TERMS:
            if re.search(rf"\b{re.escape(term)}\b", lower):
                raise PsychologicalDiagnosisViolationError(
                    f"Forbidden clinical diagnosis term '{term}' detected. Kairo is strictly forbidden from psychological profiling."
                )
