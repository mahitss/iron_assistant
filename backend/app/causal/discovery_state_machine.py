"""Explicit 10-state lifecycle engine for Causal Discovery (Task 73, Spec 4).

Epistemic Invariant:
NO SILENT PROMOTION.
Transitions must be explicit, justified by evidence, and preserve audit history.
"""

from __future__ import annotations

import logging

from app.causal.discovery_schemas import (
    CausalRelationship,
    CausalRelationshipState,
)

logger = logging.getLogger(__name__)


class CausalStateTransitionError(ValueError):
    """Raised when an illegal or unsupported state transition is attempted."""


class CausalDiscoveryStateMachine:
    """Validates and applies explicit state transitions for Causal Relationships."""

    # Legal forward and backward transitions
    _LEGAL_TRANSITIONS: dict[CausalRelationshipState, set[CausalRelationshipState]] = {
        CausalRelationshipState.CANDIDATE: {
            CausalRelationshipState.HYPOTHESIZED,
            CausalRelationshipState.INVALIDATED,
            CausalRelationshipState.UNKNOWN,
        },
        CausalRelationshipState.HYPOTHESIZED: {
            CausalRelationshipState.SUPPORTED,
            CausalRelationshipState.CONTRADICTED,
            CausalRelationshipState.INVALIDATED,
            CausalRelationshipState.UNKNOWN,
        },
        CausalRelationshipState.SUPPORTED: {
            CausalRelationshipState.STRONGLY_SUPPORTED,
            CausalRelationshipState.CONTRADICTED,
            CausalRelationshipState.INVALIDATED,
            CausalRelationshipState.CONTEXTUAL,
            CausalRelationshipState.SUPERSEDED,
            CausalRelationshipState.UNKNOWN,
        },
        CausalRelationshipState.STRONGLY_SUPPORTED: {
            CausalRelationshipState.VERIFIED,
            CausalRelationshipState.CONTRADICTED,
            CausalRelationshipState.INVALIDATED,
            CausalRelationshipState.CONTEXTUAL,
            CausalRelationshipState.SUPERSEDED,
        },
        CausalRelationshipState.VERIFIED: {
            CausalRelationshipState.CONTRADICTED,
            CausalRelationshipState.INVALIDATED,
            CausalRelationshipState.SUPERSEDED,
            CausalRelationshipState.CONTEXTUAL,
        },
        CausalRelationshipState.CONTRADICTED: {
            CausalRelationshipState.INVALIDATED,
            CausalRelationshipState.CONTEXTUAL,
            CausalRelationshipState.HYPOTHESIZED,  # If contradiction was situational
            CausalRelationshipState.UNKNOWN,
        },
        CausalRelationshipState.INVALIDATED: {
            # Terminal or archivable; cannot silently revive without complete new proposal
        },
        CausalRelationshipState.SUPERSEDED: {
            # Historical record superseded by newer version
        },
        CausalRelationshipState.CONTEXTUAL: {
            CausalRelationshipState.SUPPORTED,
            CausalRelationshipState.STRONGLY_SUPPORTED,
            CausalRelationshipState.CONTRADICTED,
            CausalRelationshipState.INVALIDATED,
            CausalRelationshipState.SUPERSEDED,
        },
        CausalRelationshipState.UNKNOWN: {
            CausalRelationshipState.CANDIDATE,
            CausalRelationshipState.HYPOTHESIZED,
            CausalRelationshipState.INVALIDATED,
        },
    }

    @classmethod
    def can_transition(
        cls,
        current_state: CausalRelationshipState,
        target_state: CausalRelationshipState,
    ) -> bool:
        """Check if transition is topologically allowed."""
        if current_state == target_state:
            return True
        allowed = cls._LEGAL_TRANSITIONS.get(current_state, set())
        return target_state in allowed

    @classmethod
    def transition(
        cls,
        relationship: CausalRelationship,
        target_state: CausalRelationshipState,
        reason: str,
        actor: str = "SYSTEM",
        evidence_ref: str | None = None,
        verification_ref: str | None = None,
        is_controlled_experiment: bool = False,
    ) -> CausalRelationship:
        """Execute an explicit state transition with strict invariant validation."""
        current_state = relationship.status

        if current_state == target_state:
            return relationship

        if not cls.can_transition(current_state, target_state):
            raise CausalStateTransitionError(
                f"Illegal causal transition from '{current_state.value}' to '{target_state.value}'. "
                f"Relation {relationship.causal_relation_id} cannot bypass intermediate lifecycle phases."
            )

        # Invariant 1: VERIFIED promotion strictly requires controlled intervention or verification ref
        if target_state == CausalRelationshipState.VERIFIED:
            has_experiment = bool(relationship.experiment_refs) or is_controlled_experiment
            has_verification = bool(relationship.verification_refs) or bool(verification_ref)
            if not (has_experiment or has_verification):
                raise CausalStateTransitionError(
                    "Causal Invariant Violation: Promotion to VERIFIED requires a verified controlled "
                    "experiment or formal verification reference. Precedence or correlation alone is insufficient."
                )

        # Invariant 2: Promotion to SUPPORTED or STRONGLY_SUPPORTED requires evidence
        if target_state in {CausalRelationshipState.SUPPORTED, CausalRelationshipState.STRONGLY_SUPPORTED}:
            if not relationship.evidence_refs and not evidence_ref:
                raise CausalStateTransitionError(
                    f"Causal Invariant Violation: Promotion to {target_state.value} requires attached evidence."
                )

        # Record audit trail in provenance
        provenance = dict(relationship.provenance or {})
        history = list(provenance.get("state_history", []))
        history.append({
            "from_state": current_state.value,
            "to_state": target_state.value,
            "actor": actor,
            "reason": reason,
            "evidence_ref": evidence_ref,
            "verification_ref": verification_ref,
            "timestamp": relationship.updated_at.isoformat(),
        })
        provenance["state_history"] = history
        relationship.provenance = provenance

        if evidence_ref and evidence_ref not in relationship.evidence_refs:
            relationship.evidence_refs.append(evidence_ref)
        if verification_ref and verification_ref not in relationship.verification_refs:
            relationship.verification_refs.append(verification_ref)

        relationship.status = target_state
        relationship.change_reason = reason
        return relationship
