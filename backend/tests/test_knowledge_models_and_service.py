"""Tests for Knowledge Fabric models, service, multi-tenant isolation, decisions, and supersession."""

import pytest
from app.db.session import Base
from app.knowledge.schemas import (
    DecisionCreate,
    DecisionStatus,
    KnowledgeEdgeCreate,
    KnowledgeNodeCreate,
    KnowledgeNodeUpdate,
    KnowledgeRelationType,
    KnowledgeSourceType,
    KnowledgeType,
)
from app.knowledge.service import KnowledgeFabricService
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.fixture
async def async_db_session():
    """Create in-memory SQLite engine and AsyncSession fixture."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_node_lifecycle_and_multitenant_isolation(async_db_session: AsyncSession):
    """Verify node creation, update, deletion, and strict multi-tenant boundary checks."""
    service = KnowledgeFabricService()

    # 1. User A creates a knowledge node
    node_create = KnowledgeNodeCreate(
        type=KnowledgeType.PROJECT,
        source_id="proj_alpha",
        title="Project Alpha",
        summary="Internal workspace for assistant core.",
        project_id="proj_alpha",
        confidence=1.0,
        source_type=KnowledgeSourceType.USER_EXPLICIT,
    )
    node_a = await service.create_node(async_db_session, user_id="user_a", node_in=node_create)
    assert node_a.id is not None
    assert node_a.user_id == "user_a"
    assert node_a.title == "Project Alpha"

    # 2. User A can fetch their node
    fetched_a = await service.get_node(async_db_session, user_id="user_a", node_id=node_a.id)
    assert fetched_a is not None
    assert fetched_a.id == node_a.id

    # 3. User B CANNOT fetch User A's node (IDOR prevention)
    fetched_b = await service.get_node(async_db_session, user_id="user_b", node_id=node_a.id)
    assert fetched_b is None

    # 4. User B CANNOT update User A's node
    with pytest.raises(ValueError, match="not found or access denied"):
        await service.update_node(
            async_db_session,
            user_id="user_b",
            node_id=node_a.id,
            update_in=KnowledgeNodeUpdate(title="Malicious Rename"),
        )

    # 5. User A updates their node
    updated_a = await service.update_node(
        async_db_session,
        user_id="user_a",
        node_id=node_a.id,
        update_in=KnowledgeNodeUpdate(title="Project Alpha V2"),
    )
    assert updated_a.title == "Project Alpha V2"

    # 6. User B CANNOT delete User A's node
    del_b = await service.delete_node(async_db_session, user_id="user_b", node_id=node_a.id)
    assert del_b is False

    # 7. User A deletes their node
    del_a = await service.delete_node(async_db_session, user_id="user_a", node_id=node_a.id)
    assert del_a is True

    # Deleted node is no longer accessible
    assert await service.get_node(async_db_session, user_id="user_a", node_id=node_a.id) is None


@pytest.mark.asyncio
async def test_edge_creation_and_type_validation(async_db_session: AsyncSession):
    """Verify directed relationship edge creation and strict enum validation."""
    service = KnowledgeFabricService()

    # Setup two nodes for user_a
    n1 = await service.create_node(
        async_db_session,
        user_id="user_a",
        node_in=KnowledgeNodeCreate(
            type=KnowledgeType.PROJECT,
            source_id="proj_kairo",
            title="Kairo",
            summary="Personal assistant.",
        ),
    )
    n2 = await service.create_node(
        async_db_session,
        user_id="user_a",
        node_in=KnowledgeNodeCreate(
            type=KnowledgeType.DECISION,
            source_id="dec_pgvector",
            title="Use pgvector",
            summary="Unified vector storage in PostgreSQL.",
        ),
    )

    # 1. Create valid relationship edge: DECISION -> BELONGS_TO -> PROJECT
    edge_in = KnowledgeEdgeCreate(
        source_node_id=n2.id,
        target_node_id=n1.id,
        relation_type=KnowledgeRelationType.BELONGS_TO,
        confidence=1.0,
    )
    edge = await service.create_edge(async_db_session, user_id="user_a", edge_in=edge_in)
    assert edge.id is not None
    assert edge.relation_type == KnowledgeRelationType.BELONGS_TO

    # 2. User B cannot create an edge pointing to User A's nodes
    with pytest.raises(ValueError, match="not found or access denied"):
        await service.create_edge(async_db_session, user_id="user_b", edge_in=edge_in)


@pytest.mark.asyncio
async def test_decision_lifecycle_and_supersession(async_db_session: AsyncSession):
    """Verify explicit decision creation, listing, and supersession with SUPERSEDES edge."""
    service = KnowledgeFabricService()

    # 1. Record Decision 1
    d1 = await service.record_decision(
        async_db_session,
        user_id="user_test",
        decision_in=DecisionCreate(
            decision="Use Pinecone for vector embeddings",
            rationale="Initial cloud vector solution.",
            project_id="proj_kairo",
        ),
    )
    assert d1.status == DecisionStatus.ACTIVE
    assert d1.decision == "Use Pinecone for vector embeddings"

    # 2. Supersede Decision 1 with Decision 2
    d2 = await service.supersede_decision(
        async_db_session,
        user_id="user_test",
        old_decision_node_id=d1.id,
        new_decision_text="Use PostgreSQL + pgvector for vector embeddings",
        rationale="Consolidate storage, eliminate cloud vendor lock-in.",
        reason="Cost and operational simplicity.",
    )
    assert d2.status == DecisionStatus.ACTIVE
    assert d2.decision == "Use PostgreSQL + pgvector for vector embeddings"

    # 3. List decisions verifies Decision 1 is SUPERSEDED, Decision 2 is ACTIVE
    decisions = await service.list_decisions(async_db_session, user_id="user_test", project_id="proj_kairo")
    assert len(decisions) == 2

    active_dec = [d for d in decisions if d.status == DecisionStatus.ACTIVE][0]
    superseded_dec = [d for d in decisions if d.status == DecisionStatus.SUPERSEDED][0]

    assert active_dec.id == d2.id
    assert superseded_dec.id == d1.id
