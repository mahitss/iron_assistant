"""Unit tests for assertions, facts vs inferences, contradictions, and domain authority reconciliation."""

from datetime import UTC, datetime, timedelta
import pytest

from app.knowledge_graph.assertions import AssertionManager, InferenceFactViolationError
from app.knowledge_graph.contradictions import ContradictionDetector
from app.knowledge_graph.facts import FactValidator
from app.knowledge_graph.reconciliation import ContradictionReconciler
from app.knowledge_graph.schemas import AssertionStatus, ScopeType


def test_inference_fact_segregation():
    mgr = AssertionManager()

    # Invariants 13 & 14: Inferred assertion cannot be saved as active known fact without validation/high confidence
    with pytest.raises(InferenceFactViolationError, match="Cannot store inferred assertion .* as active known fact"):
        mgr.create_assertion(
            subject="ProjectX",
            predicate="USES_DATABASE",
            object_val="MongoDB",
            is_inferred=True,
            status=AssertionStatus.ACTIVE,
            confidence=0.5,
        )

    # Valid unverified inferred assertion
    inferred = mgr.create_assertion(
        subject="ProjectX",
        predicate="USES_DATABASE",
        object_val="PostgreSQL",
        is_inferred=True,
        confidence=0.6,
    )
    assert inferred.is_inferred is True
    assert inferred.status == AssertionStatus.UNVERIFIED

    # Fact validator checks threshold
    assert FactValidator.is_fact(inferred) is False

    # Explicit user fact
    user_fact = mgr.create_assertion(
        subject="ProjectX",
        predicate="USES_DATABASE",
        object_val="PostgreSQL",
        is_inferred=False,
        confidence=1.0,
        source={"source_type": "USER"},
    )
    assert FactValidator.is_fact(user_fact) is True


def test_contradiction_detection_and_reconciliation():
    mgr = AssertionManager()
    detector = ContradictionDetector()

    # Step 1: Older assertion from external web scrape
    a1 = mgr.create_assertion(
        subject="KairoRepo",
        predicate="PRIMARY_LANGUAGE",
        object_val="JavaScript",
        source={"source_type": "web_scrape"},
        confidence=0.7,
        is_inferred=False,
        status=AssertionStatus.ACTIVE,
    )

    # Step 2: New authoritative assertion from GitHub
    a2 = mgr.create_assertion(
        subject="KairoRepo",
        predicate="PRIMARY_LANGUAGE",
        object_val="Python",
        source={"source_type": "GITHUB"},
        confidence=1.0,
        is_inferred=False,
        status=AssertionStatus.ACTIVE,
    )

    # Detect contradiction
    conflict = detector.check_conflict(a2, [a1])
    assert conflict is not None
    assert conflict.subject == "KairoRepo"
    assert len(conflict.conflicting_assertions) == 2

    # Step 3: Reconcile using domain authority (GitHub overrides web_scrape)
    assertions_map = {a1.assertion_id: a1, a2.assertion_id: a2}
    resolution = ContradictionReconciler.reconcile(conflict, assertions_map)

    assert resolution["winning_assertion_id"] == a2.assertion_id
    assert a2.status == AssertionStatus.ACTIVE
    assert a1.status == AssertionStatus.SUPERSEDED
    assert conflict.status == "RESOLVED"
