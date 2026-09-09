"""Unit tests for draft generation, tone adaptation, hallucination control, and sentiment safety."""

import pytest

from app.communication.drafts import DraftEngine, DraftHallucinationError
from app.communication.schemas import (
    CommunicationTone,
    DraftStatus,
    RecipientSchema,
)
from app.communication.sentiment import (
    PsychologicalDiagnosisViolationError,
    SentimentAnalyzer,
)


def test_draft_lifecycle_and_provenance():
    engine = DraftEngine()
    recipients = [RecipientSchema(identity="bob@example.com", address="bob@example.com")]

    draft = engine.create_draft(
        recipients=recipients,
        subject="Project Status Update",
        body="Here is the progress report for this sprint.",
        tone=CommunicationTone.FORMAL,
        source_context={"project_name": "Kairo Core"},
    )

    # INVARIANT 47: Draft != Sent
    assert draft.status == DraftStatus.DRAFT
    assert draft.approved_by is None
    assert "project_name" in draft.provenance["grounded_sources"]

    # Approval
    approved = engine.approve_draft(draft.draft_id, "user@kairo.internal")
    assert approved.status == DraftStatus.APPROVED
    assert approved.approved_by == "user@kairo.internal"

    # INVARIANT 109: Material draft edits invalidate previous approval
    modified = engine.update_draft(draft.draft_id, new_body="Revised progress report content.")
    assert modified.status == DraftStatus.REVIEWED
    assert modified.approved_by is None


def test_draft_hallucination_control():
    engine = DraftEngine()
    recipients = [RecipientSchema(identity="bob@example.com", address="bob@example.com")]

    # Asserting "attached is" without verified attachment in source context must raise DraftHallucinationError
    with pytest.raises(DraftHallucinationError):
        engine.create_draft(
            recipients=recipients,
            subject="Invoice",
            body="Attached is the signed payment invoice.",
            source_context={"attachments": []},  # Empty attachments
        )


def test_sentiment_analysis_safe_signal_boundary():
    analyzer = SentimentAnalyzer()

    res = analyzer.analyze("I am really frustrated that the build broke again.")
    assert res["surface_sentiment"] == "frustrated"
    # INVARIANT 40: Must explicitly declare itself as an uncertain operational signal
    assert res["is_uncertain_signal"] is True
    assert "never be treated as clinical fact" in res["disclaimer"]

    # INVARIANT 41: Clinical/psychological diagnosis terms are strictly prohibited
    with pytest.raises(PsychologicalDiagnosisViolationError):
        analyzer.analyze("The client seems clinically depressed and bipolar.")
