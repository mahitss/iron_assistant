"""Belief Snapshot Engine for Task 107.

Creates immutable, verifiable point-in-time snapshots of the belief manifold.
Enables exact decision-time epistemic reconstruction for:
- Task 94 Decision Intelligence
- Task 100 Mission Control Checkpoints
- Task 105 Experiment Runs & Adaptation Plans
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.belief.domain import (
    Belief,
    BeliefSnapshot,
    EvidenceItem,
    generate_uuid,
    utc_now,
)

logger = logging.getLogger("kairo.belief.snapshots")


class BeliefSnapshotEngine:
    """Creates and verifies immutable point-in-time epistemic snapshots."""

    def __init__(self) -> None:
        self._snapshots: Dict[str, BeliefSnapshot] = {}

    def capture_snapshot(
        self,
        beliefs: List[Belief],
        evidence_items: List[EvidenceItem],
        trigger_type: str = "MANUAL",
        reference_id: Optional[str] = None,
        scope: str = "SYSTEM",
    ) -> BeliefSnapshot:
        """Capture immutable snapshot of current active beliefs and supporting evidence."""
        b_manifest = [
            {
                "belief_id": b.belief_id,
                "version": b.current_version,
                "subject": b.subject,
                "predicate": b.predicate,
                "status": b.status.value,
                "confidence": b.confidence,
                "uncertainty": b.uncertainty,
                "scope": b.scope,
                "is_stale": b.is_stale,
                "evidence_ids": list(b.evidence_ids),
                "contradiction_ids": list(b.contradiction_evidence_ids),
            }
            for b in beliefs
        ]

        e_manifest = [
            {
                "evidence_id": e.evidence_id,
                "source_id": e.source_id,
                "source_type": e.source_type.value,
                "scope": e.scope,
                "summary": e.summary,
                "content_hash": e.content_hash,
                "weight": e.reliability_weight,
            }
            for e in evidence_items
        ]

        snapshot = BeliefSnapshot(
            snapshot_id=generate_uuid("bsnap"),
            trigger_type=trigger_type,
            reference_id=reference_id,
            scope=scope,
            beliefs_manifest=b_manifest,
            evidence_manifest=e_manifest,
            created_at=utc_now(),
        )

        self._snapshots[snapshot.snapshot_id] = snapshot
        logger.info(
            "BELIEF_SNAPSHOT_CAPTURED: id=%s trigger=%s ref=%s (beliefs=%d, evidence=%d, hash=%s)",
            snapshot.snapshot_id,
            trigger_type,
            reference_id,
            len(b_manifest),
            len(e_manifest),
            snapshot.integrity_hash[:8],
        )
        return snapshot

    def get_snapshot(self, snapshot_id: str) -> Optional[BeliefSnapshot]:
        return self._snapshots.get(snapshot_id)

    def verify_snapshot_integrity(self, snapshot: BeliefSnapshot) -> bool:
        """Verify content hash has not been tampered with."""
        from app.belief.domain import compute_content_hash
        expected_hash = compute_content_hash({
            "snapshot_id": snapshot.snapshot_id,
            "trigger_type": snapshot.trigger_type,
            "reference_id": snapshot.reference_id,
            "beliefs": snapshot.beliefs_manifest,
        })
        return snapshot.integrity_hash == expected_hash
