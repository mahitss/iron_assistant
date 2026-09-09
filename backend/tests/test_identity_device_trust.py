"""Unit and integration tests for Device Trust, Capabilities, and Pairing Security (Task 33, Spec 10-20, 148, 154)."""

from datetime import UTC, datetime, timedelta
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.devices.models import DeviceModel
from app.identity.devices import IdentityDeviceManager
from app.identity.policies import IdentityPolicyEnforcer
from app.identity.schemas import (
    ClientType,
    DeviceCapability,
    DevicePairingConsumeRequest,
    DevicePairingRequest,
    DeviceStatus,
    DeviceTrustStatus,
    IdentityErrorCode,
)
from app.identity.trust import DeviceTrustManager
from app.security.exceptions import (
    CapabilityDisabledError,
    SecurityPolicyViolationError,
    TenantIsolationError,
)


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
async def test_device_registration_explicit_untrusted(db_session: AsyncSession):
    """Verify new device registers as UNTRUSTED by default (Spec 12, 15)."""
    dev_mgr = IdentityDeviceManager(db_session)
    device = await dev_mgr.register_device(
        user_id="user_alice",
        device_name="Workstation-PC",
        os_name="windows",
        client_type=ClientType.DESKTOP,
        capabilities=["SCREEN", "MICROPHONE"],
    )

    assert device.id.startswith("dev_")
    assert device.status == DeviceStatus.ACTIVE.value
    assert device.trust_status == DeviceTrustStatus.UNTRUSTED.value
    assert "SCREEN" in device.capabilities
    assert "MICROPHONE" in device.capabilities


@pytest.mark.asyncio
async def test_offline_is_not_revoked(db_session: AsyncSession):
    """Verify marking a device offline does not revoke its authorization (Spec 11)."""
    dev_mgr = IdentityDeviceManager(db_session)
    device = await dev_mgr.register_device(
        user_id="user_alice",
        device_name="Laptop",
        os_name="darwin",
    )

    await dev_mgr.mark_offline(device.id)
    await db_session.refresh(device)

    assert device.status == DeviceStatus.OFFLINE.value
    assert device.trust_status != DeviceTrustStatus.REVOKED.value


@pytest.mark.asyncio
async def test_explicit_device_trust_lifecycle(db_session: AsyncSession):
    """Verify explicit trust promotion and expiration (Spec 12, 133)."""
    dev_mgr = IdentityDeviceManager(db_session)
    trust_mgr = DeviceTrustManager(db_session)

    device = await dev_mgr.register_device(user_id="user_alice", device_name="Home-PC", os_name="windows")
    assert device.trust_status == DeviceTrustStatus.UNTRUSTED.value

    # Explicitly trust device
    trusted = await trust_mgr.update_trust(
        user_id="user_alice", device_id=device.id, target_trust=DeviceTrustStatus.TRUSTED, expires_in_days=30
    )
    assert trusted.trust_status == DeviceTrustStatus.TRUSTED.value
    assert trusted.trust_expires_at is not None

    # Verification passes
    is_trusted = await trust_mgr.verify_device_trusted("user_alice", device.id)
    assert is_trusted is True

    # When trust expires, verification fails (Spec 133)
    trusted.trust_expires_at = datetime.now(UTC) - timedelta(days=1)
    await db_session.commit()

    is_still_trusted = await trust_mgr.verify_device_trusted("user_alice", device.id)
    assert is_still_trusted is False


@pytest.mark.asyncio
async def test_trusted_device_does_not_grant_permissions(db_session: AsyncSession):
    """Verify trusted device does NOT bypass SecurityCenter or grant computer control (Spec 13, 54)."""
    dev_mgr = IdentityDeviceManager(db_session)
    trust_mgr = DeviceTrustManager(db_session)

    device = await dev_mgr.register_device(
        user_id="user_alice", device_name="Trusted-Rig", os_name="windows", capabilities=["SCREEN"]
    )
    await trust_mgr.update_trust(user_id="user_alice", device_id=device.id, target_trust=DeviceTrustStatus.TRUSTED)

    # Invariant: Trusted device status must NOT enable computer control by default
    assert device.computer_control_enabled is False

    # Security policy enforcer confirms capability without authorization is DENIED
    with pytest.raises(SecurityPolicyViolationError) as exc:
        IdentityPolicyEnforcer.enforce_capability_vs_permission(
            device_declared_capabilities=device.capabilities,
            requested_capability="SCREEN",
            security_center_authorized=False,  # SecurityCenter denies
        )
    assert IdentityErrorCode.CAPABILITY_UNAUTHORIZED.value in str(exc.value)


@pytest.mark.asyncio
async def test_capability_advertisement_vs_hardware(db_session: AsyncSession):
    """Verify requesting a capability not supported by device hardware fails (Spec 19, 20)."""
    # Device only supports MICROPHONE
    with pytest.raises(CapabilityDisabledError):
        IdentityPolicyEnforcer.enforce_capability_vs_permission(
            device_declared_capabilities=["MICROPHONE"],
            requested_capability="CAMERA",
            security_center_authorized=True,
        )


@pytest.mark.asyncio
async def test_secure_device_pairing_and_replay_protection(db_session: AsyncSession):
    """Verify pairing code single-use consumption and replay defense (Spec 16-18, 84)."""
    dev_mgr = IdentityDeviceManager(db_session)

    # 1. Initiate pairing
    req = DevicePairingRequest(
        device_name="Desktop-Companion",
        client_type=ClientType.LOCAL_COMPANION,
        capabilities=[DeviceCapability.SCREEN, DeviceCapability.KEYBOARD],
    )
    pairing_resp = await dev_mgr.initiate_pairing(user_id="user_alice", request=req)

    assert pairing_resp.pairing_code.startswith("PAIR-")
    assert pairing_resp.device_id.startswith("dev_")

    # 2. Consume pairing code (1st time: success)
    consume_req = DevicePairingConsumeRequest(
        device_id=pairing_resp.device_id,
        pairing_code=pairing_resp.pairing_code,
    )
    consumed = await dev_mgr.consume_pairing(user_id="user_alice", request=consume_req)
    assert consumed["status"] == DeviceStatus.ACTIVE.value
    assert "device_token" in consumed

    # 3. Attempt replay of consumed pairing code (2nd time: strictly DENIED, Spec 18)
    with pytest.raises(SecurityPolicyViolationError) as exc:
        await dev_mgr.consume_pairing(user_id="user_alice", request=consume_req)
    assert "already been consumed" in str(exc.value)


@pytest.mark.asyncio
async def test_expired_pairing_code_rejected(db_session: AsyncSession):
    """Verify expired pairing code cannot be consumed (Spec 17)."""
    dev_mgr = IdentityDeviceManager(db_session)
    req = DevicePairingRequest(device_name="Old-Companion")
    pairing_resp = await dev_mgr.initiate_pairing(user_id="user_alice", request=req)

    # Simulate expired pairing code
    device = await db_session.get(DeviceModel, pairing_resp.device_id)
    device.pairing_expires_at = datetime.now(UTC) - timedelta(minutes=1)
    await db_session.commit()

    consume_req = DevicePairingConsumeRequest(
        device_id=pairing_resp.device_id,
        pairing_code=pairing_resp.pairing_code,
    )
    with pytest.raises(SecurityPolicyViolationError) as exc:
        await dev_mgr.consume_pairing(user_id="user_alice", request=consume_req)
    assert "expired" in str(exc.value)
