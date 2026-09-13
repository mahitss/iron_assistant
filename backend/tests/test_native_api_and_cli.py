"""
API and CLI tests for Kairo Native Runtime Substrate (Task 80).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from click.testing import CliRunner
from fastapi.testclient import TestClient
import pytest

from app.main import create_app
from app.native.cli import native_cli
from app.native.models import (
    CapabilityDescriptor,
    ExecutionClass,
    ResponseStatus,
    RuntimeResponse,
    SideEffectClass,
)
from app.native.router import get_native_service


@pytest.fixture
def mock_service():
    svc = MagicMock()
    svc.get_health = AsyncMock(return_value={
        "status": "READY",
        "healthy": True,
        "mode": "OPTIONAL",
        "message": "Substrate ready",
        "metadata": None,
    })
    svc.list_capabilities = AsyncMock(return_value=[
        CapabilityDescriptor(
            capability_id="sys.ping",
            name="System Ping",
            version="1.0.0",
            description="Probe",
            available=True,
            execution_class=ExecutionClass.PURE_COMPUTE,
            side_effect_class=SideEffectClass.NONE,
            supported_operations=["sys.ping"],
        )
    ])
    svc.execute = AsyncMock(return_value=RuntimeResponse(
        request_id="req-ping",
        protocol_version="1.0",
        status=ResponseStatus.OK,
        result={"reply": "pong"},
    ))
    svc.cancel = AsyncMock(return_value=True)
    return svc


@pytest.fixture
def test_client(mock_service):
    app = create_app()
    app.dependency_overrides[get_native_service] = lambda: mock_service
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_native_health_endpoint(test_client):
    response = test_client.get("/api/v1/native/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "READY"
    assert data["healthy"] is True


def test_native_capabilities_endpoint(test_client):
    response = test_client.get("/api/v1/native/capabilities")
    assert response.status_code == 200
    caps = response.json()
    assert len(caps) == 1
    assert caps[0]["capability_id"] == "sys.ping"


def test_native_ping_endpoint(test_client):
    response = test_client.post("/api/v1/native/ping", json={"message": "hello"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "OK"
    assert data["result"]["reply"] == "pong"


def test_native_cli_status():
    runner = CliRunner()
    with patch("app.native.cli.NativeRuntimeService.get_instance") as mock_get:
        mock_svc = mock_get.return_value
        mock_svc.get_health = AsyncMock(return_value={
            "status": "READY",
            "healthy": True,
            "mode": "OPTIONAL",
            "message": "Operational",
            "metadata": {
                "runtime_version": "0.1.0",
                "protocol_version": "1.0",
                "platform": "windows",
                "arch": "x86_64",
                "uptime_seconds": 120,
                "active_requests": 0,
                "capabilities": ["sys.ping", "sys.health"],
            },
        })

        result = runner.invoke(native_cli, ["status"])
        assert result.exit_code == 0
        assert "KAIRO NATIVE RUNTIME SUBSTRATE STATUS" in result.output
        assert "READY" in result.output
        assert "0.1.0" in result.output


def test_native_cli_capabilities():
    runner = CliRunner()
    with patch("app.native.cli.NativeRuntimeService.get_instance") as mock_get:
        mock_svc = mock_get.return_value
        mock_svc.list_capabilities = AsyncMock(return_value=[
            CapabilityDescriptor(
                capability_id="sys.ping",
                name="System Ping",
                version="1.0.0",
                description="Probe",
                available=True,
                execution_class=ExecutionClass.PURE_COMPUTE,
                side_effect_class=SideEffectClass.NONE,
                supported_operations=["sys.ping"],
            )
        ])

        result = runner.invoke(native_cli, ["capabilities"])
        assert result.exit_code == 0
        assert "sys.ping" in result.output
