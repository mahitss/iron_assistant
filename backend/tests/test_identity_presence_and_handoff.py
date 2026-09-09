"""Unit and integration tests for Presence, Heartbeats, and Cross-Interface Handoff (Task 33, Spec 21-32, 149, 150)."""

from datetime import UTC, datetime, timedelta
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.identity.handoff import HandoffManager
from app.identity.models import HandoffContextModel, IdentityPresenceModel
from app.identity.presence import PresenceTracker
from app.identity.schemas import (
    ClientType,
    HandoffCompleteRequest,
    HandoffCreateRequest,
    IdentityErrorCode,
    PresenceState,
    PresenceUpdateRequest,
)
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
async def test_presence_heartbeat_and_rate_limiting(db_session: AsyncSession):
    """Verify presence updates and heartbeat rate limiting (Spec 21, 24, 119)."""
    sess_mgr = SessionManager(db_session)
    presence_tracker = PresenceTracker(db_session)

    sess = await sess_mgr.create_session(user_id="user_alice", client_type=ClientType.WEB)

    # 1. First heartbeat: creates presence record
    req = PresenceUpdateRequest(session_id=sess.session_id, interface="WEB", state=PresenceState.ACTIVE)
    p1 = await presence_tracker.update_presence(user_id="user_alice", request=req)
    assert p1.state == PresenceState.ACTIVE
    assert p1.session_id == sess.session_id

    # 2. Immediate second heartbeat: rate-limited, returns without database write spam
    p2 = await presence_tracker.update_presence(user_id="user_alice", request=req)
    assert p2.id == p1.id


@pytest.mark.asyncio
async def test_presence_timeout_marks_disconnected(db_session: AsyncSession):
    """Verify stopped heartbeat marks presence DISCONNECTED without revoking session (Spec 25)."""
    sess_mgr = SessionManager(db_session)
    presence_tracker = PresenceTracker(db_session)
    sess = await sess_mgr.create_session(user_id="user_alice", client_type=ClientType.DESKTOP)

    req = PresenceUpdateRequest(session_id=sess.session_id, interface="DESKTOP", state=PresenceState.ACTIVE)
    await presence_tracker.update_presence(user_id="user_alice", request=req)

    # Simulate heartbeat stopped 120 seconds ago (>90s timeout)
    pres_model = (await db_session.execute(
        IdentityPresenceModel.__table__.select().where(IdentityPresenceModel.user_id == "user_alice")
    )).first()
    raw_model = await db_session.get(IdentityPresenceModel, pres_model.id)
    raw_model.last_seen_at = datetime.now(UTC) - timedelta(seconds=120)
    await db_session.commit()

    presences = await presence_tracker.get_presence(user_id="user_alice")
    assert len(presences) == 1
    assert presences[0].state == PresenceState.DISCONNECTED


@pytest.mark.asyncio
async def test_user_online_status_aggregation(db_session: AsyncSession):
    """Verify aggregated online state uses 'Kairo session active' (Spec 23)."""
    sess_mgr = SessionManager(db_session)
    presence_tracker = PresenceTracker(db_session)

    # When no session exists
    status_off = await presence_tracker.get_user_online_status("user_alice")
    assert status_off.status_text == "Offline"
    assert status_off.active_sessions_count == 0

    # With active session
    sess = await sess_mgr.create_session(user_id="user_alice", client_type=ClientType.WEB)
    await presence_tracker.update_presence(
        user_id="user_alice",
        request=PresenceUpdateRequest(session_id=sess.session_id, interface="WEB", state=PresenceState.ACTIVE),
    )

    status_on = await presence_tracker.get_user_online_status("user_alice")
    assert status_on.status_text == "Kairo session active"
    assert status_on.active_sessions_count == 1


