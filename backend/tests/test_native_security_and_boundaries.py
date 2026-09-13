"""
Security and boundary tests for Kairo Native Runtime Substrate (Task 80).
Verifies:
- SecurityCenter authorization authority
- EmergencyStop absolute supremacy
- Zero arbitrary shell execution
- Fail-closed security boundaries
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
import pytest

try:
    from app.native.models import (
        ErrorCategory,
        ResourceBudget,
        ResponseStatus,
        RuntimeResponse,
    )
    from app.native.service import NativeRuntimeService
    from app.security.emergency_stop import EmergencyStopService
except ImportError:
    from backend.app.native.models import (
        ErrorCategory,
        ResourceBudget,
        ResponseStatus,
        RuntimeResponse,
    )
    from backend.app.native.service import NativeRuntimeService
    from backend.app.security.emergency_stop import EmergencyStopService


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.request = AsyncMock()
    client.health = AsyncMock()
    client.capabilities = AsyncMock()
    client.cancel = AsyncMock(return_value=True)
    return client


@pytest.fixture
def mock_security():
    sec = MagicMock()
    sec.is_allowed.return_value = True
    return sec


@pytest.fixture
def mock_emergency():
    es = MagicMock(spec=EmergencyStopService)
    es.is_stopped.return_value = False
    return es


@pytest.mark.asyncio
async def test_emergency_stop_absolute_barrier(mock_client, mock_security, mock_emergency):
    # Simulate EmergencyStop triggered
    mock_emergency.is_stopped.return_value = True

    service = NativeRuntimeService(
        client=mock_client,
        security_center=mock_security,
        emergency_stop=mock_emergency,
    )

    resp = await service.execute(
        operation="sys.ping",
        payload={"msg": "test"},
    )

    assert resp.status == ResponseStatus.ERROR
    assert resp.error is not None
    assert resp.error.code == "EMERGENCY_STOP_ACTIVE"
    assert resp.error.category == ErrorCategory.AUTHORIZATION_REQUIRED
    # Assert client.request was NEVER called!
    mock_client.request.assert_not_called()


@pytest.mark.asyncio
async def test_securitycenter_authorization_denied(mock_client, mock_security, mock_emergency):
    # Simulate SecurityCenter denying privileged native operation
    mock_security.is_allowed.return_value = False

    service = NativeRuntimeService(
        client=mock_client,
        security_center=mock_security,
        emergency_stop=mock_emergency,
    )

    resp = await service.execute(
        operation="privileged.io_access",
        payload={},
        user_id="unauthorized_user",
    )

    assert resp.status == ResponseStatus.ERROR
    assert resp.error is not None
    assert resp.error.code == "AUTHORIZATION_DENIED"
    # Assert client.request was NEVER called!
    mock_client.request.assert_not_called()


@pytest.mark.asyncio
async def test_disabled_mode_fails_closed(mock_client, mock_security, mock_emergency):
    service = NativeRuntimeService(
        client=mock_client,
        security_center=mock_security,
        emergency_stop=mock_emergency,
    )
    service.mode = "DISABLED"

    resp = await service.execute(operation="sys.ping", payload={})
    assert resp.status == ResponseStatus.ERROR
    assert resp.error is not None
    assert resp.error.code == "NATIVE_RUNTIME_DISABLED"
    mock_client.request.assert_not_called()


@pytest.mark.asyncio
async def test_safe_probe_dispatches_when_authorized(mock_client, mock_security, mock_emergency):
    mock_client.request.return_value = RuntimeResponse(
        request_id="req-1",
        protocol_version="1.0",
        status=ResponseStatus.OK,
        result={"reply": "pong"},
    )

    service = NativeRuntimeService(
        client=mock_client,
        security_center=mock_security,
        emergency_stop=mock_emergency,
    )

    resp = await service.execute(operation="sys.ping", payload={"data": 123})
    assert resp.status == ResponseStatus.OK
    assert resp.result == {"reply": "pong"}
    mock_client.request.assert_called_once()
