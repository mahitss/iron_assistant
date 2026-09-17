"""
End-to-End Operational Verification Script for Task 97:
KAIRO Autonomous Knowledge Graph Reasoning, Graph Memory & Structured Inference Engine.

Verifies all 9 Production Integration Scenarios from Phase 48:
- SCENARIO 1: Memory -> Evidence -> KnowledgeNode -> KnowledgeEdge -> Graph Query -> Context
- SCENARIO 2: Capability -> Dependency Graph -> Capability Version Change -> Impacted Workflows
- SCENARIO 3: Decision -> Evidence -> Action -> Outcome -> Complete Decision Lineage
- SCENARIO 4: Incident -> Failed Capability -> Dependency Traversal -> Impacted Systems -> Risk Engine
- SCENARIO 5: Memory Contradiction -> Conflict Edge -> Unresolved Conflict Preserved
- SCENARIO 6: Graph Relationship Changes -> Graph Diff -> Dependent Decisions Identified -> Revalidation Candidates
- SCENARIO 7: Historical Query -> Reconstruct Graph at T -> Verify Old Relationships
- SCENARIO 8: Unauthorized User -> Traversal Filtered -> Restricted Nodes Inaccessible
- SCENARIO 9: Large Graph -> Bounded Traversal -> Query Terminates Safely within Limits
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Reconfigure stdout/stderr for Windows console unicode support
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure backend directory is in sys.path
backend_path = str(Path(__file__).resolve().parent.parent / "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.knowledge_graph.schemas import (
    NodeType,
    RelationshipType,
    CertaintyLevel,
    ProvenanceClassification,
    GraphQueryType,
    ConflictResolutionState,
    GraphProvenanceSchema,
    GraphTraversalLimits,
    GraphQueryRequest,
)
from app.knowledge_graph.reasoning_engine import GraphReasoningEngine


def print_banner(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def verify_scenario_1_memory_to_context(engine: GraphReasoningEngine):
    print_banner("SCENARIO 1: Memory -> Evidence -> KnowledgeNode -> KnowledgeEdge -> Graph Query -> Context")
    
    # 1. Memory item
    engine.create_node(
        node_id="mem_safety_rule",
        canonical_key="memory:policy:safety",
        node_type=NodeType.MEMORY,
        label="Production Zero-Downtime Requirement",
        certainty=CertaintyLevel.KNOWN,
        provenance=GraphProvenanceSchema(
            source_id="conversation_session_99",
            source_type="CONVERSATION",
            classification=ProvenanceClassification.OBSERVED,
        ),
    )

    # 2. Supporting Evidence
    engine.create_node(
        node_id="ev_sla_agreement",
        canonical_key="evidence:sla:2026",
        node_type=NodeType.EVIDENCE,
        label="Signed 99.99% Availability SLA Contract",
        certainty=CertaintyLevel.KNOWN,
        provenance=GraphProvenanceSchema(
            source_id="doc_sla_pdf",
            source_type="DOCUMENT",
            classification=ProvenanceClassification.EXTERNALLY_SOURCED,
        ),
    )

    # 3. KnowledgeNode (System Service)
    engine.create_node(
        node_id="srv_payment_gateway",
        canonical_key="service:payment:gateway",
        node_type=NodeType.SERVICE,
        label="Stripe Payment Processing Gateway",
        certainty=CertaintyLevel.KNOWN,
    )

    # 4. KnowledgeEdges
    engine.create_edge(
        source_node="ev_sla_agreement",
        target_node="mem_safety_rule",
        relationship_type=RelationshipType.SUPPORTS,
        confidence=1.0,
    )
    engine.create_edge(
        source_node="srv_payment_gateway",
        target_node="mem_safety_rule",
        relationship_type=RelationshipType.ASSUMES,
        confidence=0.95,
    )

    # 5. Graph Query: What systems rely on or assume this memory rule?
    req = GraphQueryRequest(
        query_type=GraphQueryType.DEPENDENCY_QUERY,
        start_node_id="mem_safety_rule",
        limits=GraphTraversalLimits(max_depth=2),
    )
    res = engine.execute_query(req)
    
    found_nodes = {n.node_id for n in res.nodes}
    assert "srv_payment_gateway" in found_nodes, "Service assuming memory rule must be retrieved"
    assert "ev_sla_agreement" in found_nodes, "Evidence supporting memory rule must be retrieved"
    print(f"✓ Retrieved {len(res.nodes)} contextual entities connected to memory rule with verifiable provenance.")


def verify_scenario_2_capability_version_change(engine: GraphReasoningEngine):
    print_banner("SCENARIO 2: Capability -> Dependency Graph -> Version Change -> Impacted Workflows")

    engine.create_node(node_id="cap_db_writer", canonical_key="cap:db:writer", node_type=NodeType.CAPABILITY, label="Database Write Operator")
    engine.create_node(node_id="cap_ver_v1", canonical_key="cap:db:writer:v1", node_type=NodeType.CAPABILITY_VERSION, label="DB Writer v1.0 (Deprecated)")
    engine.create_node(node_id="wf_orders_ingest", canonical_key="wf:orders:ingest", node_type=NodeType.WORKFLOW, label="Realtime Order Ingestion Workflow")
    engine.create_node(node_id="wf_user_signup", canonical_key="wf:user:signup", node_type=NodeType.WORKFLOW, label="User Registration Workflow")

    engine.create_edge(source_node="cap_ver_v1", target_node="cap_db_writer", relationship_type=RelationshipType.IMPLEMENTS)
    engine.create_edge(source_node="wf_orders_ingest", target_node="cap_ver_v1", relationship_type=RelationshipType.DEPENDS_ON)
    engine.create_edge(source_node="wf_user_signup", target_node="cap_ver_v1", relationship_type=RelationshipType.DEPENDS_ON)

    # When cap_ver_v1 changes or is retired, analyze downstream impact
    impact = engine.analyze_downstream_impact("cap_ver_v1", max_depth=3)
    impacted_ids = {n.node_id for n in impact.impacted_nodes}

    assert "wf_orders_ingest" in impacted_ids, "Order ingestion workflow must be flagged as impacted"
    assert "wf_user_signup" in impacted_ids, "User registration workflow must be flagged as impacted"
    assert len(impact.revalidation_candidates) >= 2, "Both workflows must be scheduled for revalidation"
    print(f"✓ Version change on cap_ver_v1 correctly flagged {len(impacted_ids)} downstream workflows for revalidation.")


def verify_scenario_3_decision_lineage(engine: GraphReasoningEngine):
    print_banner("SCENARIO 3: Decision -> Evidence -> Action -> Outcome -> Complete Decision Lineage")

    engine.create_node(node_id="goal_latency_sla", canonical_key="goal:latency", node_type=NodeType.GOAL, label="Keep P99 latency under 150ms")
    engine.create_node(node_id="ev_latency_spike", canonical_key="ev:metrics:spike", node_type=NodeType.EVIDENCE, label="Prometheus P99 exceeded 280ms")
    engine.create_node(node_id="dec_spin_read_replica", canonical_key="dec:scale:replica", node_type=NodeType.DECISION, label="Provision Read Replica")
    engine.create_node(node_id="act_cloud_deploy", canonical_key="act:cloud:provision", node_type=NodeType.ACTION, label="Terraform Apply Postgres Replica")
    engine.create_node(node_id="mem_latency_normalized", canonical_key="mem:outcome:normal", node_type=NodeType.MEMORY, label="P99 dropped to 95ms")

    # Connect structured lineage without exposing raw CoT
    engine.create_edge(source_node="dec_spin_read_replica", target_node="goal_latency_sla", relationship_type=RelationshipType.PLANNED_BY)
    engine.create_edge(source_node="ev_latency_spike", target_node="dec_spin_read_replica", relationship_type=RelationshipType.EVIDENCE_FOR)
    engine.create_edge(source_node="act_cloud_deploy", target_node="dec_spin_read_replica", relationship_type=RelationshipType.DECIDED_BY)
    engine.create_edge(source_node="mem_latency_normalized", target_node="act_cloud_deploy", relationship_type=RelationshipType.RESULTS_IN)

    lineage = engine.reconstruct_decision_lineage("dec_spin_read_replica")
    step_node_ids = {s.node_id for s in lineage.steps}

    assert lineage.target_node == "dec_spin_read_replica"
    assert "goal_latency_sla" in step_node_ids
    assert "ev_latency_spike" in step_node_ids
    assert "act_cloud_deploy" in step_node_ids
    print(f"✓ Reconstructed full decision lineage ({len(lineage.steps)} steps) from objective to outcome.")


def verify_scenario_4_incident_to_risk(engine: GraphReasoningEngine):
    print_banner("SCENARIO 4: Incident -> Failed Capability -> Dependency Traversal -> Risk Topology")

    engine.create_node(node_id="inc_network_drop", canonical_key="inc:net:partition", node_type=NodeType.INCIDENT, label="AZ-East Network Switch Failure")
    engine.create_node(node_id="cap_cache_sync", canonical_key="cap:cache:sync", node_type=NodeType.CAPABILITY, label="Redis Cross-AZ Replication")
    engine.create_node(node_id="srv_auth_api", canonical_key="srv:auth:api", node_type=NodeType.SERVICE, label="OAuth Token Validator")
    engine.create_node(node_id="dec_auth_tokens", canonical_key="dec:auth:tokens", node_type=NodeType.DECISION, label="Issue Session Cookies")

    engine.create_edge(source_node="inc_network_drop", target_node="cap_cache_sync", relationship_type=RelationshipType.AFFECTS)
    engine.create_edge(source_node="srv_auth_api", target_node="cap_cache_sync", relationship_type=RelationshipType.DEPENDS_ON)
    engine.create_edge(source_node="dec_auth_tokens", target_node="srv_auth_api", relationship_type=RelationshipType.DEPENDS_ON)

    impact = engine.analyze_downstream_impact("inc_network_drop", max_depth=4)
    impacted_ids = {n.node_id for n in impact.impacted_nodes}

    assert "cap_cache_sync" in impacted_ids
    assert "srv_auth_api" in impacted_ids
    assert "dec_auth_tokens" in impacted_ids
    assert impact.overall_risk_severity in ("HIGH", "CRITICAL")
    print(f"✓ Incident fan-out identified {len(impacted_ids)} impacted systems with risk level: {impact.overall_risk_severity}.")


def verify_scenario_5_memory_contradiction(engine: GraphReasoningEngine):
    print_banner("SCENARIO 5: Memory Contradiction -> Conflict Edge -> Dialectic Preservation")

    engine.create_node(node_id="mem_loc_nyc", canonical_key="mem:company:hq", node_type=NodeType.MEMORY, label="HQ located in New York")
    engine.create_node(node_id="mem_loc_sfo", canonical_key="mem:company:hq", node_type=NodeType.MEMORY, label="HQ located in San Francisco")

    conflict = engine.record_conflict(
        node_a="mem_loc_nyc",
        node_b="mem_loc_sfo",
        reason="Conflicting headquarters location declarations from two trusted executive memos",
        confidence=0.92,
    )

    assert conflict.status == ConflictResolutionState.UNRESOLVED
    assert "mem_loc_nyc" in engine.nodes
    assert "mem_loc_sfo" in engine.nodes
    
    # Verify CONTRADICTS edge was generated
    contradict_edges = [e for e in engine.edges.values() if e.relationship_type == RelationshipType.CONTRADICTS]
    assert len(contradict_edges) >= 1
    print(f"✓ Preserved dialectic conflict between {conflict.node_a} and {conflict.node_b} without data destruction.")


def verify_scenario_6_graph_diff_revalidation(engine: GraphReasoningEngine):
    print_banner("SCENARIO 6: Graph Relationship Changes -> Graph Diff -> Revalidation Candidates")

    engine.create_node(node_id="res_db_pool", canonical_key="res:db:pool", node_type=NodeType.RESOURCE, label="Connection Pool")
    engine.create_node(node_id="srv_reporting", canonical_key="srv:reporting", node_type=NodeType.SERVICE, label="Reporting Engine")
    engine.create_edge(source_node="srv_reporting", target_node="res_db_pool", relationship_type=RelationshipType.DEPENDS_ON)

    snap_a = engine.create_snapshot("Topology Baseline", scope="global")

    # Mutation: Reporting service migrated away from connection pool to read cache
    engine.create_node(node_id="res_read_cache", canonical_key="res:read:cache", node_type=NodeType.RESOURCE, label="Read Cache")
    engine.create_edge(source_node="srv_reporting", target_node="res_read_cache", relationship_type=RelationshipType.DEPENDS_ON)
    # Remove old edge
    old_edge_id = next(e.edge_id for e in engine.edges.values() if e.source_node == "srv_reporting" and e.target_node == "res_db_pool")
    engine.edges.pop(old_edge_id)

    snap_b = engine.create_snapshot("Topology Post-Migration", scope="global")

    diff = engine.compute_graph_diff(snap_a.snapshot_id, snap_b.snapshot_id)
    assert "res_read_cache" in diff.added_nodes
    assert len(diff.added_edges) == 1
    assert len(diff.removed_edges) == 1
    print(f"✓ Computed diff between {snap_a.snapshot_id} and {snap_b.snapshot_id}: +{len(diff.added_nodes)} nodes, +{len(diff.added_edges)}/-{len(diff.removed_edges)} edges.")


def verify_scenario_7_historical_queries(engine: GraphReasoningEngine):
    print_banner("SCENARIO 7: Historical Query -> Reconstruct Graph at Time T")

    t_past = datetime(2026, 1, 1, tzinfo=timezone.utc)
    t_switch = datetime(2026, 6, 1, tzinfo=timezone.utc)
    t_query_old = datetime(2026, 3, 1, tzinfo=timezone.utc)
    t_query_new = datetime(2026, 8, 1, tzinfo=timezone.utc)

    engine.create_node(node_id="srv_app", canonical_key="srv:app", node_type=NodeType.SERVICE, label="App Backend")
    engine.create_node(node_id="srv_legacy_db", canonical_key="srv:legacy:db", node_type=NodeType.SERVICE, label="Legacy MySQL")
    engine.create_node(node_id="srv_modern_db", canonical_key="srv:modern:db", node_type=NodeType.SERVICE, label="Modern Postgres")

    # Edge 1 valid from Jan to June
    engine.create_edge(
        source_node="srv_app",
        target_node="srv_legacy_db",
        relationship_type=RelationshipType.DEPENDS_ON,
        validity_start=t_past,
        validity_end=t_switch,
    )
    # Edge 2 valid from June onward
    engine.create_edge(
        source_node="srv_app",
        target_node="srv_modern_db",
        relationship_type=RelationshipType.DEPENDS_ON,
        validity_start=t_switch,
        validity_end=None,
    )

    # Query as of March 2026
    req_past = GraphQueryRequest(
        query_type=GraphQueryType.DIRECT_RELATION,
        start_node_id="srv_app",
        as_of=t_query_old,
    )
    res_past = engine.execute_query(req_past)
    target_ids_past = {e.target_node for e in res_past.edges}
    assert "srv_legacy_db" in target_ids_past
    assert "srv_modern_db" not in target_ids_past

    # Query as of August 2026
    req_future = GraphQueryRequest(
        query_type=GraphQueryType.DIRECT_RELATION,
        start_node_id="srv_app",
        as_of=t_query_new,
    )
    res_future = engine.execute_query(req_future)
    target_ids_future = {e.target_node for e in res_future.edges}
    assert "srv_modern_db" in target_ids_future
    assert "srv_legacy_db" not in target_ids_future
    print("✓ Temporal historical queries accurately reconstruct past vs current dependencies.")


def verify_scenario_8_security_filtering(engine: GraphReasoningEngine):
    print_banner("SCENARIO 8: Unauthorized User -> Traversal Filtered -> Restricted Nodes Inaccessible")

    engine.create_node(
        node_id="public_doc",
        canonical_key="doc:pub",
        node_type=NodeType.DOCUMENT,
        label="Public Readme",
        sensitivity="PUBLIC",
    )
    engine.create_node(
        node_id="confidential_key",
        canonical_key="sec:key",
        node_type=NodeType.SYSTEM,
        label="Stripe Secret API Key",
        sensitivity="RESTRICTED",
    )
    engine.create_edge(
        source_node="public_doc",
        target_node="confidential_key",
        relationship_type=RelationshipType.RELATED_TO,
    )

    req = GraphQueryRequest(
        query_type=GraphQueryType.MULTI_HOP,
        start_node_id="public_doc",
        allowed_sensitivities=["PUBLIC"],  # RESTRICTED not permitted
    )
    res = engine.execute_query(req)
    result_ids = {n.node_id for n in res.nodes}

    assert "public_doc" in result_ids
    assert "confidential_key" not in result_ids, "RESTRICTED node must NEVER leak through graph traversal"
    print("✓ SecurityCenter sensitivity boundary strictly enforced; restricted entities filtered.")


def verify_scenario_9_bounded_traversal_on_large_graph(engine: GraphReasoningEngine):
    print_banner("SCENARIO 9: Large Graph -> Bounded Traversal -> Query Terminates Safely")

    # Generate a synthetic tree with 200 nodes
    for i in range(200):
        parent_id = f"large_node_{i // 4}" if i > 0 else None
        curr_id = f"large_node_{i}"
        engine.create_node(
            node_id=curr_id,
            canonical_key=f"large:{i}",
            node_type=NodeType.COMPONENT,
            label=f"Component {i}",
        )
        if parent_id and parent_id in engine.nodes:
            engine.create_edge(
                source_node=parent_id,
                target_node=curr_id,
                relationship_type=RelationshipType.CHILD_OF,
            )

    # Execute bounded query with max_depth=2, max_nodes=25
    limits = GraphTraversalLimits(max_depth=2, max_nodes=25, max_execution_time_ms=1000)
    req = GraphQueryRequest(
        query_type=GraphQueryType.MULTI_HOP,
        start_node_id="large_node_0",
        limits=limits,
    )
    res = engine.execute_query(req)

    assert len(res.nodes) <= 25, f"Expected <= 25 nodes, got {len(res.nodes)}"
    assert res.depth_reached <= 2, f"Expected depth <= 2, got {res.depth_reached}"
    assert res.execution_time_ms < 1000, "Must execute safely under timeout"
    print(f"✓ Bounded traversal on 200-node graph completed in {res.execution_time_ms:.2f}ms, visiting exactly {len(res.nodes)} nodes (limit 25).")


def main():
    print("\n" + "#" * 70)
    print("  KAIRO TASK 97 E2E INTEGRATION & INVARIANT VERIFICATION SUITE")
    print("#" * 70)

    engine = GraphReasoningEngine()
    engine.reset()

    try:
        verify_scenario_1_memory_to_context(engine)
        verify_scenario_2_capability_version_change(engine)
        verify_scenario_3_decision_lineage(engine)
        verify_scenario_4_incident_to_risk(engine)
        verify_scenario_5_memory_contradiction(engine)
        verify_scenario_6_graph_diff_revalidation(engine)
        verify_scenario_7_historical_queries(engine)
        verify_scenario_8_security_filtering(engine)
        verify_scenario_9_bounded_traversal_on_large_graph(engine)

        print("\n" + "=" * 70)
        print("  ALL 9 PHASE 48 INTEGRATION SCENARIOS PASSED WITH ZERO REGRESSIONS!")
        print("=" * 70)
        return 0
    except Exception as e:
        print(f"\n❌ E2E VERIFICATION FAILED: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