@pytest.mark.asyncio
async def test_handoff_creation_and_completion(db_session: AsyncSession):
    """Verify cross-interface bounded context handoff (Spec 28-32, 149)."""
    sess_mgr = SessionManager(db_session)
    handoff_mgr = HandoffManager(db_session)

    # Web session (Source)
    web_sess = await sess_mgr.create_session(user_id="user_alice", client_type=ClientType.WEB)
    # Desktop session (Target)
    desktop_sess = await sess_mgr.create_session(user_id="user_alice", client_type=ClientType.DESKTOP)

    # Create handoff ticket
    create_req = HandoffCreateRequest(
        source_session_id=web_sess.session_id,
        conversation_id="conv_debug_123",
        task_id="tsk_ci_investigate",
        project_id="proj_kairo",
        explicit_consent=True,
    )
    resp = await handoff_mgr.create_handoff(user_id="user_alice", request=create_req)
    assert resp.handoff_id.startswith("ho_")
    assert resp.handoff_token.startswith("kairo_hnd_")

    # Complete handoff from desktop
    complete_req = HandoffCompleteRequest(
        handoff_token=resp.handoff_token,
        target_session_id=desktop_sess.session_id,
    )
    packet = await handoff_mgr.complete_handoff(
        user_id="user_alice", handoff_id=resp.handoff_id, request=complete_req
    )

    assert packet.handoff_id == resp.handoff_id
    assert packet.user_id == "user_alice"
    assert packet.target_session_id == desktop_sess.session_id
    assert packet.conversation_id == "conv_debug_123"
    assert packet.task_id == "tsk_ci_investigate"


@pytest.mark.asyncio
async def test_handoff_replay_attack_rejected(db_session: AsyncSession):
    """Verify handoff token cannot be reused a second time (Spec 85, 150)."""
    sess_mgr = SessionManager(db_session)
    handoff_mgr = HandoffManager(db_session)

    s1 = await sess_mgr.create_session(user_id="user_alice", client_type=ClientType.WEB)
    s2 = await sess_mgr.create_session(user_id="user_alice", client_type=ClientType.DESKTOP)

    resp = await handoff_mgr.create_handoff(
        user_id="user_alice",
        request=HandoffCreateRequest(source_session_id=s1.session_id, explicit_consent=True),
    )

    complete_req = HandoffCompleteRequest(handoff_token=resp.handoff_token, target_session_id=s2.session_id)

    # 1st attempt: success
    await handoff_mgr.complete_handoff(user_id="user_alice", handoff_id=resp.handoff_id, request=complete_req)

    # 2nd attempt: REPLAY REJECTED (Spec 150)
    with pytest.raises(SecurityPolicyViolationError) as exc:
        await handoff_mgr.complete_handoff(user_id="user_alice", handoff_id=resp.handoff_id, request=complete_req)
    assert IdentityErrorCode.HANDOFF_INVALID.value in str(exc.value)


@pytest.mark.asyncio
async def test_expired_handoff_rejected(db_session: AsyncSession):
    """Verify expired handoff token cannot be consumed (Spec 31, 85)."""
    sess_mgr = SessionManager(db_session)
    handoff_mgr = HandoffManager(db_session)

    s1 = await sess_mgr.create_session(user_id="user_alice", client_type=ClientType.WEB)
    s2 = await sess_mgr.create_session(user_id="user_alice", client_type=ClientType.DESKTOP)

    resp = await handoff_mgr.create_handoff(
        user_id="user_alice",
        request=HandoffCreateRequest(source_session_id=s1.session_id, explicit_consent=True),
    )

    # Simulate expired handoff
    record = await db_session.get(HandoffContextModel, resp.handoff_id)
    record.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    await db_session.commit()

    complete_req = HandoffCompleteRequest(handoff_token=resp.handoff_token, target_session_id=s2.session_id)
    with pytest.raises(SecurityPolicyViolationError) as exc:
        await handoff_mgr.complete_handoff(user_id="user_alice", handoff_id=resp.handoff_id, request=complete_req)
    assert IdentityErrorCode.HANDOFF_EXPIRED.value in str(exc.value)


@pytest.mark.asyncio
async def test_cross_user_handoff_attack_rejected(db_session: AsyncSession):
    """Verify User B cannot consume User A's handoff context (Spec 85, 147)."""
    sess_mgr = SessionManager(db_session)
    handoff_mgr = HandoffManager(db_session)

    s_alice = await sess_mgr.create_session(user_id="user_alice", client_type=ClientType.WEB)
    s_bob = await sess_mgr.create_session(user_id="user_bob", client_type=ClientType.DESKTOP)

    resp = await handoff_mgr.create_handoff(
        user_id="user_alice",
        request=HandoffCreateRequest(source_session_id=s_alice.session_id, explicit_consent=True),
    )

    complete_req = HandoffCompleteRequest(handoff_token=resp.handoff_token, target_session_id=s_bob.session_id)
    with pytest.raises(TenantIsolationError):
        await handoff_mgr.complete_handoff(user_id="user_bob", handoff_id=resp.handoff_id, request=complete_req)
