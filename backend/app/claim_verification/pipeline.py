"""Verification Pipeline Engine for Task 116.
Implements the deterministic 25-step Claim Verification lifecycle,
state transitions, uncertainty computation, and explanation tree generation.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple
import uuid

from app.claim_verification.corroboration_engine import CorroborationEngine
from app.claim_verification.domain import (
    Claim,
    ContradictionRecord,
    CorroborationGroup,
    CorroborationType,
    EvidenceArtifact,
    EvidenceQualityProfile,
    EvidenceTransformation,
    IndependenceAssessment,
    IntegrityCheck,
    ProvenanceLink,
    ProvenancePredicate,
    ReproducibilityStatus,
    ReproductionAttempt,
    Source,
    SourceRelationship,
    SourceSnapshot,
    VerificationCase,
    VerificationCaseStatus,
    VerificationEvent,
    VerificationGap,
    VerificationMethod,
    VerificationMethodType,
    VerificationResult,
    VerificationSnapshot,
)
from app.claim_verification.downstream_bridges import VerificationDownstreamBridges
from app.claim_verification.fragmentation_engine import ClaimFragmentationEngine
from app.claim_verification.integrity_engine import ContentIntegrityEngine
from app.claim_verification.provenance_engine import ProvenanceEngine
from app.claim_verification.reproducibility_engine import ReproducibilityEngine
from app.claim_verification.staleness_and_cache import StalenessAndCacheEngine

logger = logging.getLogger(__name__)


class VerificationPipeline:
    """Orchestrates the complete 25-step deterministic verification pipeline."""

    def __init__(self, event_emitter: Optional[Callable[[VerificationEvent], None]] = None) -> None:
        self.event_emitter = event_emitter

    def _emit(self, case: VerificationCase, event_type: str, payload: Dict[str, Any], actor: str = "system") -> None:
        event = VerificationEvent(
            event_id=f"evt_{uuid.uuid4().hex[:10]}",
            case_id=case.case_id,
            event_type=event_type,
            actor=actor,
            correlation_id=case.correlation_id,
            causation_id=None,
            payload=payload,
            timestamp=datetime.now(timezone.utc),
        )
        if self.event_emitter:
            try:
                self.event_emitter(event)
            except Exception as e:
                logger.error(f"Failed to emit verification event: {e}")

    def execute_pipeline(
        self,
        case: VerificationCase,
        claim_text: str,
        sources: List[Source],
        snapshots: List[SourceSnapshot],
        evidence_artifacts: List[EvidenceArtifact],
        transformations: Optional[List[EvidenceTransformation]] = None,
        existing_links: Optional[List[ProvenanceLink]] = None,
        user_id: Optional[str] = None,
    ) -> Tuple[VerificationResult, Dict[str, Any]]:
        """Run the full 25-step verification procedure."""
        transformations = transformations or []
        links = existing_links or []
        explanation_tree: Dict[str, Any] = {}

        # 1. Receive verification request
        case.status = VerificationCaseStatus.REQUESTED
        self._emit(case, "verification.requested", {"title": case.title})

        # Emergency Stop Check (Section 45: absolute fail-closed)
        if VerificationDownstreamBridges.check_emergency_stop(user_id):
            case.status = VerificationCaseStatus.FAILED
            case.resolution_summary = "EmergencyStop active; all verification halted"
            res = VerificationResult(
                result_id=f"res_{uuid.uuid4().hex[:10]}",
                case_id=case.case_id,
                claim_id=case.claim_id,
                status=VerificationCaseStatus.FAILED,
                scope=case.scope,
                justification="EmergencyStop is active. All execution and verification operations halted.",
                evidence_ids=[],
                contradiction_ids=[],
                method_types=[],
                uncertainty_profile={"emergency_stop": True},
                gaps=[],
                reproducibility_status=ReproducibilityStatus.NOT_ATTEMPTED,
                validity_window_start=None,
                validity_window_end=None,
                verified_at=datetime.now(timezone.utc),
                expires_at=None,
            )
            return res, {"error": "EmergencyStop active"}

        # 2. Normalize scope
        case.status = VerificationCaseStatus.SCOPED
        self._emit(case, "verification.scoped", {"scope": case.scope})

        # 3. Parse claims & fragmentation
        claim = ClaimFragmentationEngine.decompose_claim(
            text=claim_text,
            temporal_scope=case.scope.get("temporal"),
            spatial_scope=case.scope.get("spatial"),
            entity_scope=case.scope.get("entities", []),
            source_scope=case.scope.get("sources"),
            claim_id=case.claim_id,
        )
        case.status = VerificationCaseStatus.CLAIM_PARSED
        self._emit(case, "claim.parsed", {
            "claim_id": claim.claim_id,
            "claim_type": claim.claim_type.value,
            "fragment_count": len(claim.fragments),
        })

        # 4. Resolve relevant entities
        resolved_entities = claim.entity_scope or ([claim.subject] if claim.subject else [])

        # 5. Retrieve existing evidence
        case.status = VerificationCaseStatus.EVIDENCE_COLLECTED
        self._emit(case, "evidence.collected", {"evidence_count": len(evidence_artifacts)})

        # 6. Inspect provenance & construct links
        case.status = VerificationCaseStatus.PROVENANCE_ANALYZING
        for art in evidence_artifacts:
            # Link from artifact to source
            links.append(
                ProvenanceEngine.create_link(
                    from_type="EvidenceArtifact",
                    from_id=art.evidence_id,
                    to_type="Source",
                    to_id=art.source_id,
                    predicate=ProvenancePredicate.EXTRACTED_FROM,
                )
            )
            if art.snapshot_id:
                links.append(
                    ProvenanceEngine.create_link(
                        from_type="EvidenceArtifact",
                        from_id=art.evidence_id,
                        to_type="SourceSnapshot",
                        to_id=art.snapshot_id,
                        predicate=ProvenancePredicate.DERIVED_FROM,
                    )
                )

        # 7. Check integrity
        case.status = VerificationCaseStatus.INTEGRITY_CHECKING
        integrity_checks: List[IntegrityCheck] = []
        for snap in snapshots:
            integrity_checks.append(ContentIntegrityEngine.verify_snapshot_integrity(snap))
        for art in evidence_artifacts:
            integrity_checks.append(ContentIntegrityEngine.verify_artifact_integrity(art))

        all_integrity_passed = all(ic.passed for ic in integrity_checks)
        self._emit(case, "integrity.checked", {"all_passed": all_integrity_passed, "check_count": len(integrity_checks)})

        # 8. Check freshness
        is_fresh = True
        now = datetime.now(timezone.utc)
        for snap in snapshots:
            if snap.expired_at and now > snap.expired_at:
                is_fresh = False

        # 9. Detect source dependencies & copy detection
        relationships: List[SourceRelationship] = []
        for i in range(len(sources)):
            for j in range(i + 1, len(sources)):
                s_a, s_b = sources[i], sources[j]
                arts_a = [a for a in evidence_artifacts if a.source_id == s_a.source_id]
                arts_b = [a for a in evidence_artifacts if a.source_id == s_b.source_id]
                rel = ProvenanceEngine.detect_copy_and_derivation(s_a, s_b, arts_a, arts_b)
                if rel:
                    relationships.append(rel)
                    self._emit(case, "source.relationship.detected", {
                        "relationship_type": rel.relationship_type.value,
                        "source_a": rel.source_a_id,
                        "source_b": rel.source_b_id,
                    })

        # 10. Compare supporting evidence & assess true independence
        case.status = VerificationCaseStatus.CORROBORATING
        source_ids = [s.source_id for s in sources]
        independence = ProvenanceEngine.assess_source_independence(source_ids, relationships, links)
        corrob_group = CorroborationEngine.evaluate_corroboration(
            case_id=case.case_id,
            claim=claim,
            artifacts=evidence_artifacts,
            sources=sources,
            independence=independence,
        )
        self._emit(case, "corroboration.assessed", {
            "corroboration_type": corrob_group.corroboration_type.value,
            "independence_score": independence.independence_score,
        })

        # 11. Search contradictions
        case.status = VerificationCaseStatus.CONTRADICTION_CHECKING
        contradictions = CorroborationEngine.detect_contradictions(
            case_id=case.case_id,
            claim=claim,
            artifacts=evidence_artifacts,
        )
        if contradictions:
            self._emit(case, "contradiction.detected", {"contradiction_count": len(contradictions)})

        # 12. Identify missing evidence & verification gaps
        gaps = StalenessAndCacheEngine.identify_verification_gaps(
            case_id=case.case_id,
            claim=claim,
            artifacts=evidence_artifacts,
        )

        # 13. Determine whether reproduction is possible
        case.status = VerificationCaseStatus.REPRODUCING
        reproduction_attempts: List[ReproductionAttempt] = []
        if evidence_artifacts:
            # Perform deterministic hash check reproduction
            sample_art = evidence_artifacts[0]
            repro = ReproducibilityEngine.record_attempt(
                case_id=case.case_id,
                method="HASH_COMPARISON",
                input_data=sample_art.content_text,
                output_data=sample_art.content_text,
                expected_output_hash=sample_art.content_hash,
                deterministic=True,
                notes="Content artifact SHA-256 hash verified",
            )
            reproduction_attempts.append(repro)

        overall_repro = ReproducibilityEngine.evaluate_overall_reproducibility(reproduction_attempts)

        # 14. Generate verification methods
        applied_methods = [
            VerificationMethodType.HASH_COMPARISON.value,
            VerificationMethodType.CROSS_SOURCE_COMPARISON.value,
            VerificationMethodType.STRUCTURED_CONSISTENCY_CHECK.value,
        ]

        # 15. Check capability awareness (Task 101 Self-Model)
        for m in applied_methods:
            cap_ok, cap_msg = VerificationDownstreamBridges.check_self_model_capability(m)
            if not cap_ok:
                logger.warning(cap_msg)

        # 16-18. Decide Final Status
        case.status = VerificationCaseStatus.VERIFYING
        final_status = VerificationCaseStatus.UNKNOWN

        if not all_integrity_passed:
            final_status = VerificationCaseStatus.CONTRADICTED
            justification = "Integrity check failed: detected content drift or hash mismatch in source evidence artifacts."
        elif contradictions:
            final_status = VerificationCaseStatus.CONTRADICTED
            justification = f"Contradictions detected: {contradictions[0].description}"
        elif not is_fresh:
            final_status = VerificationCaseStatus.STALE
            justification = "Evidence source snapshot has expired; revalidation is required."
        elif corrob_group.corroboration_type == CorroborationType.SEMANTIC_MISMATCH:
            final_status = VerificationCaseStatus.INCONCLUSIVE
            justification = "Evidence artifacts do not semantically match the subject/predicate of the claim."
        elif corrob_group.corroboration_type == CorroborationType.DEPENDENT_SUPPORT:
            final_status = VerificationCaseStatus.PARTIALLY_VERIFIED
            justification = f"Claim supported by evidence, but sources are dependent/copied ({independence.justification}). Cannot grant independent verification."
        elif corrob_group.corroboration_type == CorroborationType.INDEPENDENT_SUPPORT and not gaps:
            final_status = VerificationCaseStatus.VERIFIED_UNDER_SCOPE
            justification = "Claim is verified under specified temporal and entity scope with multiple independent corroborating sources."
        elif corrob_group.corroboration_type in (CorroborationType.INDEPENDENT_SUPPORT, CorroborationType.PARTIAL_SUPPORT):
            final_status = VerificationCaseStatus.SUPPORTED
            justification = f"Claim is supported by evidence, with {len(gaps)} unresolved information gap(s)."
        elif not evidence_artifacts:
            final_status = VerificationCaseStatus.UNVERIFIABLE
            justification = "Zero evidence artifacts available for evaluation."
        else:
            final_status = VerificationCaseStatus.INCONCLUSIVE
            justification = "Available evidence is insufficient to decisively verify or contradict the claim."

        case.status = final_status
        case.resolution_summary = justification

        # 19-21. Downstream bridge outputs
        proposal = VerificationDownstreamBridges.bridge_to_belief(
            claim=claim,
            result=VerificationResult(
                result_id=f"res_{uuid.uuid4().hex[:10]}",
                case_id=case.case_id,
                claim_id=claim.claim_id,
                status=final_status,
                scope=case.scope,
                justification=justification,
                evidence_ids=[a.evidence_id for a in evidence_artifacts],
                contradiction_ids=[c.contradiction_id for c in contradictions],
                method_types=applied_methods,
                uncertainty_profile={"confidence": claim.confidence, "uncertainty": claim.uncertainty},
                gaps=[g.gap_id for g in gaps],
                reproducibility_status=overall_repro,
                validity_window_start=now,
                validity_window_end=now + timedelta(days=7),
                verified_at=now,
                expires_at=now + timedelta(days=7),
            ),
        )

        # 22. Produce final VerificationResult
        res_id = f"res_{uuid.uuid4().hex[:10]}"
        result = VerificationResult(
            result_id=res_id,
            case_id=case.case_id,
            claim_id=claim.claim_id,
            status=final_status,
            scope=case.scope,
            justification=justification,
            evidence_ids=[a.evidence_id for a in evidence_artifacts],
            contradiction_ids=[c.contradiction_id for c in contradictions],
            method_types=applied_methods,
            uncertainty_profile={
                "confidence": claim.confidence if final_status in (VerificationCaseStatus.VERIFIED_UNDER_SCOPE, VerificationCaseStatus.SUPPORTED) else 0.3,
                "uncertainty": 0.1 if final_status == VerificationCaseStatus.VERIFIED_UNDER_SCOPE else 0.7,
                "independence_score": independence.independence_score,
                "gap_count": len(gaps),
            },
            gaps=[g.gap_id for g in gaps],
            reproducibility_status=overall_repro,
            validity_window_start=now,
            validity_window_end=now + timedelta(days=7),
            verified_at=now,
            expires_at=now + timedelta(days=7),
        )

        # 24. Emit events
        self._emit(case, "verification.completed", {
            "result_id": result.result_id,
            "status": final_status.value,
            "justification": justification,
        })

        # 25. Expose explanation tree
        explanation_tree = {
            "case_id": case.case_id,
            "claim": {
                "id": claim.claim_id,
                "text": claim.canonical_text,
                "type": claim.claim_type.value,
                "subject": claim.subject,
                "predicate": claim.predicate,
                "object": claim.object_val,
                "fragments": [f.to_dict() for f in claim.fragments],
            },
            "status": final_status.value,
            "justification": justification,
            "supporting_evidence": [a.to_dict() for a in evidence_artifacts],
            "contradictions": [c.to_dict() for c in contradictions],
            "corroboration": corrob_group.to_dict(),
            "independence": independence.to_dict(),
            "reproducibility": {
                "status": overall_repro.value,
                "attempts": [r.to_dict() for r in reproduction_attempts],
            },
            "unresolved_gaps": [g.to_dict() for g in gaps],
            "belief_proposal": proposal,
            "provenance_links": [l.to_dict() for l in links],
            "integrity_checks": [ic.to_dict() for ic in integrity_checks],
        }

        return result, explanation_tree
