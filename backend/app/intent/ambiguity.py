"""Ambiguity Analysis, Candidate Evaluation, and Interactive Clarification Builder (Tasks 35 & 48)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from app.intent.schemas import (
    AmbiguityLevel,
    AmbiguityReport,
    ClarificationOption,
    IntentRiskLevel,
    IntentType,
)

logger = logging.getLogger("kairo.intent.ambiguity")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Ambiguity:
    """Explicit ambiguity model tracking candidate interpretations and resolution (Spec 55-57)."""

    subject: str
    candidates: List[Any] = field(default_factory=list)
    impact: str = "MEDIUM"  # LOW, MEDIUM, HIGH, CRITICAL
    level: AmbiguityLevel = AmbiguityLevel.MEDIUM
    confidence: float = 0.5
    resolution: Optional[Dict[str, Any]] = None
    ambiguity_id: str = field(default_factory=lambda: f"amb_{uuid.uuid4().hex[:8]}")
    created_at: datetime = field(default_factory=utc_now)

    def resolve(self, selected_candidate: Any, method: str = "USER_CLARIFICATION") -> None:
        self.resolution = {
            "selected_candidate": selected_candidate,
            "method": method,
            "resolved_at": utc_now().isoformat(),
        }
        self.level = AmbiguityLevel.NONE
        logger.info("Resolved ambiguity %s on '%s' to %s", self.ambiguity_id, self.subject, selected_candidate)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ambiguity_id": self.ambiguity_id,
            "subject": self.subject,
            "candidates": self.candidates,
            "impact": self.impact,
            "level": self.level.value if hasattr(self.level, "value") else str(self.level),
            "confidence": round(self.confidence, 3),
            "resolution": self.resolution,
            "created_at": self.created_at.isoformat(),
        }


class AmbiguityAnalyzer:
    """Analyzes intent ambiguities, determines risk severity, and constructs safe clarification prompts."""

    MAX_CLARIFICATION_ATTEMPTS = 3

    @classmethod
    def analyze(
        cls,
        intent_type: IntentType,
        risk_level: IntentRiskLevel,
        ambiguous_candidates: list[dict[str, Any]],
        missing_params: list[str] | None = None,
        target: dict[str, Any] | None = None,
        clarification_attempts: int = 0,
    ) -> AmbiguityReport:
        """Evaluates whether an intent contains ambiguity that requires clarification (Spec 55-57).
        
        CRITICAL INVARIANT (Spec 57, 111):
        Low-risk ambiguity may be resolved contextually.
        High-risk and destructive ambiguity strictly REQUIRES clarification. Never guess!
        """
        missing_params = missing_params or []

        # Check loop threshold
        if clarification_attempts >= cls.MAX_CLARIFICATION_ATTEMPTS:
            return AmbiguityReport(
                ambiguous=True,
                level=AmbiguityLevel.CRITICAL,
                missing_information=["clarification_limit_reached"],
                reason="Multiple clarification attempts were unsuccessful. Action halted for safety.",
                resolution_options=[],
            )

        # 1. Critical ambiguity check: High-risk action or destructive action without a clearly resolved target
        is_high_impact = risk_level in (IntentRiskLevel.HIGH, IntentRiskLevel.CRITICAL) or intent_type in (
            IntentType.DELETE,
            IntentType.CONTROL,
            IntentType.DEPLOY,
        )

        if is_high_impact and (ambiguous_candidates or not target or missing_params):
            candidates_list = []
            options = []
            reason = "A specific target is required for this operation. Please clarify your intended target."

            if ambiguous_candidates:
                first = ambiguous_candidates[0]
                candidates_list = first.get("candidates", [])
                reason = first.get("reason", reason)
                for idx, c in enumerate(candidates_list[:4]):
                    name = str(c)
                    options.append(ClarificationOption(id=f"opt_{idx}", label=name, value=name))

            return AmbiguityReport(
                ambiguous=True,
                level=AmbiguityLevel.CRITICAL,
                candidates=ambiguous_candidates,
                missing_information=missing_params,
                reason=reason,
                resolution_options=options,
            )

        # 2. Medium/High ambiguity: Multiple candidates for a normal action
        if ambiguous_candidates:
            first = ambiguous_candidates[0]
            candidates_list = first.get("candidates", [])
            options = [
                ClarificationOption(id=f"opt_{idx}", label=str(c), value=str(c))
                for idx, c in enumerate(candidates_list[:4])
            ]
            return AmbiguityReport(
                ambiguous=True,
                level=AmbiguityLevel.MEDIUM if risk_level == IntentRiskLevel.LOW else AmbiguityLevel.HIGH,
                candidates=ambiguous_candidates,
                missing_information=missing_params,
                reason=first.get("reason", "Multiple potential targets match your request. Which one?"),
                resolution_options=options,
            )

        # 3. Missing required parameter
        if missing_params:
            return AmbiguityReport(
                ambiguous=True,
                level=AmbiguityLevel.MEDIUM,
                candidates=[],
                missing_information=missing_params,
                reason=f"Missing required details: {', '.join(missing_params)}.",
                resolution_options=[],
            )

        # 4. Unambiguous
        return AmbiguityReport(
            ambiguous=False,
            level=AmbiguityLevel.NONE,
            candidates=[],
            missing_information=[],
            reason=None,
            resolution_options=[],
        )
