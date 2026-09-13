"""
Async Python client for communicating with Kairo Native Runtime via framed TCP socket.
"""

from __future__ import annotations

import asyncio
import json
import logging
import struct
from typing import Any, Dict, List, Optional

try:
    from app.native.circuit_breaker import NativeCircuitBreaker
    from app.native.models import (
        CURRENT_PROTOCOL_VERSION,
        CapabilityDescriptor,
        ErrorCategory,
        HandshakeRequest,
        HandshakeResponse,
        HealthState,
        RequestContext,
        ResourceBudget,
        ResponseStatus,
        RuntimeErrorModel,
        RuntimeHealth,
        RuntimeMetadata,
        RuntimeRequest,
        RuntimeResponse,
        ExecutionRequest,
        ExecutionResult,
        ExecutionState,
        PreflightResult,
    )
except ImportError:
    from backend.app.native.circuit_breaker import NativeCircuitBreaker
    from backend.app.native.models import (
        CURRENT_PROTOCOL_VERSION,
        CapabilityDescriptor,
        ErrorCategory,
        HandshakeRequest,
        HandshakeResponse,
        HealthState,
        RequestContext,
        ResourceBudget,
        ResponseStatus,
        RuntimeErrorModel,
        RuntimeHealth,
        RuntimeMetadata,
        RuntimeRequest,
        RuntimeResponse,
        ExecutionRequest,
        ExecutionResult,
        ExecutionState,
        PreflightResult,
    )

logger = logging.getLogger("kairo.native.client")

MAX_FRAME_BYTES = 1_048_576  # 1 MB


class NativeRuntimeUnavailableError(Exception):
    """Raised when native runtime is unreachable, disabled, or in tripped circuit state."""
    pass


