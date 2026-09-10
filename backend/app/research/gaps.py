"""Knowledge gap detection and automated follow-up research question formulation (Task 63)."""

from __future__ import annotations

import logging
from typing import Any

from app.research.schemas import Claim, KnowledgeGap, UncertaintyRecord

logger = logging.getLogger(__name__)


class GapDetector:
    """Identifies missing empirical dimensions and formulates targeted follow-up research questions.

    Invariant 24: Detects missing information rather than pretending complete coverage.
    Invariant 25: Formulates prioritized follow-up inquiries.
    """

    # Core architectural dimensions that should be evaluated in comprehensive research
    _STANDARD_DIMENSIONS: list[str] = [
        "latency",
        "throughput",
        "reliability",
        "security",
        "storage cost",
        "network cost",
        "failover behavior",
        "operational complexity",
    ]

    def detect_gaps(
        self,
        question: str = "",
        claims: list[Claim] | None = None,
        uncertainty: UncertaintyRecord | None = None,
        *,
        sub_questions: list[str] | None = None,
        conflicts: list[Any] | None = None,
        **kwargs: Any,
    ) -> list[KnowledgeGap]:
        """Detect dimensions omitted from extracted claims and formulate research gaps."""
        claims = claims or []
        gaps: list[KnowledgeGap] = []
        covered_text = " ".join(c.claim_text.lower() for c in claims)

        if sub_questions:
            for sq in sub_questions:
                sq_lower = sq.lower()
                for keyword in [
                    "cost",
                    "storage",
                    "network",
                    "partition",
                    "tolerance",
                    "failover",
                    "throughput",
                ]:
                    if keyword in sq_lower and keyword not in covered_text:
                        gaps.append(
                            KnowledgeGap(
                                description=f"Missing evaluation for '{keyword}' requested in sub-question: {sq}",
                                importance="HIGH",
                                impact=f"Decisions relying on {keyword} will operate under uncertainty.",
                                required_evidence=f"Empirical benchmarks or specification for {keyword}.",
                                recommended_research=[f"Targeted benchmark evaluating {keyword}: {sq}"],
                            )
                        )

        for dim in self._STANDARD_DIMENSIONS:
            if dim not in covered_text and not any(dim in g.description.lower() for g in gaps):
                gap = KnowledgeGap(
                    description=f"Empirical evaluation of '{dim}' is absent from current research findings.",
                    importance="HIGH" if dim in ("security", "reliability", "storage cost") else "MEDIUM",
                    impact=f"Decisions relying on {dim} will operate under unverified assumptions.",
                    required_evidence=f"Direct measurements or benchmark reports covering {dim}.",
                    recommended_research=[
                        f"What are the observed {dim} metrics under peak load?",
                        f"Are there independent studies evaluating {dim} for this system?",
                    ],
                )
                gaps.append(gap)

        if conflicts:
            for c in conflicts:
                if hasattr(c, "status") and c.status == "UNRESOLVED":
                    gaps.append(
                        KnowledgeGap(
                            description=f"Unresolved contradiction between claims: {getattr(c, 'description', '')}",
                            importance="HIGH",
                            impact="Contradictory findings prevent confident decision recommendation.",
                            required_evidence="Controlled reconciliation experiment under identical workloads.",
                            recommended_research=["Run controlled benchmark to reconcile discrepancy."],
                        )
                    )

        # Incorporate unanswered questions from uncertainty record
        if uncertainty and uncertainty.unknown:
            for unk in uncertainty.unknown:
                gaps.append(
                    KnowledgeGap(
                        description=f"Unresolved sub-inquiry: {unk}",
                        importance="HIGH",
                        impact="Primary research question cannot be definitively concluded.",
                        required_evidence="Targeted source ingestion addressing this sub-question.",
                        recommended_research=[unk],
                    )
                )

        logger.info("GAPS_DETECTED: gap_count=%d", len(gaps))
        return gaps

    def generate_follow_up_questions(self, gaps: list[KnowledgeGap]) -> list[str]:
        """Generate targeted follow-up research inquiries from identified knowledge gaps."""
        questions: list[str] = []
        for g in gaps:
            if g.recommended_research:
                questions.extend(g.recommended_research)
            else:
                questions.append(f"How can we empirically resolve: {g.description}?")
        return questions


gap_detector = GapDetector()
KnowledgeGapDetector = GapDetector
knowledge_gap_detector = gap_detector
