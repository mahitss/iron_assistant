"""Unit tests for approval requests, decisions, expiration, and authorization."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.automation.approvals import (
    ApprovalAlreadyDecidedError,
    ApprovalExpiredError,
    apply_approval_decision,
    create_approval_request,
    is_approval_expired,
)
from app.automation.models import ApprovalRequest, Workflow, WorkflowRun
from app.automation.service import AutomationService
from app.automation.state import WorkflowStatus
from app.db.session import Base


@pytest.fixture
async def async_db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


def test_approval_creation_and_expiration():
    """Verify approval creation and expiration calculation."""
    appr = create_approval_request(
        user_id="user_alice",
        run_id="run_123",
        tool_name="test_runner",
        tool_args={"command": "pytest"},
        permission_level="EXECUTE",
        timeout_seconds=10,
    )
    assert appr.status == "pending"
    assert is_approval_expired(appr) is False

    # Force expiration
    appr.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    assert is_approval_expired(appr) is True

    # Deciding expired approval raises ApprovalExpiredError
    with pytest.raises(ApprovalExpiredError):
        apply_approval_decision(appr, "approve", user_id="user_alice")


def test_cross_user_approval_forbidden():
    """Ensure User B cannot approve User A's action."""
    appr = create_approval_request(
        user_id="user_alice",
        run_id="run_123",
        tool_name="git_push",
        tool_args={},
        permission_level="EXTERNAL",
        timeout_seconds=60,
    )

    with pytest.raises(PermissionError):
        apply_approval_decision(appr, "approve", user_id="user_bob")


def test_already_decided_approval_rejected():
    """Ensure decided approval cannot be altered."""
    appr = create_approval_request(
        user_id="user_alice",
        run_id="run_123",
        tool_name="git_push",
        tool_args={},
        permission_level="EXTERNAL",
        timeout_seconds=60,
    )
    apply_approval_decision(appr, "approve", user_id="user_alice")
    assert appr.status == "approved"

    with pytest.raises(ApprovalAlreadyDecidedError):
        apply_approval_decision(appr, "deny", user_id="user_alice")


@pytest.mark.asyncio
async def test_service_decide_approval_flow(async_db_session: AsyncSession):
    """Verify AutomationService.decide_approval updates approval and fails run on deny."""
    now = datetime.now(UTC)
    wf = Workflow(
        user_id="user_alice",
        name="Approval Test WF",
        enabled=True,
        trigger_type="manual",
        trigger_config={},
        action_config={},
        created_at=now,
        updated_at=now,
    )
    async_db_session.add(wf)
    await async_db_session.commit()

    run = WorkflowRun(
        workflow_id=wf.id,
        user_id="user_alice",
        status=WorkflowStatus.WAITING_APPROVAL.value,
        idempotency_key="run_appr_1",
        created_at=now,
        updated_at=now,
    )
    async_db_session.add(run)
    await async_db_session.commit()

    appr = ApprovalRequest(
        user_id="user_alice",
        run_id=run.id,
        tool_name="git_push",
        tool_args={},
        permission_level="EXTERNAL",
        status="pending",
        created_at=now,
        expires_at=now + timedelta(seconds=60),
    )
    async_db_session.add(appr)
    await async_db_session.commit()

    service = AutomationService(session=async_db_session)

    # Deny action
    decided = await service.decide_approval(appr.id, "user_alice", "deny", reason="Security policy")
    assert decided.status == "denied"

    # Verify run transitioned to FAILED
    await async_db_session.refresh(run)
    assert run.status == WorkflowStatus.FAILED.value
    assert "Security policy" in run.error
