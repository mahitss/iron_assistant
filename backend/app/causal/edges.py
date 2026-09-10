"""CausalEdge creation, validation, and status tracking (Task 55, Prompt #4)."""

from __future__ import annotations

from datetime import datetime

from app.causal.safety import CausalSafetyGuard
from app.causal.schemas import (
    CausalEdge,
    CausalEdgeStatus,
    CausalEvidence,
    CausalRelationshipType,
    CausalScope,
)
from app.causal.temporal import utc_now


def generate_edge_id(cause: str, relationship: CausalRelationshipType, effect: str) -> str:
    """Generates deterministic edge identifier."""
    return f"cedge_{cause}__{relationship.value}__{effect}"


def create_causal_edge(
    cause: str,
    effect: str,
    relationship: CausalRelationshipType,
    confidence: float = 0.5,
    evidence_refs: list[str] | None = None,
    evidence_objects: list[CausalEvidence] | None = None,
    scope: CausalScope = CausalScope.SYSTEM,
    valid_from: datetime | None = None,
    valid_until: datetime | None = None,
    status: CausalEdgeStatus | None = None,
) -> CausalEdge:
    """Creates a validated CausalEdge with safety checks against false causality."""
    # Safety invariant: if direct causal claim, validate evidence
    if evidence_objects:
        CausalSafetyGuard.validate_causal_claim(relationship, evidence_objects)

    final_status = status or (CausalEdgeStatus.ACTIVE if confidence >= 0.6 else CausalEdgeStatus.CANDIDATE)
    edge_id = generate_edge_id(cause, relationship, effect)
    return CausalEdge(
        edge_id=edge_id,
        cause=cause,
        effect=effect,
        relationship=relationship,
        confidence=round(max(0.0, min(1.0, confidence)), 2),
        evidence_refs=evidence_refs or [],
        scope=scope,
        valid_from=valid_from or utc_now(),
        valid_until=valid_until,
        status=final_status,
    )


def validate_edge(edge: CausalEdge, evidence_objects: list[CausalEvidence] | None = None) -> bool:
    """Validates edge relationship against evidence."""
    if evidence_objects:
        CausalSafetyGuard.validate_causal_claim(edge.relationship, evidence_objects)
    return True

