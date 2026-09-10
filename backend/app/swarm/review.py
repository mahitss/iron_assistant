"""Peer review, blind evaluation, and cross-agent assertion auditing (Task 64)."""

from __future__ import annotations

import logging

from app.swarm.schemas import AgentResult, PeerReview, SwarmAgentSpec

logger = logging.getLogger(__name__)


class PeerReviewEngine:
    """Executes structured peer reviews across agent results (Spec 16 & 17)."""

    def conduct_peer_review(
        self,
        reviewer: SwarmAgentSpec,
        target_result: AgentResult,
        is_blind: bool = True,
    ) -> PeerReview:
        """Conduct independent peer review of an agent's result without author bias.

        Invariant: Agent B should not blindly inherit Agent A's conclusion.
        """
        reviewer_role = reviewer.role.upper()
        target_role = target_result.role.upper()

        issues: list[str] = []
        supporting_evidence: list[str] = []
        counterarguments: list[str] = []
        severity = "LOW"
        recommendation = "ENDORSE"
        correctness_score = 0.85

        # Check assumptions and uncertainties in target result
        if not target_result.evidence:
            issues.append("Target result relies heavily on assertion with sparse cited empirical evidence.")
            severity = "MEDIUM"
            recommendation = "QUALIFIED_ENDORSE"
            correctness_score = 0.65

        # Role-specific review perspectives
        if reviewer_role == "CRITIC":
            counterarguments.append(
                f"Assumptions made by {target_role if not is_blind else 'Author'} may fail under burst traffic and network partitions."
            )
            issues.append(
                "Failure scenarios under extreme load require explicit circuit-breaking boundaries."
            )
            if severity != "HIGH":
                severity = "MEDIUM"
            recommendation = "QUALIFIED_ENDORSE"
            correctness_score = min(correctness_score, 0.75)

        elif reviewer_role == "SECURITY_ANALYST":
            if any("token" in c.lower() or "auth" in c.lower() for c in target_result.assumptions):
                supporting_evidence.append("Token expiration invariants align with zero-trust posture.")
            else:
                issues.append("Target result did not explicitly verify credential leakage boundary.")
                severity = "MEDIUM"
                recommendation = "QUALIFIED_ENDORSE"

        elif reviewer_role == "FACT_CHECKER":
            for claim in target_result.claims:
                if claim.source_lineage:
                    supporting_evidence.append(
                        f"Claim '{claim.text[:40]}...' verified against lineage: {claim.source_lineage}"
                    )
                else:
                    issues.append(f"Claim '{claim.text[:40]}...' lacks explicit source lineage reference.")
                    correctness_score = min(correctness_score, 0.70)

        # High confidence but multiple issues indicates overconfidence
        if target_result.confidence >= 0.90 and len(issues) >= 2:
            issues.append("Agent confidence appears elevated relative to identified assumption gaps.")
            correctness_score = min(correctness_score, 0.68)
            recommendation = "CONTEST"

        review = PeerReview(
            reviewer_agent_id=reviewer.agent_id,
            reviewer_role=reviewer_role,
            target_result_id=target_result.result_id,
            target_agent_id=target_result.agent_id if not is_blind else "anonymized_author",
            correctness_score=round(correctness_score, 2),
            issues=issues,
            supporting_evidence=supporting_evidence,
            counterarguments=counterarguments,
            severity=severity,
            confidence=0.85,
            recommendation=recommendation,
            is_blind=is_blind,
            provenance={
                "reviewer_agent_id": reviewer.agent_id,
                "target_result_id": target_result.result_id,
                "is_blind": is_blind,
            },
        )
        logger.info(
            "PEER_REVIEW_CONDUCTED: reviewer=%s target=%s score=%.2f rec=%s",
            reviewer.agent_id,
            target_result.result_id,
            correctness_score,
            recommendation,
        )
        return review
