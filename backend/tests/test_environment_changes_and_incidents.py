"""Unit tests for Environmental Change Detection, Causal Verification, and Incidents (Task 54)."""

from datetime import datetime, timezone

from app.environment.changes import ChangeDetector
from app.environment.edges import create_environment_edge
from app.environment.incidents import IncidentManager
from app.environment.nodes import create_environment_node
from app.environment.schemas import (
    ChangeSignificance,
    ChangeType,
    IncidentStatus,
    NodeType,
    RelationshipType,
    ScopeType,
)
from app.environment.topology import TopologyGraph


def test_change_detection_and_significance():
    """Prompt #59, #62: Detect change types and assign significance."""
    fail_change = ChangeDetector.create_change_record(
        resource_id="svc_orders",
        change_type=ChangeType.FAILED,
        before={"status": "ONLINE"},
        after={"status": "OFFLINE"},
        source="k8s_events",
    )
    assert fail_change.change_type == ChangeType.FAILED
    assert fail_change.significance == ChangeSignificance.HIGH

    scaled_change = ChangeDetector.create_change_record(
        resource_id="svc_orders",
        change_type=ChangeType.SCALED,
        before={"replicas": 3},
        after={"replicas": 5},
        source="k8s_events",
    )
    assert scaled_change.change_type == ChangeType.SCALED
    assert scaled_change.significance == ChangeSignificance.LOW


def test_causality_requires_evidence():
    """Prompt #64, #65: Temporal sequence is not causality. Require evidence for causal claims."""
    change = ChangeDetector.create_change_record(
        resource_id="svc_auth",
        change_type=ChangeType.REDEPLOYED,
        before={"version": "1.0"},
        after={"version": "1.1"},
        source="deployer",
    )

    incident_time = datetime.now(timezone.utc)

    # 1. Without trace or direct verification, causal claim is rejected
    assert not ChangeDetector.validate_causal_claim(
        candidate_change=change,
        incident_id="inc_01",
        incident_time=incident_time,
        causal_evidence={},
    )

    # 2. With trace ID linking exception stack to the redeployed version, causal claim is accepted
    assert ChangeDetector.validate_causal_claim(
        candidate_change=change,
        incident_id="inc_01",
        incident_time=incident_time,
        causal_evidence={"trace_id": "tr_crash_404", "stack_trace": "NullPointerException at AuthFilter.java:42"},
    )


def test_incident_creation_and_root_cause_demotion():
    """Prompt #99, #100: Root cause requires verified evidence; otherwise suspected cause."""
    # Attempting to assign root cause without verified evidence demotes to suspected cause
    inc = IncidentManager.create_incident(
        scope=ScopeType.SYSTEM,
        symptoms=["API 504 Gateway Timeout", "Worker queue backlog"],
        affected_resources=["svc_api", "q_tasks"],
        evidence={"root_cause_verified": False},
        root_cause="Redis memory exhaustion",
    )

    assert inc.status == IncidentStatus.DETECTED
    assert inc.root_cause is None
    assert inc.suspected_cause == "Redis memory exhaustion"

    # With verified evidence, root cause is preserved
    inc_verified = IncidentManager.create_incident(
        scope=ScopeType.SYSTEM,
        symptoms=["DB connection pool exhausted"],
        affected_resources=["svc_orders", "db_main"],
        evidence={"root_cause_verified": True, "log_ref": "db_max_connections_reached"},
        root_cause="PostgreSQL max_connections exceeded",
    )
    assert inc_verified.root_cause == "PostgreSQL max_connections exceeded"


def test_incident_blast_radius_estimation():
    """Prompt #103, #104: Estimate affected resources and capture uncertainty when graph is truncated."""
    db = create_environment_node("db_shared", NodeType.DATABASE, "db:shared", "Shared DB")
    s1 = create_environment_node("svc_a", NodeType.SERVICE, "s:a", "Service A")
    s2 = create_environment_node("svc_b", NodeType.SERVICE, "s:b", "Service B")

    e1 = create_environment_edge("svc_a", RelationshipType.DEPENDS_ON, "db_shared", provenance={"source": "trace"})
    e2 = create_environment_edge("svc_b", RelationshipType.DEPENDS_ON, "db_shared", provenance={"source": "trace"})

    topology = TopologyGraph(
        nodes={"db_shared": db, "svc_a": s1, "svc_b": s2},
        edges={e1.edge_id: e1, e2.edge_id: e2},
    )

    blast = IncidentManager.estimate_blast_radius(origin_node_id="db_shared", topology=topology)
    assert blast["origin_node_id"] == "db_shared"
    assert blast["estimated_affected_count"] == 2
    assert "svc_a" in blast["affected_resources"]
    assert "svc_b" in blast["affected_resources"]
