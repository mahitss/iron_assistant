"""Unit and integration tests for Kairo Sessions and Lifecycle (Task 33, Spec 4, 6-9, 120, 121)."""

from datetime import UTC, datetime, timedelta
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.identity.models import IdentitySessionModel
from app.identity.policies import IdentityPolicyEnforcer
from app.identity.schemas import ClientType, IdentityErrorCode, SessionStatus
from app.identity.sessions import SessionManager
from app.security.exceptions import SecurityPolicyViolationError, TenantIsolationError


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
async def test_create_session_success(db_session: AsyncSession):
    """Verify session creation across client types (Spec 4, 5)."""
    manager = SessionManager(db_session)
    sess = await manager.create_session(
        user_id="user_alice",
        client_type=ClientType.WEB,
        device_id="dev_mac_01",
        metadata={"browser": "Chrome"},
    )

    assert sess.session_id.startswith("sess_")
    assert sess.user_id == "user_alice"
    assert sess.client_type == ClientType.WEB
    assert sess.device_id == "dev_mac_01"
    assert sess.status == SessionStatus.ACTIVE
    assert sess.expires_at > sess.created_at
    assert sess.metadata["browser"] == "Chrome"


@pytest.mark.asyncio
async def test_session_absolute_expiration(db_session: AsyncSession):
    """Verify expired session raises SESSION_EXPIRED (Spec 7, 151)."""
    manager = SessionManager(db_session)
    sess = await manager.create_session(
        user_id="user_alice",
        client_type=ClientType.DESKTOP,
        ttl_seconds=-10,  # Expired in past
    )

    with pytest.raises(SecurityPolicyViolationError) as exc:
        await manager.get_session(sess.session_id)
    assert IdentityErrorCode.SESSION_EXPIRED.value in str(exc.value)


@pytest.mark.asyncio
async def test_session_idle_timeout(db_session: AsyncSession):
    """Verify session idle timeout enforcement (Spec 4, 7)."""
    manager = SessionManager(db_session)
    sess = await manager.create_session(
        user_id="user_alice",
        client_type=ClientType.VOICE,
    )

    # Manually simulate idle in past
    model = await db_session.get(IdentitySessionModel, sess.session_id)
    model.last_activity_at = datetime.now(UTC) - timedelta(seconds=7200)
    await db_session.commit()

    with pytest.raises(SecurityPolicyViolationError) as exc:
        await manager.get_session(sess.session_id)
    assert IdentityErrorCode.SESSION_EXPIRED.value in str(exc.value)


@pytest.mark.asyncio
async def test_session_revocation(db_session: AsyncSession):
    """Verify revoking session blocks future requests (Spec 8, 151)."""
    manager = SessionManager(db_session)
    sess = await manager.create_session(
        user_id="user_alice",
        client_type=ClientType.WEB,
    )

    # Revoke
    revoked = await manager.revoke_session(sess.session_id, user_id="user_alice", reason="Logout")
    assert revoked.status == SessionStatus.REVOKED
    assert revoked.revoked_at is not None

    # Accessing revoked session fails
    with pytest.raises(SecurityPolicyViolationError) as exc:
        await manager.get_session(sess.session_id)
    assert IdentityErrorCode.SESSION_REVOKED.value in str(exc.value)


@pytest.mark.asyncio
async def test_global_sign_out_everywhere(db_session: AsyncSession):
    """Verify 'Sign out everywhere' revokes all active sessions for user (Spec 9, 78)."""
    manager = SessionManager(db_session)
    s1 = await manager.create_session(user_id="user_alice", client_type=ClientType.WEB)
    s2 = await manager.create_session(user_id="user_alice", client_type=ClientType.DESKTOP)
    s3 = await manager.create_session(user_id="user_alice", client_type=ClientType.VOICE)
    s_other = await manager.create_session(user_id="user_bob", client_type=ClientType.WEB)

    count = await manager.revoke_all_sessions(user_id="user_alice")
    assert count == 3

    # Alice sessions are now revoked
    active_alice = await manager.list_user_sessions("user_alice", include_revoked=False)
    assert len(active_alice) == 0

    # Bob session remains unaffected
    bob_sess = await manager.get_session(s_other.session_id)
    assert bob_sess.status == SessionStatus.ACTIVE.value


@pytest.mark.asyncio
async def test_max_sessions_limit_enforcement(db_session: AsyncSession):
    """Verify session ceiling revokes oldest idle session when limit exceeded (Spec 120, 121)."""
    manager = SessionManager(db_session)
    manager.max_sessions = 3

    s1 = await manager.create_session(user_id="user_alice", client_type=ClientType.WEB)
    s2 = await manager.create_session(user_id="user_alice", client_type=ClientType.DESKTOP)
    s3 = await manager.create_session(user_id="user_alice", client_type=ClientType.VOICE)

    # Creating 4th session exceeds limit (3)
    s4 = await manager.create_session(user_id="user_alice", client_type=ClientType.MOBILE)

    active = await manager.list_user_sessions("user_alice", include_revoked=False)
    active_ids = {s.session_id for s in active}

    assert len(active) == 3
    assert s1.session_id not in active_ids  # Oldest revoked
    assert s4.session_id in active_ids


@pytest.mark.asyncio
async def test_cross_user_session_access_denied(db_session: AsyncSession):
    """Verify User B cannot revoke or access User A's session (Spec 6, 147)."""
    manager = SessionManager(db_session)
    s_alice = await manager.create_session(user_id="user_alice", client_type=ClientType.WEB)

    with pytest.raises(TenantIsolationError):
        await manager.revoke_session(s_alice.session_id, user_id="user_bob")
