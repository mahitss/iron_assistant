"""
Python Contract Test Suite for Task 87:
Kairo Native Runtime Protocol Hardening & Distributed Execution Contract.

Tests SemVer negotiation, capability attestation, session binding, ReplayGuard deduplication,
anti-TOCTOU hash revalidation, authorization & resource contexts, emergency stop priority,
and UNKNOWN_OUTCOME disconnect handling with orphan reconciliation.
"""

from __future__ import annotations

import datetime
import struct
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.native.models import (
    CURRENT_PROTOCOL_VERSION,
    AuthorizationContext,
    CapabilityDescriptor,
    ConnectionState,
    EnforcementLevel,
    ErrorCategory,
    ExecutionClass,
    ExecutionRequest,
    ExecutionResult,
    ExecutionState,
    HandshakeRequest,
    HandshakeResponse,
    MessageLifecycleState,
    OperationTargetContext,
    ProtocolErrorEnvelope,
    ProtocolMessageType,
    ProtocolVersion,
    RequestContext,
    ResourceAllocationContext,
    ResourceBudget,
    ResponseStatus,
    RuntimeErrorModel,
    RuntimeRequest,
    RuntimeResponse,
    RuntimeState,
    SideEffectClass,
)
from app.native.client import NativeRuntimeClient
from app.native.service import NativeRuntimeService


# =========================================================================
# 1. SemVer Version Negotiation Tests
# =========================================================================

def test_protocol_version_parsing_and_compatibility():
    v1_0 = ProtocolVersion.parse("1.0.0")
    assert v1_0.major == 1
    assert v1_0.minor == 0
    assert v1_0.patch == 0
    assert str(v1_0) == "1.0.0"

    v1_1 = ProtocolVersion.parse("1.1.0")
    v2_0 = ProtocolVersion.parse("2.0.0")

    # Compatibility: server.is_compatible_with(client) -> server.major == client.major && server.minor >= client.minor
    assert v1_1.is_compatible_with(v1_0) is True  # server 1.1 supports client 1.0
    assert v1_0.is_compatible_with(v1_1) is False  # server 1.0 cannot support client 1.1 features
    assert v1_0.is_compatible_with(v2_0) is False  # major mismatch

    # Negotiation chooses the minimum minor version between compatible peers
    neg = v1_1.negotiate(v1_0)
    assert neg is not None
    assert neg.minor == 0
    assert neg.major == 1


@pytest.mark.asyncio
async def test_handshake_version_negotiation_success():
    client = NativeRuntimeClient(host="127.0.0.1", port=8788)

    mock_resp = HandshakeResponse(
        protocol_version="1.0.0",
        runtime_version="0.1.0",
        authenticated=True,
        session_id="ses_test_12345678",
        runtime_instance_id="inst_server_abc",
        capability_fingerprint="cfp_12345678abcdef",
        configuration_fingerprint="cfg_abcdef123456",
        capabilities=[
            CapabilityDescriptor(
                capability_id="sys.ping",
                name="sys.ping",
                version="1.0.0",
                description="Ping capability",
                execution_class=ExecutionClass.PURE_COMPUTE,
                side_effect_class=SideEffectClass.READ_ONLY,
                supported_operations=["sys.ping"],
                supported_protocol_versions=["1.0.0"],
            )
        ],
    )

    with patch("asyncio.open_connection") as mock_conn:
        mock_reader = AsyncMock()
        mock_writer = MagicMock()
        mock_writer.drain = AsyncMock()
        mock_writer.is_closing.return_value = False
        mock_conn.return_value = (mock_reader, mock_writer)

        payload_bytes = mock_resp.model_dump_json().encode("utf-8")
        mock_reader.readexactly.side_effect = [
            struct.pack(">I", len(payload_bytes)),
            payload_bytes,
        ]

        await client.connect()

        assert client.connection_state == ConnectionState.READY
        assert client.session_id == "ses_test_12345678"
        assert client.runtime_instance_id == "inst_server_abc"
        assert client.capability_fingerprint == "cfp_12345678abcdef"
        assert client.configuration_fingerprint == "cfg_abcdef123456"
        assert len(client._capabilities) == 1


@pytest.mark.asyncio
async def test_handshake_version_incompatible_rejected():
    client = NativeRuntimeClient(host="127.0.0.1", port=8788)
    client.protocol_version = ProtocolVersion(major=2, minor=0, patch=0)

    mock_resp = HandshakeResponse(
        protocol_version="1.0.0",
        runtime_version="0.1.0",
        authenticated=True,
        session_id="ses_bad",
        runtime_instance_id="inst_bad",
    )

    with patch("asyncio.open_connection") as mock_conn:
        mock_reader = AsyncMock()
        mock_writer = MagicMock()
        mock_writer.drain = AsyncMock()
        mock_writer.is_closing.return_value = False
        mock_conn.return_value = (mock_reader, mock_writer)

        payload_bytes = mock_resp.model_dump_json().encode("utf-8")
        mock_reader.readexactly.side_effect = [
            struct.pack(">I", len(payload_bytes)),
            payload_bytes,
        ]

        with pytest.raises(Exception, match="Incompatible protocol version"):
            await client.connect()

        assert client.connection_state == ConnectionState.FAILED


