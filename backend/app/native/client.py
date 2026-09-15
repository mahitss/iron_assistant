"""
Async Python client for communicating with Kairo Native Runtime via framed TCP socket.
"""

from __future__ import annotations

import asyncio
import json
import logging
import datetime
import struct
import time
import uuid
from typing import Any, Dict, List, Optional

try:
    from app.native.circuit_breaker import NativeCircuitBreaker
    from app.native.models import (
        CURRENT_PROTOCOL_VERSION,
        CapabilityDescriptor,
        ConnectionState,
        ErrorCategory,
        HandshakeRequest,
        HandshakeResponse,
        HealthState,
        MessageLifecycleState,
        ProtocolErrorEnvelope,
        ProtocolMessageType,
        ProtocolVersion,
        RequestContext,
        ResourceBudget,
        ResponseStatus,
        RuntimeErrorModel,
        RuntimeHealth,
        RuntimeMetadata,
        RuntimeRequest,
        RuntimeResponse,
        RuntimeState,
        ExecutionRequest,
        ExecutionResult,
        ExecutionState,
        PreflightResult,
    )
    from app.observability.correlation import get_current_span_id, get_current_trace_id
except ImportError:
    from backend.app.native.circuit_breaker import NativeCircuitBreaker
    from backend.app.native.models import (
        CURRENT_PROTOCOL_VERSION,
        CapabilityDescriptor,
        ConnectionState,
        ErrorCategory,
        HandshakeRequest,
        HandshakeResponse,
        HealthState,
        MessageLifecycleState,
        ProtocolErrorEnvelope,
        ProtocolMessageType,
        ProtocolVersion,
        RequestContext,
        ResourceBudget,
        ResponseStatus,
        RuntimeErrorModel,
        RuntimeHealth,
        RuntimeMetadata,
        RuntimeRequest,
        RuntimeResponse,
        RuntimeState,
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

        # Task 87 Distributed Execution Contract state
        self.client_instance_id: str = f"client_{uuid.uuid4().hex[:12]}"
        self.session_id: Optional[str] = None
        self.runtime_instance_id: Optional[str] = None
        self.capability_fingerprint: Optional[str] = None
        self.configuration_fingerprint: Optional[str] = None
        self.protocol_version: ProtocolVersion = ProtocolVersion(major=1, minor=0, patch=0)
        self.connection_state: ConnectionState = ConnectionState.DISCONNECTED
        self.runtime_state: RuntimeState = RuntimeState.STARTING
        self.last_heartbeat_at: Optional[datetime.datetime] = None
        self.heartbeat_latency_ms: float = 0.0
        self._heartbeat_task: Optional[asyncio.Task] = None

    async def connect(self) -> HandshakeResponse:
        """Establish connection and perform authenticated handshake with the native runtime."""
        if not self.circuit_breaker.can_attempt():
            self.connection_state = ConnectionState.FAILED
            raise NativeRuntimeUnavailableError(
                f"Circuit breaker is OPEN. Native runtime at {self.host}:{self.port} is temporarily marked unavailable."
            )

        self.connection_state = ConnectionState.CONNECTING
        self.runtime_state = RuntimeState.NEGOTIATING

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=5.0,
            )
            self._reader = reader
            self._writer = writer
            self.connection_state = ConnectionState.AUTHENTICATING
            self.runtime_state = RuntimeState.AUTHENTICATING

            # Handshake with client_instance_id and nonce
            nonce = uuid.uuid4().hex
            handshake_req = HandshakeRequest(
                protocol_version=CURRENT_PROTOCOL_VERSION,
                secret=self.secret,
                client_id="kairo-python-client",
                client_version="1.0.0",
                client_instance_id=self.client_instance_id,
                nonce=nonce,
            )
            payload_bytes = handshake_req.model_dump_json().encode("utf-8")
            await self._send_frame(payload_bytes)

            resp_bytes = await self._recv_frame()
            resp_data = json.loads(resp_bytes.decode("utf-8"))
            handshake_resp = HandshakeResponse.model_validate(resp_data)

            if not handshake_resp.authenticated:
                self._close()
                self.connection_state = ConnectionState.FAILED
                self.runtime_state = RuntimeState.UNAUTHORIZED
                self.circuit_breaker.record_failure()
                raise PermissionError(f"Native runtime authentication failed: {handshake_resp.error}")

            # Negotiate protocol version
            server_ver = ProtocolVersion.from_string(handshake_resp.protocol_version)
            negotiated = self.protocol_version.negotiate(server_ver)
            if negotiated is None:
                self._close()
                self.connection_state = ConnectionState.FAILED
                self.runtime_state = RuntimeState.INCOMPATIBLE
                raise ValueError(
                    f"Incompatible protocol version: client {self.protocol_version} vs server {handshake_resp.protocol_version}"
                )

            self.protocol_version = negotiated
            self.session_id = handshake_resp.session_id
            self.runtime_instance_id = handshake_resp.runtime_instance_id
            self.capability_fingerprint = handshake_resp.capability_fingerprint
            self.configuration_fingerprint = handshake_resp.configuration_fingerprint
            self._capabilities = handshake_resp.capabilities
            self._connected = True
            self.connection_state = ConnectionState.READY
            self.runtime_state = RuntimeState.READY
            self.circuit_breaker.record_success()

            logger.info(
                "native_client.connected host=%s port=%d version=%s session=%s capabilities=%d",
                self.host,
                self.port,
                handshake_resp.runtime_version,
                self.session_id,
                len(self._capabilities),
            )
            return handshake_resp

        except Exception as exc:
            self._close()
            self.connection_state = ConnectionState.FAILED
            self.runtime_state = RuntimeState.FAILED
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
                execution_state=MessageLifecycleState.REJECTED,
                error=RuntimeErrorModel(
                    category=ErrorCategory.RUNTIME_UNAVAILABLE,
                    code="CIRCUIT_BREAKER_OPEN",
                    message="Native runtime circuit breaker is open",
                    retryable=True,
                ),
                error_envelope=ProtocolErrorEnvelope(
                    error_code="CIRCUIT_BREAKER_OPEN",
                    category=ErrorCategory.RUNTIME_UNAVAILABLE,
                    message="Native runtime circuit breaker is open",
                    request_id=req.request_id,
                    correlation_id=req.correlation_id,
                    retryable=True,
                    terminal=True,
                    component="circuit_breaker",
                ),
            )

        # Propagate distributed trace and span context if not explicitly set (Task 86)
        try:
            if req.trace_id is None:
                req.trace_id = get_current_trace_id()
            if req.span_id is None:
                req.span_id = get_current_span_id()
        except Exception:
            pass

        # Decorate request with Task 87 contract session metadata
        if req.session_id is None and self.session_id is not None:
            req.session_id = self.session_id
        if req.runtime_instance_id is None and self.runtime_instance_id is not None:
            req.runtime_instance_id = self.runtime_instance_id
        if req.client_instance_id is None:
            req.client_instance_id = self.client_instance_id
        if req.nonce is None:
            req.nonce = uuid.uuid4().hex
        if req.created_at is None:
            req.created_at = datetime.datetime.now(datetime.timezone.utc)
        if req.deadline is None and req.deadline_ms:
            req.deadline = req.created_at + datetime.timedelta(milliseconds=req.deadline_ms)

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

                # Bridge native events from Rust runtime into Python unified event fabric (Task 86)
                if response.native_events:
                    try:
                        from app.events.bus import event_bus
                        from app.events.schemas import Event, EventOutcome, EventSeverity, ExecutionDomain

                        for nev in response.native_events:
                            domain_str = str(getattr(nev, "effective_domain", "RUNTIME")).lower()
                            try:
                                domain_val = ExecutionDomain(domain_str)
                            except Exception:
                                domain_val = ExecutionDomain.SYSTEM

                            sev_str = str(getattr(nev, "severity", "INFO")).upper()
                            try:
                                sev_val = EventSeverity(sev_str)
                            except Exception:
                                sev_val = EventSeverity.INFO

                            outcome_str = str(getattr(nev, "outcome", "SUCCESS")).upper()
                            try:
                                outcome_val = EventOutcome(outcome_str)
                            except Exception:
                                outcome_val = None

                            mono_ns = getattr(nev, "effective_monotonic_nanos", 0)

                            ev = Event(
                                event_id=nev.event_id,
                                correlation_id=nev.correlation_id or req.correlation_id or "unspecified",
                                trace_id=nev.trace_id or req.trace_id,
                                span_id=nev.span_id or req.span_id,
                                parent_event_id=nev.parent_event_id,
                                causation_id=nev.causation_id or req.causation_id,
                                event_type=nev.event_type,
                                severity=sev_val,
                                execution_domain=domain_val,
                                outcome=outcome_val,
                                source=getattr(nev, "effective_source", "rust_runtime"),
                                monotonic_timestamp=mono_ns / 1_000_000_000.0 if mono_ns else time.perf_counter(),
                                payload=nev.payload,
                            )
                            asyncio.create_task(event_bus.publish(ev))
                    except Exception as ev_bridge_err:
                        logger.debug("Failed to bridge native events: %s", ev_bridge_err)

                return response

            except asyncio.TimeoutError:
                self.circuit_breaker.record_failure()
                # Attempt proactive cancellation if cancellation_id is known
                cancel_id = req.cancellation_id or req.request_id
                asyncio.create_task(self.cancel(cancel_id))
                return RuntimeResponse(
                    message_id=req.message_id,
                    request_id=req.request_id,
                    protocol_version=CURRENT_PROTOCOL_VERSION,
                    status=ResponseStatus.ERROR,
                    execution_state=MessageLifecycleState.TIMED_OUT,
                    error=RuntimeErrorModel(
                        category=ErrorCategory.DEADLINE_EXCEEDED,
                        code="CLIENT_TIMEOUT",
                        message=f"Request timed out waiting for native response after {deadline_sec}s",
                        retryable=True,
                    ),
                    error_envelope=ProtocolErrorEnvelope(
                        error_code="CLIENT_TIMEOUT",
                        category=ErrorCategory.DEADLINE_EXCEEDED,
                        message=f"Request timed out waiting for native response after {deadline_sec}s",
                        request_id=req.request_id,
                        correlation_id=req.correlation_id,
                        retryable=True,
                        terminal=True,
                        component="native_client",
                    ),
                )
            except Exception as exc:
                self._close()
                self.circuit_breaker.record_failure(exc)
                self.connection_state = ConnectionState.DISCONNECTED

                is_side_effecting = not (
                    req.operation.startswith("sys.ping")
                    or req.operation.startswith("sys.health")
                    or req.operation.startswith("sys.info")
                    or req.operation.startswith("sys.metrics")
                    or req.operation.startswith("sys.capabilities")
                    or req.operation.startswith("sys.contract")
                    or req.operation.startswith("obs.")
                )

                if is_side_effecting:
                    outcome_status = ResponseStatus.UNKNOWN_OUTCOME
                    exec_state = MessageLifecycleState.UNKNOWN_OUTCOME
                    err_cat = ErrorCategory.UNKNOWN_OUTCOME
                    err_code = "UNKNOWN_OUTCOME"
                    msg = f"Transport disconnected during side-effecting operation '{req.operation}'; outcome unconfirmed: {exc}"
                else:
                    outcome_status = ResponseStatus.ERROR
                    exec_state = MessageLifecycleState.FAILED
                    err_cat = ErrorCategory.RUNTIME_UNAVAILABLE
                    err_code = "IPC_ERROR"
                    msg = f"Communication error with native runtime: {exc}"

                return RuntimeResponse(
                    message_id=req.message_id,
                    request_id=req.request_id,
                    protocol_version=CURRENT_PROTOCOL_VERSION,
                    status=outcome_status,
                    execution_state=exec_state,
                    error=RuntimeErrorModel(
                        category=err_cat,
                        code=err_code,
                        message=msg,
                        retryable=not is_side_effecting,
                    ),
                    error_envelope=ProtocolErrorEnvelope(
                        error_code=err_code,
                        category=err_cat,
                        message=msg,
                        request_id=req.request_id,
                        correlation_id=req.correlation_id,
                        retryable=not is_side_effecting,
                        terminal=True,
                        component="client_contract_guard",
                    ),
                )

    async def emergency_stop(self, reason: str = "emergency_stop") -> RuntimeResponse:
        """Issue protocol-level emergency stop to halt all native executions immediately."""
        req = RuntimeRequest(
            message_type=ProtocolMessageType.STOP_REQUEST,
            operation="sys.stop",
            payload={"reason": reason},
            deadline_ms=5000,
        )
        resp = await self.request(req)
        self.runtime_state = RuntimeState.STOPPING
        logger.critical("native_client.emergency_stop_triggered reason=%s status=%s", reason, resp.status)
        return resp

    async def get_contract_diagnostics(self) -> Dict[str, Any]:
        """Inspect active protocol contract, fingerprints, session ID, and attestation invariants."""
        contract_info: Dict[str, Any] = {}
        try:
            req = RuntimeRequest(operation="sys.contract", deadline_ms=5000)
            resp = await self.request(req)
            if resp.status == ResponseStatus.OK and resp.result:
                contract_info = resp.result
        except Exception as e:
            logger.debug("native_client.contract_diagnostics_query_failed: %s", e)

        return {
            "protocol_version": str(self.protocol_version),
            "connection_state": self.connection_state.value,
            "runtime_state": self.runtime_state.value,
            "session_id": self.session_id,
            "runtime_instance_id": self.runtime_instance_id,
            "client_instance_id": self.client_instance_id,
            "capability_fingerprint": self.capability_fingerprint or contract_info.get("capability_fingerprint"),
            "configuration_fingerprint": self.configuration_fingerprint or contract_info.get("configuration_fingerprint"),
            "capabilities_count": len(self._capabilities),
            "heartbeat_latency_ms": self.heartbeat_latency_ms,
            "last_heartbeat": self.last_heartbeat_at.isoformat() if self.last_heartbeat_at else None,
            "circuit_breaker_state": self.circuit_breaker.state.value,
            "contract_invariants": {
                "at_most_once_enforced": True,
                "replay_resistant": True,
                "deadlines_propagated": True,
                "toctou_revalidated": True,
                "emergency_stop_priority": True,
            },
        }

    async def heartbeat(self) -> bool:
        """Send heartbeat ping to native runtime and record latency."""
        t0 = time.perf_counter()
        req = RuntimeRequest(
            message_type=ProtocolMessageType.HEARTBEAT_PING,
            operation="sys.ping",
            payload={"heartbeat": True},
            deadline_ms=5000,
        )
        resp = await self.request(req)
        latency = (time.perf_counter() - t0) * 1000.0
        if resp.status == ResponseStatus.OK:
            self.last_heartbeat_at = datetime.datetime.now(datetime.timezone.utc)
            self.heartbeat_latency_ms = latency
            return True
        return False

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
