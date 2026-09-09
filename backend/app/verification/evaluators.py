"""Citation, Fact, and Source Evaluators for Kairo (Task 42).

Enforces citation integrity, verifies source existence and content relevance,
detects hallucinated sources and confabulated citations, and evaluates test
rigor (rejecting empty/always-pass assertions).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.verification.claims import Claim, ClaimType, TruthStatus

logger = logging.getLogger("kairo.verification.evaluators")


@dataclass
class CitationValidationResult:
    """Result of validating a source citation."""

    citation_ref: str
    is_valid: bool
    exists: bool
    supports_claim: bool
    rejection_reason: str | None = None
    extracted_quote: str | None = None
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "citation_ref": self.citation_ref,
            "is_valid": self.is_valid,
            "exists": self.exists,
            "supports_claim": self.supports_claim,
            "rejection_reason": self.rejection_reason,
            "extracted_quote": self.extracted_quote,
            "evaluated_at": self.evaluated_at.isoformat(),
        }


@dataclass
class TestQualityAssessment:
    """Result of evaluating test rigor and assertion quality."""

    test_name: str
    is_rigorous: bool
    has_assertions: bool
    is_mock_only: bool
    is_always_pass: bool
    weakness_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "test_name": self.test_name,
            "is_rigorous": self.is_rigorous,
            "has_assertions": self.has_assertions,
            "is_mock_only": self.is_mock_only,
            "is_always_pass": self.is_always_pass,
            "weakness_reasons": self.weakness_reasons,
        }


class CitationValidator:
    """Validates citations against known source registries and document bodies."""

    def __init__(self, known_sources: dict[str, str] | None = None) -> None:
        # Map of source_reference -> source text content
        self._sources: dict[str, str] = dict(known_sources or {})

    def register_source(self, source_ref: str, content: str) -> None:
        """Register a valid document or endpoint source."""
        self._sources[source_ref.strip()] = content

    def remove_source(self, source_ref: str) -> None:
        """Mark source as unavailable / removed (Spec 94)."""
        self._sources.pop(source_ref.strip(), None)

    def validate_citation(
        self,
        claim_statement: str,
        citation_ref: str,
        claimed_excerpt: str | None = None,
    ) -> CitationValidationResult:
        """Validate that a citation exists and meaningfully corroborates the claim."""
        clean_ref = citation_ref.strip()

        # Check existence (Spec 92, 161)
        if clean_ref not in self._sources:
            return CitationValidationResult(
                citation_ref=clean_ref,
                is_valid=False,
                exists=False,
                supports_claim=False,
                rejection_reason=f"Source '{clean_ref}' does not exist or has become unavailable.",
            )

        source_body = self._sources[clean_ref].lower()
        
        # If specific excerpt provided, verify it actually exists in the source text
        if claimed_excerpt:
            norm_excerpt = claimed_excerpt.strip().lower()
            if norm_excerpt not in source_body:
                return CitationValidationResult(
                    citation_ref=clean_ref,
                    is_valid=False,
                    exists=True,
                    supports_claim=False,
                    rejection_reason="Claimed citation excerpt was not found in source text (fabricated citation).",
                )

        # Keyword token overlap check
        claim_tokens = {
            t.lower() for t in re.findall(r"\b[A-Za-z0-9_]{3,}\b", claim_statement)
            if t.lower() not in {"the", "and", "for", "with", "that", "this", "from"}
        }

        if claim_tokens:
            matches = [t for t in claim_tokens if t in source_body]
            overlap_ratio = len(matches) / len(claim_tokens)
            if overlap_ratio < 0.25:
                return CitationValidationResult(
                    citation_ref=clean_ref,
                    is_valid=False,
                    exists=True,
                    supports_claim=False,
                    rejection_reason=f"Citation content has low relevance to claim (overlap {overlap_ratio:.1%}).",
                )

        return CitationValidationResult(
            citation_ref=clean_ref,
            is_valid=True,
            exists=True,
            supports_claim=True,
            extracted_quote=claimed_excerpt,
        )


class TestQualityEvaluator:
    """Detects weak, empty, or mock-only test suites (Spec 128)."""

    @staticmethod
    def evaluate_test_code(test_name: str, code_content: str) -> TestQualityAssessment:
        weaknesses: list[str] = []
        lower_code = code_content.lower()

        # Check for assertions
        has_assert = bool(re.search(r"\b(assert|expect|self\.assert|toBe|toEqual)\b", code_content))
        if not has_assert:
            weaknesses.append("Test contains no assertions or expectations.")

        # Check for always-pass tautologies (e.g. assert True, assert 1 == 1)
        is_always_pass = bool(re.search(r"assert\s+(true|1\s*==\s*1)\b", lower_code))
        if is_always_pass:
            weaknesses.append("Test contains tautological always-pass assertions (e.g., assert True).")

        # Check for mock-only tests that do not exercise actual logic
        is_mock_only = ("unittest.mock" in lower_code or "mocker" in lower_code) and (
            "real_" not in lower_code and "client." not in lower_code and "engine." not in lower_code
        )
        if is_mock_only and len(re.findall(r"assert", lower_code)) <= 1:
            weaknesses.append("Test appears to be mock-only without exercising concrete behavioral paths.")

        is_rigorous = (has_assert and not is_always_pass and len(weaknesses) == 0)

        return TestQualityAssessment(
            test_name=test_name,
            is_rigorous=is_rigorous,
            has_assertions=has_assert,
            is_mock_only=is_mock_only,
            is_always_pass=is_always_pass,
            weakness_reasons=weaknesses,
        )
