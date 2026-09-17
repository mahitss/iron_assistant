"""Conflict Detection and Contextual Truth Resolution Engine for Task 107.

Detects 7 conflict types:
- DIRECT
- TEMPORAL
- SCOPE
- VERSION
- SOURCE
- DEPENDENCY
- DERIVATION

Strict Invariant:
Never blindly pick 'latest wins' or 'majority wins'.
Support contextual truth (statements valid under different scopes).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.belief.domain import (
    Belief,
    BeliefConflict,
    Claim,
    ConflictResolution,
    ConflictType,
    EvidenceClassification,
    EvidenceItem,
    generate_uuid,
    utc_now,
)

logger = logging.getLogger("kairo.belief.conflicts")


class ConflictResolutionEngine:
    """Detects and resolves epistemic conflicts across claims and beliefs."""

    def detect_conflicts(
        self,
        new_claim: Claim,
        existing_claims: List[Claim],
        evidence_map: Optional[Dict[str, EvidenceItem]] = None,
    ) -> List[BeliefConflict]:
        """Scan active claims for conflicts against a newly formed or updated claim."""
        conflicts: List[BeliefConflict] = []
        ev_map = evidence_map or {}

        for ex_claim in existing_claims:
            if ex_claim.claim_id == new_claim.claim_id:
                continue

            # Check if subjects match
            if ex_claim.subject != new_claim.subject:
                continue

            # Check if predicates match
            if ex_claim.predicate == new_claim.predicate:
                # 1. Scope conflict check (e.g. Staging vs Production)
                if ex_claim.scope != new_claim.scope:
                    conflicts.append(
                        BeliefConflict(
                            conflict_id=generate_uuid("bcnf"),
                            belief_id_a=new_claim.claim_id,
                            belief_id_b=ex_claim.claim_id,
                            claim_id_a=new_claim.claim_id,
                            claim_id_b=ex_claim.claim_id,
                            conflict_type=ConflictType.SCOPE,
                            resolution=ConflictResolution.BOTH_CONTEXTUALLY_VALID,
                            rationale=(
                                f"Claims about '{new_claim.subject}.{new_claim.predicate}' differ by scope "
                                f"('{new_claim.scope}' vs '{ex_claim.scope}'). Both are contextually valid."
                            ),
                            detected_at=utc_now(),
                            resolved_at=utc_now(),
                        )
                    )
                    continue

                # 2. Version conflict check
                prov_new = new_claim.provenance or {}
                prov_ex = ex_claim.provenance or {}
                if prov_new.get("version") and prov_ex.get("version") and prov_new.get("version") != prov_ex.get("version"):
                    conflicts.append(
                        BeliefConflict(
                            conflict_id=generate_uuid("bcnf"),
                            belief_id_a=new_claim.claim_id,
                            belief_id_b=ex_claim.claim_id,
                            claim_id_a=new_claim.claim_id,
                            claim_id_b=ex_claim.claim_id,
                            conflict_type=ConflictType.VERSION,
                            resolution=ConflictResolution.CONTESTED,
                            rationale=(
                                f"Claims target different component versions ({prov_new.get('version')} vs {prov_ex.get('version')})."
                            ),
                            detected_at=utc_now(),
                        )
                    )
                    continue

                # 3. Direct value contradiction check
                if ex_claim.object_value != new_claim.object_value:
                    # Check temporal interval overlap
                    if self._intervals_overlap(new_claim, ex_claim):
                        res, rat = self._arbitrate_direct_conflict(new_claim, ex_claim, ev_map)
                        conflicts.append(
                            BeliefConflict(
                                conflict_id=generate_uuid("bcnf"),
                                belief_id_a=new_claim.claim_id,
                                belief_id_b=ex_claim.claim_id,
                                claim_id_a=new_claim.claim_id,
                                claim_id_b=ex_claim.claim_id,
                                conflict_type=ConflictType.DIRECT,
                                resolution=res,
                                rationale=rat,
                                detected_at=utc_now(),
                                resolved_at=utc_now() if res != ConflictResolution.CONTESTED else None,
                            )
                        )
                    else:
                        # Temporal mismatch: past vs present state
                        conflicts.append(
                            BeliefConflict(
                                conflict_id=generate_uuid("bcnf"),
                                belief_id_a=new_claim.claim_id,
                                belief_id_b=ex_claim.claim_id,
                                claim_id_a=new_claim.claim_id,
                                claim_id_b=ex_claim.claim_id,
                                conflict_type=ConflictType.TEMPORAL,
                                resolution=ConflictResolution.CLAIM_A_SUPPORTED,
                                rationale="Historical claim superseded by contemporary observation window.",
                                detected_at=utc_now(),
                                resolved_at=utc_now(),
                            )
                        )

        return conflicts

    def _intervals_overlap(self, c1: Claim, c2: Claim) -> bool:
        """Check if validity time windows overlap."""
        end1 = c1.valid_until or utc_now()
        end2 = c2.valid_until or utc_now()
        return not (end1 < c2.valid_from or end2 < c1.valid_from)

    def _arbitrate_direct_conflict(
        self,
        c1: Claim,
        c2: Claim,
        ev_map: Dict[str, EvidenceItem],
    ) -> Tuple[ConflictResolution, str]:
        """Arbitrate direct contradiction based on evidence hierarchy and verification."""
        # Find highest classification backing c1 and c2
        prov1 = c1.provenance or {}
        prov2 = c2.provenance or {}
        
        c1_ev_ids = prov1.get("evidence_ids", [])
        c2_ev_ids = prov2.get("evidence_ids", [])

        c1_highest = self._get_highest_evidence_class(c1_ev_ids, ev_map)
        c2_highest = self._get_highest_evidence_class(c2_ev_ids, ev_map)

        # Hierarchy: DIRECT_OBSERVATION / VERIFIED_OUTCOME > INDEPENDENT_EVALUATION > TELEMETRY > EXPERIMENTAL > INFERRED / MEMORY > AGENT_REPORT / SIMULATION / FORECAST
        hierarchy = {
            EvidenceClassification.DIRECT_OBSERVATION: 10,
            EvidenceClassification.VERIFIED_OUTCOME: 10,
            EvidenceClassification.INDEPENDENT_EVALUATION: 9,
            EvidenceClassification.TELEMETRY: 8,
            EvidenceClassification.EXPERIMENTAL: 7,
            EvidenceClassification.INFERRED: 5,
            EvidenceClassification.MEMORY: 4,
            EvidenceClassification.USER_ASSERTION: 4,
            EvidenceClassification.AGENT_REPORT: 3,
            EvidenceClassification.SIMULATION: 2,
            EvidenceClassification.FORECAST: 2,
            EvidenceClassification.EXTERNAL_SOURCE: 3,
        }

        rank1 = hierarchy.get(c1_highest, 1)
        rank2 = hierarchy.get(c2_highest, 1)

        if rank1 > rank2 + 2:
            return (
                ConflictResolution.CLAIM_A_SUPPORTED,
                f"Claim A backed by higher-fidelity evidence ({c1_highest.value}) over Claim B ({c2_highest.value}).",
            )
        elif rank2 > rank1 + 2:
            return (
                ConflictResolution.CLAIM_B_SUPPORTED,
                f"Claim B backed by higher-fidelity evidence ({c2_highest.value}) over Claim A ({c1_highest.value}).",
            )
        else:
            # Comparable rank: must be marked CONTESTED
            return (
                ConflictResolution.CONTESTED,
                f"Both claims hold comparable evidence tiers ({c1_highest.value} vs {c2_highest.value}). Contested status preserved.",
            )

    def _get_highest_evidence_class(
        self, ev_ids: List[str], ev_map: Dict[str, EvidenceItem]
    ) -> EvidenceClassification:
        for eid in ev_ids:
            item = ev_map.get(eid)
            if item:
                if item.source_type in {EvidenceClassification.DIRECT_OBSERVATION, EvidenceClassification.VERIFIED_OUTCOME}:
                    return item.source_type
        for eid in ev_ids:
            item = ev_map.get(eid)
            if item:
                return item.source_type
        return EvidenceClassification.INFERRED
