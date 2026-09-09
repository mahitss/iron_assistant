"""Tests for Kairo V1.1.0 Release Engineering, Observability, and Operations."""

import json
import sys
from pathlib import Path

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.config.settings import get_settings
from app.main import app
from app.observability.health import generate_incident_id

# Ensure repo root is available for scripts imports
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.smoke_test import SmokeTestRunner  # noqa: E402


@pytest.fixture
def client():
    return TestClient(app)


def test_authoritative_version_constant():
    """Verify one authoritative application version is set to 1.1.0."""
    settings = get_settings()
    assert settings.VERSION == "1.1.0"
    assert "Kairo" in settings.PROJECT_NAME


def test_health_version_endpoint(client):
    """GET /health/version returns safe version, git_sha, build_timestamp without secrets."""
    res = client.get("/health/version")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["version"] == "1.1.0"
    assert "git_sha" in data
    assert "build_timestamp" in data
    assert "environment" in data

    # Verify zero secrets leaked
    text_data = json.dumps(data).lower()
    for sensitive_keyword in ["secret", "password", "token", "sk-", "key="]:
        assert sensitive_keyword not in text_data


def test_health_operations_endpoint(client):
    """GET /health/operations exposes full operational dashboard safely."""
    res = client.get("/health/operations")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()

    assert data["title"] == "KAIRO OPERATIONS"
    assert data["version"] == "1.1.0"
    assert "uptime" in data
    assert "requests" in data
    assert "error_rate" in data
    assert "latency" in data

    subsystems = data["subsystems"]
    assert "database" in subsystems
    assert "redis" in subsystems
    assert "model" in subsystems
    assert "automations" in subsystems
    assert "agents" in subsystems
    assert "security" in subsystems
    assert "github" in subsystems
    assert "browser" in subsystems

    for name, stat in subsystems.items():
        assert "HEALTHY" in stat or "DEGRADED" in stat or "UNAVAILABLE" in stat

    assert "incident_correlation" in data
    assert data["incident_correlation"]["format"] == "INC-YYYYMMDDHHMM-<uuid>"


def test_incident_id_generator():
    """Verify structured, unique incident correlation identifiers."""
    inc_id = generate_incident_id("AUTH")
    assert inc_id.startswith("AUTH-")
    parts = inc_id.split("-")
    assert len(parts) == 3
    assert len(parts[1]) == 12  # YYYYMMDDHHMM
    assert len(parts[2]) == 8  # 8-char hex

    # Default category
    default_id = generate_incident_id()
    assert default_id.startswith("INC-")


def test_smoke_test_runner_in_process():
    """Verify the automated smoke test runner executes and succeeds in-process."""
    runner = SmokeTestRunner(base_url="http://testserver", environment="staging", in_process=True)
    success = runner.run_all()
    assert success is True
    assert len(runner.results) >= 5
    assert all(r["passed"] for r in runner.results)


def test_release_manifest_structure():
    """Verify generated release manifest contains all audit fields and no secrets."""
    manifest_path = Path(__file__).resolve().parent.parent.parent / "release_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["release_version"] == "1.1.0"
        assert "git_sha" in manifest
        assert "backend_image" in manifest
        assert "frontend_artifact" in manifest
        assert "migration_version" in manifest
        assert manifest["release_decision"] in ("READY FOR RELEASE", "READY WITH NON-CRITICAL ISSUES")
