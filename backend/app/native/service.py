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

    async def _emit_audit(self, event_name: str, payload: Dict[str, Any]) -> None:
        try:
            if hasattr(self.event_registry, "emit"):
                await self.event_registry.emit(event_name, payload)
        except Exception as exc:
            logger.debug("native_service.audit_emit_ignored event=%s error=%s", event_name, exc)
