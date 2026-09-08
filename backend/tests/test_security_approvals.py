"""Unit tests for Security ApprovalManager: lifecycle, decisions, and tenant isolation."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import Base
from app.security.approvals import ApprovalManager
from app.security.exceptions import (
    ApprovalExpiredError,
    TenantIsolationError,
)
from app.security.models import SecurityApprovalRequest


@pytest.fixture
async def async_db_session():
    """In-memory SQLite database session for unit tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_approval_lifecycle_and_decision(async_db_session: AsyncSession):
    """Verify approval creation, pending listing, and approve decision."""
    req = await ApprovalManager.create_request(
        db_session=async_db_session,
        user_id="user_alice",
        tool_name="browser_click",
        arguments={"selector": "#submit-btn"},
        risk_level="MEDIUM",
        timeout_seconds=30,
    )
    assert req.id is not None
    assert req.status == "pending"

    pending = await ApprovalManager.list_pending_approvals(async_db_session, "user_alice")
    assert len(pending) == 1
    assert pending[0].id == req.id

    # User Alice approves
    decided = await ApprovalManager.apply_decision(
        db_session=async_db_session,
        approval_id=req.id,
        user_id="user_alice",
        decision="approve",
    )
    assert decided.status == "approved"

    # Subsequent pending query is now empty
    pending_after = await ApprovalManager.list_pending_approvals(async_db_session, "user_alice")
    assert len(pending_after) == 0


@pytest.mark.asyncio
async def test_cross_user_approval_forbidden(async_db_session: AsyncSession):
    """Verify User Bob cannot approve or deny User Alice's approval request."""
    req = await ApprovalManager.create_request(
        db_session=async_db_session,
        user_id="user_alice",
        tool_name="git_push",
        arguments={"branch": "main"},
        risk_level="HIGH",
        timeout_seconds=30,
    )

    with pytest.raises(TenantIsolationError):
        await ApprovalManager.apply_decision(
            db_session=async_db_session,
            approval_id=req.id,
            user_id="user_bob",  # Wrong user!
            decision="approve",
        )


@pytest.mark.asyncio
async def test_expired_approval_rejected(async_db_session: AsyncSession):
    """Verify expired approval cannot be approved."""
    now = datetime.now(UTC)
    req = SecurityApprovalRequest(
        user_id="user_alice",
        tool_name="test_runner",
        action_description="Run tests",
        risk_level="HIGH",
        arguments_summary={},
        action_fingerprint="fp_expired",
        status="pending",
        created_at=now - timedelta(seconds=60),
        expires_at=now - timedelta(seconds=10),  # Already expired
    )
    async_db_session.add(req)
    await async_db_session.commit()

    with pytest.raises(ApprovalExpiredError):
        await ApprovalManager.apply_decision(
            db_session=async_db_session,
            approval_id=req.id,
            user_id="user_alice",
            decision="approve",
        )