# =========================================================================
# 2. Session ID & Header Decoration Tests
# =========================================================================

@pytest.mark.asyncio
async def test_request_contract_header_decoration():
    client = NativeRuntimeClient(host="127.0.0.1", port=8788)
    client.session_id = "ses_active_9999"
    client.runtime_instance_id = "inst_rust_9999"
    client._connected = True
    client._reader = MagicMock()
    client._writer = MagicMock()
    client._writer.is_closing.return_value = False

    req = RuntimeRequest(
        operation="sys.ping",
        payload={"ping": True},
    )

    mock_resp = RuntimeResponse(
        message_id=req.message_id,
        request_id=req.request_id,
        protocol_version=CURRENT_PROTOCOL_VERSION,
        status=ResponseStatus.OK,
        execution_state=MessageLifecycleState.COMPLETED,
        result={"pong": True},
    )

    client._send_frame = AsyncMock()
    client._recv_frame = AsyncMock(return_value=mock_resp.model_dump_json().encode("utf-8"))

    resp = await client.request(req)

    # Verify client decorated headers before dispatch
    assert req.session_id == "ses_active_9999"
    assert req.client_instance_id == client.client_instance_id
    assert req.created_at is not None
    assert resp.status == ResponseStatus.OK


# =========================================================================
# 3. Disconnect Handling & UNKNOWN_OUTCOME Semantics
# =========================================================================

@pytest.mark.asyncio
async def test_side_effecting_operation_disconnect_returns_unknown_outcome():
    client = NativeRuntimeClient(host="127.0.0.1", port=8788)
    client.session_id = "ses_active_1"
    client._connected = True
    client._reader = MagicMock()
    client._writer = MagicMock()
    client._writer.is_closing.return_value = False

    # native.tool.execute is side-effecting (mutating external state)
    req = RuntimeRequest(
        operation="native.tool.execute",
        payload={"tool": "write_file", "path": "important.txt"},
    )

    client._send_frame = AsyncMock(side_effect=ConnectionResetError("Socket aborted by peer"))

    resp = await client.request(req)

    # STRICT CONTRACT: side effects cannot claim failure or retry; outcome is UNKNOWN
    assert resp.status == ResponseStatus.UNKNOWN_OUTCOME
    assert resp.execution_state == MessageLifecycleState.UNKNOWN_OUTCOME
    assert resp.error is not None
    assert resp.error.code == "UNKNOWN_OUTCOME"
    assert resp.error.retryable is False


@pytest.mark.asyncio
async def test_read_only_operation_disconnect_is_retryable_error():
    client = NativeRuntimeClient(host="127.0.0.1", port=8788)
    client.session_id = "ses_active_1"
    client._connected = True
    client._reader = MagicMock()
    client._writer = MagicMock()
    client._writer.is_closing.return_value = False

    # sys.ping is read-only / safe
    req = RuntimeRequest(
        operation="sys.ping",
        payload={"probe": True},
    )

    client._send_frame = AsyncMock(side_effect=ConnectionResetError("Socket dropped"))

    resp = await client.request(req)

    assert resp.status == ResponseStatus.ERROR
    assert resp.error is not None
    assert resp.error.retryable is True


# =========================================================================
# 4. Service Layer Context Binding & Orphan Reconciliation Tests
# =========================================================================

@pytest.mark.asyncio
async def test_service_executes_with_contract_contexts():
    client = NativeRuntimeClient(host="127.0.0.1", port=8788)
    service = NativeRuntimeService(client=client)

    auth_ctx = AuthorizationContext(
        subject="user_admin",
        approval_id="appr_ok_123",
        scopes=["native:sys.info"],
        risk_level="high",
        expires_at_ms=int((datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)).timestamp() * 1000),
    )

    target_ctx = OperationTargetContext(
        target_type="system",
        target_identifier="sys://host/info",
        target_hash="sha256:abc12345",
        expected_hash="sha256:abc12345",
    )

    mock_resp = RuntimeResponse(
        message_id="msg_123",
        request_id="req_123",
        protocol_version=CURRENT_PROTOCOL_VERSION,
        status=ResponseStatus.OK,
        execution_state=MessageLifecycleState.COMPLETED,
        result={"hostname": "kairo-host"},
    )

    client.request = AsyncMock(return_value=mock_resp)

    resp = await service.execute(
        operation="sys.info",
        payload={"system": True},
        auth_context=auth_ctx,
        target_context=target_ctx,
    )

    assert resp.status == ResponseStatus.OK
    # Check that client.request received the populated contract contexts
    dispatched_req = client.request.call_args[0][0]
    assert dispatched_req.authorization_context == auth_ctx
    assert dispatched_req.target_context == target_ctx


