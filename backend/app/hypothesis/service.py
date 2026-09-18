"""HypothesisService singleton orchestrator (Task 115 Section 8, 9, 10, 18, 51, 60).

Coordinates generation, evidence evaluation, falsification checks, bias safeguards,
refinements, discriminators, snapshots, and safety bridges.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.hypothesis.bias_guard_engine import BiasGuardEngine
from app.hypothesis.discriminator_engine import DiscriminatorEngine
from app.hypothesis.domain import (
    EvidenceIndependence,
    EvidenceType,
    Hypothesis,
    HypothesisClaim,
    HypothesisConfidenceProfile,
    HypothesisEvent,
    HypothesisEventType,
    HypothesisEvidenceItem,
    HypothesisProvenance,
    HypothesisScope,
    HypothesisSet,
    HypothesisSnapshot,
    HypothesisStatus,
    SupportVerdict,
)
from app.hypothesis.downstream_bridges import HypothesisBridgeHub
from app.hypothesis.evidence_evaluator import EvidenceEvaluator
from app.hypothesis.falsification_engine import FalsificationEngine
from app.hypothesis.generation_engine import HypothesisGenerationEngine
from app.hypothesis.refinement_engine import RefinementEngine
from app.hypothesis.staleness_engine import StalenessEngine

logger = logging.getLogger("kairo.hypothesis.service")


class HypothesisService:
    """Singleton service for autonomous hypothesis lifecycle and competing explanations."""

    _instance: Optional[HypothesisService] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._sets: Dict[str, HypothesisSet] = {}
        self._hypotheses: Dict[str, Hypothesis] = {}
        self._evidence: Dict[str, HypothesisEvidenceItem] = {}
        self._snapshots: Dict[str, List[HypothesisSnapshot]] = {}
        self._events: List[HypothesisEvent] = []
        self._feedback: Dict[str, List[Dict[str, Any]]] = {}

        # Sub-engines
        self.generation_engine = HypothesisGenerationEngine()
        self.evidence_evaluator = EvidenceEvaluator()
        self.falsification_engine = FalsificationEngine()
        self.bias_guard_engine = BiasGuardEngine()
        self.refinement_engine = RefinementEngine()
        self.discriminator_engine = DiscriminatorEngine()
        self.staleness_engine = StalenessEngine()
        self.bridge_hub = HypothesisBridgeHub()

        # Disk cache path for robustness
        self._cache_dir = Path("data/hypothesis_cache")
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._load_cache()

    @classmethod
    def get_instance(cls) -> HypothesisService:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        with cls._lock:
            cls._instance = None

    def _save_cache(self) -> None:
        """Persists hypothesis state to local disk JSON."""
        try:
            state = {
                "sets": {sid: s.to_dict() for sid, s in self._sets.items()},
                "hypotheses": {hid: h.to_dict() for hid, h in self._hypotheses.items()},
                "evidence": {eid: e.to_dict() for eid, e in self._evidence.items()},
            }
            with open(self._cache_dir / "hypothesis_store.json", "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.debug("Cache save skipped or failed: %s", e)

    def _load_cache(self) -> None:
        """Loads cached hypothesis state from disk if present."""
        path = self._cache_dir / "hypothesis_store.json"
        if not path.exists():
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Reconstruct sets and hypotheses
            for sid, sdata in data.get("sets", {}).items():
                hset = HypothesisSet(
                    set_id=sdata["set_id"],
                    version=sdata.get("version", 1),
                    target_description=sdata.get("target_description", ""),
                    target_incident_id=sdata.get("target_incident_id"),
                    active_hypothesis_ids=sdata.get("active_hypothesis_ids", []),
                    rejected_hypothesis_ids=sdata.get("rejected_hypothesis_ids", []),
                    unknown_hypothesis_id=sdata.get("unknown_hypothesis_id"),
                    information_gaps=sdata.get("information_gaps", []),
                    is_resolved=sdata.get("is_resolved", False),
                    resolution_summary=sdata.get("resolution_summary", "CAUSE_UNKNOWN"),
                )
                self._sets[sid] = hset

            for hid, hdata in data.get("hypotheses", {}).items():
                claim_d = hdata.get("claim", {})
                claim = HypothesisClaim(
                    claim_id=claim_d.get("claim_id", ""),
                    subject=claim_d.get("subject", ""),
                    predicate=claim_d.get("predicate", ""),
                    object_value=claim_d.get("object_value"),
                    target_metric=claim_d.get("target_metric"),
                    expected_direction=claim_d.get("expected_direction"),
                )
                conf_d = hdata.get("confidence_profile", {})
                conf = HypothesisConfidenceProfile(
                    evidence_strength=conf_d.get("evidence_strength", 0.0),
                    evidence_independence=conf_d.get("evidence_independence", 0.0),
                    temporal_consistency=conf_d.get("temporal_consistency", 0.5),
                    mechanism_plausibility=conf_d.get("mechanism_plausibility", 0.5),
                    causal_support=conf_d.get("causal_support", 0.5),
                    predictive_success=conf_d.get("predictive_success", 0.5),
                    counterfactual_support=conf_d.get("counterfactual_support", 0.0),
                    contradiction_score=conf_d.get("contradiction_score", 0.0),
                    source_reliability=conf_d.get("source_reliability", 0.8),
                    completeness=conf_d.get("completeness", 0.3),
                    uncertainty=conf_d.get("uncertainty", 0.7),
                    historical_consistency=conf_d.get("historical_consistency", 0.5),
                )
                hyp = Hypothesis(
                    hypothesis_id=hdata["hypothesis_id"],
                    set_id=hdata["set_id"],
                    version=hdata.get("version", 1),
                    statement=hdata.get("statement", ""),
                    claim=claim,
                    status=HypothesisStatus(hdata.get("status", "CANDIDATE")),
                    provenance=HypothesisProvenance(hdata.get("provenance", "GENERATED")),
                    proposer_agent_id=hdata.get("proposer_agent_id"),
                    is_unknown_hypothesis=hdata.get("is_unknown_hypothesis", False),
                    mechanism_summary=hdata.get("mechanism_summary", ""),
                    causal_node_refs=hdata.get("causal_node_refs", []),
                    assumptions=hdata.get("assumptions", []),
                    confidence_profile=conf,
                    supporting_evidence_ids=hdata.get("supporting_evidence_ids", []),
                    contradicting_evidence_ids=hdata.get("contradicting_evidence_ids", []),
                    falsifying_evidence_ids=hdata.get("falsifying_evidence_ids", []),
                    parent_hypothesis_ids=hdata.get("parent_hypothesis_ids", []),
                    child_hypothesis_ids=hdata.get("child_hypothesis_ids", []),
                    superseded_by_id=hdata.get("superseded_by_id"),
                    contradiction_search_performed=hdata.get("contradiction_search_performed", False),
                    bias_guard_triggers=hdata.get("bias_guard_triggers", []),
                )
                self._hypotheses[hid] = hyp

            for eid, edata in data.get("evidence", {}).items():
                ev = HypothesisEvidenceItem(
                    evidence_id=edata["evidence_id"],
                    source=edata.get("source", ""),
                    source_type=edata.get("source_type", "system"),
                    source_agent_id=edata.get("source_agent_id"),
                    provenance=edata.get("provenance", ""),
                    parent_evidence_ids=edata.get("parent_evidence_ids", []),
                    independence=EvidenceIndependence(edata.get("independence", "INDEPENDENT")),
                    freshness_seconds=edata.get("freshness_seconds", 0.0),
                    reliability_score=edata.get("reliability_score", 1.0),
                    direct_status=edata.get("direct_status", True),
                    evidence_type=EvidenceType(edata.get("evidence_type", "OBSERVATION")),
                    payload=edata.get("payload", {}),
                    is_simulation=edata.get("is_simulation", False),
                    is_counterfactual=edata.get("is_counterfactual", False),
                )
                self._evidence[eid] = ev
        except Exception as e:
            logger.warning("Failed loading cached hypotheses: %s", e)

    def _emit_event(self, event_type: HypothesisEventType, hyp_id: Optional[str] = None, set_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> None:
        evt = HypothesisEvent(
            event_type=event_type,
            hypothesis_id=hyp_id,
            set_id=set_id,
            details=details or {},
        )
        self._events.append(evt)

    # --- Core Service APIs ---

    def create_hypothesis_set(
        self,
        target_description: str,
        scope: Optional[HypothesisScope] = None,
        target_incident_id: Optional[str] = None,
        candidate_explanations: Optional[List[Dict[str, Any]]] = None,
    ) -> HypothesisSet:
        """Initializes a new competing hypothesis set with mandatory UNKNOWN hypothesis."""
        self.bridge_hub.verify_safety_and_governance()

        with self._lock:
            hset, hypotheses = self.generation_engine.create_hypothesis_set_for_target(
                target_description=target_description,
                scope=scope,
                target_incident_id=target_incident_id,
                candidate_explanations=candidate_explanations,
            )

            self._sets[hset.set_id] = hset
            for h in hypotheses:
                self._hypotheses[h.hypothesis_id] = h
                self._emit_event(HypothesisEventType.HYPOTHESIS_CREATED, hyp_id=h.hypothesis_id, set_id=hset.set_id)

            # Generate initial discriminators
            self.discriminator_engine.find_discriminating_observations(hset, hypotheses)
            self._save_cache()
            return hset

    def get_hypothesis_set(self, set_id: str) -> Optional[HypothesisSet]:
        with self._lock:
            return self._sets.get(set_id)

    def list_hypothesis_sets(self) -> List[HypothesisSet]:
        with self._lock:
            return list(self._sets.values())

    def get_hypothesis(self, hypothesis_id: str) -> Optional[Hypothesis]:
        with self._lock:
            return self._hypotheses.get(hypothesis_id)

    def list_hypotheses(self, set_id: Optional[str] = None) -> List[Hypothesis]:
        with self._lock:
            if set_id:
                return [h for h in self._hypotheses.values() if h.set_id == set_id]
            return list(self._hypotheses.values())

    def add_hypothesis_to_set(self, set_id: str, data: Dict[str, Any]) -> Hypothesis:
        """Adds a new candidate explanation (e.g. proposed by user or agent)."""
        self.bridge_hub.verify_safety_and_governance()

        with self._lock:
            hset = self._sets.get(set_id)
            if not hset:
                raise ValueError(f"HypothesisSet {set_id} not found.")

            hyp = self.generation_engine.build_hypothesis_from_dict(set_id, data, hset.scope)
            self._hypotheses[hyp.hypothesis_id] = hyp
            hset.active_hypothesis_ids.append(hyp.hypothesis_id)
            hset.version += 1
            hset.updated_at = datetime.now(timezone.utc)

            self._emit_event(HypothesisEventType.HYPOTHESIS_CREATED, hyp_id=hyp.hypothesis_id, set_id=set_id)
            self.discriminator_engine.find_discriminating_observations(hset, self.list_hypotheses(set_id))
            self._save_cache()
            return hyp

    def attach_evidence_to_set(
        self,
        set_id: str,
        evidence_data: Dict[str, Any],
        target_hypothesis_id: Optional[str] = None,
    ) -> HypothesisEvidenceItem:
        """Ingests evidence, determines independence, assesses against hypotheses, and updates confidence."""
        self.bridge_hub.verify_safety_and_governance()

        with self._lock:
            hset = self._sets.get(set_id)
            if not hset:
                raise ValueError(f"HypothesisSet {set_id} not found.")

            ev_item = HypothesisEvidenceItem(
                source=evidence_data.get("source", "telemetry"),
                source_type=evidence_data.get("source_type", "system"),
                source_agent_id=evidence_data.get("source_agent_id"),
                provenance=evidence_data.get("provenance", ""),
                parent_evidence_ids=evidence_data.get("parent_evidence_ids", []),
                reliability_score=float(evidence_data.get("reliability_score", 1.0)),
                direct_status=bool(evidence_data.get("direct_status", True)),
                evidence_type=EvidenceType(evidence_data.get("evidence_type", "OBSERVATION")),
                payload=evidence_data.get("payload", {}),
                is_simulation=bool(evidence_data.get("is_simulation", False)),
                is_counterfactual=bool(evidence_data.get("is_counterfactual", False)),
            )

            # Lineage & Independence check
            existing_ev = list(self._evidence.values())
            ev_item.independence = self.evidence_evaluator.assess_independence(ev_item, existing_ev)
            self._evidence[ev_item.evidence_id] = ev_item

            # Determine affected hypotheses
            affected_hyps: List[Hypothesis] = []
            if target_hypothesis_id:
                th = self._hypotheses.get(target_hypothesis_id)
                if th:
                    affected_hyps.append(th)
            else:
                affected_hyps = [
                    h for h in self._hypotheses.values()
                    if h.set_id == set_id and not h.is_unknown_hypothesis and h.status not in (HypothesisStatus.FALSIFIED, HypothesisStatus.REJECTED)
                ]

            for hyp in affected_hyps:
                # 1. Falsification check
                self.falsification_engine.evaluate_falsification_conditions(
                    hyp, ev_item.payload, ev_item.evidence_id
                )

                # 2. Evidence assessment
                assessment = self.evidence_evaluator.evaluate_evidence_against_hypothesis(
                    hyp, ev_item, existing_ev
                )
                self.evidence_evaluator.apply_assessment_to_hypothesis(hyp, assessment)

                # 3. Bias Guard checks
                self.bias_guard_engine.check_and_apply_safeguards(
                    hyp, hset, self.list_hypotheses(set_id), list(self._evidence.values())
                )

                # Emit events
                if assessment.verdict in (SupportVerdict.SUPPORTS, SupportVerdict.WEAKLY_SUPPORTS):
                    self._emit_event(HypothesisEventType.HYPOTHESIS_SUPPORTED, hyp_id=hyp.hypothesis_id, set_id=set_id)
                elif assessment.verdict in (SupportVerdict.CONTRADICTS, SupportVerdict.WEAKLY_CONTRADICTS):
                    self._emit_event(HypothesisEventType.HYPOTHESIS_WEAKENED, hyp_id=hyp.hypothesis_id, set_id=set_id)
                elif assessment.verdict == SupportVerdict.FALSIFIES:
                    self._emit_event(HypothesisEventType.HYPOTHESIS_FALSIFIED, hyp_id=hyp.hypothesis_id, set_id=set_id)
                    if hyp.hypothesis_id in hset.active_hypothesis_ids:
                        hset.active_hypothesis_ids.remove(hyp.hypothesis_id)
                    if hyp.hypothesis_id not in hset.rejected_hypothesis_ids:
                        hset.rejected_hypothesis_ids.append(hyp.hypothesis_id)

            # Re-evaluate discriminators
            self.discriminator_engine.find_discriminating_observations(hset, self.list_hypotheses(set_id))
            hset.version += 1
            hset.updated_at = datetime.now(timezone.utc)
            self._save_cache()
            return ev_item

    def split_hypothesis(
        self, set_id: str, parent_hypothesis_id: str, child_specs: List[Dict[str, Any]]
    ) -> List[Hypothesis]:
        """Splits an overly broad hypothesis into granular children."""
        self.bridge_hub.verify_safety_and_governance()

        with self._lock:
            hset = self._sets.get(set_id)
            if not hset:
                raise ValueError(f"HypothesisSet {set_id} not found.")
            parent_hyp = self._hypotheses.get(parent_hypothesis_id)
            if not parent_hyp:
                raise ValueError(f"Parent hypothesis {parent_hypothesis_id} not found.")

            children = self.refinement_engine.split_hypothesis(hset, parent_hyp, child_specs)
            for child in children:
                self._hypotheses[child.hypothesis_id] = child
                self._emit_event(HypothesisEventType.HYPOTHESIS_SPLIT, hyp_id=child.hypothesis_id, set_id=set_id)

            self.discriminator_engine.find_discriminating_observations(hset, self.list_hypotheses(set_id))
            self._save_cache()
            return children

    def merge_hypotheses(
        self, set_id: str, source_hypothesis_ids: List[str], consolidated_statement: str
    ) -> Hypothesis:
        """Merges duplicate/equivalent hypotheses with complete lineage preservation."""
        self.bridge_hub.verify_safety_and_governance()

        with self._lock:
            hset = self._sets.get(set_id)
            if not hset:
                raise ValueError(f"HypothesisSet {set_id} not found.")
            source_hyps = [self._hypotheses[hid] for hid in source_hypothesis_ids if hid in self._hypotheses]
            if len(source_hyps) < 2:
                raise ValueError("Must provide at least 2 existing hypotheses to merge.")

            merged = self.refinement_engine.merge_hypotheses(hset, source_hyps, consolidated_statement)
            self._hypotheses[merged.hypothesis_id] = merged
            self._emit_event(HypothesisEventType.HYPOTHESIS_MERGED, hyp_id=merged.hypothesis_id, set_id=set_id)

            self.discriminator_engine.find_discriminating_observations(hset, self.list_hypotheses(set_id))
            self._save_cache()
            return merged

    def verify_hypothesis(self, hypothesis_id: str) -> Dict[str, Any]:
        """Evaluates whether a hypothesis meets strict multi-criteria standards for VERIFIED status.

        Hard Invariant: Does NOT automatically move to VERIFIED.
        Requires:
        - Independent evidence strength >= 0.85
        - Evidence independence ratio >= 0.70
        - Contradiction score <= 0.05
        - Zero failed predictions
        - Contradiction search actively performed
        - All falsification conditions tested and passed
        - Competing active alternatives evaluated
        """
        self.bridge_hub.verify_safety_and_governance()

        with self._lock:
            hyp = self._hypotheses.get(hypothesis_id)
            if not hyp:
                raise ValueError(f"Hypothesis {hypothesis_id} not found.")

            hset = self._sets.get(hyp.set_id)
            all_hyps = self.list_hypotheses(hyp.set_id)
            all_evidence = list(self._evidence.values())

            # Perform contradiction search first
            self.bias_guard_engine.perform_contradiction_search(hyp, all_evidence)
            hyp.contradiction_search_performed = True

            p = hyp.confidence_profile
            reasons_blocked: List[str] = []

            if p.evidence_strength < 0.80:
                reasons_blocked.append(f"Evidence strength {p.evidence_strength:.2f} < required 0.80")
            if p.evidence_independence < 0.60:
                reasons_blocked.append(f"Evidence independence ratio {p.evidence_independence:.2f} < required 0.60")
            if p.contradiction_score > 0.08:
                reasons_blocked.append(f"Contradiction score {p.contradiction_score:.2f} > allowed threshold 0.08")

            # Check predictions
            failed_preds = [pred for pred in hyp.predictions if pred.outcome_status == "FAILED"]
            if failed_preds:
                reasons_blocked.append(f"{len(failed_preds)} testable predictions failed")

            # Check unexamined alternatives in set
            if hset:
                unexamined = [
                    h for h in all_hyps
                    if h.hypothesis_id in hset.active_hypothesis_ids
                    and h.hypothesis_id != hyp.hypothesis_id
                    and not h.is_unknown_hypothesis
                    and len(h.assessments) == 0
                ]
                if unexamined:
                    reasons_blocked.append(f"{len(unexamined)} competing alternatives remain uninvestigated")

            if reasons_blocked:
                hyp.status = HypothesisStatus.SUPPORTED if p.evidence_strength >= 0.4 else HypothesisStatus.CONTESTED
                self._save_cache()
                return {
                    "verified": False,
                    "hypothesis_id": hyp.hypothesis_id,
                    "status": hyp.status.value,
                    "reasons_blocked": reasons_blocked,
                    "advice": "Hypothesis remains viable but cannot be certified as VERIFIED due to residual uncertainty or unexamined alternatives.",
                }

            hyp.status = HypothesisStatus.VERIFIED
            hyp.updated_at = datetime.now(timezone.utc)
            if hset:
                hset.is_resolved = True
                hset.resolution_summary = f"VERIFIED: {hyp.statement[:64]}"
            self._emit_event(HypothesisEventType.HYPOTHESIS_VERIFIED, hyp_id=hyp.hypothesis_id, set_id=hyp.set_id)
            self._save_cache()
            return {
                "verified": True,
                "hypothesis_id": hyp.hypothesis_id,
                "status": "VERIFIED",
                "notes": "Hypothesis satisfied all rigorous verification criteria without contradiction.",
            }

    def record_feedback(self, hypothesis_id: str, feedback: Dict[str, Any]) -> None:
        """Appends user or reviewer feedback."""
        with self._lock:
            if hypothesis_id not in self._feedback:
                self._feedback[hypothesis_id] = []
            self._feedback[hypothesis_id].append({
                "evaluator": feedback.get("evaluator", "user"),
                "comment": feedback.get("comment", ""),
                "suggested_status": feedback.get("suggested_status"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    def create_snapshot(self, set_id: str, summary: str = "Periodic hypothesis state checkpoint") -> HypothesisSnapshot:
        """Persists an immutable snapshot of a hypothesis set."""
        with self._lock:
            hset = self._sets.get(set_id)
            if not hset:
                raise ValueError(f"HypothesisSet {set_id} not found.")

            hyps = self.list_hypotheses(set_id)
            evs = [e for e in self._evidence.values()]

            snap = HypothesisSnapshot(
                set_id=set_id,
                hypotheses_state=[h.to_dict() for h in hyps],
                evidence_state=[e.to_dict() for e in evs],
                relationships_state=[r.to_dict() for r in hset.relationships],
                summary=summary,
            )

            if set_id not in self._snapshots:
                self._snapshots[set_id] = []
            self._snapshots[set_id].append(snap)
            self._emit_event(HypothesisEventType.HYPOTHESIS_SNAPSHOT_CREATED, set_id=set_id)
            return snap

    def get_side_by_side_comparison(self, set_id: str) -> Dict[str, Any]:
        """Generates the side-by-side comparison matrix for competing explanations (Section 56).

        Hard Invariant: Does NOT include 'BEST HYPOTHESIS', 'WINNER', or 'RANKING'. Exposes evidence transparently.
        """
        with self._lock:
            hset = self._sets.get(set_id)
            if not hset:
                raise ValueError(f"HypothesisSet {set_id} not found.")

            hyps = self.list_hypotheses(set_id)
            rows = []
            for h in hyps:
                rows.append({
                    "hypothesis_id": h.hypothesis_id,
                    "statement": h.statement,
                    "is_unknown": h.is_unknown_hypothesis,
                    "status": h.status.value,
                    "mechanism": h.mechanism_summary or "Unspecified",
                    "supporting_evidence_count": len(h.supporting_evidence_ids),
                    "contradicting_evidence_count": len(h.contradicting_evidence_ids),
                    "falsification_conditions": [fc.description for fc in h.falsification_conditions],
                    "predictions": [p.predicted_event for p in h.predictions],
                    "temporal_fit": round(h.confidence_profile.temporal_consistency, 2),
                    "causal_fit": round(h.confidence_profile.causal_support, 2),
                    "uncertainty": round(h.confidence_profile.uncertainty, 2),
                    "evidence_strength": round(h.confidence_profile.evidence_strength, 2),
                    "contradiction_score": round(h.confidence_profile.contradiction_score, 2),
                    "bias_guard_triggers": h.bias_guard_triggers,
                })

            return {
                "set_id": hset.set_id,
                "target_description": hset.target_description,
                "is_resolved": hset.is_resolved,
                "resolution_summary": hset.resolution_summary,
                "information_gaps": hset.information_gaps,
                "discriminators": [d.to_dict() for d in hset.discriminators],
                "matrix": rows,
            }


_hypothesis_service: Optional[HypothesisService] = None


def get_hypothesis_service() -> HypothesisService:
    global _hypothesis_service
    if _hypothesis_service is None:
        _hypothesis_service = HypothesisService.get_instance()
    return _hypothesis_service
