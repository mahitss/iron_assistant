"""Workflow action execution interfacing with ToolRegistry and ToolExecutor."""

import logging
from typing import Any

from app.tools.executor import ToolExecutor
from app.tools.permissions import PermissionDecision, PermissionLevel, PermissionManager
from app.tools.registry import ToolRegistry, create_default_tool_registry
from app.tools.schemas import ToolCall, ToolResult

logger = logging.getLogger("kairo.automation.actions")


class ActionExecutionResult:
    """Outcome of a workflow step action evaluation."""

    def __init__(
        self,
        success: bool,
        result: Any = None,
        error: str | None = None,
        requires_approval: bool = False,
        permission_level: PermissionLevel | None = None,
        tool_name: str | None = None,
        tool_args: dict[str, Any] | None = None,
    ) -> None:
        self.success = success
        self.result = result
        self.error = error
        self.requires_approval = requires_approval
        self.permission_level = permission_level
        self.tool_name = tool_name
        self.tool_args = tool_args or {}


class WorkflowActionRunner:
    """Executes registered tools on behalf of workflow steps under strict permissions."""

    def __init__(
        self,
        registry: ToolRegistry | None = None,
        executor: ToolExecutor | None = None,
        permission_manager: PermissionManager | None = None,
    ) -> None:
        self.registry = registry or create_default_tool_registry()
        self.permission_manager = permission_manager or PermissionManager()
        self.executor = executor or ToolExecutor(
            registry=self.registry,
            permission_manager=self.permission_manager,
        )

    async def execute_action(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        is_approved: bool = False,
    ) -> ActionExecutionResult:
        """Validate and execute a tool action.

        If the tool requires approval (WRITE, EXTERNAL, EXECUTE) and is not yet approved,
        signals requires_approval=True so the workflow can pause in WAITING_APPROVAL.
        """
        tool = self.registry.get(tool_name)
        if not tool:
            return ActionExecutionResult(
                success=False,
                error=f"Tool '{tool_name}' is not registered in ToolRegistry.",
            )

        # Check permission level
        decision = self.permission_manager.evaluate(tool_name, tool.permission_level)

        if decision == PermissionDecision.DENIED:
            return ActionExecutionResult(
                success=False,
                error=f"Execution of '{tool_name}' is prohibited by security policy.",
                permission_level=tool.permission_level,
            )

        if decision == PermissionDecision.REQUIRES_APPROVAL and not is_approved:
            logger.info("Tool '%s' requires approval before workflow execution.", tool_name)
            return ActionExecutionResult(
                success=False,
                requires_approval=True,
                permission_level=tool.permission_level,
                tool_name=tool_name,
                tool_args=arguments,
            )

        # Execute tool via ToolExecutor
        tool_call = ToolCall(
            id=f"wf_call_{tool_name}",
            name=tool_name,
            arguments=arguments,
        )
        try:
            # If approved, bypass executor's initial check
            if is_approved:
                # Direct execute on tool instance
                args_obj = tool.args_model(**arguments)
                tool_result: ToolResult = await tool.execute(args_obj)
            else:
                tool_result: ToolResult = await self.executor.execute(tool_call)

            return ActionExecutionResult(
                success=tool_result.success,
                result=tool_result.result,
                error=tool_result.error,
                permission_level=tool.permission_level,
                tool_name=tool_name,
                tool_args=arguments,
            )
        except Exception as exc:
            return ActionExecutionResult(
                success=False,
                error=f"Action execution error: {exc}",
                permission_level=tool.permission_level,
                tool_name=tool_name,
                tool_args=arguments,
            )