class NativeRuntimeClient:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8788,
        secret: Optional[str] = None,
        timeout_seconds: float = 30.0,
        circuit_breaker: Optional[NativeCircuitBreaker] = None,
    ):
        self.host = host
        self.port = port
        self.secret = secret
        self.timeout_seconds = timeout_seconds
        self.circuit_breaker = circuit_breaker or NativeCircuitBreaker()
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._lock = asyncio.Lock()
        self._capabilities: List[CapabilityDescriptor] = []
        self._connected = False

    async def connect(self) -> HandshakeResponse:
        """Establish connection and perform authenticated handshake with the native runtime."""
        if not self.circuit_breaker.can_attempt():
            raise NativeRuntimeUnavailableError(
                f"Circuit breaker is OPEN. Native runtime at {self.host}:{self.port} is temporarily marked unavailable."
            )

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=5.0,
            )
            self._reader = reader
            self._writer = writer

            # Handshake
            handshake_req = HandshakeRequest(
                protocol_version=CURRENT_PROTOCOL_VERSION,
                secret=self.secret,
                client_id="kairo-python-client",
                client_version="1.0.0",
            )
            payload_bytes = handshake_req.model_dump_json().encode("utf-8")
            await self._send_frame(payload_bytes)

            resp_bytes = await self._recv_frame()
            resp_data = json.loads(resp_bytes.decode("utf-8"))
            handshake_resp = HandshakeResponse.model_validate(resp_data)

            if not handshake_resp.authenticated:
                self._close()
                self.circuit_breaker.record_failure()
                raise PermissionError(f"Native runtime authentication failed: {handshake_resp.error}")

            self._capabilities = handshake_resp.capabilities
            self._connected = True
            self.circuit_breaker.record_success()
            logger.info(
                "native_client.connected host=%s port=%d version=%s capabilities=%d",
                self.host,
                self.port,
                handshake_resp.runtime_version,
                len(self._capabilities),
            )
            return handshake_resp

        except Exception as exc:
            self._close()
            self.circuit_breaker.record_failure(exc)
            logger.warning("native_client.connect_failed host=%s port=%d error=%s", self.host, self.port, exc)
            raise NativeRuntimeUnavailableError(f"Could not connect to native runtime: {exc}") from exc

    async def _ensure_connected(self) -> None:
        if not self._connected or self._reader is None or self._writer is None or self._writer.is_closing():
            await self.connect()

    async def _send_frame(self, data: bytes) -> None:
        if len(data) > MAX_FRAME_BYTES:
            raise ValueError(f"Message size {len(data)} exceeds maximum frame limit of {MAX_FRAME_BYTES} bytes")
        if self._writer is None:
            raise NativeRuntimeUnavailableError("Socket is not connected")

        header = struct.pack(">I", len(data))
        self._writer.write(header + data)
        await self._writer.drain()

    async def _recv_frame(self) -> bytes:
        if self._reader is None:
            raise NativeRuntimeUnavailableError("Socket is not connected")

        header_bytes = await self._reader.readexactly(4)
        length = struct.unpack(">I", header_bytes)[0]
        if length > MAX_FRAME_BYTES:
            raise ValueError(f"Received frame size {length} exceeds maximum allowed {MAX_FRAME_BYTES} bytes")

        return await self._reader.readexactly(length)

    def _close(self) -> None:
        self._connected = False
        if self._writer:
            try:
                self._writer.close()
            except Exception:
                pass
        self._reader = None
        self._writer = None

    async def close(self) -> None:
        async with self._lock:
            self._close()

    async def request(self, req: RuntimeRequest) -> RuntimeResponse:
        """Send a strongly typed RuntimeRequest and receive RuntimeResponse."""
        if not self.circuit_breaker.can_attempt():
            return RuntimeResponse(
                request_id=req.request_id,
                protocol_version=CURRENT_PROTOCOL_VERSION,
                status=ResponseStatus.ERROR,
                error=RuntimeErrorModel(
                    category=ErrorCategory.RUNTIME_UNAVAILABLE,
                    code="CIRCUIT_BREAKER_OPEN",
                    message="Native runtime circuit breaker is open",
                    retryable=True,
                ),
            )

        deadline_sec = (req.deadline_ms / 1000.0) if req.deadline_ms else self.timeout_seconds

        async with self._lock:
            try:
                await self._ensure_connected()
                payload_bytes = req.model_dump_json().encode("utf-8")
                await self._send_frame(payload_bytes)

                resp_bytes = await asyncio.wait_for(self._recv_frame(), timeout=deadline_sec + 2.0)
                resp_json = json.loads(resp_bytes.decode("utf-8"))
                response = RuntimeResponse.model_validate(resp_json)
                self.circuit_breaker.record_success()
                return response

            except asyncio.TimeoutError:
                self.circuit_breaker.record_failure()
                # Attempt proactive cancellation if cancellation_id is known
                cancel_id = req.cancellation_id or req.request_id
                asyncio.create_task(self.cancel(cancel_id))
                return RuntimeResponse(
                    request_id=req.request_id,
                    protocol_version=CURRENT_PROTOCOL_VERSION,
                    status=ResponseStatus.ERROR,
                    error=RuntimeErrorModel(
                        category=ErrorCategory.DEADLINE_EXCEEDED,
                        code="CLIENT_TIMEOUT",
                        message=f"Request timed out waiting for native response after {deadline_sec}s",
                        retryable=True,
                    ),
                )
            except Exception as exc:
                self._close()
                self.circuit_breaker.record_failure(exc)
                return RuntimeResponse(
                    request_id=req.request_id,
                    protocol_version=CURRENT_PROTOCOL_VERSION,
                    status=ResponseStatus.ERROR,
                    error=RuntimeErrorModel(
                        category=ErrorCategory.RUNTIME_UNAVAILABLE,
                        code="IPC_ERROR",
                        message=f"Communication error with native runtime: {exc}",
                        retryable=True,
                    ),
                )

    async def ping(self, payload: Optional[Dict[str, Any]] = None) -> RuntimeResponse:
        req = RuntimeRequest(
            operation="sys.ping",
            payload=payload or {"client_ping": True},
        )
        return await self.request(req)

    async def health(self) -> Optional[RuntimeHealth]:
        req = RuntimeRequest(operation="sys.health")
        resp = await self.request(req)
        if resp.status == ResponseStatus.OK and resp.result:
            try:
                return RuntimeHealth.model_validate(resp.result)
            except Exception as e:
                logger.warning("native_client.health_parse_failed error=%s", e)
        return None

    async def capabilities(self) -> List[CapabilityDescriptor]:
        if not self._capabilities:
            try:
                await self.connect()
            except Exception:
                pass
        return self._capabilities

    async def cancel(self, cancellation_id: str) -> bool:
        req = RuntimeRequest(
            operation="sys.cancel",
            payload={"cancellation_id": cancellation_id},
        )
        resp = await self.request(req)
        if resp.status == ResponseStatus.OK and resp.result:
            return bool(resp.result.get("found_and_cancelled", False))
        return False

    async def is_available(self) -> bool:
        if not self.circuit_breaker.can_attempt():
            return False
        try:
            resp = await self.ping()
            return resp.status == ResponseStatus.OK
        except Exception:
            return False

    async def sandbox_preflight(self, req: ExecutionRequest) -> PreflightResult:
        """Perform dry-run preflight evaluation without executing workload."""
        runtime_req = RuntimeRequest(
            request_id=req.request_id,
            protocol_version=CURRENT_PROTOCOL_VERSION,
            operation="sandbox.preflight",
            deadline_ms=10000,
            caller_context=req.authorization_context,
            resource_budget=req.resource_budget,
            payload=req.model_dump(mode="json"),
        )
        resp = await self.request(runtime_req)
        if resp.status == ResponseStatus.OK and resp.result:
            return PreflightResult.model_validate(resp.result)
        
        return PreflightResult(
            accepted=False,
            capability_id=req.capability_id,
            effective_policy=req.sandbox_policy,
            effective_budget=req.resource_budget,
            rejection_reason=resp.error.message if resp.error else "Preflight rejected",
        )

    async def sandbox_execute(self, req: ExecutionRequest) -> ExecutionResult:
        """Execute a typed sandboxed workload within the native substrate."""
        runtime_req = RuntimeRequest(
            request_id=req.request_id,
            protocol_version=CURRENT_PROTOCOL_VERSION,
            operation="sandbox.execute",
            deadline_ms=req.resource_budget.max_execution_time_ms or 30000,
            cancellation_id=req.cancellation_id,
            correlation_id=req.correlation_id,
            caller_context=req.authorization_context,
            resource_budget=req.resource_budget,
            payload=req.model_dump(mode="json"),
        )
        resp = await self.request(runtime_req)
        if resp.status == ResponseStatus.OK and resp.result:
            return ExecutionResult.model_validate(resp.result)

        # Build fallback failure ExecutionResult
        return ExecutionResult(
            request_id=req.request_id,
            execution_id=f"exec_err_{req.request_id[:8]}",
            capability_id=req.capability_id,
            state=ExecutionState.FAILED if resp.status != ResponseStatus.CANCELLED else ExecutionState.CANCELLED,
            exit_code=1 if resp.status != ResponseStatus.CANCELLED else None,
            stderr=resp.error.message if resp.error else "Execution failed",
            error=resp.error,
        )
