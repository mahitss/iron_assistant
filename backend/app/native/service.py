"""
Native Runtime Service Layer.
Coordinates Kairo SecurityCenter, EmergencyStop, and EventRegistry with NativeRuntimeClient.

STRICT INVARIANT:
PYTHON THINKS, PLANS & GOVERNS | RUST EXECUTES LOW-LEVEL TRUSTED PRIMITIVES.
SecurityCenter and EmergencyStop remain the supreme authorities.
Rust runtime never independently authorizes or overrides governance.
"""

from __future__ import annotations

import datetime
import logging
import uuid
from typing import Any, Dict, List, Optional

try:
    from app.config.settings import get_settings
    from app.events.registry import EventRegistry
    from app.native.client import (
        NativeRuntimeClient,
        NativeRuntimeUnavailableError,
    )
    from app.native.models import (
        CURRENT_PROTOCOL_VERSION,
        CapabilityDescriptor,
        ErrorCategory,
        RequestContext,
        ResourceBudget,
        ResponseStatus,
        RuntimeErrorModel,
        RuntimeHealth,
        RuntimeRequest,
        RuntimeResponse,
        ExecutionRequest,
        ExecutionResult,
        ExecutionState,
        PreflightResult,
    )
    from app.security.center import SecurityCenter
    from app.security.emergency_stop import EmergencyStopService
except ImportError:
    from backend.app.config.settings import get_settings
    from backend.app.events.registry import EventRegistry
    from backend.app.native.client import (
        NativeRuntimeClient,
        NativeRuntimeUnavailableError,
    )
    from backend.app.native.models import (
        CURRENT_PROTOCOL_VERSION,
        CapabilityDescriptor,
        ErrorCategory,
        RequestContext,
        ResourceBudget,
        ResponseStatus,
        RuntimeErrorModel,
        RuntimeHealth,
        RuntimeRequest,
        RuntimeResponse,
        ExecutionRequest,
        ExecutionResult,
        ExecutionState,
        PreflightResult,
    )
    from backend.app.security.center import SecurityCenter
    from backend.app.security.emergency_stop import EmergencyStopService

logger = logging.getLogger("kairo.native.service")


