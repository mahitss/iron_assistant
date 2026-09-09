"""Tests for Hybrid Search, Graph Traversal, Timeline Reasoning, and Conflict Detection."""

import datetime

import pytest
from app.db.session import Base
from app.knowledge.graph import GraphTraversalService
from app.knowledge.models import KnowledgeNodeModel
from app.knowledge.schemas import (
    KnowledgeEdgeCreate,
    KnowledgeNodeCreate,
    KnowledgeRelationType,
    KnowledgeSearchRequest,
    KnowledgeType,
)
from app.knowledge.search import HybridSearchEngine
from app.knowledge.service import KnowledgeFabricService
from app.knowledge.temporal import TemporalReasoner
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
async def test_hybrid_search_scoring_and_fallback(async_db_session: AsyncSession):
    """Verify hybrid search with keyword, semantic similarity, recency decay, and fallback."""
    service = KnowledgeFabricService()
    user_id = "user_search"

    # Create test nodes
    n1 = await service.create_node(
        async_db_session,
        user_id=user_id,
        node_in=KnowledgeNodeCreate(
            type=KnowledgeType.DECISION,
            source_id="dec_db_arch",
            title="Database Architecture Decision",
            summary="Adopt PostgreSQL with pgvector for unified long-term memory and context embeddings.",
        ),
    )
    n2 = await service.create_node(
        async_db_session,
        user_id=user_id,
        node_in=KnowledgeNodeCreate(
            type=KnowledgeType.WORKFLOW_RUN,
            source_id="run_ci_44",
            title="CI Build Run 44",
            summary="Docker container build failed on lint check.",
        ),
    )

    # 1. Search for database architecture
    req1 = KnowledgeSearchRequest(query="PostgreSQL pgvector architecture", limit=5)
    results1 = await service.search(async_db_session, user_id=user_id, request=req1)
    assert len(results1) >= 1
    assert results1[0].id == n1.id
    assert results1[0].relevance > 0.5

    # 2. Search for CI failure
    req2 = KnowledgeSearchRequest(query="CI build failed docker", limit=5)
    results2 = await service.search(async_db_session, user_id=user_id, request=req2)
    assert len(results2) >= 1
    assert results2[0].id == n2.id

    # 3. Verify fallback when embedding provider raises an exception
    class FailingEmbeddingProvider:
        async def embed(self, text: str):
            raise RuntimeError("Simulated embedding service outage")

    fallback_engine = HybridSearchEngine(embedding_provider=FailingEmbeddingProvider())
    fallback_results = await fallback_engine.search(async_db_session, user_id=user_id, request=req1)
    # Should not raise an error, falls back to lexical search
    assert len(fallback_results) >= 1
    assert fallback_results[0].id == n1.id


@pytest.mark.asyncio
async def test_bounded_graph_traversal_and_cycles(async_db_session: AsyncSession):
    """Verify bounded graph traversal, depth limiting, and cycle prevention."""
    service = KnowledgeFabricService()
    traversal_svc = GraphTraversalService(max_depth=3, max_nodes=10, max_edges=10)
    user_id = "user_graph"

    # Create connected chain: Node A -> Node B -> Node C -> Node A (Cycle)
    na = await service.create_node(
        async_db_session,
        user_id=user_id,
        node_in=KnowledgeNodeCreate(
            type=KnowledgeType.PROJECT, source_id="p_a", title="Project A", summary="Root project"
        ),
    )
    nb = await service.create_node(
        async_db_session,
        user_id=user_id,
        node_in=KnowledgeNodeCreate(
            type=KnowledgeType.REPOSITORY, source_id="r_b", title="Repo B", summary="Code repository"
        ),
    )
    nc = await service.create_node(
        async_db_session,
        user_id=user_id,
        node_in=KnowledgeNodeCreate(
            type=KnowledgeType.COMMIT, source_id="c_c", title="Commit C", summary="Release commit"
        ),
    )

    # Edges: A -> B -> C -> A
    await service.create_edge(
        async_db_session,
        user_id=user_id,
        edge_in=KnowledgeEdgeCreate(
            source_node_id=na.id, target_node_id=nb.id, relation_type=KnowledgeRelationType.REFERENCES
        ),
    )
    await service.create_edge(
        async_db_session,
        user_id=user_id,
        edge_in=KnowledgeEdgeCreate(
            source_node_id=nb.id, target_node_id=nc.id, relation_type=KnowledgeRelationType.REFERENCES
        ),
    )
    await service.create_edge(
        async_db_session,
        user_id=user_id,
        edge_in=KnowledgeEdgeCreate(
            source_node_id=nc.id, target_node_id=na.id, relation_type=KnowledgeRelationType.REFERENCES
        ),
    )

    # Traverse starting from Node A
    graph = await traversal_svc.traverse_subgraph(
        async_db_session, user_id=user_id, root_node_id=na.id, depth_limit=2
    )
    assert graph.root_node_id == na.id
    assert len(graph.nodes) >= 2
    assert graph.depth_reached <= 2
    # Ensure cycle did not cause infinite loop
    assert len(graph.nodes) <= 3


