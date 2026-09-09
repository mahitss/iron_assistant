"""Ambiguity analysis, candidate evaluation, and interactive clarification builder (Spec 39-47, 159)."""

import logging
from typing import Any

from app.intent.schemas import (
    AmbiguityLevel,
    AmbiguityReport,
    ClarificationOption,
    IntentRiskLevel,
    IntentType,
)

logger = logging.getLogger("kairo.intent.ambiguity")


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
        """
        Evaluates whether an intent contains ambiguity that requires clarification.
        Enforces: NEVER guess for high-risk or destructive actions (Spec 43, 44).
        """
        missing_params = missing_params or []

        # Check loop threshold (Spec 159)
        if clarification_attempts >= cls.MAX_CLARIFICATION_ATTEMPTS:
            return AmbiguityReport(
                ambiguous=True,
                level=AmbiguityLevel.CRITICAL,
                missing_information=["clarification_limit_reached"],
                reason="Multiple clarification attempts were unsuccessful. Action halted for safety.",
                resolution_options=[],
            )

        # 1. Critical ambiguity check: High-risk action without a clearly resolved target
        is_high_impact = risk_level in (IntentRiskLevel.HIGH, IntentRiskLevel.CRITICAL) or intent_type in (
            IntentType.DELETE,
            IntentType.CONTROL,
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

        # 3. Missing required parameter (e.g. "remind me" without time or content, "update config" without file)
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
            level=AmbiguityLevel.LOW,
            candidates=[],
            missing_information=[],
            reason=None,
            resolution_options=[],
        )
