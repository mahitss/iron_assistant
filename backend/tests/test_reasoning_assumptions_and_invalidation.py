"""Unit tests for Assumption Tracking & Invalidation Cascades (Task 71)."""

from app.reasoning.assumptions import AssumptionTracker
from app.reasoning.schemas import (
    AssumptionStatus,
    ConclusionStatus,
    ReasoningConclusion,
)


def test_assumption_registration_and_validation():
    """Verify assumption tracking lifecycle from UNVERIFIED to VALIDATED."""
    tracker = AssumptionTracker()

    asm = tracker.register_assumption(
        description="Configuration file schema has not been modified since release v1.8",
    )
    assert asm.status == AssumptionStatus.UNVERIFIED
    assert len(asm.dependent_conclusion_ids) == 0

    validated_asm = tracker.validate_assumption(
        assumption_id=asm.assumption_id,
        validation_source="git diff origin/main - zero delta verified",
    )
    assert validated_asm.status == AssumptionStatus.VALIDATED
    assert "git diff" in validated_asm.validation_source


def test_assumption_invalidation_cascades_to_dependent_conclusions():
    """Verify that invalidating an assumption cascades and marks all dependent conclusions INVALIDATED."""
    tracker = AssumptionTracker()

    asm = tracker.register_assumption(
        description="Deployment configuration was identical across all availability zones",
    )

    concl_1 = ReasoningConclusion(
        summary="AZ-1 failure caused by upstream cloud provider network drop",
        status=ConclusionStatus.SUPPORTED,
        assumption_ids=[asm.assumption_id],
        is_verified=True,
    )
    concl_2 = ReasoningConclusion(
        summary="AZ-2 traffic routing remained unaffected",
        status=ConclusionStatus.SUPPORTED,
        assumption_ids=[asm.assumption_id],
    )
    concl_independent = ReasoningConclusion(
        summary="Database disk IOPS are within provisioned limits",
        status=ConclusionStatus.SUPPORTED,
        assumption_ids=[],
    )

    tracker.link_conclusion(asm.assumption_id, concl_1.conclusion_id)
    tracker.link_conclusion(asm.assumption_id, concl_2.conclusion_id)

    pool = [concl_1, concl_2, concl_independent]

    # Invalidate the underlying assumption
    updated_asm, affected = tracker.invalidate_assumption(
        assumption_id=asm.assumption_id,
        reason="Zone AZ-1 had distinct override flag enabled in config map",
        conclusions_pool=pool,
    )

    assert updated_asm.status == AssumptionStatus.INVALIDATED
    assert len(affected) == 2
    assert concl_1.conclusion_id in affected
    assert concl_2.conclusion_id in affected

    # Dependent conclusions must now be INVALIDATED and unverified
    assert concl_1.status == ConclusionStatus.INVALIDATED
    assert concl_1.is_verified is False
    assert concl_2.status == ConclusionStatus.INVALIDATED

    # Independent conclusion must remain intact
    assert concl_independent.status == ConclusionStatus.SUPPORTED
