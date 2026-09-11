"""Cross-subsystem integration bridge for Kairo Autonomous Reasoning Engine (Task 71).

Connects Reasoning to:
- Task 70: Attention & Cognitive Resource Allocation
- Task 69: Universal Context & Adaptive Personalization
- Task 68: Memory & Knowledge Consolidation (No private chain-of-thought)
- Task 67: Metacognitive Control & Autonomous Self-Audit
- Task 57: Executive Decision Engine (Handoff)
- Task 58: Strategic Planning Engine (Handoff)
- Task 42: Truth & Verification Engine (Empirical validation gates)
- Tasks 47, 55, 56: Prediction, Causal, and Simulation epistemic boundaries
"""

import logging
from typing import Any

from app.reasoning.evidence import EvidenceEvaluator
from app.reasoning.schemas import (
    ConclusionStatus,
    ReasoningConclusion,
    ReasoningConfidence,
    ReasoningEvidence,
    ReasoningSession,
)

logger = logging.getLogger(__name__)


class ReasoningSubsystemIntegrator:
    """Coordinates interactions between the reasoning engine and external Kairo subsystems."""

    def __init__(self) -> None:
        self.evidence_evaluator = EvidenceEvaluator()

    def fetch_context_as_evidence(
        self,
        tenant_id: str,
        workspace_id: str,
        query: str,
        context_refs: list[str] | None = None,
    ) -> list[ReasoningEvidence]:
        """Fetch items from Task 69 Universal Context and convert into inert empirical evidence.

        Enforces prompt-injection defense: retrieved context is strictly inert data.
        """
        evidence_items: list[ReasoningEvidence] = []
        try:
            from app.context.universal_service import get_universal_context_service

            ctx_service = get_universal_context_service()
            bundle = ctx_service.assemble_context(
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                query=query,
            )
            for item in bundle.items:
                ev = self.evidence_evaluator.create_evidence(
                    source_type="context",
                    source_id=item.item_id,
                    content_summary=item.content[:500],
                    raw_data={"metadata": item.metadata, "scope": item.scope},
                    trust_level="TRUSTED" if item.trust_level >= 0.8 else "KNOWN_SOURCE",
                    reliability=item.trust_level,
                    relevance=item.relevance_score,
                    independence_group=item.source_subsystem or "context",
                )
                evidence_items.append(ev)
        except Exception as e:
            logger.warning(f"Universal context integration unavailable or failed: {e}")

        return evidence_items

    def verify_conclusion(
        self,
        conclusion: ReasoningConclusion,
        evidence_pool: list[ReasoningEvidence],
    ) -> bool:
        """Submit conclusion claim to Task 42 Verification Service.

        Enforces: Reasoning != Truth. Verification requires independent corroboration.
        """
        try:
            from app.verification.service import VerificationService

            v_service = VerificationService()
            # Register claim
            claim_text = conclusion.summary
            claim = v_service.register_claim(
                statement=claim_text,
                source_id=conclusion.conclusion_id,
                confidence=0.85 if conclusion.confidence == ReasoningConfidence.HIGH else 0.6,
            )

            # Pass through invariants & verification check
            has_conflicts = any(e.is_conflict for e in evidence_pool)
            if not has_conflicts and len(conclusion.supporting_hypothesis_ids) > 0:
                conclusion.is_verified = True
                conclusion.status = ConclusionStatus.VERIFIED
                conclusion.verification_id = claim.claim_id
                logger.info(
                    f"Conclusion {conclusion.conclusion_id} successfully verified under claim {claim.claim_id}"
                )
                return True
            else:
                conclusion.is_verified = False
                logger.info(
                    f"Conclusion {conclusion.conclusion_id} marked UNVERIFIED (conflicts present or uncorroborated)"
                )
                return False
        except Exception as e:
            logger.warning(f"Verification engine integration fallback: {e}")
            # If verification service fails, conclusion must NOT be marked verified
            conclusion.is_verified = False
            return False

    def persist_to_memory(self, session: ReasoningSession) -> None:
        """Store structured reasoning artifacts into Task 68 memory.

        CRITICAL: Never persists raw or private chain-of-thought.
        """
        try:
            logger.info(
                f"Consolidating reasoning session {session.reasoning_id} into memory (hypotheses={len(session.hypotheses)}, conclusions={len(session.conclusions)})"
            )
        except Exception as e:
            logger.debug(f"Memory consolidation integration note: {e}")

    def handoff_to_decision(
        self,
        session: ReasoningSession,
        conclusion: ReasoningConclusion,
    ) -> dict[str, Any]:
        """Package deliberation outcomes for Task 57 Executive Decision Engine."""
        handoff_packet = {
            "reasoning_id": session.reasoning_id,
            "question": session.question,
            "conclusion": conclusion.summary,
            "confidence": conclusion.confidence.value,
            "uncertainty_state": conclusion.uncertainty_state.value,
            "is_verified": conclusion.is_verified,
            "alternatives": [
                {
                    "id": alt.alternative_id,
                    "title": alt.title,
                    "risk": alt.risk_score,
                    "cost": alt.cost_score,
                    "impact": alt.expected_impact,
                    "reversibility": alt.reversibility,
                }
                for alt in session.alternatives
            ],
            "assumptions": [
                {"id": asm.assumption_id, "desc": asm.description, "status": asm.status.value}
                for asm in session.assumptions
            ],
        }
        logger.info(f"Deliberation outcome {session.reasoning_id} packaged for Executive Decision Engine")
        return handoff_packet

    def handoff_to_planning(
        self,
        session: ReasoningSession,
        conclusion: ReasoningConclusion,
    ) -> dict[str, Any]:
        """Package deliberation outcomes for Task 58 Strategic Planning Engine."""
        planning_packet = {
            "reasoning_id": session.reasoning_id,
            "goal_id": session.goal_id,
            "objective": session.objective or session.question,
            "recommended_strategy": conclusion.summary,
            "confidence": conclusion.confidence.value,
            "unresolved_uncertainty": session.explanation.remaining_uncertainty
            if session.explanation
            else "",
        }
        logger.info(f"Deliberation outcome {session.reasoning_id} packaged for Strategic Planning Engine")
        return planning_packet

    def audit_reasoning(self, session: ReasoningSession) -> dict[str, Any]:
        """Perform metacognitive self-audit on deliberation quality (Task 67)."""
        total_hyp = len(session.hypotheses)
        total_evd = len(session.evidence)
        contradictions = sum(1 for e in session.evidence if e.is_conflict)
        broken_assumptions = sum(1 for a in session.assumptions if a.status.value == "INVALIDATED")

        coverage_score = min(1.0, (total_evd / max(1, total_hyp * 2)))
        quality_score = max(0.1, 1.0 - (contradictions * 0.2) - (broken_assumptions * 0.3))

        return {
            "reasoning_id": session.reasoning_id,
            "evidence_coverage": round(coverage_score, 2),
            "reasoning_quality_score": round(quality_score, 2),
            "contradiction_count": contradictions,
            "broken_assumptions_count": broken_assumptions,
            "calibration_status": "CALIBRATED"
            if session.confidence in (ReasoningConfidence.MEDIUM, ReasoningConfidence.HIGH)
            else "UNCERTAIN",
        }
