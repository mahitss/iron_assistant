"""Tests for Evidence trust grading, Causal reasoning, and Uncertainty quantification (Task 57)."""

from app.decision.evidence import EvidenceEngine
from app.decision.schemas import (
    CandidateOption,
    DataTrustLevel,
    DecisionRequest,
    EvidenceItem,
    EvidenceStrength,
    OptionType,
)
from app.decision.uncertainty import UncertaintyEngine


def test_evidence_trust_grading_and_classification():
    engine = EvidenceEngine()

    provided = [
        EvidenceItem(
            evidence_type="audit_log",
            strength=EvidenceStrength.VERIFIED,
            trust_level=DataTrustLevel.TRUSTED_SYSTEM_DATA,
            source="audit_trail",
            summary="Immutable audit record verified.",
            is_primary=True,
        ),
        EvidenceItem(
            evidence_type="web_scraping_report",
            strength=EvidenceStrength.SPECULATIVE,
            trust_level=DataTrustLevel.UNVERIFIED_EXTERNAL_DATA,
            source="external_blog",
            summary="External blog claims new vulnerability.",
            is_primary=False,
        ),
    ]

    evidence_set = engine.build_evidence_set(
        decision_id="dec_test_ev",
        provided_items=provided,
        digital_twin_state={"scope": "PRODUCTION"},
        causal_inference={"suspected_cause": "connection_pool_starvation", "confidence_score": 0.88},
    )

    assert len(evidence_set.items) == 4
    # Untrusted/unverified external items are counted
    assert evidence_set.untrusted_data_count >= 1
    # Primary verified telemetry ensures overall strength is VERIFIED
    assert evidence_set.overall_strength == EvidenceStrength.VERIFIED


def test_uncertainty_quantification_with_stale_simulation():
    uncertainty_engine = UncertaintyEngine()
    evidence_engine = EvidenceEngine()

    req = DecisionRequest(
        question="Should we migrate production databases tonight?",
        intent="DATABASE_MIGRATION",
    )

    options = [
        CandidateOption(
            name="Immediate Migration",
            option_type=OptionType.AGGRESSIVE,
            metrics={"cost": 50.0},
        )
    ]

    evidence_set = evidence_engine.build_evidence_set(decision_id=req.request_id)

    # Simulation is marked STALE due to schema drift
    simulations = [
        {"simulation_id": "sim_yesterday", "confidence": 0.8, "is_stale": True}
    ]

    uncertainty = uncertainty_engine.assess_uncertainty(
        request=req,
        options=options,
        evidence_set=evidence_set,
        simulations=simulations,
        stale_environment=True,
    )

    # Confidence must NOT equal the highest option score
    assert uncertainty.confidence < 0.70
    assert len(uncertainty.stale_signals) >= 2
    # Invariant: Safe to proceed is FALSE when critical stale signals exist
    assert not uncertainty.safe_to_proceed
    assert uncertainty.overall_uncertainty in {"HIGH", "CRITICAL"}
