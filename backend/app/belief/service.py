"""Master Belief Service for Task 107:
Autonomous Belief, Evidence Arbitration, Conflict Resolution & World-Model Revision Engine.

Coordinates all sub-engines, enforces EmergencyStop primacy, and provides
the primary interface for external consumers (Decision, World-State, Self-Model, Missions, Memory).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.belief.arbitration_engine import EvidenceArbitrationEngine
from app.belief.conflict_engine import ConflictResolutionEngine
from app.belief.dependency_engine import DependencyPropagationEngine
from app.belief.domain import (
    ArbitrationOutcome,
    Belief,
    BeliefConflict,
    BeliefCorrection,
    BeliefDependency,
    BeliefEvent,
    BeliefRevision,
    BeliefSnapshot,
    BeliefStatus,
    BeliefSupport,
    BeliefValidation,
    BeliefVersion,
    Claim,
    ClaimVersion,
    ConflictResolution,
    ConflictType,
    EvidenceAssessment,
    EvidenceClassification,
    EvidenceItem,
    RevisionReason,
    UncertaintyType,
    generate_uuid,
    utc_now,
)
from app.belief.meta_evaluator import MetaBeliefEvaluator
from app.belief.query_engine import BeliefQueryEngine
from app.belief.revision_engine import BeliefRevisionEngine
from app.belief.schemas import (
    BeliefDashboardMetrics,
    BeliefEvidencePack,
    BeliefExplanationResponse,
)
from app.belief.snapshot_engine import BeliefSnapshotEngine
from app.belief.temporal_engine import TemporalFreshnessEngine
from app.security.emergency_stop import EmergencyStopService
from app.security.exceptions import EmergencyStopActiveError

logger = logging.getLogger("kairo.belief.service")


class BeliefService:
    """Master coordinator for epistemic beliefs, evidence arbitration, and world-model revisions."""

    _instance: Optional[BeliefService] = None

    def __init__(self, emergency_stop: Optional[EmergencyStopService] = None) -> None:
        self.emergency_stop = emergency_stop or EmergencyStopService()
        
        # Sub-engines
        self.arbitration_engine = EvidenceArbitrationEngine()
        self.conflict_engine = ConflictResolutionEngine()
        self.temporal_engine = TemporalFreshnessEngine()
        self.dependency_engine = DependencyPropagationEngine()
        self.snapshot_engine = BeliefSnapshotEngine()
        self.revision_engine = BeliefRevisionEngine()
        self.query_engine = BeliefQueryEngine()
        self.meta_evaluator = MetaBeliefEvaluator()

        # In-memory storage registries
        self._claims: Dict[str, Claim] = {}
        self._claim_versions: Dict[str, List[ClaimVersion]] = {}
        self._evidence: Dict[str, EvidenceItem] = {}
        self._assessments: Dict[str, List[EvidenceAssessment]] = {}  # claim_id -> list of assessments
        self._beliefs: Dict[str, Belief] = {}
        self._belief_versions: Dict[str, List[BeliefVersion]] = {}   # belief_id -> list of versions
        self._conflicts: Dict[str, BeliefConflict] = {}
        self._revisions: List[BeliefRevision] = []
        self._corrections: List[BeliefCorrection] = []
        self._events: List[BeliefEvent] = []

    @classmethod
    def get_instance(cls) -> BeliefService:
        if cls._instance is None:
            cls._instance = BeliefService()
        return cls._instance

    def _check_emergency_stop(self) -> None:
        """Enforce EmergencyStop absolute primacy fail-closed."""
        if getattr(self.emergency_stop, "_global_stopped", False):
            logger.critical("EPISTEMIC OPERATIONS BLOCKED: Global EmergencyStop is active.")
            raise EmergencyStopActiveError("Epistemic belief operations blocked: EmergencyStop active.")

    # ------------------------------------------------------------------
    # Claims
    # ------------------------------------------------------------------
    def create_claim(
        self,
        subject: str,
        predicate: str,
        object_value: Any,
        scope: str = "SYSTEM",
        uncertainty: float = 0.2,
        uncertainty_type: UncertaintyType = UncertaintyType.NONE,
        provenance: Optional[Dict[str, Any]] = None,
    ) -> Claim:
        self._check_emergency_stop()
        claim = Claim(
            claim_id=generate_uuid("clm"),
            subject=subject,
            predicate=predicate,
            object_value=object_value,
            scope=scope,
            valid_from=utc_now(),
            version=1,
            uncertainty=uncertainty,
            uncertainty_type=uncertainty_type,
            provenance=provenance or {},
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        self._claims[claim.claim_id] = claim

        # Mint ClaimVersion 1
        cv = ClaimVersion(
            version_id=generate_uuid("clmv"),
            claim_id=claim.claim_id,
            version_number=1,
            subject=subject,
            predicate=predicate,
            object_value=object_value,
            scope=scope,
            valid_from=claim.valid_from,
            uncertainty=uncertainty,
            uncertainty_type=uncertainty_type,
            created_at=utc_now(),
        )
        self._claim_versions[claim.claim_id] = [cv]
        self._emit_event("claim.created", payload={"claim_id": claim.claim_id, "subject": subject})
        return claim

    def get_claim(self, claim_id: str) -> Optional[Claim]:
        return self._claims.get(claim_id)

    # ------------------------------------------------------------------
    # Evidence
    # ------------------------------------------------------------------
    def ingest_evidence(
        self,
        source_id: str,
        source_type: EvidenceClassification = EvidenceClassification.DIRECT_OBSERVATION,
        scope: str = "SYSTEM",
        content: Optional[Dict[str, Any]] = None,
        summary: str = "",
        freshness_ttl_seconds: int = 300,
        derived_from_evidence_ids: Optional[List[str]] = None,
        reliability_weight: float = 0.8,
    ) -> EvidenceItem:
        self._check_emergency_stop()
        item = EvidenceItem(
            evidence_id=generate_uuid("evi"),
            source_id=source_id,
            source_type=source_type,
            timestamp=utc_now(),
            scope=scope,
            content=content or {},
            summary=summary,
            freshness_ttl_seconds=freshness_ttl_seconds,
            derived_from_evidence_ids=derived_from_evidence_ids or [],
            reliability_weight=reliability_weight,
            created_at=utc_now(),
        )
        self._evidence[item.evidence_id] = item
        self._emit_event("evidence.ingested", evidence_id=item.evidence_id, payload={"source_type": source_type.value})
        logger.info("EVIDENCE_INGESTED: id=%s source=%s type=%s scope=%s", item.evidence_id, source_id, source_type.value, scope)
        return item

    def get_evidence(self, evidence_id: str) -> Optional[EvidenceItem]:
        return self._evidence.get(evidence_id)

    def list_evidence(self, limit: int = 100) -> List[EvidenceItem]:
        return list(self._evidence.values())[-limit:]

    # ------------------------------------------------------------------
    # Beliefs
    # ------------------------------------------------------------------
    def create_belief(
        self,
        subject: str,
        predicate: str,
        object_value: Any,
        scope: str = "SYSTEM",
        initial_confidence: float = 0.5,
        evidence_ids: Optional[List[str]] = None,
        freshness_ttl_seconds: Optional[int] = None,
        provenance: Optional[Dict[str, Any]] = None,
    ) -> Belief:
        self._check_emergency_stop()
        
        # 1. Create underlying Claim
        claim = self.create_claim(
            subject=subject,
            predicate=predicate,
            object_value=object_value,
            scope=scope,
            uncertainty=round(1.0 - initial_confidence, 2),
            provenance=provenance or {},
        )

        ttl = freshness_ttl_seconds or self.temporal_engine.compute_ttl_for_belief(subject, predicate)

        # 2. Instantiate Belief
        ev_ids = evidence_ids or []
        belief = Belief(
            belief_id=generate_uuid("blf"),
            subject=subject,
            predicate=predicate,
            claim_id=claim.claim_id,
            current_version=1,
            scope=scope,
            status=BeliefStatus.CANDIDATE if not ev_ids else BeliefStatus.SUPPORTED,
            confidence=initial_confidence,
            uncertainty=round(1.0 - initial_confidence, 2),
            uncertainty_type=UncertaintyType.NONE if initial_confidence >= 0.7 else UncertaintyType.INSUFFICIENT_EVIDENCE,
            valid_from=utc_now(),
            freshness_ttl_seconds=ttl,
            is_stale=False,
            evidence_ids=ev_ids,
            contradiction_evidence_ids=[],
            provenance=provenance or {},
            created_at=utc_now(),
            updated_at=utc_now(),
        )

        self._beliefs[belief.belief_id] = belief

        # 3. Mint Version 1
        bv = BeliefVersion(
            version_id=generate_uuid("blfv"),
            belief_id=belief.belief_id,
            version_number=1,
            status=belief.status,
            confidence=belief.confidence,
            uncertainty=belief.uncertainty,
            uncertainty_type=belief.uncertainty_type,
            claim_id=claim.claim_id,
            evidence_ids=ev_ids,
            contradiction_evidence_ids=[],
            revision_reason=RevisionReason.NEW_EVIDENCE,
            revision_notes="Initial belief instantiation.",
            created_at=utc_now(),
        )
        self._belief_versions[belief.belief_id] = [bv]

        # 4. Check for conflicts against existing claims
        conflicts = self.conflict_engine.detect_conflicts(claim, list(self._claims.values()), self._evidence)
        for cnf in conflicts:
            self._conflicts[cnf.conflict_id] = cnf
            if cnf.resolution == ConflictResolution.CONTESTED:
                belief.status = BeliefStatus.CONTESTED
                belief.uncertainty_type = UncertaintyType.CONFLICTED

        self._emit_event("belief.created", belief_id=belief.belief_id, payload={"subject": subject, "predicate": predicate})
        return belief

    def get_belief(self, belief_id: str) -> Optional[Belief]:
        belief = self._beliefs.get(belief_id)
        if belief:
            self.temporal_engine.apply_freshness_check(belief)
        return belief

    def list_beliefs(
        self,
        scope: Optional[str] = None,
        status: Optional[BeliefStatus] = None,
        is_stale: Optional[bool] = None,
        limit: int = 100,
    ) -> List[Belief]:
        results: List[Belief] = []
        for b in self._beliefs.values():
            self.temporal_engine.apply_freshness_check(b)
            if scope and b.scope != scope:
                continue
            if status and b.status != status:
                continue
            if is_stale is not None and b.is_stale != is_stale:
                continue
            results.append(b)
        return results[-limit:]

    def get_belief_versions(self, belief_id: str) -> List[BeliefVersion]:
        return self._belief_versions.get(belief_id, [])

    # ------------------------------------------------------------------
    # Arbitration & Revision
    # ------------------------------------------------------------------
    def arbitrate_and_revise(
        self,
        belief_id: str,
        evidence_id: str,
        reason: RevisionReason = RevisionReason.NEW_EVIDENCE,
        notes: str = "",
    ) -> Tuple[Belief, Optional[BeliefVersion], Optional[BeliefRevision]]:
        """Evaluate incoming evidence against a belief, re-arbitrate, and revise non-destructively."""
        self._check_emergency_stop()
        belief = self.get_belief(belief_id)
        if not belief:
            raise KeyError(f"Belief '{belief_id}' not found.")

        evidence = self.get_evidence(evidence_id)
        if not evidence:
            raise KeyError(f"Evidence '{evidence_id}' not found.")

        claim = self.get_claim(belief.claim_id)
        if not claim:
            raise KeyError(f"Claim '{belief.claim_id}' for belief '{belief_id}' not found.")

        # 1. Arbitrate evidence against claim
        assessment = self.arbitration_engine.evaluate_evidence(evidence, claim, list(self._evidence.values()))
        if claim.claim_id not in self._assessments:
            self._assessments[claim.claim_id] = []
        self._assessments[claim.claim_id].append(assessment)

        # 2. Perform versioned revision
        revision_res = self.revision_engine.revise_belief_with_evidence(
            belief=belief,
            new_evidence=evidence,
            assessment=assessment,
            all_assessments=self._assessments[claim.claim_id],
            reason=reason,
            notes=notes,
        )

        version_record: Optional[BeliefVersion] = None
        revision_record: Optional[BeliefRevision] = None

        if revision_res:
            _, version_record, revision_record = revision_res
            self._belief_versions[belief.belief_id].append(version_record)
            self._revisions.append(revision_record)

            # 3. Propagate uncertainty to downstream dependents if material
            impacted = self.dependency_engine.propagate_upstream_change(belief, self._beliefs)
            if impacted:
                logger.info(
                    "DEPENDENCY_PROPAGATION_APPLIED: Upstream change in belief %s affected %d dependent(s)",
                    belief.belief_id,
                    len(impacted),
                )

            self._emit_event(
                "belief.revised",
                belief_id=belief.belief_id,
                evidence_id=evidence.evidence_id,
                payload={"version": belief.current_version, "status": belief.status.value, "confidence": belief.confidence},
            )

        return belief, version_record, revision_record

    # ------------------------------------------------------------------
    # Dependencies & Snapshots
    # ------------------------------------------------------------------
    def register_dependency(
        self,
        parent_belief_id: str,
        child_belief_id: str,
        dependency_strength: float = 1.0,
        is_hard_prerequisite: bool = True,
        notes: str = "",
    ) -> BeliefDependency:
        self._check_emergency_stop()
        return self.dependency_engine.register_dependency(
            parent_belief_id, child_belief_id, dependency_strength, is_hard_prerequisite, notes
        )

    def get_dependencies(self, belief_id: str) -> List[BeliefDependency]:
        return self.dependency_engine.get_dependencies_for_parent(belief_id)

    def capture_snapshot(
        self,
        trigger_type: str = "MANUAL",
        reference_id: Optional[str] = None,
        scope: str = "SYSTEM",
    ) -> BeliefSnapshot:
        self._check_emergency_stop()
        snap = self.snapshot_engine.capture_snapshot(
            beliefs=list(self._beliefs.values()),
            evidence_items=list(self._evidence.values()),
            trigger_type=trigger_type,
            reference_id=reference_id,
            scope=scope,
        )
        self._emit_event("belief.snapshot_created", payload={"snapshot_id": snap.snapshot_id, "ref": reference_id})
        return snap

    def get_snapshot(self, snapshot_id: str) -> Optional[BeliefSnapshot]:
        return self.snapshot_engine.get_snapshot(snapshot_id)

    # ------------------------------------------------------------------
    # User Corrections
    # ------------------------------------------------------------------
    def record_user_correction(
        self,
        belief_id: str,
        correction_statement: str,
        source: str = "USER",
    ) -> BeliefCorrection:
        """Record a human user correction as evidence classified as USER_ASSERTION.
        
        Strict invariant: User assertion is evidence, NOT universal fact.
        """
        self._check_emergency_stop()
        belief = self.get_belief(belief_id)
        if not belief:
            raise KeyError(f"Belief '{belief_id}' not found.")

        # Ingest as USER_ASSERTION evidence
        ev = self.ingest_evidence(
            source_id=f"user_{source.lower()}",
            source_type=EvidenceClassification.USER_ASSERTION,
            scope=belief.scope,
            content={"correction": correction_statement, "subject": belief.subject, "predicate": belief.predicate},
            summary=f"User correction: {correction_statement}",
            reliability_weight=0.5,
        )

        corr = BeliefCorrection(
            correction_id=generate_uuid("bcor"),
            belief_id=belief_id,
            source=source,
            correction_statement=correction_statement,
            verified=False,
            evidence_id=ev.evidence_id,
            created_at=utc_now(),
        )
        self._corrections.append(corr)

        # Trigger re-arbitration under USER_CORRECTION reason
        self.arbitrate_and_revise(
            belief_id=belief_id,
            evidence_id=ev.evidence_id,
            reason=RevisionReason.USER_CORRECTION,
            notes=correction_statement,
        )
        self._emit_event("belief.corrected", belief_id=belief_id, evidence_id=ev.evidence_id)
        return corr

    # ------------------------------------------------------------------
    # Explanations & Evidence Packs
    # ------------------------------------------------------------------
    def explain_belief(self, belief_id: str) -> BeliefExplanationResponse:
        belief = self.get_belief(belief_id)
        if not belief:
            raise KeyError(f"Belief '{belief_id}' not found.")

        claim = self.get_claim(belief.claim_id)
        supporting_ev = [self._evidence[eid] for eid in belief.evidence_ids if eid in self._evidence]
        contradicting_ev = [self._evidence[eid] for eid in belief.contradiction_evidence_ids if eid in self._evidence]

        return self.query_engine.explain_belief(belief, claim, supporting_ev, contradicting_ev)

    def get_evidence_pack(self, belief_id: str) -> BeliefEvidencePack:
        belief = self.get_belief(belief_id)
        if not belief:
            raise KeyError(f"Belief '{belief_id}' not found.")

        supporting_ev = [self._evidence[eid] for eid in belief.evidence_ids if eid in self._evidence]
        contradicting_ev = [self._evidence[eid] for eid in belief.contradiction_evidence_ids if eid in self._evidence]

        return self.query_engine.assemble_evidence_pack(belief, supporting_ev, contradicting_ev)

    def get_conflicts(self, belief_id: Optional[str] = None) -> List[BeliefConflict]:
        if belief_id:
            return [c for c in self._conflicts.values() if c.belief_id_a == belief_id or c.belief_id_b == belief_id]
        return list(self._conflicts.values())

    def get_revisions(self, belief_id: Optional[str] = None) -> List[BeliefRevision]:
        if belief_id:
            return [r for r in self._revisions if r.belief_id == belief_id]
        return list(self._revisions)

    # ------------------------------------------------------------------
    # Telemetry & Dashboard
    # ------------------------------------------------------------------
    def get_dashboard_metrics(self) -> BeliefDashboardMetrics:
        beliefs = list(self._beliefs.values())
        for b in beliefs:
            self.temporal_engine.apply_freshness_check(b)

        confident = sum(1 for b in beliefs if b.status == BeliefStatus.CONFIDENT)
        contested = sum(1 for b in beliefs if b.status == BeliefStatus.CONTESTED)
        stale = sum(1 for b in beliefs if b.is_stale)
        unknown = sum(1 for b in beliefs if b.status == BeliefStatus.UNKNOWN)

        return BeliefDashboardMetrics(
            total_beliefs=len(beliefs),
            confident_beliefs=confident,
            contested_beliefs=contested,
            stale_beliefs=stale,
            unknown_beliefs=unknown,
            total_evidence_items=len(self._evidence),
            active_conflicts=len(self._conflicts),
            total_revisions=len(self._revisions),
            total_snapshots=len(self.snapshot_engine._snapshots),
            epistemic_invariants_enforced=True,
        )

    def _emit_event(
        self,
        event_type: str,
        belief_id: Optional[str] = None,
        evidence_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        event = BeliefEvent(
            event_id=generate_uuid("bev"),
            event_type=event_type,
            belief_id=belief_id,
            evidence_id=evidence_id,
            payload=payload or {},
            emitted_at=utc_now(),
        )
        self._events.append(event)
        # Attempt emission to core event bus if present
        try:
            from app.events.bus import get_event_bus
            from app.events.schemas import Event
            bus = get_event_bus()
            bus.publish_sync(
                Event(
                    type=event_type,
                    source="belief_service",
                    payload={"event_id": event.event_id, "belief_id": belief_id, **(payload or {})},
                )
            )
        except Exception:
            pass  # Standalone or test environment fallback
