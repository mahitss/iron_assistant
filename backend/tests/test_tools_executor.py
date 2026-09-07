"""Tests for ToolExecutor validation, execution, and verification."""

from typing import Any
import pytest
from pydantic import BaseModel, Field

from app.tools.base import BaseTool
from app.tools.executor import ToolExecutor
from app.tools.permissions import PermissionLevel
from app.tools.registry import ToolRegistry
from app.tools.schemas import ToolCall, ToolResult


class StrictArgs(BaseModel):
    number: int = Field(..., description="An integer number")
    multiplier: float = Field(default=1.0, description="Multiplier float")


class MultiplierTool(BaseTool):
    name = "multiplier"
    description = "Multiplies an integer by a multiplier"
    permission_level = PermissionLevel.READ
    args_model = StrictArgs

    async def execute(self, number: int, multiplier: float = 1.0, **kwargs: Any) -> float:
        if number < 0:
            raise ValueError("Negative numbers are disallowed.")
        return float(number * multiplier)

    def verify(self, result: Any) -> bool:
        # Rejects non-numbers or values over 100,000
        return isinstance(result, (int, float)) and result <= 100_000


@pytest.fixture
def executor() -> ToolExecutor:
    registry = ToolRegistry()
    registry.register(MultiplierTool())
    return ToolExecutor(registry=registry)


@pytest.mark.asyncio
async def test_successful_tool_execution(executor: ToolExecutor) -> None:
    """Ensure valid tool call executes and returns verified ToolResult."""
    call = ToolCall(id="call_1", name="multiplier", arguments={"number": 5, "multiplier": 2.5})
    result: ToolResult = await executor.execute(call)

    assert result.success is True
    assert result.tool_name == "multiplier"
    assert result.result == 12.5
    assert result.verification_status == "verified"
    assert result.error is None
    assert "12.5" in result.to_model_output()


@pytest.mark.asyncio
async def test_unknown_tool_execution(executor: ToolExecutor) -> None:
    """Ensure unknown tool returns clean error without crashing."""
    call = ToolCall(id="call_2", name="nonexistent", arguments={})
    result = await executor.execute(call)

    assert result.success is False
    assert result.verification_status == "failed"
    assert "not registered" in result.error


@pytest.mark.asyncio
async def test_missing_argument_validation_failure(executor: ToolExecutor) -> None:
    """Ensure missing required arguments fail validation cleanly."""
    call = ToolCall(id="call_3", name="multiplier", arguments={"multiplier": 2.0})
    result = await executor.execute(call)

    assert result.success is False
    assert "Argument validation failed" in result.error


@pytest.mark.asyncio
async def test_wrong_argument_type_validation_failure(executor: ToolExecutor) -> None:
    """Ensure wrong argument types fail validation cleanly."""
    call = ToolCall(id="call_4", name="multiplier", arguments={"number": "not_an_int"})
    result = await executor.execute(call)

    assert result.success is False
    assert "Argument validation failed" in result.error


@pytest.mark.asyncio
async def test_tool_exception_handling(executor: ToolExecutor) -> None:
    """Ensure exceptions raised within tool execution are captured safely without stack traces."""
    call = ToolCall(id="call_5", name="multiplier", arguments={"number": -10})
    result = await executor.execute(call)

    assert result.success is False
    assert "Negative numbers are disallowed" in result.error


@pytest.mark.asyncio
async def test_tool_verification_failure(executor: ToolExecutor) -> None:
    """Ensure results failing verification hook return verification_status='failed'."""
    call = ToolCall(id="call_6", name="multiplier", arguments={"number": 200_000})
    result = await executor.execute(call)

    assert result.success is False
    assert result.verification_status == "failed"
    assert "verification failed" in result.error
