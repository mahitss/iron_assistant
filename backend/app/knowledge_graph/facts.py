"""Fact validation and evidence-based promotion rules."""

from __future__ import annotations

from typing import Any, Dict, List
from app.knowledge_graph.schemas import AssertionSchema, AssertionStatus


class FactValidator:
    """Evaluates whether an assertion has sufficient evidence to be considered a verified fact (INVARIANT 12)."""

    @staticmethod
    def is_fact(assertion: AssertionSchema) -> bool:
        """A fact must be ACTIVE, verified or observed with confidence >= 0.85, and not unverified inference."""
        if assertion.status != AssertionStatus.ACTIVE:
            return False
        if assertion.is_inferred and assertion.confidence < 0.90:
            return False
        return assertion.confidence >= 0.85

    @staticmethod
    def promote_to_fact(assertion: AssertionSchema, verification_evidence: Dict[str, Any]) -> AssertionSchema:
        """Promotes an unverified or candidate assertion to verified fact status."""
        assertion.is_inferred = False
        assertion.confidence = 1.0
        assertion.status = AssertionStatus.ACTIVE
        assertion.source["verification"] = verification_evidence
        return assertion
