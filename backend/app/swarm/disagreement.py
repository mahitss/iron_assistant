"""Disagreement detection and 10-class taxonomy root-cause classification (Task 64)."""

from __future__ import annotations

import logging

from app.swarm.schemas import (
    AgentResult,
    DisagreementRecord,
    DisagreementType,
    PeerReview,
)

logger = logging.getLogger(__name__)


class DisagreementDetector:
    """Detects, isolates, and classifies disagreements between specialized agents (Spec 18 & 19)."""

    def detect_disagreements(
        self,
        results: list[AgentResult],
        reviews: list[PeerReview],
    ) -> list[DisagreementRecord]:
        """Examine agent results and peer reviews to detect and classify root-cause disagreements.

        Invariant: AGENT AGREEMENT != TRUTH. Preserve disagreements rather than collapsing to naive voting.
        """
        disagreements: list[DisagreementRecord] = []

        # 1. Detect conflicts from critical peer reviews
        for rev in reviews:
            if (
                rev.counterarguments
                or rev.recommendation in ("CONTEST", "REJECT")
                or rev.severity in ("MEDIUM", "HIGH")
            ):
                target_result = next((r for r in results if r.result_id == rev.target_result_id), None)
                if not target_result:
                    continue

                category = self._classify_disagreement_nature(rev.issues, rev.counterarguments, target_result)
                issue_summary = (
                    rev.counterarguments[0]
                    if rev.counterarguments
                    else (rev.issues[0] if rev.issues else "Conflicting assessment")
                )

                record = DisagreementRecord(
                    category=category,
                    issue=issue_summary,
                    involved_agent_ids=[rev.reviewer_agent_id, target_result.agent_id],
                    positions={
                        target_result.agent_id: target_result.answer,
                        rev.reviewer_agent_id: "; ".join(rev.counterarguments) or "; ".join(rev.issues),
                    },
                    root_cause_explanation=f"Reviewer {rev.reviewer_role} identified divergent {category.value.lower()} constraints in {target_result.role}'s proposal.",
                    severity=rev.severity,
                    status="DETECTED",
                )
                disagreements.append(record)

        # 2. Detect cross-claim contradictions across results
        for i in range(len(results)):
            for j in range(i + 1, len(results)):
                r1, r2 = results[i], results[j]
                if self._claims_contradict(r1, r2):
                    category = self._classify_cross_result_disagreement(r1, r2)
                    record = DisagreementRecord(
                        category=category,
                        issue=f"Divergent position between {r1.role} and {r2.role}",
                        involved_agent_ids=[r1.agent_id, r2.agent_id],
                        positions={
                            r1.agent_id: r1.answer,
                            r2.agent_id: r2.answer,
                        },
                        root_cause_explanation=f"Agents hold opposing conclusions based on differing {category.value.lower()} assessments.",
                        severity="HIGH"
                        if category in (DisagreementType.CAUSAL, DisagreementType.FACTUAL)
                        else "MEDIUM",
                        status="DETECTED",
                    )
                    disagreements.append(record)

        logger.info("DISAGREEMENTS_DETECTED: total=%d", len(disagreements))
        return disagreements

    def _claims_contradict(self, r1: AgentResult, r2: AgentResult) -> bool:
        """Check if two agents' recommendations or claims are substantively contradictory."""
        # Critic vs Architect inherently flags an operational contradiction
        if (r1.role == "ARCHITECT" and r2.role == "CRITIC") or (
            r1.role == "CRITIC" and r2.role == "ARCHITECT"
        ):
            return True

        text1 = r1.answer.lower()
        text2 = r2.answer.lower()
        # Direct linguistic contradiction checks
        contradiction_markers = [
            ("satisfies", "stall"),
            ("scales", "bottleneck"),
            ("sub-10ms", "delayed"),
            ("feasible", "unfeasible"),
            ("secure", "vulnerable"),
        ]
        for pos, neg in contradiction_markers:
            if (pos in text1 and neg in text2) or (pos in text2 and neg in text1):
                return True
        return False

    def _classify_disagreement_nature(
        self,
        issues: list[str],
        counterarguments: list[str],
        target_result: AgentResult,
    ) -> DisagreementType:
        """Classify root cause into the 10-class taxonomy."""
        all_text = " ".join(issues + counterarguments).lower()

        if "cause" in all_text or "correlation" in all_text or "causation" in all_text:
            return DisagreementType.CAUSAL
        if "assumption" in all_text or "assumes" in all_text:
            return DisagreementType.ASSUMPTION
        if (
            "evidence" in all_text
            or "source" in all_text
            or "citation" in all_text
            or "sparse" in all_text
            or "empirical" in all_text
        ):
            return DisagreementType.EVIDENCE
        if "fact" in all_text or "benchmark" in all_text or "measured" in all_text:
            return DisagreementType.FACTUAL
        if "interpretation" in all_text or "meaning" in all_text:
            return DisagreementType.INTERPRETATION
        if "time" in all_text or "latency" in all_text or "timeout" in all_text or "short-term" in all_text:
            return DisagreementType.TEMPORAL
        if "scope" in all_text or "boundary" in all_text or "limits" in all_text:
            return DisagreementType.SCOPE
        if "model" in all_text or "simulation" in all_text:
            return DisagreementType.MODEL
        if "objective" in all_text or "priority" in all_text:
            return DisagreementType.OBJECTIVE
        return DisagreementType.PREFERENCE

    def _classify_cross_result_disagreement(self, r1: AgentResult, r2: AgentResult) -> DisagreementType:
        """Classify cross-agent disagreement between two results."""
        if r1.assumptions != r2.assumptions and (
            not r1.assumptions or not r2.assumptions or set(r1.assumptions) != set(r2.assumptions)
        ):
            return DisagreementType.ASSUMPTION
        if r1.role == "CRITIC" or r2.role == "CRITIC":
            return DisagreementType.CAUSAL
        return DisagreementType.EVIDENCE