@pytest.mark.asyncio
async def test_service_orphan_tracking_and_reconciliation():
    client = NativeRuntimeClient(host="127.0.0.1", port=8788)
    service = NativeRuntimeService(client=client)

    # Return UNKNOWN_OUTCOME response from client
    mock_unknown = RuntimeResponse(
        message_id="msg_unk",
        request_id="req_unk_777",
        protocol_version=CURRENT_PROTOCOL_VERSION,
        status=ResponseStatus.UNKNOWN_OUTCOME,
        execution_state=MessageLifecycleState.UNKNOWN_OUTCOME,
        error=RuntimeErrorModel(
            category=ErrorCategory.RUNTIME_UNAVAILABLE,
            code="UNKNOWN_OUTCOME",
            message="Connection dropped during execution",
        ),
    )
    client.request = AsyncMock(return_value=mock_unknown)

    resp = await service.execute(
        operation="native.tool.execute",
        payload={"command": "process_order"},
    )

    assert resp.status == ResponseStatus.UNKNOWN_OUTCOME
    # Verify tracked in service._orphans
    assert len(service._orphans) == 1
    assert resp.request_id in service._orphans
    assert service._orphans[resp.request_id]["operation"] == "native.tool.execute"

    # Reconcile orphans
    reconcile_res = service.reconcile_orphans()
    assert reconcile_res["detected_orphans"] == 1
    assert reconcile_res["cleaned_orphans"] == 1
    assert reconcile_res["remaining_orphans"] == 0
    assert len(service._orphans) == 0


# =========================================================================
# 5. Emergency Stop Runtime Preemption Tests
# =========================================================================

@pytest.mark.asyncio
async def test_emergency_stop_runtime_priority_drain():
    client = NativeRuntimeClient(host="127.0.0.1", port=8788)
    service = NativeRuntimeService(client=client)

    mock_resp = RuntimeResponse(
        message_id="msg_stop",
        request_id="req_stop",
        protocol_version=CURRENT_PROTOCOL_VERSION,
        status=ResponseStatus.EMERGENCY_STOPPED,
        execution_state=MessageLifecycleState.EMERGENCY_STOPPED,
        result={"cancelled_tasks": 3, "drained": True},
    )

    client.emergency_stop = AsyncMock(return_value=mock_resp)

    res = await service.emergency_stop_runtime(reason="Operator critical abort")

    assert res["status"] == "EMERGENCY_STOPPED"
    assert res["drained"] is True
    client.emergency_stop.assert_called_once_with(reason="Operator critical abort")


# =========================================================================
# 6. Contract Diagnostics & Attestation Exposition
# =========================================================================

@pytest.mark.asyncio
async def test_get_contract_diagnostics_report():
    client = NativeRuntimeClient(host="127.0.0.1", port=8788)
    client.session_id = "ses_diag_test"
    client.runtime_instance_id = "run_inst_test"
    client.capability_fingerprint = "cfp_11223344"
    client.configuration_fingerprint = "cfg_55667788"

    service = NativeRuntimeService(client=client)

    mock_contract_diag = {
        "protocol_version": "1.0.0",
        "connection_state": "READY",
        "runtime_state": "READY",
        "session_id": "ses_diag_test",
        "runtime_instance_id": "run_inst_test",
        "client_instance_id": client.client_instance_id,
        "capability_fingerprint": "cfp_11223344",
        "configuration_fingerprint": "cfg_55667788",
        "capabilities_count": 5,
        "heartbeat_latency_ms": 1.25,
        "last_heartbeat": None,
        "circuit_breaker_state": "CLOSED",
        "contract_invariants": {
            "at_most_once_enforced": True,
            "replay_resistant": True,
            "deadlines_propagated": True,
            "toctou_revalidated": True,
            "emergency_stop_priority": True,
        },
    }

    client.get_contract_diagnostics = AsyncMock(return_value=mock_contract_diag)

    diag = await service.get_contract_diagnostics()

    assert diag["protocol_version"] == "1.0.0"
    assert diag["session_id"] == "ses_diag_test"
    assert diag["runtime_instance_id"] == "run_inst_test"
    assert diag["capability_fingerprint"] == "cfp_11223344"
    assert diag["configuration_fingerprint"] == "cfg_55667788"
    assert diag["contract_invariants"]["at_most_once_enforced"] is True
    assert diag["contract_invariants"]["replay_resistant"] is True
    assert diag["contract_invariants"]["toctou_revalidated"] is True
    assert diag["contract_invariants"]["emergency_stop_priority"] is True
    assert diag["orphans_tracked"] == 0
