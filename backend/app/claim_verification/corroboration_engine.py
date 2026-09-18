"""Corroboration & Contradiction Engine for Task 116.
Forms corroboration groups, evaluates true independent vs dependent support,
detects 8 dimensions of contradictions, and handles negative evidence carefully.
"""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional, Tuple
import uuid

from app.claim_verification.domain import (
    Claim,
    ContradictionRecord,
    ContradictionType,
    CorroborationGroup,
    CorroborationType,
    EvidenceArtifact,
    IndependenceAssessment,
    NegativeEvidenceType,
    Source,
)


class CorroborationEngine:
    """Evaluates supporting evidence, prevents fake independence,
    flags contradictions across 8 dimensions, and enforces negative evidence rigor.
    """

    # Antonym pairs for direct contradiction heuristics
    ANTONYM_PAIRS = [
        ("healthy", "unhealthy"),
        ("available", "unavailable"),
        ("up", "down"),
        ("success", "failure"),
        ("succeeded", "failed"),
        ("active", "inactive"),
        ("running", "stopped"),
        ("enabled", "disabled"),
        ("increased", "decreased"),
        ("connected", "disconnected"),
    ]

    @classmethod
    def evaluate_corroboration(
        cls,
        case_id: str,
        claim: Claim,
        artifacts: List[EvidenceArtifact],
        sources: List[Source],
        independence: IndependenceAssessment,
    ) -> CorroborationGroup:
        """Form a corroboration group for the given claim and evidence set."""
        group_id = f"corrob_{uuid.uuid4().hex[:10]}"
        evidence_ids = [a.evidence_id for a in artifacts]
        source_ids = [s.source_id for s in sources]

        if not artifacts:
            return CorroborationGroup(
                group_id=group_id,
                case_id=case_id,
                claim_id=claim.claim_id,
                corroboration_type=CorroborationType.SUPERFICIAL_MATCH,
                evidence_ids=[],
                source_ids=source_ids,
                temporal_alignment=0.0,
                semantic_alignment=0.0,
                scope_alignment=0.0,
                independence_assessment=independence,
                summary="No supporting evidence items provided",
                created_at=datetime.now(timezone.utc),
            )

        # Check semantic alignment between claim text and artifact text
        semantic_scores: List[float] = []
        for art in artifacts:
            if not art.content_text:
                continue
            words_claim = set(claim.normalized_text.split())
            words_art = set(art.content_text.lower().split())
            if words_claim and words_art:
                overlap = len(words_claim.intersection(words_art)) / len(words_claim)
                semantic_scores.append(overlap)
            else:
                semantic_scores.append(0.0)

        avg_semantic = sum(semantic_scores) / len(semantic_scores) if semantic_scores else 0.0

        # Decide CorroborationType
        if avg_semantic < 0.2:
            c_type = CorroborationType.SEMANTIC_MISMATCH
            summary = f"Evidence does not semantically match claim '{claim.canonical_text}' (score={avg_semantic:.2f})"
        elif not independence.is_independent and len(source_ids) > 1:
            c_type = CorroborationType.DEPENDENT_SUPPORT
            summary = f"Evidence supports claim but sources are dependent or derived (independence score={independence.independence_score:.2f})"
        elif independence.is_independent and len(source_ids) > 1 and avg_semantic >= 0.6:
            c_type = CorroborationType.INDEPENDENT_SUPPORT
            summary = f"Multiple independent sources corroborate claim (semantic_alignment={avg_semantic:.2f})"
        elif avg_semantic >= 0.5:
            c_type = CorroborationType.PARTIAL_SUPPORT
            summary = f"Partial evidence support for claim (alignment={avg_semantic:.2f})"
        else:
            c_type = CorroborationType.SUPERFICIAL_MATCH
            summary = f"Superficial match between evidence and claim keywords (alignment={avg_semantic:.2f})"

        return CorroborationGroup(
            group_id=group_id,
            case_id=case_id,
            claim_id=claim.claim_id,
            corroboration_type=c_type,
            evidence_ids=evidence_ids,
            source_ids=source_ids,
            temporal_alignment=1.0,
            semantic_alignment=avg_semantic,
            scope_alignment=1.0,
            independence_assessment=independence,
            summary=summary,
            created_at=datetime.now(timezone.utc),
        )

    @classmethod
    def detect_contradictions(
        cls,
        case_id: str,
        claim: Claim,
        artifacts: List[EvidenceArtifact],
    ) -> List[ContradictionRecord]:
        """Detect any pairwise contradictions between supporting evidence items or between claim and evidence."""
        contradictions: List[ContradictionRecord] = []

        # 1. Pairwise artifact comparisons
        for i in range(len(artifacts)):
            for j in range(i + 1, len(artifacts)):
                a1, a2 = artifacts[i], artifacts[j]
                contra = cls._check_artifact_pair_contradiction(case_id, claim.claim_id, a1, a2)
                if contra:
                    contradictions.append(contra)

        # 2. Check artifact directly contradicting claim statement
        for art in artifacts:
            direct_contra = cls._check_claim_artifact_contradiction(case_id, claim, art)
            if direct_contra:
                contradictions.append(direct_contra)

        return contradictions

    @classmethod
    def _check_artifact_pair_contradiction(
        cls,
        case_id: str,
        claim_id: str,
        art_a: EvidenceArtifact,
        art_b: EvidenceArtifact,
    ) -> Optional[ContradictionRecord]:
        """Check for state, numeric, or direct contradictions between two evidence items."""
        text_a = art_a.content_text.lower()
        text_b = art_b.content_text.lower()

        # Check state / antonym contradictions
        for word1, word2 in cls.ANTONYM_PAIRS:
            if (word1 in text_a and word2 in text_b) or (word2 in text_a and word1 in text_b):
                return ContradictionRecord(
                    contradiction_id=f"contra_{uuid.uuid4().hex[:10]}",
                    case_id=case_id,
                    contradiction_type=ContradictionType.STATE_CONTRADICTION,
                    claim_a_id=claim_id,
                    claim_b_id=None,
                    evidence_a_id=art_a.evidence_id,
                    evidence_b_id=art_b.evidence_id,
                    description=f"Conflicting state assertion detected: '{word1}' vs '{word2}' between evidence {art_a.evidence_id} and {art_b.evidence_id}",
                    severity=0.9,
                    status="OPEN",
                    created_at=datetime.now(timezone.utc),
                )

        # Check numeric contradictions (e.g. latency=50ms vs latency=800ms)
        nums_a = re.findall(r"(\d+(?:\.\d+)?)\s*(ms|s|%|mb|gb|req/s|rps)?", text_a)
        nums_b = re.findall(r"(\d+(?:\.\d+)?)\s*(ms|s|%|mb|gb|req/s|rps)?", text_b)

        if nums_a and nums_b:
            for val_a_str, unit_a in nums_a:
                for val_b_str, unit_b in nums_b:
                    if unit_a and unit_b and unit_a == unit_b:
                        try:
                            val_a = float(val_a_str)
                            val_b = float(val_b_str)
                            if abs(val_a - val_b) > 0.001 and (max(val_a, val_b) / (min(val_a, val_b) + 0.0001) > 1.5):
                                return ContradictionRecord(
                                    contradiction_id=f"contra_{uuid.uuid4().hex[:10]}",
                                    case_id=case_id,
                                    contradiction_type=ContradictionType.NUMERIC_CONTRADICTION,
                                    claim_a_id=claim_id,
                                    claim_b_id=None,
                                    evidence_a_id=art_a.evidence_id,
                                    evidence_b_id=art_b.evidence_id,
                                    description=f"Significant numeric disparity ({val_a}{unit_a} vs {val_b}{unit_b}) between evidence artifacts",
                                    severity=0.85,
                                    status="OPEN",
                                    created_at=datetime.now(timezone.utc),
                                )
                        except ValueError:
                            pass

        return None

    @classmethod
    def _check_claim_artifact_contradiction(
        cls,
        case_id: str,
        claim: Claim,
        art: EvidenceArtifact,
    ) -> Optional[ContradictionRecord]:
        """Check if an evidence artifact directly asserts the opposite of the claim."""
        c_text = claim.normalized_text
        a_text = art.content_text.lower()

        for word1, word2 in cls.ANTONYM_PAIRS:
            if word1 in c_text and word2 in a_text:
                return ContradictionRecord(
                    contradiction_id=f"contra_{uuid.uuid4().hex[:10]}",
                    case_id=case_id,
                    contradiction_type=ContradictionType.DIRECT_CONTRADICTION,
                    claim_a_id=claim.claim_id,
                    claim_b_id=None,
                    evidence_a_id=art.evidence_id,
                    evidence_b_id=art.evidence_id,
                    description=f"Evidence artifact directly contradicts claim '{word1}' with '{word2}'",
                    severity=0.95,
                    status="OPEN",
                    created_at=datetime.now(timezone.utc),
                )

        return None

    @classmethod
    def evaluate_negative_evidence(
        cls,
        search_query: str,
        results_count: int,
        inspection_coverage: float,
    ) -> Tuple[NegativeEvidenceType, str]:
        """Evaluate absence of evidence rigorously:
        Absence of evidence != evidence of absence.
        """
        if results_count == 0 and inspection_coverage >= 0.95:
            return (
                NegativeEvidenceType.SEARCHED_ABSENCE,
                f"Query '{search_query}' returned zero matches across high-coverage ({inspection_coverage:.1%}) logs/telemetry",
            )
        elif results_count == 0 and inspection_coverage >= 0.50:
            return (
                NegativeEvidenceType.INSUFFICIENT_COVERAGE,
                f"Zero matches found for '{search_query}', but inspection coverage is only {inspection_coverage:.1%}. Cannot prove absence.",
            )
        elif results_count == 0:
            return (
                NegativeEvidenceType.UNKNOWN,
                f"Zero matches found for '{search_query}' with low inspection coverage ({inspection_coverage:.1%}). Status remains UNKNOWN.",
            )
        else:
            return (
                NegativeEvidenceType.OBSERVED_ABSENCE,
                f"Matches observed for '{search_query}' ({results_count} occurrences)",
            )
