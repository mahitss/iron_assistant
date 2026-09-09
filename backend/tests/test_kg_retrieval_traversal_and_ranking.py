"""Unit tests for bounded graph traversal, structural queries, path discovery, ranking, and profile summarization."""

from datetime import UTC, datetime, timedelta

from app.knowledge_graph.edges import EdgeManager
from app.knowledge_graph.graph import KnowledgeGraph
from app.knowledge_graph.nodes import NodeManager
from app.knowledge_graph.ranking import GraphRanker
from app.knowledge_graph.retrieval import GraphRetrievalEngine
from app.knowledge_graph.schemas import (
    KnowledgeNodeSchema,
    NodeType,
    RelationshipType,
)
from app.knowledge_graph.summarization import GraphSummarizer


def test_bounded_graph_traversal_and_cycle_handling():
    nm = NodeManager()
    em = EdgeManager(nm)
    kg = KnowledgeGraph(nm, em)

    # Create cycle: NodeA -> NodeB -> NodeC -> NodeA
    na = nm.create_node("ServiceA", NodeType.SERVICE)
    nb = nm.create_node("ServiceB", NodeType.SERVICE)
    nc = nm.create_node("ServiceC", NodeType.SERVICE)

    em.create_edge(na.node_id, RelationshipType.DEPENDS_ON, nb.node_id)
    em.create_edge(nb.node_id, RelationshipType.DEPENDS_ON, nc.node_id)
    em.create_edge(nc.node_id, RelationshipType.DEPENDS_ON, na.node_id)

    # Invariant 88, 89, 176: Traversal with depth=2 does not loop infinitely on cycle
    result = kg.traverse(start_node_id=na.node_id, max_depth=2, max_nodes=50)
    visited_names = [n.canonical_name for n in result.nodes]
    assert "ServiceA" in visited_names
    assert "ServiceB" in visited_names
    assert "ServiceC" in visited_names
    assert result.total_nodes_visited <= 3


def test_structural_and_path_queries():
    nm = NodeManager()
    em = EdgeManager(nm)
    kg = KnowledgeGraph(nm, em)
    retrieval = GraphRetrievalEngine(kg)

    dep = nm.create_node("DeploymentProduction", NodeType.DEPLOYMENT)
    t1 = nm.create_node("MigrateDatabaseTask", NodeType.TASK)
    t2 = nm.create_node("NotifyTeamTask", NodeType.TASK)

    # Invariant 170: Tasks depend on DeploymentProduction
    em.create_edge(t1.node_id, RelationshipType.DEPENDS_ON, dep.node_id)
    em.create_edge(t2.node_id, RelationshipType.DEPENDS_ON, dep.node_id)

    # Query tasks depending on deployment (incoming edges with DEPENDS_ON)
    dependent_tasks = retrieval.query_structural(
        node_id=dep.node_id,
        relationship=RelationshipType.DEPENDS_ON,
        direction="incoming",
    )
    task_names = [t.canonical_name for t in dependent_tasks]
    assert "MigrateDatabaseTask" in task_names
    assert "NotifyTeamTask" in task_names

    # Invariant 173 & 174: Path queries
    path_result = retrieval.query_path(t1.node_id, dep.node_id, max_depth=2)
    assert path_result is not None
    assert len(path_result.edges) == 1
    assert path_result.edges[0].relationship == RelationshipType.DEPENDS_ON


def test_ranking_without_popularity_bias():
    now = datetime.now(UTC)
    old_time = now - timedelta(days=20)

    # Node 1: High connectivity, but unrelated to task context and older
    n1 = KnowledgeNodeSchema(
        node_id="n1",
        node_type=NodeType.SERVICE,
        canonical_name="GlobalLogDrain",
        aliases=["drain"],
        scope="GLOBAL",
        created_at=old_time,
        updated_at=old_time,
        confidence=0.9,
        status="ACTIVE",
    )

    # Node 2: Less connected, but relevant to task context ("payment checkout") and recent
    n2 = KnowledgeNodeSchema(
        node_id="n2",
        node_type=NodeType.SERVICE,
        canonical_name="CheckoutPaymentGateway",
        aliases=["payment-api"],
        scope="PROJECT",
        project_id="proj_pay",
        created_at=now,
        updated_at=now,
        confidence=1.0,
        status="ACTIVE",
    )

    # Invariant 198: Node 2 outranks Node 1 despite Node 1 having hypothetical high degree
    ranked = GraphRanker.rank_nodes(
        candidates=[n1, n2],
        active_task_context="payment checkout gateway integration",
        now=now,
    )
    assert ranked[0].canonical_name == "CheckoutPaymentGateway"


def test_profile_summarization():
    nm = NodeManager()
    em = EdgeManager(nm)
    kg = KnowledgeGraph(nm, em)
    summarizer = GraphSummarizer(kg)

    proj = nm.create_node("KairoAI", NodeType.PROJECT)
    repo = nm.create_node("kairo-repo", NodeType.REPOSITORY)
    em.create_edge(proj.node_id, RelationshipType.OWNS, repo.node_id)

    profile = summarizer.summarize_entity(proj.node_id)
    assert profile is not None
    assert profile.canonical_name == "KairoAI"
    assert profile.node_type == NodeType.PROJECT
    assert len(profile.key_relationships) == 1
    assert profile.key_relationships[0]["relationship"] == RelationshipType.OWNS.value
