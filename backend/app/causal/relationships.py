"""Causal Relationship Types, Semantics, and Composition (Task 55, Prompt #5)."""

from __future__ import annotations

from app.causal.schemas import CausalRelationshipType


def is_direct_causal(rel: CausalRelationshipType) -> bool:
    """Checks if relationship implies direct generative causality."""
    return rel in (
        CausalRelationshipType.CAUSES,
        CausalRelationshipType.CONTRIBUTES_TO,
        CausalRelationshipType.ENABLES,
        CausalRelationshipType.PREVENTS,
    )


def is_non_causal_association(rel: CausalRelationshipType) -> bool:
    """Checks if relationship represents mere association or dependency rather than direct causation."""
    return rel in (
        CausalRelationshipType.CORRELATES_WITH,
        CausalRelationshipType.TEMPORALLY_PRECEDES,
        CausalRelationshipType.DEPENDS_ON,
        CausalRelationshipType.UNKNOWN,
    )


def compose_path_confidence(step_confidences: list[float]) -> float:
    """Prompt #57: Combined causal confidence must account for weakest links in the path."""
    if not step_confidences:
        return 0.0
    # Weakest link (min) penalized slightly by path length
    weakest = min(step_confidences)
    length_penalty = 0.95 ** (len(step_confidences) - 1)
    return round(max(0.05, weakest * length_penalty), 2)


is_direct_causal_relationship = is_direct_causal

