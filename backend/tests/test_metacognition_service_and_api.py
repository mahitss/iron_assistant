"""Unit and integration tests for MetacognitionService and FastAPI endpoints."""

from fastapi.testclient import TestClient
import pytest

from app.core.config import get_settings
from app.main import app
from app.metacognition.schemas import (
    CapabilityState,
    ExecutionReadiness,
    LimitationCategory,
    LimitationSeverity,
)
from app.metacognition.service import MetacognitionService

settings = get_settings()
client = TestClient(app)
PREFIX = f"{settings.API_V1_STR}/metacognition"


def test_metacognition_service_e2e():
    service = MetacognitionService()

    # Invariant 2: Build operational snapshot
    snapshot = service.get_self_model(user_id="alice")
    assert snapshot.version == "1.0.0"
    assert snapshot.is_operational_metadata_only is True
    assert "text_generation" in snapshot.capabilities
    assert snapshot.resource_state.compute_pressure == "NORMAL"

    # Invariants 176-178: Safe projection without sensitive credentials
    proj = service.get_user_facing_projection(user_id="alice")
    assert "version" in proj
    assert "available_capabilities" in proj
    assert "active_limitations" in proj
    # Verify no credential keys leaked
    assert "api_key" not in str(proj).lower()
    assert "jwt" not in str(proj).lower()

    # Invariant 45-47: Action readiness check
    readiness = service.check_action_readiness(
        action_name="generate_code",
        required_capabilities=["code_generation"],
        user_id="alice",
    )
    assert readiness.readiness == ExecutionReadiness.READY
    assert readiness.preconditions_met is True

    # Introspection via service
    intro_what = service.introspect("WHAT_CAN_YOU_DO")
    assert intro_what.question_type == "WHAT_CAN_YOU_DO"
    assert "text_generation" in intro_what.grounded_answer

    intro_sure = service.introspect("HOW_SURE", subject_or_action="Deployment readiness")
    assert intro_sure.question_type == "HOW_SURE"
    assert intro_sure.confidence > 0.0

    # Reconcile tools
    recon = service.reconcile(["web_search", "browser_navigate", "file_read"])
    assert recon["status"] == "RECONCILED"


def test_metacognition_api_health():
    res = client.get(f"{PREFIX}/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["is_operational_metadata_only"] is True


def test_metacognition_api_snapshot_and_projection():
    res_snap = client.get(f"{PREFIX}/self-model?user_id=bob")
    assert res_snap.status_code == 200
    snap = res_snap.json()
    assert snap["is_operational_metadata_only"] is True
    assert "text_generation" in snap["capabilities"]

    res_proj = client.get(f"{PREFIX}/self-model/projection?user_id=bob")
    assert res_proj.status_code == 200
    proj = res_proj.json()
    assert "available_capabilities" in proj


def test_metacognition_api_capabilities_and_limitations():
    res_caps = client.get(f"{PREFIX}/capabilities")
    assert res_caps.status_code == 200
    caps = res_caps.json()
    assert len(caps) >= 14

    # Register limitation via API
    res_reg = client.post(
        f"{PREFIX}/limitations",
        json={
            "category": "NETWORK",
            "description": "External third-party API rate limit exceeded",
            "scope": "EXTERNAL_API",
            "severity": "HIGH",
            "source": "MONITOR",
            "mitigation_suggestion": "Wait 60 seconds before retrying",
        },
    )
    assert res_reg.status_code == 200
    lim = res_reg.json()
    assert lim["category"] == "NETWORK"
    assert lim["status"] == "ACTIVE"

    # List limitations
    res_list = client.get(f"{PREFIX}/limitations")
    assert res_list.status_code == 200
    limits = res_list.json()
    assert any(l["category"] == "NETWORK" for l in limits)


def test_metacognition_api_readiness_and_introspect():
    # Readiness check via API
    res_readiness = client.post(
        f"{PREFIX}/readiness",
        json={
            "action_name": "delete_cluster",
            "required_capabilities": ["automation"],
            "requires_approval": True,
            "is_approved": False,
        },
    )
    assert res_readiness.status_code == 200
    readiness = res_readiness.json()
    assert readiness["readiness"] == "NEEDS_APPROVAL"
    assert "approval required" in readiness["blocking_reasons"][0].lower()

    # Introspect via API
    res_intro = client.post(
        f"{PREFIX}/introspect",
        json={
            "question_type": "WHAT_CAN_YOU_DO",
        },
    )
    assert res_intro.status_code == 200
    intro_data = res_intro.json()
    assert intro_data["question_type"] == "WHAT_CAN_YOU_DO"
    assert "text_generation" in intro_data["grounded_answer"]


def test_metacognition_api_reflection_and_metrics():
    res_refl = client.post(
        f"{PREFIX}/reflection",
        json={
            "goal": "Verify database backup",
            "attempted": "Run checksum verification script",
            "worked": ["Script initiated", "Hashes matched"],
            "failed": [],
            "verified": ["SHA-256 match confirmed"],
            "remaining_uncertainties": [],
            "lessons": ["Backup validation script is reliable"],
            "corrections_applied": [],
        },
    )
    assert res_refl.status_code == 200
    refl = res_refl.json()
    assert refl["goal"] == "Verify database backup"
    assert len(refl["lessons"]) == 1

    # Metrics endpoint
    res_metrics = client.get(f"{PREFIX}/metrics")
    assert res_metrics.status_code == 200
    metrics = res_metrics.json()
    assert "confidence_calibration" in metrics
    assert "false_capability_claims" in metrics
