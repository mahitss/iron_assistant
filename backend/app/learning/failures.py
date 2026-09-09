"""Failure management, RCA integration, and pre-flight warning engine (Task 43)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.learning.patterns import FailurePattern, PatternClusterer

logger = logging.getLogger("kairo.learning.failures")


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class PreFlightWarning:
    """Evidence-backed warning surfaced before task or plan execution (Spec 71)."""

    warning_id: str
    target_workflow: str
    pattern_signature: str
    frequency: int
    message: str
    recommended_mitigation: str
    confidence: str
    is_blocking: bool = False  # Prediction cannot block unless policy dictates (Spec 72)
    created_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "warning_id": self.warning_id,
            "target_workflow": self.target_workflow,
            "pattern_signature": self.pattern_signature,
            "frequency": self.frequency,
            "message": self.message,
            "recommended_mitigation": self.recommended_mitigation,
            "confidence": self.confidence,
            "is_blocking": self.is_blocking,
            "created_at": self.created_at.isoformat(),
        }


class FailureManager:
    """Manages failure patterns, registers occurrences, and generates pre-flight warnings."""

    def __init__(self) -> None:
        self._patterns: dict[str, FailurePattern] = {}  # signature -> FailurePattern

    def record_failure(
        self,
        domain: str,
        error_message: str,
        component: str | None = None,
        mitigation: str = "Verify dependent service health or check network parameters.",
        evidence_item: dict[str, Any] | None = None,
    ) -> FailurePattern:
        """Record and cluster a failure occurrence."""
        sig = PatternClusterer.extract_signature(error_message)
        if sig not in self._patterns:
            pattern = FailurePattern(
                domain=domain,
                signature=sig,
                affected_components=[component] if component else [],
                mitigation=mitigation,
                evidence=[evidence_item] if evidence_item else [],
            )
            self._patterns[sig] = pattern
        else:
            pattern = self._patterns[sig]
            pattern.record_occurrence(component=component, evidence_item=evidence_item)

        return pattern

    def check_pre_flight(self, workflow_name: str, domain: str = "system") -> PreFlightWarning | None:
        """Check for recurring failure patterns associated with a workflow or domain (Spec 71)."""
        clean_name = workflow_name.strip().lower()
        matching_patterns = [
            p for p in self._patterns.values()
            if (clean_name in p.signature.lower() or p.domain.lower() == domain.lower()) and p.frequency >= 3
        ]

        if not matching_patterns:
            return None

        # Pick most frequent pattern
        top_pattern = max(matching_patterns, key=lambda p: p.frequency)
        msg = f"Kairo has seen this workflow fail due to '{top_pattern.signature}' {top_pattern.frequency} times recently."

        return PreFlightWarning(
            warning_id=f"warn_{top_pattern.pattern_id}",
            target_workflow=workflow_name,
            pattern_signature=top_pattern.signature,
            frequency=top_pattern.frequency,
            message=msg,
            recommended_mitigation=top_pattern.mitigation,
            confidence=top_pattern.confidence,
            is_blocking=False,
        )

    def list_patterns(self, domain: str | None = None) -> list[FailurePattern]:
        patterns = list(self._patterns.values())
        if domain:
            patterns = [p for p in patterns if p.domain.lower() == domain.lower()]
        return patterns
