"""Unit tests for temporal memory, validity windows, as-of point-in-time queries, and temporal diffs."""

from datetime import UTC, datetime, timedelta

from app.knowledge_graph.edges import EdgeManager
from app.knowledge_graph.nodes import NodeManager
from app.knowledge_graph.schemas import (
    NodeType,
    RelationshipType,
    ScopeType,
    TemporalState,
)
from app.knowledge_graph.temporal import TemporalMemoryEngine


def test_temporal_validity_window_and_as_of_query():
    nm = NodeManager()
    em = EdgeManager(nm)
    temporal_engine = TemporalMemoryEngine(nm, em)

    now = datetime.now(UTC)
    last_month = now - timedelta(days=30)
    two_months_ago = now - timedelta(days=60)

    proj = nm.create_node(
        canonical_name="KairoApp",
        node_type=NodeType.PROJECT,
        created_at=two_months_ago,
    )
    fw_x = nm.create_node(
        canonical_name="FrameworkX",
        node_type=NodeType.APPLICATION,
        created_at=two_months_ago,
    )
    fw_y = nm.create_node(
        canonical_name="FrameworkY",
        node_type=NodeType.APPLICATION,
        created_at=last_month,
    )

    # Invariant 22: Framework X was used until last month, Framework Y used since last month
    # Framework X edge: valid from 2 months ago until last month
    edge_x = em.create_edge(
        source_node_id=proj.node_id,
        relationship=RelationshipType.USES,
        target_node_id=fw_x.node_id,
        valid_from=two_months_ago,
        valid_until=last_month,
        confidence=1.0,
    )

    # Framework Y edge: valid from last month until indefinite (now)
    edge_y = em.create_edge(
        source_node_id=proj.node_id,
        relationship=RelationshipType.USES,
        target_node_id=fw_y.node_id,
        valid_from=last_month,
        valid_until=None,
        confidence=1.0,
    )

    # Query as-of 45 days ago (between 60 days ago and 30 days ago)
    mid_point = now - timedelta(days=45)
    as_of_state = temporal_engine.query_as_of(mid_point, node_id=proj.node_id)
    edge_targets = [e["target_node_id"] for e in as_of_state["edges"]]
    assert fw_x.node_id in edge_targets
    assert fw_y.node_id not in edge_targets

    # Query as-of now
    now_state = temporal_engine.query_as_of(now, node_id=proj.node_id)
    now_edge_targets = [e["target_node_id"] for e in now_state["edges"]]
    assert fw_y.node_id in now_edge_targets
    assert fw_x.node_id not in now_edge_targets

    # Temporal state labels (Invariant 167: CURRENT vs HISTORICAL vs INFERRED)
    assert temporal_engine.determine_temporal_state(edge_x, now=now) == TemporalState.HISTORICAL
    assert temporal_engine.determine_temporal_state(edge_y, now=now) == TemporalState.CURRENT


def test_temporal_diff_query():
    nm = NodeManager()
    em = EdgeManager(nm)
    temporal_engine = TemporalMemoryEngine(nm, em)

    now = datetime.now(UTC)
    t0 = now - timedelta(days=20)
    t1 = now - timedelta(days=10)

    p = nm.create_node("AlphaProj", NodeType.PROJECT)
    t_task = nm.create_node("DeployTask", NodeType.TASK)

    edge = em.create_edge(
        source_node_id=p.node_id,
        relationship=RelationshipType.DEPENDS_ON,
        target_node_id=t_task.node_id,
        project_id="proj_alpha",
        valid_from=t1,
        valid_until=None,
    )

    diff = temporal_engine.compute_temporal_diff(
        project_id="proj_alpha",
        start_time=t0,
        end_time=now,
    )

    assert len(diff["added_relationships"]) == 1
    assert diff["added_relationships"][0]["edge_id"] == edge.edge_id
