"""Integration tests for Policy Engine defense in depth across ToolExecutor and TaskEngine (Task 36, Specs 98, 99, 136-139)."""

import pytest
from app.policy.engine import policy_engine
from app.policy.schemas import PolicyContext, PolicyDecisionType
from app.security.emergency_stop import get_emergency_stop_service
from app.tasks.engine import AutonomousTaskEngine
from app.tasks.schemas import TaskBudget, TaskPlanSchema, TaskStatus, TaskStepSchema
from app.tools.executor import ToolExecutor
from app.tools.registry import create_default_tool_registry
from app.tools.schemas import ToolCall


@pytest.mark.asyncio
async def test_tool_executor_defense_in_depth_policy_enforcement():
    registry = create_default_tool_registry()
    executor = ToolExecutor(registry=registry)

    # Emergency stop trigger test (Section 139)
    es = get_emergency_stop_service()
    es.trigger_emergency_stop(reason="Test emergency stop defense in depth")

    try:
        call = ToolCall(id="tc_1", name="system_info", arguments={})
        res = await executor.execute(call, user_id="user_1")
        assert res.success is False
        assert res.verification_status == "denied"
        assert "Emergency Stop" in res.error
    finally:
        es.reset_emergency_stop(is_human_user=True)


@pytest.mark.asyncio
async def test_tool_executor_allows_safe_tools_when_normal():
    registry = create_default_tool_registry()
    executor = ToolExecutor(registry=registry)

    call = ToolCall(id="tc_2", name="system_info", arguments={})
    res = await executor.execute(call, user_id="user_1")
    # Should succeed or pass policy verification (verification_status != denied)
    assert res.verification_status != "denied"


@pytest.mark.asyncio
async def test_task_engine_policy_check_blocks_privileged_step():
    engine = AutonomousTaskEngine()

    # Step attempting production deployment
    step = TaskStepSchema(
        id="step_1",
        task_id="task_test_1",
        plan_id="plan_1",
        sequence=1,
        title="Deploy to production cluster",
        objective="Deploy to production cluster",
        tool_name="deploy_production",
        arguments={"environment": "production", "target": "core_api"},
        dependencies=[],
    )

    # Check directly via check_task_step
    dec = await policy_engine.check_task_step(
        task_id="task_test_1",
        action="deploy_production",
        target=step.arguments,
        user_id="user_1",
        environment="production",
    )
    # Production deployment requires approval or is denied
    assert dec.decision in (PolicyDecisionType.REQUIRE_APPROVAL, PolicyDecisionType.DENY)
    assert dec.decision != PolicyDecisionType.ALLOW
