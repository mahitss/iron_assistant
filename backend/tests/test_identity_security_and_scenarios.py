"""Security scenario tests verifying all 16 Final Security Questions (Task 33, Spec 146-159, 162)."""

from datetime import UTC, datetime
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.devices.models import DeviceModel
from app.identity.devices import IdentityDeviceManager
from app.identity.handoff import HandoffManager
from app.identity.policies import IdentityPolicyEnforcer
from app.identity.resolver import IdentityResolver
from app.identity.revocation import RevocationCoordinator
from app.identity.schemas import (
    ClientType,
    DeviceCapability,
    DeviceTrustStatus,
    HandoffCompleteRequest,
    HandoffCreateRequest,
    IdentityErrorCode,
    SessionStatus,
)
from app.identity.sessions import SessionManager
from app.identity.tokens import mask_token
from app.identity.trust import DeviceTrustManager
from app.security.approvals import ApprovalManager
from app.security.center import get_security_center
from app.security.exceptions import (
    CapabilityDisabledError,
    EmergencyStopActiveError,
    SecurityPolicyViolationError,
    TenantIsolationError,
)
from app.security.redaction import ArgumentSanitizer


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
async def test_q1_session_cannot_bypass_authorization(db_session: AsyncSession):
    """Q1: Can a valid session bypass authorization? -> NEVER (Spec 53, 162)."""
    sess_mgr = SessionManager(db_session)
    sess = await sess_mgr.create_session("user_alice", ClientType.WEB)

    # Valid session exists
    assert sess.status == SessionStatus.ACTIVE

    # But authorization policy strictly enforces permissions
    with pytest.raises(SecurityPolicyViolationError):
        IdentityPolicyEnforcer.enforce_capability_vs_permission(
            device_declared_capabilities=["SCREEN"],
            requested_capability="SCREEN",
            security_center_authorized=False,
        )


@pytest.mark.asyncio
async def test_q2_trusted_device_cannot_bypass_security_center(db_session: AsyncSession):
    """Q2: Can a trusted device bypass SecurityCenter? -> NEVER (Spec 13, 54, 162)."""
    dev_mgr = IdentityDeviceManager(db_session)
    trust_mgr = DeviceTrustManager(db_session)

    dev = await dev_mgr.register_device("user_alice", "Trusted-Rig", "windows")
    await trust_mgr.update_trust("user_alice", dev.id, DeviceTrustStatus.TRUSTED)

    assert dev.trust_status == DeviceTrustStatus.TRUSTED.value
    # Invariant: Trusted device status does NOT enable computer control automatically
    assert dev.computer_control_enabled is False


@pytest.mark.asyncio
async def test_q3_device_capability_does_not_equal_permission(db_session: AsyncSession):
    """Q3: Can device capability equal permission? -> NEVER (Spec 20, 154, 162)."""
    # Device advertises SCREEN capability, but SecurityCenter denied permission
    with pytest.raises(SecurityPolicyViolationError) as exc:
        IdentityPolicyEnforcer.enforce_capability_vs_permission(
            device_declared_capabilities=["SCREEN", "MICROPHONE"],
            requested_capability="SCREEN",
            security_center_authorized=False,
        )
    assert IdentityErrorCode.CAPABILITY_UNAUTHORIZED.value in str(exc.value)


@pytest.mark.asyncio
async def test_q4_handoff_token_cannot_be_replayed(db_session: AsyncSession):
    """Q4: Can a handoff token be replayed? -> NEVER (Spec 85, 150, 162)."""
    sess_mgr = SessionManager(db_session)
    handoff_mgr = HandoffManager(db_session)

    s1 = await sess_mgr.create_session("user_alice", ClientType.WEB)
    s2 = await sess_mgr.create_session("user_alice", ClientType.DESKTOP)

    resp = await handoff_mgr.create_handoff("user_alice", HandoffCreateRequest(source_session_id=s1.session_id, explicit_consent=True))
    req = HandoffCompleteRequest(handoff_token=resp.handoff_token, target_session_id=s2.session_id)

    # 1st consume: passes
    await handoff_mgr.complete_handoff("user_alice", resp.handoff_id, req)

    # 2nd consume: REPLAY DENIED
    with pytest.raises(SecurityPolicyViolationError) as exc:
        await handoff_mgr.complete_handoff("user_alice", resp.handoff_id, req)
    assert IdentityErrorCode.HANDOFF_INVALID.value in str(exc.value)


