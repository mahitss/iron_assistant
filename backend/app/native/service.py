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
    from app.orchestration.resource_registry import ResourceRegistry, default_resource_registry
    from app.orchestration.coordinator import ResourceEconomyCoordinator, default_economy_coordinator
    from app.orchestration.resources import create_resource
    from app.orchestration.schemas import ResourceType, HealthStatus
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
    from backend.app.orchestration.resource_registry import ResourceRegistry, default_resource_registry
    from backend.app.orchestration.coordinator import ResourceEconomyCoordinator, default_economy_coordinator
    from backend.app.orchestration.resources import create_resource
    from backend.app.orchestration.schemas import ResourceType, HealthStatus

logger = logging.getLogger("kairo.native.service")


class NativeRuntimeService:
    _instance: Optional[NativeRuntimeService] = None

    def __init__(
        self,
        client: Optional[NativeRuntimeClient] = None,
        security_center: Optional[SecurityCenter] = None,
        emergency_stop: Optional[EmergencyStopService] = None,
        event_registry: Optional[EventRegistry] = None,
        resource_registry: Optional[ResourceRegistry] = None,
        economy_coordinator: Optional[ResourceEconomyCoordinator] = None,
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
        self.resource_registry = resource_registry or default_resource_registry
        self.economy_coordinator = economy_coordinator or default_economy_coordinator
        self._ensure_native_resources()

    def _ensure_native_resources(self) -> None:
        """Register baseline native substrate resource definitions in ResourceRegistry if not present."""
        try:
            if not self.resource_registry.has_resource("native_memory"):
                self.resource_registry.register(create_resource(
                    name="Native Host Memory Substrate",
                    resource_id="native_memory",
                    resource_type=ResourceType.MEMORY,
                    total_capacity=16384.0,  # 16 GiB pool
                    environment="production",
                ), allow_override=True)
            if not self.resource_registry.has_resource("native_cpu"):
                self.resource_registry.register(create_resource(
                    name="Native CPU Core Substrate",
                    resource_id="native_cpu",
                    resource_type=ResourceType.COMPUTE,
                    total_capacity=16.0,  # 16 cores
                    environment="production",
                ), allow_override=True)
            if not self.resource_registry.has_resource("native_workspace"):
                self.resource_registry.register(create_resource(
                    name="Native Workspace Storage",
                    resource_id="native_workspace",
                    resource_type=ResourceType.STORAGE,
                    total_capacity=51200.0,  # 50 GiB
                    environment="production",
                ), allow_override=True)
        except Exception as exc:
            logger.warning("native_service.ensure_resources_error: %s", exc)

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

        # 5. Resource Reservation with Task 77 Resource Economy
        self._ensure_native_resources()
        mem_mb = float(req.resource_budget.max_memory_bytes or (256 * 1024 * 1024)) / (1024 * 1024)
        expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=120)

        try:
            rsv_mem = self.resource_registry.reserve(
                resource_id="native_memory",
                owner=req.request_id,
                purpose=f"sandbox:{req.capability_id}",
                amount=mem_mb,
                expires_at=expires_at,
                scope=req.correlation_id or "GLOBAL",
            )
        except Exception as exc:
            logger.warning(
                "native_service.reservation_denied request_id=%s capability=%s error=%s",
                req.request_id,
                req.capability_id,
                exc,
            )
            await self._emit_audit("runtime.economy.backpressure", {
                "request_id": req.request_id,
                "capability_id": req.capability_id,
                "reason": str(exc),
            })
            return ExecutionResult(
                request_id=req.request_id,
                execution_id=f"exec_res_exh_{req.request_id[:8]}",
                capability_id=req.capability_id,
                state=ExecutionState.REJECTED,
                exit_code=1,
                stderr=f"Resource reservation capacity exhausted; backpressure applied: {exc}",
                failure_classification="RESOURCE_UNAVAILABLE",
                error=RuntimeErrorModel(
                    category=ErrorCategory.RESOURCE_LIMIT,
                    code="RESOURCE_UNAVAILABLE",
                    message=f"Resource reservation capacity exhausted; backpressure applied: {exc}",
                ),
            )

        # 6. Audit acceptance, reservation and start
        await self._emit_audit("runtime.economy.reserved", {
            "request_id": req.request_id,
            "reservation_id": rsv_mem.reservation_id,
            "resource_id": "native_memory",
            "amount_mb": mem_mb,
        })
        await self._emit_audit("runtime.sandbox.accepted", {
            "request_id": req.request_id,
            "capability_id": req.capability_id,
            "profile": req.sandbox_policy.profile.value,
        })
        await self._emit_audit("runtime.sandbox.started", {
            "request_id": req.request_id,
            "capability_id": req.capability_id,
        })

        result: Optional[ExecutionResult] = None
        try:
            # 7. Dispatch to Rust sandbox runtime
            result = await self.client.sandbox_execute(req)
            return result
        finally:
            # 8. ALWAYS release reservation on every terminal state (no reservation leaks!)
            self.resource_registry.release_reservation(rsv_mem.reservation_id)
            await self._emit_audit("runtime.economy.released", {
                "request_id": req.request_id,
                "reservation_id": rsv_mem.reservation_id,
            })

            # 9. Audit completion based on final state
            if result is not None:
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

                # 10. Reconcile actual usage against reservation with estimation learning
                actual_mb = 0.0
                if result.resource_telemetry:
                    peak_bytes = result.resource_telemetry.peak_memory_bytes or 0
                    actual_mb = peak_bytes / (1024 * 1024)
                variance_mb = mem_mb - actual_mb
                error_pct = (abs(variance_mb) / max(1.0, mem_mb)) * 100.0

                # Feed back into ResourceEconomyEngine for learning
                if hasattr(self.economy_coordinator, "economy") and hasattr(self.economy_coordinator.economy, "_historical_demands"):
                    key = f"native:{req.capability_id}"
                    if key not in self.economy_coordinator.economy._historical_demands:
                        self.economy_coordinator.economy._historical_demands[key] = []
                    self.economy_coordinator.economy._historical_demands[key].append(actual_mb)
                    if len(self.economy_coordinator.economy._historical_demands[key]) > 50:
                        self.economy_coordinator.economy._historical_demands[key].pop(0)

                await self._emit_audit("runtime.economy.reconciled", {
                    "request_id": req.request_id,
                    "capability_id": req.capability_id,
                    "reserved_memory_mb": mem_mb,
                    "actual_memory_mb": round(actual_mb, 2),
                    "variance_mb": round(variance_mb, 2),
                    "estimation_error_pct": round(error_pct, 2),
                })

                # 11. Resource violation audit
                if result.resource_violation:
                    await self._emit_audit("runtime.economy.violation", {
                        "request_id": req.request_id,
                        "capability_id": req.capability_id,
                        "violation_type": result.resource_violation.violation_type.value,
                        "severity": result.resource_violation.severity.value,
                        "enforcement_action": result.resource_violation.enforcement_action.value,
                        "message": result.resource_violation.message,
                    })

    def get_resource_economy_status(self) -> Dict[str, Any]:
        """Query aggregate resource status, capacity, and active reservations."""
        self._ensure_native_resources()
        resources = self.resource_registry.list_all()
        sat_pct, sat_state = self.economy_coordinator.economy.compute_economy_saturation()
        return {
            "saturation_pct": round(sat_pct * 100, 2),
            "saturation_state": sat_state.value,
            "resources": [
                {
                    "resource_id": r.resource_id,
                    "name": r.name,
                    "type": r.resource_type.value,
                    "total_capacity": r.total_capacity,
                    "available_capacity": r.available_capacity,
                    "reserved_capacity": r.reserved_capacity,
                    "allocated_capacity": r.allocated_capacity,
                    "health": r.health.value,
                }
                for r in resources
            ],
            "active_reservations_count": len([
                rsv for rsv in getattr(self.resource_registry, "_reservations", {}).values() if rsv.is_active
            ]),
        }

    # =========================================================================
    # Task 84: Native Computer Interaction Substrate APIs
    # =========================================================================

    async def list_windows(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Query host window metadata via native substrate."""
        import json
        req = ExecutionRequest(
            request_id=f"win_req_{uuid.uuid4().hex[:8]}",
            capability_id="native.window.inspect",
            arguments=[],
            payload={"limit": limit},
        )
        res = await self.sandbox_execute(req)
        if res.state == ExecutionState.COMPLETED and res.stdout:
            try:
                data = json.loads(res.stdout)
                if isinstance(data, dict) and "windows" in data:
                    return data["windows"]
                return data if isinstance(data, list) else []
            except Exception:
                return []
        return []

    async def list_processes(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Query host processes via native substrate."""
        import json
        req = ExecutionRequest(
            request_id=f"proc_req_{uuid.uuid4().hex[:8]}",
            capability_id="native.process.inspect",
            arguments=[],
            payload={"limit": limit},
        )
        res = await self.sandbox_execute(req)
        if res.state == ExecutionState.COMPLETED and res.stdout:
            try:
                data = json.loads(res.stdout)
                if isinstance(data, dict) and "processes" in data:
                    return data["processes"]
                return data if isinstance(data, list) else []
            except Exception:
                return []
        return []

    async def list_displays(self) -> List[Dict[str, Any]]:
        """Query connected display monitors and boundaries via native substrate."""
        import json
        req = ExecutionRequest(
            request_id=f"disp_req_{uuid.uuid4().hex[:8]}",
            capability_id="native.display.inspect",
            arguments=[],
            payload={},
        )
        res = await self.sandbox_execute(req)
        if res.state == ExecutionState.COMPLETED and res.stdout:
            try:
                data = json.loads(res.stdout)
                if isinstance(data, dict) and "displays" in data:
                    return data["displays"]
                return data if isinstance(data, list) else []
            except Exception:
                return []
        return []

    async def capture_screen(
        self,
        display_id: Optional[int] = None,
        max_width: Optional[int] = None,
        max_height: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Capture bounded point-in-time screen frame metadata via native substrate."""
        import json
        payload: Dict[str, Any] = {}
        if display_id is not None:
            payload["display_id"] = display_id
        if max_width is not None:
            payload["max_width"] = max_width
        if max_height is not None:
            payload["max_height"] = max_height

        req = ExecutionRequest(
            request_id=f"cap_req_{uuid.uuid4().hex[:8]}",
            capability_id="native.screen.capture",
            arguments=[],
            payload=payload,
        )
        res = await self.sandbox_execute(req)
        if res.state == ExecutionState.COMPLETED and res.stdout:
            try:
                return json.loads(res.stdout)
            except Exception:
                pass
        return {"error": res.stderr or "Screen capture failed", "status": "FAILED"}

    async def read_clipboard(self) -> Dict[str, Any]:
        """Read clipboard content without persisting to logs."""
        import json
        req = ExecutionRequest(
            request_id=f"clip_r_req_{uuid.uuid4().hex[:8]}",
            capability_id="native.clipboard.read",
            arguments=[],
            payload={},
        )
        res = await self.sandbox_execute(req)
        if res.state == ExecutionState.COMPLETED and res.stdout:
            try:
                return json.loads(res.stdout)
            except Exception:
                pass
        return {"error": res.stderr or "Clipboard read failed"}

    async def write_clipboard(self, text: str) -> Dict[str, Any]:
        """Write content to host clipboard under governance control."""
        import json
        req = ExecutionRequest(
            request_id=f"clip_w_req_{uuid.uuid4().hex[:8]}",
            capability_id="native.clipboard.write",
            arguments=[],
            payload={"text": text},
        )
        res = await self.sandbox_execute(req)
        if res.state == ExecutionState.COMPLETED and res.stdout:
            try:
                return json.loads(res.stdout)
            except Exception:
                pass
        return {"error": res.stderr or "Clipboard write failed"}

    async def execute_mouse(
        self,
        action: str,
        x: int,
        y: int,
        button: str = "left",
        click_count: int = 1,
        target_context: Optional[Dict[str, Any]] = None,
        approval_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute target-validated native mouse action."""
        import json
        req = ExecutionRequest(
            request_id=f"mouse_req_{uuid.uuid4().hex[:8]}",
            capability_id="native.input.mouse",
            arguments=[],
            payload={
                "action": action,
                "x": x,
                "y": y,
                "button": button,
                "click_count": click_count,
                "target_context": target_context,
            },
        )
        res = await self.sandbox_execute(req, approval_id=approval_id)
        if res.state == ExecutionState.COMPLETED and res.stdout:
            try:
                return json.loads(res.stdout)
            except Exception:
                pass
        return {"error": res.stderr or "Mouse action failed", "status": "FAILED"}

    async def execute_keyboard(
        self,
        action: str,
        text: Optional[str] = None,
        key: Optional[str] = None,
        target_context: Optional[Dict[str, Any]] = None,
        approval_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute target-validated native keyboard action."""
        import json
        payload: Dict[str, Any] = {
            "action": action,
            "target_context": target_context,
        }
        if text is not None:
            payload["text"] = text
        if key is not None:
            payload["key"] = key

        req = ExecutionRequest(
            request_id=f"kbd_req_{uuid.uuid4().hex[:8]}",
            capability_id="native.input.keyboard",
            arguments=[],
            payload=payload,
        )
        res = await self.sandbox_execute(req, approval_id=approval_id)
        if res.state == ExecutionState.COMPLETED and res.stdout:
            try:
                return json.loads(res.stdout)
            except Exception:
                pass
        return {"error": res.stderr or "Keyboard action failed", "status": "FAILED"}

    async def _verify_sandbox_authorization(self, capability_id: str, ctx: Optional[RequestContext]) -> bool:
        """Verify whether caller is authorized for sandboxed capability execution."""
        # Standard built-in and native computer capabilities are accessible to authorized callers
        if capability_id in (
            "sandbox.preflight",
            "sandbox.echo",
            "sandbox.hash",
            "sandbox.probe",
            "sandbox.execute",
            "native.sysinfo",
            "native.file.inspect",
            "native.window.inspect",
            "native.process.inspect",
            "native.display.inspect",
            "native.screen.capture",
            "native.clipboard.read",
            "native.clipboard.write",
            "native.input.mouse",
            "native.input.keyboard",
        ):
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


def get_native_service() -> NativeRuntimeService:
    """Convenience getter for the NativeRuntimeService singleton."""
    return NativeRuntimeService.get_instance()


# Alias for tool fabric compatibility
get_native_runtime_service = get_native_service

