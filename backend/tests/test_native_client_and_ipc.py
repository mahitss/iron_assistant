"""
Unit and integration tests for NativeRuntimeClient and IPC communication (Task 80).
"""

from __future__ import annotations

import asyncio
import json
import struct
import pytest

try:
    from app.native.circuit_breaker import CircuitState, NativeCircuitBreaker
    from app.native.client import (
        MAX_FRAME_BYTES,
        NativeRuntimeClient,
        NativeRuntimeUnavailableError,
    )
    from app.native.models import (
        CURRENT_PROTOCOL_VERSION,
        HandshakeRequest,
        HandshakeResponse,
        ResponseStatus,
        RuntimeRequest,
        RuntimeResponse,
        TimingMetadata,
    )
except ImportError:
    from backend.app.native.circuit_breaker import CircuitState, NativeCircuitBreaker
    from backend.app.native.client import (
        MAX_FRAME_BYTES,
        NativeRuntimeClient,
        NativeRuntimeUnavailableError,
    )
    from backend.app.native.models import (
        CURRENT_PROTOCOL_VERSION,
        HandshakeRequest,
        HandshakeResponse,
        ResponseStatus,
        RuntimeRequest,
        RuntimeResponse,
        TimingMetadata,
    )


@pytest.mark.asyncio
async def test_length_prefixed_framing():
    client = NativeRuntimeClient()
    # Test frame size limit
    oversized = b"x" * (MAX_FRAME_BYTES + 10)
    with pytest.raises(ValueError, match="exceeds maximum frame limit"):
        await client._send_frame(oversized)


@pytest.mark.asyncio
async def test_circuit_breaker_lifecycle():
    cb = NativeCircuitBreaker(failure_threshold=2, recovery_timeout_seconds=0.1)

    assert cb.can_attempt()
    assert cb.state == CircuitState.CLOSED

    # First failure
    cb.record_failure()
    assert cb.can_attempt()
    assert cb.state == CircuitState.CLOSED

    # Second failure -> trips to OPEN
    cb.record_failure()
    assert not cb.can_attempt()
    assert cb.state == CircuitState.OPEN

    # Wait for recovery timeout
    await asyncio.sleep(0.15)
    assert cb.can_attempt()
    assert cb.state == CircuitState.HALF_OPEN

    # Success recovers to CLOSED
    cb.record_success()
    assert cb.state == CircuitState.CLOSED
    assert cb.can_attempt()


@pytest.mark.asyncio
async def test_native_client_mock_socket_roundtrip():
    # Start a local test mock server
    async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        # 1. Read handshake frame
        header = await reader.readexactly(4)
        length = struct.unpack(">I", header)[0]
        req_bytes = await reader.readexactly(length)
        handshake_data = json.loads(req_bytes.decode("utf-8"))

        # 2. Send handshake response
        handshake_resp = HandshakeResponse(
            protocol_version=CURRENT_PROTOCOL_VERSION,
            runtime_version="0.1.0",
            authenticated=(handshake_data.get("secret") == "test-secret"),
            capabilities=[],
        )
        resp_data = handshake_resp.model_dump_json().encode("utf-8")
        writer.write(struct.pack(">I", len(resp_data)) + resp_data)
        await writer.drain()

        # 3. Read request
        header = await reader.readexactly(4)
        length = struct.unpack(">I", header)[0]
        req_bytes = await reader.readexactly(length)
        req_data = json.loads(req_bytes.decode("utf-8"))

        # 4. Send response
        runtime_resp = RuntimeResponse(
            request_id=req_data["request_id"],
            protocol_version=CURRENT_PROTOCOL_VERSION,
            status=ResponseStatus.OK,
            result={"echo": req_data.get("payload")},
            timing=TimingMetadata(queue_time_ms=1, execution_time_ms=2, total_time_ms=3),
        )
        out_bytes = runtime_resp.model_dump_json().encode("utf-8")
        writer.write(struct.pack(">I", len(out_bytes)) + out_bytes)
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    server = await asyncio.start_server(handle_client, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]

    client = NativeRuntimeClient(host="127.0.0.1", port=port, secret="test-secret")
    try:
        resp = await client.ping({"hello": "ipc"})
        assert resp.status == ResponseStatus.OK
        assert resp.result == {"echo": {"hello": "ipc"}}
    finally:
        await client.close()
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_native_client_bad_authentication():
    async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        header = await reader.readexactly(4)
        length = struct.unpack(">I", header)[0]
        await reader.readexactly(length)

        handshake_resp = HandshakeResponse(
            protocol_version=CURRENT_PROTOCOL_VERSION,
            runtime_version="0.1.0",
            authenticated=False,
            error="Invalid authentication secret",
        )
        resp_data = handshake_resp.model_dump_json().encode("utf-8")
        writer.write(struct.pack(">I", len(resp_data)) + resp_data)
        await writer.drain()
        writer.close()

    server = await asyncio.start_server(handle_client, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]

    client = NativeRuntimeClient(host="127.0.0.1", port=port, secret="wrong-secret")
    try:
        with pytest.raises(NativeRuntimeUnavailableError):
            await client.connect()

        resp = await client.ping()
        assert resp.status == ResponseStatus.ERROR
    finally:
        await client.close()
        server.close()
        await server.wait_closed()
