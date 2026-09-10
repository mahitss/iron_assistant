"""Cross-source conflict detection, discrepancy factor analysis, and unresolved contradiction tracking (Task 63)."""

from __future__ import annotations

import logging
import re

from app.research.schemas import Claim, ConflictRecord, ConflictStatus, ConflictType

logger = logging.getLogger(__name__)


class ConflictDetector:
    """Detects contradictory assertions across multi-source claims and explains discrepancies.

    Invariant 15: Contradictory claims are not automatically averaged or blindly resolved.
    The system identifies underlying causes of divergence; otherwise marks CONFLICT_UNRESOLVED.
    """

    def __init__(self) -> None:
        self._conflicts: dict[str, ConflictRecord] = {}

    def detect_conflicts(self, claims: list[Claim]) -> list[ConflictRecord]:
        """Cross-compare claims across sources to identify direct contradictions or numerical discrepancies."""
        detected: list[ConflictRecord] = []

        for i in range(len(claims)):
            for j in range(i + 1, len(claims)):
                c1 = claims[i]
                c2 = claims[j]

                # Only compare claims about the same subject
                if c1.subject.lower() != c2.subject.lower():
                    continue

                # Ignore comparison of a claim with its own superseded version
                if c1.superseded_by == c2.claim_id or c2.superseded_by == c1.claim_id:
                    continue

                conflict = self._evaluate_claim_pair(c1, c2)
                if conflict:
                    self._conflicts[conflict.conflict_id] = conflict
                    detected.append(conflict)

        return detected

    def get_conflict(self, conflict_id: str) -> ConflictRecord | None:
        """Retrieve conflict record by ID."""
        return self._conflicts.get(conflict_id)

    def list_conflicts(self) -> list[ConflictRecord]:
        """List tracked conflicts."""
        return list(self._conflicts.values())

    def _evaluate_claim_pair(self, c1: Claim, c2: Claim) -> ConflictRecord | None:
        """Analyze if two claims about the same subject express contradictory statements or diverging metrics."""
        text1 = c1.claim_text.lower()
        text2 = c2.claim_text.lower()

        # Check for numerical discrepancy on the same subject
        num1 = self._extract_first_number(text1)
        num2 = self._extract_first_number(text2)

        if num1 is not None and num2 is not None and abs(num1 - num2) > 0.05 * max(abs(num1), abs(num2)):
            # Determine discrepancy factors
            factors = []
            if c1.scope != c2.scope:
                factors.append(f"Scope difference: '{c1.scope}' vs '{c2.scope}'")
            if c1.source_id != c2.source_id:
                factors.append("Independent reporting sources with differing benchmark harnesses")

            disc_factor = factors[0] if factors else f"{num1} vs {num2}"
            return ConflictRecord(
                claim_a_id=c1.claim_id,
                claim_b_id=c2.claim_id,
                claim_a_text=c1.claim_text,
                claim_b_text=c2.claim_text,
                conflict_type=ConflictType.MEASUREMENT_DISCREPANCY,
                description=f"Diverging quantitative measurements for '{c1.subject}': {num1} vs {num2}",
                discrepancy_factors=factors or ["Differing measurement methodologies or workloads"],
                discrepancy_factor=disc_factor,
                status=ConflictStatus.UNRESOLVED,
            )

        # Check for explicit antonym or negation
        has_negation_diff = ("not" in text1 and "not" not in text2) or ("not" in text2 and "not" not in text1)
        if has_negation_diff and (c1.predicate.lower() == c2.predicate.lower() or c1.object.lower() in text2):
            return ConflictRecord(
                claim_a_id=c1.claim_id,
                claim_b_id=c2.claim_id,
                claim_a_text=c1.claim_text,
                claim_b_text=c2.claim_text,
                conflict_type=ConflictType.DIRECT_CONTRADICTION,
                description=f"Direct contradictory assertions regarding '{c1.subject}': '{c1.claim_text}' vs '{c2.claim_text}'",
                discrepancy_factors=["Conflicting assertions from separate authors"],
                discrepancy_factor="Direct negation between assertions",
                status=ConflictStatus.UNRESOLVED,
            )

        return None

    def _extract_first_number(self, text: str) -> float | None:
        """Extract the first numeric value from a string."""
        match = re.search(r"(\d+(?:\.\d+)?)", text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None


conflict_detector = ConflictDetector()
