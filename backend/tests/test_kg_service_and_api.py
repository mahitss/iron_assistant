"""Unit tests for KnowledgeGraphService end-to-end orchestration and FastAPI router endpoints."""

from fastapi.testclient import TestClient
import pytest

from app.knowledge_graph.router import get_kg_service, router
from app.knowledge_graph.schemas import (
    NodeType,
    PreferenceCategory,
    RelationshipType,
    ScopeType,
)
from app.knowledge_graph.service import KnowledgeGraphService
from app.main import app

client = TestClient(app)


def test_service_end_to_end_orchestration():
    svc = KnowledgeGraphService()

    # 1. Create entities
    p = svc.create_entity("PhoenixProject", NodeType.PROJECT, aliases=["phoenix-app"], user_id="u1")
    repo = svc.create_entity("phoenix-repo", NodeType.REPOSITORY, user_id="u1")

    # 2. Connect with relationship edge
    edge = svc.link_entities(
        source_node_id=p.node_id,
        relationship=RelationshipType.OWNS,
        target_node_id=repo.node_id,
        user_id="u1",
    )
    assert edge.relationship == RelationshipType.OWNS

    # 3. Record assertion
    a = svc.record_assertion(
        subject="PhoenixProject",
        predicate="LANGUAGE",
        object_val="Python",
        source={"source": "direct_user_statement", "source_type": "USER"},
        confidence=1.0,
        user_id="u1",
    )
    assert a.object == "Python"

    # 4. Record decision
    d = svc.record_decision(
        question="Which API framework?",
        decision="FastAPI",
        alternatives=["Flask", "Django"],
        rationale_reference="High async performance and OpenAPI typing",
        owner="lead_dev",
        user_id="u1",
    )
    assert d.decision == "FastAPI"

    # 5. Set and resolve preference
    svc.set_preference(
        category=PreferenceCategory.FORMATTING,
        value={"indent": 4, "line_length": 100},
        user_id="u1",
    )
    pref = svc.resolve_preference(category=PreferenceCategory.FORMATTING, user_id="u1")
    assert pref["value"]["indent"] == 4

    # 6. Traverse graph
    trav = svc.traverse(start_node_id=p.node_id, max_depth=1, user_id="u1")
    assert trav.total_nodes_visited == 2

    # 7. Summarize
    summary = svc.summarize(p.node_id)
    assert summary is not None
    assert summary.canonical_name == "PhoenixProject"

    # 8. Forget entity
    forget_res = svc.forget_entity(repo.node_id, user_id="u1")
    assert forget_res["action"] == "FORGET_ENTITY"
    assert svc.get_entity(repo.node_id) is None


def test_api_endpoints_health_and_operations():
    # 1. Health check
    res = client.get("/api/v1/knowledge-graph/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "USER" in data["supported_node_types"]
    assert "OWNS" in data["supported_relationship_types"]

    # 2. Create node via POST /nodes
    node_res = client.post(
        "/api/v1/knowledge-graph/nodes",
        json={
            "canonical_name": "API_Gateway",
            "node_type": "SERVICE",
            "aliases": ["kong", "envoy"],
            "scope": "PROJECT",
            "confidence": 1.0,
            "user_id": "api_user_test",
        },
    )
    assert node_res.status_code == 200
    node_data = node_res.json()
    node_id = node_data["node_id"]

    # 3. Create target node and edge
    target_res = client.post(
        "/api/v1/knowledge-graph/nodes",
        json={
            "canonical_name": "Auth_Service",
            "node_type": "SERVICE",
            "aliases": [],
            "scope": "PROJECT",
            "confidence": 1.0,
            "user_id": "api_user_test",
        },
    )
    target_id = target_res.json()["node_id"]

    edge_res = client.post(
        "/api/v1/knowledge-graph/edges",
        json={
            "source_node_id": node_id,
            "relationship": "DEPENDS_ON",
            "target_node_id": target_id,
            "user_id": "api_user_test",
        },
    )
    assert edge_res.status_code == 200

    # 4. Traverse
    trav_res = client.post(
        "/api/v1/knowledge-graph/traverse",
        json={
            "start_node_id": node_id,
            "max_depth": 2,
            "user_id": "api_user_test",
        },
    )
    assert trav_res.status_code == 200
    assert len(trav_res.json()["nodes"]) == 2

    # 5. Record decision
    dec_res = client.post(
        "/api/v1/knowledge-graph/decisions",
        json={
            "question": "Which rate limiter?",
            "decision": "TokenBucket",
            "alternatives": ["LeakyBucket"],
            "rationale_reference": "RFC 6585 compliance",
            "owner": "lead",
            "user_id": "api_user_test",
        },
    )
    assert dec_res.status_code == 200

    # 6. Forget entity
    forget_res = client.post(
        "/api/v1/knowledge-graph/forget",
        json={
            "node_id": target_id,
            "user_id": "api_user_test",
            "reason": "cleanup",
        },
    )
    assert forget_res.status_code == 200
