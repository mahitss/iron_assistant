"""Tool execution engine with argument validation, permissions check, governance, resource economy, and native sandbox routing."""

import json
import logging
import time
import uuid
from typing import Any, Optional

from pydantic import ValidationError

from app.security.center import SecurityCenter, get_security_center
from app.security.policies import SecurityDecision
from app.tools.base import (
    ToolExecutionClass,
    ToolExecutionPreference,
)
from app.tools.permissions import (
    PermissionDecision,
    PermissionDeniedError,
    PermissionManager,
)
from app.tools.registry import ToolRegistry
from app.tools.schemas import ToolCall, ToolResult

logger = logging.getLogger("kairo.tools.executor")


class ToolExecutor:
    """Executes structured tool calls safely against the registry, Security Center, and Native Runtime."""

    def __init__(
        self,
        registry: ToolRegistry,
        permission_manager: PermissionManager | None = None,
        security_center: SecurityCenter | None = None,
    ) -> None:
        self.registry = registry
        self.permission_manager = permission_manager or PermissionManager()
        self.security_center = security_center or get_security_center()

    async def execute(
        self,
        tool_call: ToolCall,
        user_id: str = "default_user",
        session_id: str | None = None,
        approval_id: str | None = None,
        correlation_id: str | None = None,
        db_session: Any = None,
    ) -> ToolResult:
        """Execute a structured tool call safely through governance and native/python execution routing."""
        tool_name = tool_call.name
        tool = self.registry.get(tool_name)

        # 1. Lookup tool in registry
        if tool is None:
            logger.warning("Attempted execution of unknown tool: %s", tool_name)
            return ToolResult(
                success=False,
                tool_name=tool_name,
                tool_call_id=tool_call.id,
                error=f"Tool '{tool_name}' is not registered or unavailable.",
                verification_status="failed",
            )

        # 2. Authoritative Security Center evaluation
        sec_decision = await self.security_center.authorize(
            user_id=user_id,
            tool_name=tool.name,
            arguments=tool_call.arguments,
            permission_level=tool.permission_level,
            session_id=session_id,
            db_session=db_session,
        )

        if sec_decision.decision == SecurityDecision.DENIED:
            logger.warning("Security Center DENIED tool '%s': %s", tool.name, sec_decision.reason)
            return ToolResult(
                success=False,
                tool_name=tool.name,
                tool_call_id=tool_call.id,
                error=sec_decision.reason or f"Action '{tool.name}' is denied by Security Center.",
                verification_status="denied",
                approval_required=False,
            )

        if sec_decision.decision == SecurityDecision.APPROVAL_REQUIRED:
            if not approval_id:
                logger.info("Security Center requires approval for tool '%s'", tool.name)
                return ToolResult(
                    success=False,
                    tool_name=tool.name,
                    tool_call_id=tool_call.id,
                    error=sec_decision.reason or f"Action '{tool.name}' requires explicit user approval.",
                    verification_status="denied",
                    approval_required=True,
                )

        # 2b. Policy & Governance Engine defense-in-depth check (Task 36, Spec 99)
        from app.policy.engine import policy_engine
        from app.policy.schemas import PolicyDecisionType

        policy_dec = await policy_engine.check_tool_execution(
            tool_name=tool.name,
            arguments=tool_call.arguments,
            user_id=user_id,
            session_id=session_id,
            environment="development",
        )
        if policy_dec.decision == PolicyDecisionType.DENY:
            logger.warning("Policy Engine DENIED tool '%s': %s", tool.name, policy_dec.safe_explanation)
            return ToolResult(
                success=False,
                tool_name=tool.name,
                tool_call_id=tool_call.id,
                error=policy_dec.safe_explanation or f"Action '{tool.name}' is denied by governance policy.",
                verification_status="denied",
                approval_required=False,
            )
        if policy_dec.decision == PolicyDecisionType.REQUIRE_APPROVAL:
            if not approval_id:
                return ToolResult(
                    success=False,
                    tool_name=tool.name,
                    tool_call_id=tool_call.id,
                    error=policy_dec.safe_explanation or f"Action '{tool.name}' requires formal human approval.",
                    verification_status="denied",
                    approval_required=True,
                )
        if policy_dec.decision == PolicyDecisionType.REQUIRE_STEP_UP_AUTH:
            return ToolResult(
                success=False,
                tool_name=tool.name,
                tool_call_id=tool_call.id,
                error=policy_dec.safe_explanation or f"Action '{tool.name}' requires step-up authentication.",
                verification_status="denied",
                approval_required=False,
            )

        # 3. Check legacy permission manager for backward compatibility with custom test policies
        try:
            self.permission_manager.check_permission(tool.name, tool.permission_level)
        except PermissionDeniedError as exc:
            logger.warning("Permission denied for tool '%s': %s", tool.name, exc.reason)
            decision = self.permission_manager.evaluate(tool.name, tool.permission_level)
            requires_approval = decision == PermissionDecision.REQUIRES_APPROVAL
            if requires_approval and approval_id:
                pass  # Approved
            else:
                return ToolResult(
                    success=False,
                    tool_name=tool.name,
                    tool_call_id=tool_call.id,
                    error=f"Permission denied: {exc.reason}",
                    verification_status="denied",
                    approval_required=requires_approval,
                )

        # 4. Validate arguments against tool's Pydantic schema
        try:
            validated_args = tool.args_model(**tool_call.arguments)
        except ValidationError as exc:
            clean_errors = "; ".join(
                f"{err.get('loc', ['arg'])[0]}: {err.get('msg', 'invalid')}" for err in exc.errors()
            )
            logger.info("Argument validation failed for tool '%s': %s", tool.name, clean_errors)
            return ToolResult(
                success=False,
                tool_name=tool.name,
                tool_call_id=tool_call.id,
                error=f"Argument validation failed: {clean_errors}",
                verification_status="failed",
            )

        # 5. Resilience & Circuit Breaker Check
        from app.resilience import resilience_manager
        from app.resilience.failures import ErrorSanitizer

        circuit_id = f"tool:{tool.name}"
        cb = resilience_manager.circuit_registry.get_or_create(circuit_id)
        if not cb.is_call_permitted():
            logger.warning("ToolExecutor: Circuit breaker for '%s' is OPEN. Failing fast.", tool.name)
            return ToolResult(
                success=False,
                tool_name=tool.name,
                tool_call_id=tool_call.id,
                error=f"Circuit breaker for tool '{tool.name}' is OPEN (fail-fast active).",
                verification_status="failed",
            )

        # 6. ROUTING: Check if tool is NATIVE_RUST or has native capability preference
        is_native_candidate = (
            tool.execution_class == ToolExecutionClass.NATIVE_RUST
            or (tool.preference in (ToolExecutionPreference.NATIVE_REQUIRED, ToolExecutionPreference.NATIVE_PREFERRED)
                and tool.capability_id is not None)
        )

        if is_native_candidate:
            return await self._execute_native(
                tool=tool,
                tool_call=tool_call,
                validated_args=validated_args,
                user_id=user_id,
                session_id=session_id,
                approval_id=approval_id,
                correlation_id=correlation_id,
                cb=cb,
            )

        # 7. Standard Python Execution
        return await self._execute_python(
            tool=tool,
            tool_call=tool_call,
            validated_args=validated_args,
            cb=cb,
            is_fallback=False,
        )

    async def _execute_native(
        self,
        tool: Any,
        tool_call: ToolCall,
        validated_args: Any,
        user_id: str,
        session_id: Optional[str],
        approval_id: Optional[str],
        correlation_id: Optional[str],
        cb: Any,
    ) -> ToolResult:
        """Execute a tool through the Rust native sandbox substrate with resource enforcement."""
        from app.native.service import get_native_runtime_service
        from app.native.models import (
            AuthorizationContext,
            ExecutionRequest,
            ExecutionState,
            ResourceBudget,
            SandboxPolicy,
            SandboxProfile,
        )

        native_service = get_native_runtime_service()
        exec_start = time.perf_counter()

        # Check native service availability
        health = await native_service.get_health()
        runtime_available = native_service.is_enabled() and health.get("healthy", False)

        if not runtime_available:
            # Check preference: NATIVE_REQUIRED fails closed immediately!
            if tool.preference == ToolExecutionPreference.NATIVE_REQUIRED:
                logger.warning(
                    "Tool '%s' requires native execution substrate, but runtime is unavailable (state=%s)",
                    tool.name,
                    health.get("status"),
                )
                self.registry.record_invocation(tool.name, 0.0, success=False)
                return ToolResult(
                    success=False,
                    tool_name=tool.name,
                    tool_call_id=tool_call.id,
                    error=f"Tool '{tool.name}' requires native runtime substrate, which is currently {health.get('status')}.",
                    verification_status="failed",
                    execution_class="NATIVE_RUST",
                )

            # NATIVE_PREFERRED: Route to verified Python fallback
            logger.info(
                "Tool '%s' native substrate unavailable (%s); routing to verified Python fallback.",
                tool.name,
                health.get("status"),
            )
            return await self._execute_python(
                tool=tool,
                tool_call=tool_call,
                validated_args=validated_args,
                cb=cb,
                is_fallback=True,
            )

        # Check EmergencyStop
        if native_service.emergency_stop.is_stopped():
            logger.critical("Tool '%s' native execution blocked by active EmergencyStop", tool.name)
            self.registry.record_invocation(tool.name, 0.0, success=False)
            return ToolResult(
                success=False,
                tool_name=tool.name,
                tool_call_id=tool_call.id,
                error="Execution blocked by active EmergencyStop.",
                verification_status="denied",
                execution_class="NATIVE_RUST",
            )

        # Map sandbox profile
        try:
            profile_enum = SandboxProfile[tool.sandbox_profile]
        except (KeyError, ValueError):
            profile_enum = SandboxProfile.STANDARD

        # Construct typed ExecutionRequest
        req_id = f"tool_{uuid.uuid4().hex[:12]}"
        payload = validated_args.model_dump()
        timeout_ms = int(tool.timeout_seconds * 1000)

        exec_req = ExecutionRequest(
            request_id=req_id,
            capability_id=tool.capability_id,
            arguments=[str(v) for v in payload.values() if isinstance(v, (str, int, float, bool))],
            payload=payload,
            sandbox_policy=SandboxPolicy(
                profile=profile_enum,
                resource_budget=ResourceBudget(
                    max_execution_time_ms=timeout_ms,
                ),
            ),
            resource_budget=ResourceBudget(
                max_execution_time_ms=timeout_ms,
            ),
            deadline_ms=timeout_ms,
            correlation_id=correlation_id or session_id or "tool_exec",
            authorization_context=AuthorizationContext(
                user_id=user_id,
                session_id=session_id,
                permissions=[tool.permission_level.value],
            ),
        )

        try:
            res = await native_service.sandbox_execute(exec_req, approval_id=approval_id)
            cb.record_success()
            dur_ms = (time.perf_counter() - exec_start) * 1000.0
        except Exception as exc:
            cb.record_failure()
            dur_ms = (time.perf_counter() - exec_start) * 1000.0
            logger.error("Native execution error for tool '%s': %s", tool.name, exc)
            self.registry.record_invocation(tool.name, dur_ms, success=False)
            return ToolResult(
                success=False,
                tool_name=tool.name,
                tool_call_id=tool_call.id,
                error=f"Native runtime error executing '{tool.name}': {exc}",
                verification_status="failed",
                execution_class="NATIVE_RUST",
                duration_ms=dur_ms,
            )

        # Handle native execution results
        if res.state == ExecutionState.COMPLETED:
            # Parse structured output if tool defines output_model or stdout is JSON
            parsed_result: Any = res.stdout
            if tool.output_model is not None:
                try:
                    parsed_result = tool.output_model.model_validate_json(res.stdout).model_dump()
                except Exception:
                    try:
                        parsed_result = json.loads(res.stdout)
                    except Exception:
                        parsed_result = res.stdout
            else:
                try:
                    parsed_result = json.loads(res.stdout)
                except Exception:
                    parsed_result = res.stdout

            # Post-execution verification hook
            try:
                is_valid = tool.verify(parsed_result)
            except Exception:
                is_valid = False

            if not is_valid:
                logger.warning("Tool '%s' native output verification failed", tool.name)
                self.registry.record_invocation(tool.name, dur_ms, success=False)
                return ToolResult(
                    success=False,
                    tool_name=tool.name,
                    tool_call_id=tool_call.id,
                    result=parsed_result,
                    error=f"Output verification failed for native tool '{tool.name}'.",
                    verification_status="failed",
                    execution_class="NATIVE_RUST",
                    capability_id=tool.capability_id,
                    duration_ms=dur_ms,
                )

            self.registry.record_invocation(tool.name, dur_ms, success=True)
            return ToolResult(
                success=True,
                tool_name=tool.name,
                tool_call_id=tool_call.id,
                result=parsed_result,
                error=None,
                verification_status="verified",
                execution_class="NATIVE_RUST",
                capability_id=tool.capability_id,
                duration_ms=dur_ms,
                resource_telemetry=res.resource_telemetry.model_dump() if res.resource_telemetry else None,
                provenance={
                    "tool_version": tool.version,
                    "runtime_version": "0.1.0",
                    "request_id": res.request_id,
                    "execution_id": res.execution_id,
                },
            )

        elif res.state == ExecutionState.RESOURCE_EXCEEDED:
            self.registry.record_invocation(tool.name, dur_ms, success=False, is_resource_violation=True)
            return ToolResult(
                success=False,
                tool_name=tool.name,
                tool_call_id=tool_call.id,
                error=f"Resource limit exceeded during native execution: {res.stderr or res.failure_classification}",
                verification_status="failed",
                execution_class="NATIVE_RUST",
                capability_id=tool.capability_id,
                duration_ms=dur_ms,
                resource_telemetry=res.resource_telemetry.model_dump() if res.resource_telemetry else None,
            )

        elif res.state == ExecutionState.TIMED_OUT:
            self.registry.record_invocation(tool.name, dur_ms, success=False, is_timeout=True)
            return ToolResult(
                success=False,
                tool_name=tool.name,
                tool_call_id=tool_call.id,
                error=f"Native execution exceeded timeout of {tool.timeout_seconds}s.",
                verification_status="failed",
                execution_class="NATIVE_RUST",
                duration_ms=dur_ms,
            )

        elif res.state == ExecutionState.REJECTED:
            self.registry.record_invocation(tool.name, dur_ms, success=False)
            return ToolResult(
                success=False,
                tool_name=tool.name,
                tool_call_id=tool_call.id,
                error=res.stderr or "Native execution request was rejected by runtime admission control.",
                verification_status="denied",
                execution_class="NATIVE_RUST",
                duration_ms=dur_ms,
            )

        else:
            self.registry.record_invocation(tool.name, dur_ms, success=False)
            return ToolResult(
                success=False,
                tool_name=tool.name,
                tool_call_id=tool_call.id,
                error=res.stderr or f"Native execution failed with status: {res.state.value}",
                verification_status="failed",
                execution_class="NATIVE_RUST",
                duration_ms=dur_ms,
            )

    async def _execute_python(
        self,
        tool: Any,
        tool_call: ToolCall,
        validated_args: Any,
        cb: Any,
        is_fallback: bool = False,
    ) -> ToolResult:
        """Execute a tool logic via Python implementation."""
        from app.resilience.failures import ErrorSanitizer

        exec_start = time.perf_counter()
        try:
            raw_result = await tool.execute(**validated_args.model_dump())
            cb.record_success()
            dur_ms = (time.perf_counter() - exec_start) * 1000.0
            from app.observability.dependencies import dependency_tracker
            from app.observability.metrics import get_metrics_collector

            dependency_tracker.record_call(source="agent", target=f"tool:{tool.name}", duration_ms=dur_ms, is_error=False)
            get_metrics_collector().record_latency("tool_duration_seconds", dur_ms / 1000.0, labels={"tool": tool.name})
        except ValueError as exc:
            cb.record_failure()
            dur_ms = (time.perf_counter() - exec_start) * 1000.0
            from app.observability.dependencies import dependency_tracker

            dependency_tracker.record_call(source="agent", target=f"tool:{tool.name}", duration_ms=dur_ms, is_error=True)
            logger.info("Tool '%s' returned value error: %s", tool.name, exc)
            self.registry.record_invocation(tool.name, dur_ms, success=False, is_fallback=is_fallback)
            return ToolResult(
                success=False,
                tool_name=tool.name,
                tool_call_id=tool_call.id,
                error=ErrorSanitizer.sanitize_text(str(exc)),
                verification_status="failed",
                execution_class="PYTHON",
                duration_ms=dur_ms,
            )
        except Exception as exc:
            cb.record_failure()
            dur_ms = (time.perf_counter() - exec_start) * 1000.0
            logger.exception("Unexpected exception executing tool '%s'", tool.name)
            clean_err = ErrorSanitizer.sanitize_text(f"An error occurred while executing tool '{tool.name}': {type(exc).__name__}")
            self.registry.record_invocation(tool.name, dur_ms, success=False, is_fallback=is_fallback)
            return ToolResult(
                success=False,
                tool_name=tool.name,
                tool_call_id=tool_call.id,
                error=clean_err,
                verification_status="failed",
                execution_class="PYTHON",
                duration_ms=dur_ms,
            )

        # Output verification
        try:
            is_valid = tool.verify(raw_result)
        except Exception:
            is_valid = False

        if not is_valid:
            logger.warning("Tool '%s' output verification failed", tool.name)
            self.registry.record_invocation(tool.name, dur_ms, success=False, is_fallback=is_fallback)
            return ToolResult(
                success=False,
                tool_name=tool.name,
                tool_call_id=tool_call.id,
                result=raw_result,
                error=f"Output verification failed for tool '{tool.name}'.",
                verification_status="failed",
                execution_class="PYTHON",
                duration_ms=dur_ms,
            )

        self.registry.record_invocation(tool.name, dur_ms, success=True, is_fallback=is_fallback)
        return ToolResult(
            success=True,
            tool_name=tool.name,
            tool_call_id=tool_call.id,
            result=raw_result,
            error=None,
            verification_status="verified",
            execution_class="PYTHON",
            duration_ms=dur_ms,
            provenance={"tool_version": getattr(tool, "version", "1.0.0"), "fallback": is_fallback},
        )

    async def execute_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        user_id: str = "default_user",
        project_id: str | None = None,
        session_id: str | None = None,
        approval_id: str | None = None,
        correlation_id: str | None = None,
        db_session: Any = None,
    ) -> ToolResult:
        """Convenience method to execute a tool by name and argument dict."""
        call = ToolCall(id=f"call_{uuid.uuid4().hex[:8]}", name=name, arguments=arguments)
        return await self.execute(
            tool_call=call,
            user_id=user_id,
            session_id=session_id,
            approval_id=approval_id,
            correlation_id=correlation_id,
            db_session=db_session,
        )


_global_tool_executor: ToolExecutor | None = None


def get_tool_executor() -> ToolExecutor:
    """Return canonical global ToolExecutor singleton."""
    global _global_tool_executor
    if _global_tool_executor is None:
        from app.tools.registry import create_default_tool_registry

        _global_tool_executor = ToolExecutor(registry=create_default_tool_registry())
    return _global_tool_executor