@pytest.mark.asyncio
async def test_timeline_and_conflict_detection(async_db_session: AsyncSession):
    """Verify timeline ordering, causality evidence check, and conflict detection."""
    service = KnowledgeFabricService()
    reasoner = TemporalReasoner()
    user_id = "user_temporal"

    now = datetime.datetime.now(datetime.timezone.utc)
    t1 = now - datetime.timedelta(hours=2)
    t2 = now - datetime.timedelta(hours=1)

    # Create timestamped nodes with conflicting claims
    n1 = await service.create_node(
        async_db_session,
        user_id=user_id,
        node_in=KnowledgeNodeCreate(
            type=KnowledgeType.MEMORY,
            source_id="m_1",
            title="Python Version Requirement",
            summary="Kairo requires Python 3.11 for core runtime.",
        ),
    )
    n2 = await service.create_node(
        async_db_session,
        user_id=user_id,
        node_in=KnowledgeNodeCreate(
            type=KnowledgeType.REPOSITORY,
            source_id="r_1",
            title="Runtime Specification",
            summary="Project configuration updated to Python 3.12.",
        ),
    )

    # 1. Timeline fetch
    tl = await reasoner.get_timeline(async_db_session, user_id=user_id)
    assert tl.total_events == 2
    assert tl.events[0].node_id in (n1.id, n2.id)

    # 2. Conflict Detection
    conflicts = await reasoner.detect_conflicts(async_db_session, user_id=user_id)
    assert len(conflicts) >= 1
    assert conflicts[0]["entity"] == "python"
    assert "3.11" in conflicts[0]["differing_values"]
    assert "3.12" in conflicts[0]["differing_values"]

    # 3. Causality Verification
    commit_node = KnowledgeNodeModel(
        user_id=user_id,
        type=KnowledgeType.COMMIT.value,
        source_id="commit_abc12345",
        title="Commit abc12345",
        summary="Add new feature",
        created_at=t1,
    )
    ci_node_with_evidence = KnowledgeNodeModel(
        user_id=user_id,
        type=KnowledgeType.WORKFLOW_RUN.value,
        source_id="ci_run_99",
        title="CI Run 99 Failed",
        summary="Job failed on commit abc12345 due to lint error.",
        created_at=t2,
    )
    ci_node_no_evidence = KnowledgeNodeModel(
        user_id=user_id,
        type=KnowledgeType.WORKFLOW_RUN.value,
        source_id="ci_run_100",
        title="CI Run 100 Failed",
        summary="Network timeout communicating with docker daemon.",
        created_at=t2,
    )

    has_ev, conf, exp = reasoner.verify_causality_evidence(commit_node, ci_node_with_evidence)
    assert has_ev is True
    assert conf > 0.9

    has_ev2, _, _ = reasoner.verify_causality_evidence(commit_node, ci_node_no_evidence)
    assert has_ev2 is False
