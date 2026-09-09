"""Tests for Claims, Evidence, Provenance, and Anti-Self-Attestation (Task 42)."""

import pytest
from app.verification.claims import Claim, ClaimType, TruthStatus
from app.verification.evidence import Evidence, EvidenceType
from app.verification.provenance import ProvenanceChain
from app.verification.service import VerificationService


def test_claim_model_and_types():
    """Verify claim creation across supported claim types and truth statuses."""
    claim = Claim(
        claim_id="clm-001",
        statement="Database migration applied",
        claim_type=ClaimType.STATE,
        subject="db_migration",
        predicate="status",
        object_ref="applied",
        source="system",
        truth_status=TruthStatus.UNVERIFIED,
    )
    assert claim.claim_id == "clm-001"
    assert claim.claim_type == ClaimType.STATE
    assert claim.truth_status == TruthStatus.UNVERIFIED

    d = claim.to_dict()
    assert d["claim_type"] == "STATE"
    assert d["truth_status"] == "UNVERIFIED"


def test_anti_self_attestation_model_claims():
    """Model assertion saying 'done' or 'fixed' must NOT be marked VERIFIED automatically (Spec 19, 75)."""
    service = VerificationService()
    claim = service.register_claim(
        statement="Task is completed and bug is fixed",
        claim_type=ClaimType.MODEL_ASSERTION,
        subject="task_123",
        predicate="status",
        object_ref="COMPLETED",
        source="model",
    )
    # Origin does not determine truth; model assertion cannot self-certify
    assert claim.truth_status == TruthStatus.UNVERIFIED
    assert claim.confidence == "LOW"


def test_claim_deduplication():
    """Identical claims within same scope should be deduplicated (Spec 68)."""
    service = VerificationService()
    c1 = service.register_claim(
        statement="Server healthy",
        subject="srv_prod",
        predicate="health",
        object_ref="healthy",
        scope={"project_id": "proj-1"},
    )
    c2 = service.register_claim(
        statement="Server healthy",
        subject="srv_prod",
        predicate="health",
        object_ref="healthy",
        scope={"project_id": "proj-1"},
    )
    assert c1.claim_id == c2.claim_id


def test_evidence_model_and_reliability_scoring():
    """Evidence calculation must score reliability based on source type (Spec 15)."""
    ev_direct = Evidence(
        evidence_id="ev-1",
        source_type=EvidenceType.DIRECT_OBSERVATION,
        source_reference="system_probe",
        observation={"status": "ok"},
    )
    ev_model = Evidence(
        evidence_id="ev-2",
        source_type=EvidenceType.MODEL_INFERENCE,
        source_reference="llm_output",
        observation={"status": "ok"},
    )

    # Direct observation has higher authority than model inference
    assert ev_direct.calculate_reliability() > ev_model.calculate_reliability()
    assert ev_direct.calculate_reliability() >= 0.95
    assert ev_model.calculate_reliability() <= 0.45


def test_evidence_secret_redaction():
    """Evidence registration must automatically redact secrets and tokens (Spec 180, 181)."""
    service = VerificationService()
    ev = service.register_evidence(
        source_type=EvidenceType.API_RESPONSE,
        source_reference="auth_endpoint",
        observation={
            "token": "ghp_12345678901234567890",
            "password": "secret_password_123",
            "status": "active",
        },
    )
    obs = ev.observation
    assert obs["token"] != "ghp_12345678901234567890"
    assert obs["password"] != "secret_password_123"
    assert "[REDACTED" in obs["token"]
    assert "[REDACTED" in obs["password"]
    assert obs["status"] == "active"


def test_provenance_chain_tracking():
    """Important claims must preserve full provenance chains (Spec 16, 17)."""
    chain = ProvenanceChain(claim_id="clm-99")
    chain.add_step(action="created", source="model_planner")
    chain.add_step(action="evidence_attached", source="deployment_api", evidence_ref="ev-101")
    chain.add_step(action="verified", source="health_probe", evidence_ref="ev-102")

    d = chain.to_dict()
    assert d["claim_id"] == "clm-99"
    assert len(d["steps"]) == 3
    assert d["steps"][1]["evidence_ref"] == "ev-101"
    assert d["steps"][2]["source"] == "health_probe"
