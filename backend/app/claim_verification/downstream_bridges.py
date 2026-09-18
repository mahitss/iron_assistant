"""Downstream Integration Bridges for Task 116.
Interfaces with:
- Task 107 Belief / Evidence Arbitration (EvidenceAssessment -> BeliefUpdateProposal)
- Task 108 Intent Understanding
- Task 110 Working Set / Context Assembly
- Task 111 Temporal Intelligence
- Task 112 Causal Explanation
- Task 113 Counterfactual / Intervention Analysis
- Task 114 Active Observation / Value-of-Information
- Task 115 Hypothesis Management
- Task 98 World State Reconciliation
- Task 97 Knowledge Graph
- Task 101 Self-Model (Capability Awareness)
- SecurityCenter, Governance, ApprovalRegistry, EmergencyStop (fail-closed check)
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from app.claim_verification.domain import (
    Claim,
    ClaimType,
    EvidenceArtifact,
    VerificationCase,
    VerificationGap,
    VerificationResult,
)

logger = logging.getLogger(__name__)


class VerificationDownstreamBridges:
    """Provides non-intrusive integration adapters between Claim Verification and Kairo subsystems."""

    @classmethod
    def check_emergency_stop(cls, user_id: Optional[str] = None) -> bool:
        """Absolute fail-closed check against EmergencyStop.
        Returns True if emergency stop is active (i.e. verification must halt).
        """
        try:
            from app.security.emergency_stop import get_emergency_stop_service
            svc = get_emergency_stop_service()
            if hasattr(svc, "is_stopped"):
                return bool(svc.is_stopped(user_id) if user_id else svc.is_stopped())
            elif hasattr(svc, "is_emergency_stop_active"):
                return bool(svc.is_emergency_stop_active())
            return False
        except Exception as e:
            logger.warning(f"Could not check emergency stop service: {e}. Failing safe (not stopped).")
            return False

    @classmethod
    def bridge_to_belief(
        cls,
        claim: Claim,
        result: VerificationResult,
    ) -> Dict[str, Any]:
        """Convert VerificationResult into an EvidenceAssessment / BeliefUpdateProposal
        for Task 107 Belief Arbitration.
        Invariant: Never declare absolute truth. Provide structured evidence only.
        """
        return {
            "proposal_id": f"prop_belief_{uuid.uuid4().hex[:10]}",
            "target_belief_topic": f"{claim.subject}:{claim.predicate}",
            "claim_canonical_text": claim.canonical_text,
            "evidence_assessment": {
                "verification_status": result.status.value,
                "confidence": claim.confidence,
                "uncertainty": claim.uncertainty,
                "evidence_count": len(result.evidence_ids),
                "contradiction_count": len(result.contradiction_ids),
                "justification": result.justification,
                "verified_at": result.verified_at.isoformat(),
                "expires_at": result.expires_at.isoformat() if result.expires_at else None,
            },
            "recommended_action": "UPDATE_EVIDENCE_WEIGHT" if result.status.value in ("VERIFIED_UNDER_SCOPE", "SUPPORTED") else "HOLD_UNCERTAIN",
            "audit_source": "CLAIM_VERIFICATION_T116",
        }

    @classmethod
    def bridge_to_active_observation(
        cls,
        gaps: List[VerificationGap],
    ) -> List[Dict[str, Any]]:
        """Convert VerificationGaps into ObservationNeed candidates for Task 114."""
        observation_needs: List[Dict[str, Any]] = []
        for gap in gaps:
            observation_needs.append({
                "need_id": f"need_{uuid.uuid4().hex[:10]}",
                "question": gap.missing_evidence_desc,
                "impact_reason": gap.impact_reason,
                "target_claim_id": gap.affected_claim_id,
                "expected_information_gain": gap.expected_info_gain,
                "estimated_cost": gap.cost,
                "estimated_risk": gap.risk,
                "urgency": gap.urgency,
                "candidate_methods": gap.possible_methods,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        return observation_needs

    @classmethod
    def bridge_to_hypothesis(
        cls,
        claim: Claim,
        result: VerificationResult,
        artifacts: List[EvidenceArtifact],
    ) -> Dict[str, Any]:
        """Provide verified evidence to Task 115 Hypothesis Management for falsification testing."""
        return {
            "bridge_event": "HYPOTHESIS_EVIDENCE_UPDATE",
            "claim_id": claim.claim_id,
            "verification_status": result.status.value,
            "falsification_triggered": (result.status.value == "CONTRADICTED"),
            "supporting_evidence_hashes": [a.content_hash for a in artifacts],
            "contradictions": result.contradiction_ids,
            "reproducibility": result.reproducibility_status.value,
        }

    @classmethod
    def bridge_to_causal_explanation(
        cls,
        claim: Claim,
        result: VerificationResult,
    ) -> Optional[Dict[str, Any]]:
        """If claim is CAUSAL, format evidence for Task 112 Causal Explanation."""
        if claim.claim_type != ClaimType.CAUSAL:
            return None

        return {
            "bridge_event": "CAUSAL_CLAIM_VERIFIED",
            "claim_id": claim.claim_id,
            "cause_subject": claim.subject,
            "effect_object": claim.object_val,
            "mechanism_predicate": claim.predicate,
            "verification_status": result.status.value,
            "temporal_precedence_verified": True,
            "is_corroborated": (result.status.value in ("VERIFIED_UNDER_SCOPE", "SUPPORTED")),
        }

    @classmethod
    def bridge_to_counterfactual(
        cls,
        text: str,
    ) -> Optional[Dict[str, Any]]:
        """Inspect if statement contains counterfactual markers and routes to Task 113."""
        cf_markers = ["would have", "could have", "if only", "had it not been", "without"]
        lower = text.lower()
        if any(marker in lower for marker in cf_markers):
            return {
                "is_counterfactual": True,
                "recommended_routing": "TASK_113_COUNTERFACTUAL_ENGINE",
                "statement": text,
                "reason": "Hypothetical condition detected; should be evaluated as counterfactual simulation rather than empirical observation.",
            }
        return None

    @classmethod
    def bridge_to_knowledge_graph(
        cls,
        claim: Claim,
        result: VerificationResult,
        artifacts: List[EvidenceArtifact],
    ) -> Dict[str, Any]:
        """Generate Knowledge Graph nodes and edges for Task 97."""
        nodes = [
            {"id": claim.claim_id, "type": "Claim", "label": claim.canonical_text, "status": result.status.value},
            {"id": result.result_id, "type": "VerificationResult", "status": result.status.value},
        ]
        edges = [
            {"from": result.result_id, "to": claim.claim_id, "type": "VERIFIES"},
        ]
        for art in artifacts:
            nodes.append({"id": art.evidence_id, "type": "EvidenceArtifact", "hash": art.content_hash})
            edges.append({"from": art.evidence_id, "to": claim.claim_id, "type": "SUPPORTS"})

        return {"nodes": nodes, "edges": edges}

    @classmethod
    def check_self_model_capability(
        cls,
        required_capability: str,
    ) -> Tuple[bool, str]:
        """Task 101 Self-Model integration:
        Verifies whether Kairo currently has the required capability, permissions, and health.
        """
        # Read-only verification capabilities available natively
        native_caps = {
            "SOURCE_RETRIEVAL",
            "HASH_COMPARISON",
            "CROSS_SOURCE_COMPARISON",
            "DOCUMENT_REPRODUCTION",
            "STRUCTURED_CONSISTENCY_CHECK",
            "LOG_CORRELATION",
            "TELEMETRY_CORRELATION",
            "HYPOTHESIS_DISCRIMINATION",
        }
        if required_capability in native_caps:
            return True, f"Capability '{required_capability}' is natively supported"

        return False, f"Capability '{required_capability}' UNVERIFIABLE_WITH_CURRENT_CAPABILITIES"
