"""Impact assessment, blast radius analysis, and controlled invalidation engine for Task 117.

Answers:
- What is the blast radius if a source or evidence changes?
- What becomes invalid if a source changes?
- What becomes stale if evidence expires?
- Which downstream decisions, beliefs, missions, and hypotheses require revalidation?
- Can this verification result or evidence be safely reused?

Core Principle: Controlled propagation without silent truth destruction.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import uuid

from app.evidence_graph.domain import (
    EvidenceGraphEdge,
    EvidenceGraphEdgeType,
    EvidenceGraphNode,
    EvidenceGraphNodeType,
    FreshnessState,
    ImpactAssessment,
    ImpactSeverity,
    IntegrityState,
    RevalidationCandidate,
    RevalidationRecommendation,
)
from app.evidence_graph.traversal_engine import TraversalEngine

logger = logging.getLogger(__name__)


class ImpactEngine:
    """Blast radius, controlled invalidation, and revalidation candidate generator."""

    def __init__(self, traversal_engine: Optional[TraversalEngine] = None):
        self.traversal = traversal_engine or TraversalEngine()

    def assess_blast_radius(
        self,
        root_node_id: str,
        cause_reason: str,
        get_node_fn: Callable[[str], Optional[EvidenceGraphNode]],
        get_outgoing_edges_fn: Callable[[str], List[EvidenceGraphEdge]],
        get_incoming_edges_fn: Callable[[str], List[EvidenceGraphEdge]],
        max_depth: int = 10,
        max_nodes: int = 200,
    ) -> ImpactAssessment:
        """Calculate the full downstream blast radius of an invalidation, mutation, or staleness event."""
        root_node = get_node_fn(root_node_id)
        root_type = root_node.node_type.value if root_node else "UNKNOWN"

        traversal_result = self.traversal.traverse_downstream(
            start_node_id=root_node_id,
            get_node_fn=get_node_fn,
            get_outgoing_edges_fn=get_outgoing_edges_fn,
            get_incoming_edges_fn=get_incoming_edges_fn,
            max_depth=max_depth,
            max_nodes=max_nodes,
        )

        direct_impacts: List[Dict[str, Any]] = []
        indirect_impacts: List[Dict[str, Any]] = []
        impacted_claims: List[str] = []
        impacted_verifications: List[str] = []
        impacted_beliefs: List[str] = []
        impacted_decisions: List[str] = []
        impacted_missions: List[str] = []
        impacted_situations: List[str] = []
        impacted_hypotheses: List[str] = []
        impacted_memories: List[str] = []
        impacted_strategies: List[str] = []
        impacted_self_models: List[str] = []
        revalidation_candidates: List[RevalidationCandidate] = []

        for node_dict in traversal_result["nodes"]:
            nid = node_dict["node_id"]
            if nid == root_node_id:
                continue

            ntype = node_dict.get("node_type", "")
            depth = 1  # will estimate from path if needed

            # Check if directly connected to root
            is_direct = any(
                e["source_node_id"] == root_node_id or e["target_node_id"] == root_node_id
                for e in traversal_result["edges"]
                if (e["source_node_id"] == nid or e["target_node_id"] == nid)
            )

            severity = ImpactSeverity.DIRECT if is_direct else ImpactSeverity.INDIRECT
            impact_entry = {
                "node_id": nid,
                "node_type": ntype,
                "severity": severity.value,
                "reason": f"Downstream dependent on {root_node_id} ({cause_reason})",
            }

            if is_direct:
                direct_impacts.append(impact_entry)
            else:
                indirect_impacts.append(impact_entry)

            # Categorize downstream objects by architectural domain
            if ntype in {EvidenceGraphNodeType.CLAIM.value, EvidenceGraphNodeType.CLAIM_FRAGMENT.value}:
                impacted_claims.append(nid)
            elif ntype in {EvidenceGraphNodeType.VERIFICATION_CASE.value, EvidenceGraphNodeType.VERIFICATION_RESULT.value}:
                impacted_verifications.append(nid)
            elif ntype == EvidenceGraphNodeType.BELIEF.value:
                impacted_beliefs.append(nid)
            elif ntype == EvidenceGraphNodeType.DECISION.value:
                impacted_decisions.append(nid)
            elif ntype == EvidenceGraphNodeType.MISSION.value:
                impacted_missions.append(nid)
            elif ntype == EvidenceGraphNodeType.SITUATION.value:
                impacted_situations.append(nid)
            elif ntype == EvidenceGraphNodeType.HYPOTHESIS.value:
                impacted_hypotheses.append(nid)
            elif ntype == EvidenceGraphNodeType.MEMORY.value:
                impacted_memories.append(nid)
            elif ntype == EvidenceGraphNodeType.STRATEGY.value:
                impacted_strategies.append(nid)
            elif ntype == EvidenceGraphNodeType.SELF_MODEL_ASSERTION.value:
                impacted_self_models.append(nid)

            # Recommend next step for revalidation candidate
            recommendation = RevalidationRecommendation.REVALIDATE_NOW if is_direct else RevalidationRecommendation.REVALIDATE_LATER
            if ntype in {EvidenceGraphNodeType.DECISION.value, EvidenceGraphNodeType.MISSION.value}:
                recommendation = RevalidationRecommendation.ESCALATE

            candidate = RevalidationCandidate(
                candidate_id=f"reval-{uuid.uuid4().hex[:12]}",
                affected_node_id=nid,
                affected_node_type=ntype,
                reason=f"Upstream cause {root_node_id}: {cause_reason}",
                upstream_cause_id=root_node_id,
                severity=severity,
                freshness_state=FreshnessState.STALE,
                decision_impact=f"Decision affected: {nid}" if ntype == EvidenceGraphNodeType.DECISION.value else None,
                mission_impact=f"Mission affected: {nid}" if ntype == EvidenceGraphNodeType.MISSION.value else None,
                resource_estimate=1.5 if is_direct else 0.8,
                expected_information_value=0.9 if is_direct else 0.6,
                recommended_next_step=recommendation,
                required_capability=f"verify_{ntype.lower()}",
            )
            revalidation_candidates.append(candidate)

        overall_severity = ImpactSeverity.DIRECT if direct_impacts else (
            ImpactSeverity.INDIRECT if indirect_impacts else ImpactSeverity.UNKNOWN
        )

        return ImpactAssessment(
            target_node_id=root_node_id,
            target_node_type=root_type,
            root_cause_node_id=root_node_id,
            cause_reason=cause_reason,
            severity=overall_severity,
            direct_impacts=direct_impacts,
            indirect_impacts=indirect_impacts,
            impacted_claims=impacted_claims,
            impacted_verifications=impacted_verifications,
            impacted_beliefs=impacted_beliefs,
            impacted_decisions=impacted_decisions,
            impacted_missions=impacted_missions,
            impacted_situations=impacted_situations,
            impacted_hypotheses=impacted_hypotheses,
            impacted_memories=impacted_memories,
            impacted_strategies=impacted_strategies,
            impacted_self_models=impacted_self_models,
            revalidation_candidates=revalidation_candidates,
        )

    def validate_evidence_reuse(
        self,
        evidence_node: EvidenceGraphNode,
        target_scope: Dict[str, Any],
        max_age_seconds: int = 86400 * 7,  # 7 days
    ) -> Dict[str, Any]:
        """Verify whether an evidence node can be safely reused without revalidation."""
        # 1. Freshness check
        if evidence_node.freshness_state in {FreshnessState.INVALID, FreshnessState.EXPIRED, FreshnessState.STALE}:
            return {
                "reusable": False,
                "status": "REVALIDATION_REQUIRED",
                "reason": f"Evidence is in {evidence_node.freshness_state.value} state",
            }

        # 2. Age check
        now = datetime.now(timezone.utc)
        try:
            created = datetime.fromisoformat(evidence_node.created_at.replace("Z", "+00:00"))
            age = (now - created).total_seconds()
            if age > max_age_seconds:
                return {
                    "reusable": False,
                    "status": "REVALIDATION_REQUIRED",
                    "reason": f"Evidence age ({int(age)}s) exceeds max allowed age ({max_age_seconds}s)",
                }
        except Exception:
            pass

        # 3. Integrity check
        if evidence_node.integrity_state in {
            IntegrityState.HASH_MISMATCH,
            IntegrityState.MUTATED,
            IntegrityState.CORRUPTED,
        }:
            return {
                "reusable": False,
                "status": "REVALIDATION_REQUIRED",
                "reason": f"Evidence integrity state is compromised: {evidence_node.integrity_state.value}",
            }

        # 4. Scope match check
        ev_scope = evidence_node.temporal_scope or {}
        if target_scope:
            for k, v in target_scope.items():
                if k in ev_scope and ev_scope[k] != v and v is not None:
                    return {
                        "reusable": False,
                        "status": "REVALIDATION_REQUIRED",
                        "reason": f"Scope mismatch on key '{k}': target={v} vs evidence={ev_scope[k]}",
                    }

        return {
            "reusable": True,
            "status": "REUSABLE",
            "reason": "Evidence satisfies freshness, integrity, and scope compatibility requirements",
        }
