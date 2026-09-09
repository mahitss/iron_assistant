"""Tests for Task & Approval Continuity, Cascading Revocation, and Ambiguity Handling (Spec 33-38, 41, 65, 101-103, 148, 152, 153)."""

from datetime import UTC, datetime
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.devices.models import DeviceModel
from app.identity.devices import IdentityDeviceManager
from app.identity.policies import IdentityPolicyEnforcer
from app.identity.resolver import IdentityResolver
from app.identity.revocation import RevocationCoordinator
from app.identity.schemas import ClientType, DeviceTrustStatus, IdentityErrorCode, SessionStatus
from app.identity.sessions import SessionManager
from app.identity.trust import DeviceTrustManager
from app.security.approvals import ApprovalManager
from app.security.exceptions import SecurityPolicyViolationError
from app.security.redaction import ArgumentSanitizer
from app.tasks.models import TaskModel


@pytest.fixture
async def db_session():
    """Create in-memory async SQLite database session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_task_continuity_across_sessions(db_session: AsyncSession):
    """Verify single running task seamlessly resolves across sessions (Spec 33, 34, 155)."""
    # 1. Create running task
    task = TaskModel(
        id="tsk_cont_01",
        user_id="user_alice",
        objective="Run CI and diagnose failures",
        status="RUNNING",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(task)
    await db_session.commit()

    # 2. Desktop session connects and asks to continue
    resolver = IdentityResolver(db_session)
    res = await resolver.resolve_task_continuity(user_id="user_alice")

    assert res["ambiguous"] is False
    assert res["task_id"] == "tsk_cont_01"
    assert "Run CI" in res["objective"]


@pytest.mark.asyncio
async def test_task_ambiguity_prompts_user_without_guessing(db_session: AsyncSession):
    """Verify multiple active tasks triggers prompt rather than guessing (Spec 41, 152)."""
    t1 = TaskModel(
        id="tsk_01",
        user_id="user_alice",
        objective="Deploy frontend to staging",
        status="RUNNING",
        created_at=datetime.now(UTC),
    )
    t2 = TaskModel(
        id="tsk_02",
        user_id="user_alice",
        objective="Analyze database migration logs",
        status="RUNNING",
        created_at=datetime.now(UTC),
    )
    db_session.add_all([t1, t2])
    await db_session.commit()

    resolver = IdentityResolver(db_session)
    res = await resolver.resolve_task_continuity(user_id="user_alice")

    # Strict requirement: DO NOT GUESS (Spec 41, 152)
    assert res["ambiguous"] is True
    assert res["error_code"] == IdentityErrorCode.AMBIGUOUS_TARGET.value
    assert "multiple active tasks" in res["prompt"]
    assert len(res["options"]) == 2


@pytest.mark.asyncio
async def test_device_ambiguity_prompts_user_without_guessing(db_session: AsyncSession):
    """Verify multiple candidate devices triggers prompt without guessing (Spec 66, 153)."""
    dev_mgr = IdentityDeviceManager(db_session)
    trust_mgr = DeviceTrustManager(db_session)

    d1 = await dev_mgr.register_device("user_alice", "Desktop-A", "windows", capabilities=["SCREEN"])
    d2 = await dev_mgr.register_device("user_alice", "Desktop-B", "darwin", capabilities=["SCREEN"])
    await trust_mgr.update_trust("user_alice", d1.id, DeviceTrustStatus.TRUSTED)
    await trust_mgr.update_trust("user_alice", d2.id, DeviceTrustStatus.TRUSTED)

    resolver = IdentityResolver(db_session)
    res = await resolver.resolve_device_target(user_id="user_alice", required_capability="SCREEN")

    # Strict requirement: DO NOT GUESS (Spec 66, 153)
    assert res["ambiguous"] is True
    assert res["error_code"] == IdentityErrorCode.AMBIGUOUS_DEVICE.value
    assert "Multiple authorized devices" in res["prompt"]
    assert len(res["options"]) == 2


@pytest.mark.asyncio
async def test_cross_session_approval_and_stale_approval_defense(db_session: AsyncSession):
    """Verify approvals belong to user/action and stale target changes are rejected (Spec 36, 101-103)."""
    # 1. Desktop task creates approval request for target File A
    args_target_a = {"file_path": "/var/data/config.yaml", "action": "write"}
    approval = await ApprovalManager.create_request(
        db_session=db_session,
        user_id="user_alice",
        tool_name="filesystem_write",
        arguments=args_target_a,
        risk_level="HIGH",
    )
    assert approval.status == "pending"

    # 2. User approves from Web session
    approved_req = await ApprovalManager.apply_decision(
        db_session=db_session,
        approval_id=approval.id,
        user_id="user_alice",
        decision="approve",
    )
    assert approved_req.status == "approved"

    # 3. Valid match: Tool checks approval for File A -> Found!
    fingerprint_a = ArgumentSanitizer.compute_action_fingerprint(
        tool_name="filesystem_write",
        user_id="user_alice",
        session_id=None,
        arguments=args_target_a,
    )
    active_approval = await ApprovalManager.find_active_approval(
        db_session=db_session,
        user_id="user_alice",
        action_fingerprint=fingerprint_a,
    )
    assert active_approval is not None

    # 4. Target changed to File B -> Stale approval rejected! (Spec 103)
    args_target_b = {"file_path": "/etc/shadow", "action": "write"}
    fingerprint_b = ArgumentSanitizer.compute_action_fingerprint(
        tool_name="filesystem_write",
        user_id="user_alice",
        session_id=None,
        arguments=args_target_b,
    )
    stale_check = await ApprovalManager.find_active_approval(
        db_session=db_session,
        user_id="user_alice",
        action_fingerprint=fingerprint_b,
    )
    assert stale_check is None


@pytest.mark.asyncio
async def test_device_revocation_cascading_ripple(db_session: AsyncSession):
    """Verify device revocation immediately terminates all sessions on that device (Spec 14, 75, 148)."""
    dev_mgr = IdentityDeviceManager(db_session)
    sess_mgr = SessionManager(db_session)
    trust_mgr = DeviceTrustManager(db_session)
    coordinator = RevocationCoordinator(db_session)

    # 1. Register and trust device
    dev = await dev_mgr.register_device("user_alice", "My-Workstation", "windows")
    await trust_mgr.update_trust("user_alice", dev.id, DeviceTrustStatus.TRUSTED)

    # 2. Create 2 sessions bound to this device
    s1 = await sess_mgr.create_session("user_alice", ClientType.DESKTOP, device_id=dev.id)
    s2 = await sess_mgr.create_session("user_alice", ClientType.LOCAL_COMPANION, device_id=dev.id)

    # 3. Revoke device
    result = await coordinator.revoke_device("user_alice", dev.id, reason="Lost laptop")
    assert result["status"] == "REVOKED"
    assert result["terminated_sessions"] == 2

    # 4. Verify sessions on this device are REVOKED
    with pytest.raises(SecurityPolicyViolationError):
        await sess_mgr.get_session(s1.session_id)
    with pytest.raises(SecurityPolicyViolationError):
        await sess_mgr.get_session(s2.session_id)