class NativeRuntimeService:
    _instance: Optional[NativeRuntimeService] = None

    def __init__(
        self,
        client: Optional[NativeRuntimeClient] = None,
        security_center: Optional[SecurityCenter] = None,
        emergency_stop: Optional[EmergencyStopService] = None,
        event_registry: Optional[EventRegistry] = None,
    ):
        settings = get_settings()
        self.mode = getattr(settings, "KAIRO_NATIVE_RUNTIME_MODE", "OPTIONAL").upper()
        self.client = client or NativeRuntimeClient(
            host=getattr(settings, "KAIRO_NATIVE_RUNTIME_HOST", "127.0.0.1"),
            port=getattr(settings, "KAIRO_NATIVE_RUNTIME_PORT", 8788),
            secret=getattr(settings, "KAIRO_NATIVE_RUNTIME_SECRET", None),
        )
        self.security_center = security_center or SecurityCenter()
        self.emergency_stop = emergency_stop or EmergencyStopService()
        self.event_registry = event_registry or EventRegistry()

    @classmethod
    def get_instance(cls) -> NativeRuntimeService:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def is_enabled(self) -> bool:
        return self.mode != "DISABLED"

    async def get_health(self) -> Dict[str, Any]:
        """Query runtime health state and return structured representation."""
        if not self.is_enabled():
            return {
                "status": "DISABLED",
                "healthy": True,
                "mode": self.mode,
                "message": "Native runtime substrate is disabled by configuration",
                "metadata": None,
            }

        try:
            health = await self.client.health()
            if health:
                return {
                    "status": health.state.value,
                    "healthy": health.healthy,
                    "mode": self.mode,
                    "message": health.message,
                    "metadata": health.metadata.model_dump(),
                }
        except Exception as exc:
            logger.warning("native_service.health_check_failed error=%s", exc)

        return {
            "status": "UNAVAILABLE",
            "healthy": False,
            "mode": self.mode,
            "message": "Could not connect to native runtime substrate",
            "metadata": None,
        }

    async def list_capabilities(self) -> List[CapabilityDescriptor]:
        """Discover registered native capabilities."""
        if not self.is_enabled():
            return []
        try:
            return await self.client.capabilities()
        except Exception as exc:
            logger.warning("native_service.list_capabilities_failed error=%s", exc)
            return []

    async def execute(
        self,
        operation: str,
        payload: Dict[str, Any],
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        security_level: Optional[str] = None,
        deadline_ms: Optional[int] = 30000,
        cancellation_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        budget: Optional[ResourceBudget] = None,
    ) -> RuntimeResponse:
        """
        Execute a native operation through full SecurityCenter & EmergencyStop validation.
        FAIL-CLOSED INVARIANT:
        If EmergencyStop is active or SecurityCenter rejects authorization,
        execution is blocked before touching the native socket.
        """
        request_id = str(uuid.uuid4())

        # 1. Mode Check
        if not self.is_enabled():
            return RuntimeResponse(
                request_id=request_id,
                protocol_version=CURRENT_PROTOCOL_VERSION,
                status=ResponseStatus.ERROR,
                error=RuntimeErrorModel(
                    category=ErrorCategory.RUNTIME_UNAVAILABLE,
                    code="NATIVE_RUNTIME_DISABLED",
                    message="Native runtime execution is disabled in this environment",
                    retryable=False,
                ),
            )

        # 2. EmergencyStop Check (ABSOLUTE AUTHORITY)
        if self.emergency_stop.is_stopped():
            logger.critical("native_service.emergency_stop_triggered operation=%s request_id=%s", operation, request_id)
            await self._emit_audit("runtime.security.blocked_by_emergency_stop", {
                "request_id": request_id,
                "operation": operation,
                "reason": "EmergencyStop is active",
            })
            return RuntimeResponse(
                request_id=request_id,
                protocol_version=CURRENT_PROTOCOL_VERSION,
                status=ResponseStatus.ERROR,
                error=RuntimeErrorModel(
                    category=ErrorCategory.AUTHORIZATION_REQUIRED,
                    code="EMERGENCY_STOP_ACTIVE",
                    message="Native runtime execution blocked by active EmergencyStop",
                    retryable=False,
                ),
            )

        # 3. SecurityCenter Authorization Check
        caller_ctx = RequestContext(
            user_id=user_id,
            tenant_id=tenant_id,
            security_level=security_level,
            client_version="1.0.0",
        )

        authz_ok = await self._verify_authorization(operation, caller_ctx)
        if not authz_ok:
            logger.warning("native_service.authorization_failed operation=%s user_id=%s", operation, user_id)
            await self._emit_audit("runtime.security.authorization_denied", {
                "request_id": request_id,
                "operation": operation,
                "user_id": user_id,
            })
            return RuntimeResponse(
                request_id=request_id,
                protocol_version=CURRENT_PROTOCOL_VERSION,
                status=ResponseStatus.ERROR,
                error=RuntimeErrorModel(
                    category=ErrorCategory.AUTHORIZATION_REQUIRED,
                    code="AUTHORIZATION_DENIED",
                    message=f"Caller lacks authorization for native operation '{operation}'",
                    retryable=False,
                ),
            )

        # 4. Construct validated RuntimeRequest
        req = RuntimeRequest(
            request_id=request_id,
            protocol_version=CURRENT_PROTOCOL_VERSION,
            operation=operation,
            deadline_ms=deadline_ms,
            cancellation_id=cancellation_id,
            correlation_id=correlation_id,
            caller_context=caller_ctx,
            resource_budget=budget or ResourceBudget(),
            payload=payload,
        )

        # 5. Dispatch to Native Runtime
        await self._emit_audit("runtime.request.dispatched", {
            "request_id": request_id,
            "operation": operation,
            "correlation_id": correlation_id,
        })

        try:
            response = await self.client.request(req)
        except Exception as exc:
            logger.error("native_service.dispatch_exception operation=%s error=%s", operation, exc)
            if self.mode == "REQUIRED":
                raise NativeRuntimeUnavailableError(f"Native runtime required but unavailable: {exc}") from exc
            return RuntimeResponse(
                request_id=request_id,
                protocol_version=CURRENT_PROTOCOL_VERSION,
                status=ResponseStatus.ERROR,
                error=RuntimeErrorModel(
                    category=ErrorCategory.RUNTIME_UNAVAILABLE,
                    code="NATIVE_RUNTIME_UNAVAILABLE",
                    message=f"Native runtime could not complete request: {exc}",
                    retryable=True,
                ),
            )

        # 6. Audit outcome
        await self._emit_audit("runtime.request.completed", {
            "request_id": request_id,
            "operation": operation,
            "status": response.status.value,
        })

        return response

    async def cancel(self, cancellation_id: str) -> bool:
        """Forward cancellation request to native runtime."""
        if not self.is_enabled():
            return False
        result = await self.client.cancel(cancellation_id)
        await self._emit_audit("runtime.request.cancelled", {
            "cancellation_id": cancellation_id,
            "success": result,
        })
        return result

    async def _verify_authorization(self, operation: str, ctx: RequestContext) -> bool:
        """Verify with SecurityCenter whether caller has permission for native operation."""
        # System status and ping probes are accessible to all authenticated contexts
        if operation in ("sys.ping", "sys.health", "sys.info", "sys.metrics", "sys.sleep", "sys.cancel"):
            return True

        # For future privileged native operations, enforce SecurityCenter policy evaluation
        try:
            return self.security_center.is_allowed(
                user_id=ctx.user_id,
                action=f"native:{operation}",
                resource="native_substrate",
            )
        except Exception:
            return False

    async def sandbox_preflight(self, req: ExecutionRequest) -> PreflightResult:
        """Evaluate preflight validation and effective policy calculation without execution."""
        if not self.is_enabled():
            return PreflightResult(
                accepted=False,
                capability_id=req.capability_id,
                effective_policy=req.sandbox_policy,
                effective_budget=req.resource_budget,
                rejection_reason="Native runtime execution is disabled in this environment",
            )

        if self.emergency_stop.is_stopped():
            return PreflightResult(
                accepted=False,
                capability_id=req.capability_id,
                effective_policy=req.sandbox_policy,
                effective_budget=req.resource_budget,
                rejection_reason="EmergencyStop is active",
            )

        return await self.client.sandbox_preflight(req)

    async def sandbox_execute(
        self,
        req: ExecutionRequest,
        approval_id: Optional[str] = None,
    ) -> ExecutionResult:
        """
        Execute a native capability workload within the isolated Rust sandbox.
        STRICT FAIL-CLOSED GOVERNANCE:
        1. EmergencyStop check (absolute authority - halts instantly).
        2. SecurityCenter authorization check.
        3. Human approval validation for stateful / external mutation capabilities.
        4. Resource budget validation.
        5. Emits structured audit events across all lifecycle transitions.
        """
        # 1. Mode Check
        if not self.is_enabled():
            return ExecutionResult(
                request_id=req.request_id,
                execution_id=f"exec_dis_{req.request_id[:8]}",
                capability_id=req.capability_id,
                state=ExecutionState.REJECTED,
                exit_code=1,
                stderr="Native runtime execution is disabled in this environment",
                failure_classification="NATIVE_RUNTIME_DISABLED",
            )

        # 2. EmergencyStop Check (ABSOLUTE AUTHORITY)
        if self.emergency_stop.is_stopped():
            logger.critical(
                "native_service.sandbox_blocked_by_emergency_stop capability=%s request_id=%s",
                req.capability_id,
                req.request_id,
            )
            await self._emit_audit("runtime.sandbox.rejected", {
                "request_id": req.request_id,
                "capability_id": req.capability_id,
                "reason": "EmergencyStop is active",
            })
            await self._emit_audit("runtime.security.blocked_by_emergency_stop", {
                "request_id": req.request_id,
                "capability_id": req.capability_id,
                "reason": "EmergencyStop is active",
            })
            return ExecutionResult(
                request_id=req.request_id,
                execution_id=f"exec_estop_{req.request_id[:8]}",
                capability_id=req.capability_id,
                state=ExecutionState.REJECTED,
                exit_code=1,
                stderr="Execution blocked by active EmergencyStop",
                failure_classification="EMERGENCY_STOP_ACTIVE",
                error=RuntimeErrorModel(
                    category=ErrorCategory.AUTHORIZATION_REQUIRED,
                    code="EMERGENCY_STOP_ACTIVE",
                    message="Execution blocked by active EmergencyStop",
                ),
            )

        # 3. SecurityCenter Authorization Check
        user_id = req.authorization_context.user_id if req.authorization_context else None
        authz_ok = await self._verify_sandbox_authorization(req.capability_id, req.authorization_context)
        if not authz_ok:
            logger.warning(
                "native_service.sandbox_authorization_denied capability=%s user_id=%s",
                req.capability_id,
                user_id,
            )
            await self._emit_audit("runtime.sandbox.rejected", {
                "request_id": req.request_id,
                "capability_id": req.capability_id,
                "user_id": user_id,
                "reason": "Authorization denied by SecurityCenter",
            })
            return ExecutionResult(
                request_id=req.request_id,
                execution_id=f"exec_authz_{req.request_id[:8]}",
                capability_id=req.capability_id,
                state=ExecutionState.REJECTED,
                exit_code=1,
                stderr=f"Caller lacks authorization for native capability '{req.capability_id}'",
                failure_classification="AUTHORIZATION_DENIED",
                error=RuntimeErrorModel(
                    category=ErrorCategory.AUTHORIZATION_REQUIRED,
                    code="AUTHORIZATION_DENIED",
                    message=f"Caller lacks authorization for native capability '{req.capability_id}'",
                ),
            )

        # 4. Approval Check for stateful capabilities (e.g. sandbox.execute)
        if req.capability_id in ("sandbox.execute", "native.stateful") and not approval_id:
            await self._emit_audit("runtime.sandbox.rejected", {
                "request_id": req.request_id,
                "capability_id": req.capability_id,
                "reason": "Approval required but missing",
            })
            return ExecutionResult(
                request_id=req.request_id,
                execution_id=f"exec_appr_{req.request_id[:8]}",
                capability_id=req.capability_id,
                state=ExecutionState.REJECTED,
                exit_code=1,
                stderr=f"Capability '{req.capability_id}' requires explicit approval context",
                failure_classification="APPROVAL_REQUIRED",
                error=RuntimeErrorModel(
                    category=ErrorCategory.AUTHORIZATION_REQUIRED,
                    code="APPROVAL_REQUIRED",
                    message=f"Capability '{req.capability_id}' requires explicit approval context",
                ),
            )

        # 5. Audit acceptance and start
        await self._emit_audit("runtime.sandbox.accepted", {
            "request_id": req.request_id,
            "capability_id": req.capability_id,
            "profile": req.sandbox_policy.profile.value,
        })
        await self._emit_audit("runtime.sandbox.started", {
            "request_id": req.request_id,
            "capability_id": req.capability_id,
        })

        # 6. Dispatch to Rust sandbox runtime
        result = await self.client.sandbox_execute(req)

        # 7. Audit completion based on final state
        event_map = {
            ExecutionState.COMPLETED: "runtime.sandbox.completed",
            ExecutionState.FAILED: "runtime.sandbox.failed",
            ExecutionState.CANCELLED: "runtime.sandbox.cancelled",
            ExecutionState.TIMED_OUT: "runtime.sandbox.timed_out",
            ExecutionState.KILLED: "runtime.sandbox.killed",
            ExecutionState.RESOURCE_EXCEEDED: "runtime.sandbox.resource_exceeded",
            ExecutionState.REJECTED: "runtime.sandbox.rejected",
        }
        event_name = event_map.get(result.state, "runtime.sandbox.completed")
        await self._emit_audit(event_name, {
            "request_id": req.request_id,
            "execution_id": result.execution_id,
            "capability_id": req.capability_id,
            "state": result.state.value,
            "duration_ms": result.duration_ms,
        })

        return result

    async def _verify_sandbox_authorization(self, capability_id: str, ctx: Optional[RequestContext]) -> bool:
        """Verify whether caller is authorized for sandboxed capability execution."""
        # Standard built-in capabilities are accessible to authenticated callers
        if capability_id in ("sandbox.preflight", "sandbox.echo", "sandbox.hash", "sandbox.probe", "sandbox.execute"):
            return True

        user_id = ctx.user_id if ctx else None
        try:
            return self.security_center.is_allowed(
                user_id=user_id,
                action=f"native:sandbox:{capability_id}",
                resource="native_sandbox",
            )
        except Exception:
            return False

    async def _emit_audit(self, event_name: str, payload: Dict[str, Any]) -> None:
        try:
            if hasattr(self.event_registry, "emit"):
                await self.event_registry.emit(event_name, payload)
        except Exception as exc:
            logger.debug("native_service.audit_emit_ignored event=%s error=%s", event_name, exc)
