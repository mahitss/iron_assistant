"""Tool execution engine with argument validation, permissions check, and verification."""

import logging
from typing import Any

from pydantic import ValidationError

from app.security.center import SecurityCenter, get_security_center
from app.security.policies import SecurityDecision
from app.tools.permissions import (
    PermissionDecision,
    PermissionDeniedError,
    PermissionManager,
)
from app.tools.registry import ToolRegistry
from app.tools.schemas import ToolCall, ToolResult

logger = logging.getLogger("kairo.tools.executor")


class ToolExecutor:
    """Executes structured tool calls safely against the registry and Security Center."""

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
        db_session: Any = None,
    ) -> ToolResult:
        """Execute a single structured tool call safely through the Security Center."""
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
            logger.info("Security Center requires approval for tool '%s'", tool.name)
            return ToolResult(
                success=False,
                tool_name=tool.name,
                tool_call_id=tool_call.id,
                error=sec_decision.reason or f"Action '{tool.name}' requires explicit user approval.",
                verification_status="denied",
                approval_required=True,
            )

        # 3. Check legacy permission manager for backward compatibility with custom test policies
        try:
            self.permission_manager.check_permission(tool.name, tool.permission_level)
        except PermissionDeniedError as exc:
            logger.warning("Permission denied for tool '%s': %s", tool.name, exc.reason)
            decision = self.permission_manager.evaluate(tool.name, tool.permission_level)
            requires_approval = decision == PermissionDecision.REQUIRES_APPROVAL
            return ToolResult(
                success=False,
                tool_name=tool.name,
                tool_call_id=tool_call.id,
                error=f"Permission denied: {exc.reason}",
                verification_status="denied",
                approval_required=requires_approval,
            )

        # 3. Validate arguments against Pydantic schema
        try:
            validated_args = tool.args_model(**tool_call.arguments)
        except ValidationError as exc:
            # Format clean validation message without internal trace
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

        # 4. Execute tool logic
        try:
            raw_result = await tool.execute(**validated_args.model_dump())
        except ValueError as exc:
            logger.info("Tool '%s' returned value error: %s", tool.name, exc)
            return ToolResult(
                success=False,
                tool_name=tool.name,
                tool_call_id=tool_call.id,
                error=str(exc),
                verification_status="failed",
            )
        except Exception as exc:
            # Never expose internal Python stack traces to model/user
            logger.exception("Unexpected exception executing tool '%s'", tool.name)
            return ToolResult(
                success=False,
                tool_name=tool.name,
                tool_call_id=tool_call.id,
                error=f"An error occurred while executing tool '{tool.name}': {type(exc).__name__}",
                verification_status="failed",
            )

        # 5. Output verification
        try:
            is_valid = tool.verify(raw_result)
        except Exception:
            is_valid = False

        if not is_valid:
            logger.warning("Tool '%s' output verification failed", tool.name)
            return ToolResult(
                success=False,
                tool_name=tool.name,
                tool_call_id=tool_call.id,
                result=raw_result,
                error=f"Output verification failed for tool '{tool.name}'.",
                verification_status="failed",
            )

        return ToolResult(
            success=True,
            tool_name=tool.name,
            tool_call_id=tool_call.id,
            result=raw_result,
            error=None,
            verification_status="verified",
        )
