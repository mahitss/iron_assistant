"""Integration tests for Central SecurityCenter authorization, capability gates, and policy."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import Base
from app.security.approvals import ApprovalManager
from app.security.center import SecurityCenter
from app.security.emergency_stop import EmergencyStopService
from app.security.permissions import PermissionLevel
from app.security.policies import SecurityDecision
from app.security.risk import RiskLevel
from app.security.schemas import CapabilitySettingsUpdate


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
async def test_security_center_allows_safe_read_tools(async_db_session: AsyncSession):
    """Verify safe read tools are automatically allowed."""
    sec_center = SecurityCenter()

    decision = await sec_center.authorize(
        user_id="user_1",
        tool_name="web_search",
        arguments={"query": "python"},
        permission_level=PermissionLevel.READ,
        db_session=async_db_session,
    )
    assert decision.decision == SecurityDecision.ALLOWED
    assert decision.risk_level == RiskLevel.LOW


@pytest.mark.asyncio
async def test_security_center_denies_destructive_tools(async_db_session: AsyncSession):
    """Verify destructive actions are strictly denied by policy."""
    sec_center = SecurityCenter()

    decision = await sec_center.authorize(
        user_id="user_1",
        tool_name="github_merge_pr",
        arguments={"pr_id": 42},
        permission_level=PermissionLevel.DESTRUCTIVE,
        db_session=async_db_session,
    )
    assert decision.decision == SecurityDecision.DENIED
    assert decision.risk_level == RiskLevel.CRITICAL


@pytest.mark.asyncio
async def test_security_center_approval_flow_and_fingerprint_binding(async_db_session: AsyncSession):
    """Verify approval requirement, approval creation, and fingerprint validation."""
    sec_center = SecurityCenter()

    # 1. Initial attempt -> APPROVAL_REQUIRED
    dec1 = await sec_center.authorize(
        user_id="user_alice",
        tool_name="browser_click",
        arguments={"selector": "#confirm-btn"},
        permission_level=PermissionLevel.EXTERNAL,
        session_id="sess_123",
        db_session=async_db_session,
    )
    assert dec1.decision == SecurityDecision.APPROVAL_REQUIRED
    assert dec1.approval_id is not None

    # 2. User approves the request
    await ApprovalManager.apply_decision(
        db_session=async_db_session,
        approval_id=dec1.approval_id,
        user_id="user_alice",
        decision="approve",
    )

    # 3. Exact matching attempt -> now ALLOWED
    dec2 = await sec_center.authorize(
        user_id="user_alice",
        tool_name="browser_click",
        arguments={"selector": "#confirm-btn"},
        permission_level=PermissionLevel.EXTERNAL,
        session_id="sess_123",
        db_session=async_db_session,
    )
    assert dec2.decision == SecurityDecision.ALLOWED

    # 4. Same tool but DIFFERENT argument -> APPROVAL_REQUIRED (cannot reuse approval!)
    dec3 = await sec_center.authorize(
        user_id="user_alice",
        tool_name="browser_click",
        arguments={"selector": "#delete-btn"},  # Changed selector!
        permission_level=PermissionLevel.EXTERNAL,
        session_id="sess_123",
        db_session=async_db_session,
    )
    assert dec3.decision == SecurityDecision.APPROVAL_REQUIRED
    assert dec3.approval_id != dec1.approval_id


@pytest.mark.asyncio
async def test_security_center_capability_gate_enforcement(async_db_session: AsyncSession):
    """Verify disabled capabilities deny all associated tools."""
    sec_center = SecurityCenter()

    # Default: computer_control is False
    comp_dec = await sec_center.authorize(
        user_id="user_test",
        tool_name="computer_click",
        arguments={"x": 10, "y": 20},
        permission_level=PermissionLevel.EXTERNAL,
        db_session=async_db_session,
    )
    assert comp_dec.decision == SecurityDecision.DENIED
    assert "computer_control" in comp_dec.reason

    # Disable browser capability
    await sec_center.update_user_capabilities(
        db_session=async_db_session,
        user_id="user_test",
        updates=CapabilitySettingsUpdate(browser=False),
    )

    browser_dec = await sec_center.authorize(
        user_id="user_test",
        tool_name="browser_navigate",
        arguments={"url": "https://example.com"},
        permission_level=PermissionLevel.READ,
        db_session=async_db_session,
    )
    assert browser_dec.decision == SecurityDecision.DENIED
    assert "browser" in browser_dec.reason


@pytest.mark.asyncio
async def test_security_center_emergency_stop_blocks_side_effects(async_db_session: AsyncSession):
    """Verify active emergency stop blocks modifying actions while allowing safe reads."""
    estop = EmergencyStopService()
    sec_center = SecurityCenter(emergency_stop=estop)

    estop.trigger_emergency_stop("user_alice", reason="Manual kill switch")

    # Modifying action is blocked
    block_dec = await sec_center.authorize(
        user_id="user_alice",
        tool_name="git_push",
        arguments={"branch": "main"},
        permission_level=PermissionLevel.WRITE,
        db_session=async_db_session,
    )
    assert block_dec.decision == SecurityDecision.DENIED
    assert "Emergency stop is ACTIVE" in block_dec.reason

    # Safe read action is permitted
    read_dec = await sec_center.authorize(
        user_id="user_alice",
        tool_name="git_status",
        arguments={},
        permission_level=PermissionLevel.READ,
        db_session=async_db_session,
    )
    assert read_dec.decision == SecurityDecision.ALLOWED