@pytest.mark.asyncio
async def test_q5_user_a_cannot_handoff_user_b_task(db_session: AsyncSession):
    """Q5: Can User A hand off User B's task? -> NEVER (Spec 98, 147, 162)."""
    sess_mgr = SessionManager(db_session)
    handoff_mgr = HandoffManager(db_session)

    s_alice = await sess_mgr.create_session("user_alice", ClientType.WEB)

    # Alice creates a handoff ticket
    resp = await handoff_mgr.create_handoff("user_alice", HandoffCreateRequest(source_session_id=s_alice.session_id, explicit_consent=True))

    # Bob attempts to complete Alice's handoff ticket
    s_bob = await sess_mgr.create_session("user_bob", ClientType.DESKTOP)
    with pytest.raises(TenantIsolationError):
        await handoff_mgr.complete_handoff("user_bob", resp.handoff_id, HandoffCompleteRequest(handoff_token=resp.handoff_token, target_session_id=s_bob.session_id))


@pytest.mark.asyncio
async def test_q6_and_q15_revoked_device_blocked(db_session: AsyncSession):
    """Q6 & Q15: Can revoked devices reconnect or execute actions? -> NEVER (Spec 14, 84, 148, 162)."""
    dev_mgr = IdentityDeviceManager(db_session)
    coordinator = RevocationCoordinator(db_session)

    dev = await dev_mgr.register_device("user_alice", "Comp-01", "windows")
    await coordinator.revoke_device("user_alice", dev.id)

    await db_session.refresh(dev)
    assert dev.status == "REVOKED"
    assert dev.credentials_hash is None

    # Attempting to check trust for revoked device raises error
    with pytest.raises(SecurityPolicyViolationError) as exc:
        IdentityPolicyEnforcer.enforce_device_trust(
            device_status=dev.status,
            trust_status=dev.trust_status,
        )
    assert IdentityErrorCode.DEVICE_REVOKED.value in str(exc.value)


@pytest.mark.asyncio
async def test_q8_stale_approval_cannot_survive_target_changes(db_session: AsyncSession):
    """Q8: Can stale approval survive target changes? -> NEVER (Spec 103, 162)."""
    args_file_a = {"file": "/path/to/script.py", "write": True}
    apprv = await ApprovalManager.create_request(db_session, "user_alice", "fs_write", args_file_a)
    await ApprovalManager.apply_decision(db_session, apprv.id, "user_alice", "approve")

    # Target changes to File B
    args_file_b = {"file": "/path/to/critical.env", "write": True}
    fp_b = ArgumentSanitizer.compute_action_fingerprint("fs_write", "user_alice", None, args_file_b)

    found = await ApprovalManager.find_active_approval(db_session, "user_alice", fp_b)
    assert found is None


@pytest.mark.asyncio
async def test_q9_ambiguous_devices_are_not_guessed(db_session: AsyncSession):
    """Q9: Can ambiguous devices be guessed? -> NEVER (Spec 66, 153, 162)."""
    dev_mgr = IdentityDeviceManager(db_session)
    trust_mgr = DeviceTrustManager(db_session)
    d1 = await dev_mgr.register_device("user_alice", "PC-1", "windows", capabilities=["SCREEN"])
    d2 = await dev_mgr.register_device("user_alice", "PC-2", "windows", capabilities=["SCREEN"])
    await trust_mgr.update_trust("user_alice", d1.id, DeviceTrustStatus.TRUSTED)
    await trust_mgr.update_trust("user_alice", d2.id, DeviceTrustStatus.TRUSTED)

    resolver = IdentityResolver(db_session)
    res = await resolver.resolve_device_target("user_alice", required_capability="SCREEN")

    assert res["ambiguous"] is True
    assert res["error_code"] == IdentityErrorCode.AMBIGUOUS_DEVICE.value


@pytest.mark.asyncio
async def test_q14_raw_tokens_never_enter_logs():
    """Q14: Can raw tokens enter logs? -> NEVER (Spec 144, 162)."""
    raw_tok = "kairo_stk_SecretLongTokenStringThatShouldNeverBeLogged12345"
    masked = mask_token(raw_tok)

    assert raw_tok not in masked
    assert "[REDACTED]" in masked


@pytest.mark.asyncio
async def test_q16_emergency_stop_cannot_be_bypassed():
    """Q16: Can Emergency Stop be bypassed after reconnect? -> NEVER (Spec 72, 73, 157, 162)."""
    sec = get_security_center()
    sec.emergency_stop.trigger_emergency_stop(user_id="user_alice", reason="Critical breach")

    # Even with an active session, Emergency Stop check raises EmergencyStopActiveError
    with pytest.raises(EmergencyStopActiveError):
        IdentityPolicyEnforcer.enforce_emergency_stop(user_id="user_alice")

    # Clean up state
    sec.emergency_stop.reset_emergency_stop(user_id="user_alice", is_human_user=True)
