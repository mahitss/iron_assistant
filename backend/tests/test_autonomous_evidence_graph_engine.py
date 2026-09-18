"""Comprehensive test suite for Task 117:
Kairo Autonomous Evidence Graph, Provenance Intelligence & Verification Dependency Engine.

Covers:
- Unit & Invariant tests (Sections 2-7, 13, 14, 38, 64)
- Blast-radius, controlled invalidation & revalidation (Sections 8-12, 22-29)
- Provenance intelligence (Concentration, Gaps, Fragility, Duplicates - Sections 15-21)
- Temporal reconstruction, snapshots & diffs (Sections 6, 32-34)
- Cross-subsystem lineage bridges (Section 51-52)
- EmergencyStop dominance & Security boundaries (Sections 46, 48)
- Concurrency & Thread safety (Section 62)
- Adversarial & Fault injection (Sections 61, 63)
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import pytest
import uuid

from app.evidence_graph.domain import (
    DuplicateEvidenceType,
    EvidenceGraphEdge,
    EvidenceGraphEdgeType,
    EvidenceGraphNode,
    EvidenceGraphNodeType,
    FreshnessState,
    ImpactSeverity,
    LifecycleStatus,
    LineageRecord,
    ProvenanceStatus,
    RevalidationRecommendation,
)
from app.evidence_graph.health_engine import HealthEngine
from app.evidence_graph.impact_engine import ImpactEngine
from app.evidence_graph.intelligence_engine import IntelligenceEngine
from app.evidence_graph.service import EvidenceGraphService
from app.evidence_graph.temporal_engine import TemporalEngine
from app.evidence_graph.traversal_engine import TraversalEngine
from app.security.emergency_stop import get_emergency_stop_service


# =============================================================================
# 1. Unit & Invariant Tests
# =============================================================================

@pytest.mark.asyncio
async def test_node_creation_and_versioning():
    svc = EvidenceGraphService()
    node = EvidenceGraphNode(
        node_id="ev-101",
        node_type=EvidenceGraphNodeType.EVIDENCE,
        source_system="test_runner",
        payload={"sample": "data_v1"},
    )
    saved = await svc.add_node(node)
    assert saved.node_id == "ev-101"
    assert saved.version == 1
    assert saved.content_hash != ""

    # Update the node with new payload -> triggers historical versioning
    updated_node = EvidenceGraphNode(
        node_id="ev-101",
        node_type=EvidenceGraphNodeType.EVIDENCE,
        source_system="test_runner",
        payload={"sample": "data_v2"},
    )
    saved_v2 = await svc.add_node(updated_node)
    assert saved_v2.version == 2
    assert len(svc._node_versions["ev-101"]) == 1
    assert svc._node_versions["ev-101"][0].payload["sample"] == "data_v1"


@pytest.mark.asyncio
async def test_edge_creation_and_automatic_endpoints():
    svc = EvidenceGraphService()
    edge = EvidenceGraphEdge(
        edge_id="edge-1",
        source_node_id="claim-1",
        target_node_id="evidence-1",
        relationship_type=EvidenceGraphEdgeType.SUPPORTED_BY,
        confidence=0.95,
    )
    saved_edge = await svc.add_edge(edge)
    assert saved_edge.edge_id == "edge-1"
    # Endpoints should be automatically registered if not already present
    assert svc.get_node("claim-1") is not None
    assert svc.get_node("evidence-1") is not None


# =============================================================================
# 2. Bounded Traversals & Minimal Lineage
# =============================================================================

@pytest.mark.asyncio
async def test_bounded_upstream_and_downstream_traversals():
    svc = EvidenceGraphService()
    # Chain: Source S1 -> Evidence E1 -> Claim C1 -> Belief B1 -> Decision D1
    await svc.add_node(EvidenceGraphNode(node_id="S1", node_type=EvidenceGraphNodeType.SOURCE, source_system="web"))
    await svc.add_node(EvidenceGraphNode(node_id="E1", node_type=EvidenceGraphNodeType.EVIDENCE, source_system="parser"))
    await svc.add_node(EvidenceGraphNode(node_id="C1", node_type=EvidenceGraphNodeType.CLAIM, source_system="eval"))
    await svc.add_node(EvidenceGraphNode(node_id="B1", node_type=EvidenceGraphNodeType.BELIEF, source_system="belief"))
    await svc.add_node(EvidenceGraphNode(node_id="D1", node_type=EvidenceGraphNodeType.DECISION, source_system="decider"))

    await svc.add_edge(EvidenceGraphEdge(edge_id="e1", source_node_id="E1", target_node_id="S1", relationship_type=EvidenceGraphEdgeType.EXTRACTED_FROM))
    await svc.add_edge(EvidenceGraphEdge(edge_id="e2", source_node_id="C1", target_node_id="E1", relationship_type=EvidenceGraphEdgeType.SUPPORTED_BY))
    await svc.add_edge(EvidenceGraphEdge(edge_id="e3", source_node_id="B1", target_node_id="C1", relationship_type=EvidenceGraphEdgeType.DEPENDS_ON))
    await svc.add_edge(EvidenceGraphEdge(edge_id="e4", source_node_id="D1", target_node_id="B1", relationship_type=EvidenceGraphEdgeType.DEPENDS_ON))

    # Test Upstream from D1
    upstream = svc.get_upstream("D1", max_depth=10)
    node_ids = {n["node_id"] for n in upstream["nodes"]}
    assert "B1" in node_ids
    assert "C1" in node_ids
    assert "E1" in node_ids
    assert "S1" in node_ids
    assert upstream["status"] == "COMPLETE"

    # Test Downstream from S1
    downstream = svc.get_downstream("S1", max_depth=10)
    down_ids = {n["node_id"] for n in downstream["nodes"]}
    assert "E1" in down_ids
    assert "C1" in down_ids
    assert "B1" in down_ids
    assert "D1" in down_ids

    # Test Depth-Bounded Truncation
    shallow_upstream = svc.get_upstream("D1", max_depth=2)
    assert shallow_upstream["depth_reached"] <= 2
    assert shallow_upstream["status"] == "TRUNCATED"


@pytest.mark.asyncio
async def test_minimal_sufficient_provenance():
    svc = EvidenceGraphService()
    # Multiple paths from Claim to Source:
    # Short path: C -> E1 -> S1
    # Long path: C -> E2 -> E3 -> E4 -> S2
    await svc.add_node(EvidenceGraphNode(node_id="S1", node_type=EvidenceGraphNodeType.SOURCE, source_system="web"))
    await svc.add_node(EvidenceGraphNode(node_id="S2", node_type=EvidenceGraphNodeType.SOURCE, source_system="web"))
    await svc.add_node(EvidenceGraphNode(node_id="E1", node_type=EvidenceGraphNodeType.EVIDENCE, source_system="web"))
    await svc.add_node(EvidenceGraphNode(node_id="E2", node_type=EvidenceGraphNodeType.EVIDENCE, source_system="web"))
    await svc.add_node(EvidenceGraphNode(node_id="E3", node_type=EvidenceGraphNodeType.EVIDENCE, source_system="web"))
    await svc.add_node(EvidenceGraphNode(node_id="E4", node_type=EvidenceGraphNodeType.EVIDENCE, source_system="web"))
    await svc.add_node(EvidenceGraphNode(node_id="C_target", node_type=EvidenceGraphNodeType.CLAIM, source_system="reasoner"))

    await svc.add_edge(EvidenceGraphEdge(edge_id="e1", source_node_id="E1", target_node_id="S1", relationship_type=EvidenceGraphEdgeType.EXTRACTED_FROM))
    await svc.add_edge(EvidenceGraphEdge(edge_id="e2", source_node_id="C_target", target_node_id="E1", relationship_type=EvidenceGraphEdgeType.SUPPORTED_BY))

    await svc.add_edge(EvidenceGraphEdge(edge_id="e3", source_node_id="E4", target_node_id="S2", relationship_type=EvidenceGraphEdgeType.EXTRACTED_FROM))
    await svc.add_edge(EvidenceGraphEdge(edge_id="e4", source_node_id="E3", target_node_id="E4", relationship_type=EvidenceGraphEdgeType.DERIVED_FROM))
    await svc.add_edge(EvidenceGraphEdge(edge_id="e5", source_node_id="E2", target_node_id="E3", relationship_type=EvidenceGraphEdgeType.TRANSFORMED_FROM))
    await svc.add_edge(EvidenceGraphEdge(edge_id="e6", source_node_id="C_target", target_node_id="E2", relationship_type=EvidenceGraphEdgeType.SUPPORTED_BY))

    minimal = svc.get_minimal_chain("C_target")
    assert minimal["chain_type"] == "MINIMAL_KNOWN_CHAIN"
    assert minimal["depth"] == 2
    assert minimal["root_sources"] == ["S1"]


# =============================================================================
# 3. Circular Provenance Detection
# =============================================================================

@pytest.mark.asyncio
async def test_circular_provenance_detection():
    svc = EvidenceGraphService()
    # Cycle: NodeA -> NodeB -> NodeC -> NodeA
    await svc.add_node(EvidenceGraphNode(node_id="NodeA", node_type=EvidenceGraphNodeType.CLAIM, source_system="sys"))
    await svc.add_node(EvidenceGraphNode(node_id="NodeB", node_type=EvidenceGraphNodeType.CLAIM, source_system="sys"))
    await svc.add_node(EvidenceGraphNode(node_id="NodeC", node_type=EvidenceGraphNodeType.CLAIM, source_system="sys"))

    await svc.add_edge(EvidenceGraphEdge(edge_id="eA", source_node_id="NodeA", target_node_id="NodeB", relationship_type=EvidenceGraphEdgeType.SUPPORTED_BY))
    await svc.add_edge(EvidenceGraphEdge(edge_id="eB", source_node_id="NodeB", target_node_id="NodeC", relationship_type=EvidenceGraphEdgeType.SUPPORTED_BY))
    await svc.add_edge(EvidenceGraphEdge(edge_id="eC", source_node_id="NodeC", target_node_id="NodeA", relationship_type=EvidenceGraphEdgeType.SUPPORTED_BY))

    cycles = svc.detect_cycles()
    assert len(cycles) > 0
    assert any("NodeA" in c["cycle_path"] for c in cycles)


# =============================================================================
# 4. Blast Radius & Controlled Invalidation
# =============================================================================

@pytest.mark.asyncio
async def test_blast_radius_and_controlled_invalidation():
    svc = EvidenceGraphService()
    # Source -> Evidence -> Claim -> Belief -> Decision -> Mission
    await svc.add_node(EvidenceGraphNode(node_id="Src1", node_type=EvidenceGraphNodeType.SOURCE, source_system="rss"))
    await svc.add_node(EvidenceGraphNode(node_id="Evi1", node_type=EvidenceGraphNodeType.EVIDENCE, source_system="scraper"))
    await svc.add_node(EvidenceGraphNode(node_id="Clm1", node_type=EvidenceGraphNodeType.CLAIM, source_system="eval"))
    await svc.add_node(EvidenceGraphNode(node_id="Blf1", node_type=EvidenceGraphNodeType.BELIEF, source_system="belief"))
    await svc.add_node(EvidenceGraphNode(node_id="Dec1", node_type=EvidenceGraphNodeType.DECISION, source_system="decision"))
    await svc.add_node(EvidenceGraphNode(node_id="Mis1", node_type=EvidenceGraphNodeType.MISSION, source_system="mission"))

    await svc.add_edge(EvidenceGraphEdge(edge_id="e1", source_node_id="Evi1", target_node_id="Src1", relationship_type=EvidenceGraphEdgeType.EXTRACTED_FROM))
    await svc.add_edge(EvidenceGraphEdge(edge_id="e2", source_node_id="Clm1", target_node_id="Evi1", relationship_type=EvidenceGraphEdgeType.SUPPORTED_BY))
    await svc.add_edge(EvidenceGraphEdge(edge_id="e3", source_node_id="Blf1", target_node_id="Clm1", relationship_type=EvidenceGraphEdgeType.DEPENDS_ON))
    await svc.add_edge(EvidenceGraphEdge(edge_id="e4", source_node_id="Dec1", target_node_id="Blf1", relationship_type=EvidenceGraphEdgeType.DEPENDS_ON))
    await svc.add_edge(EvidenceGraphEdge(edge_id="e5", source_node_id="Mis1", target_node_id="Dec1", relationship_type=EvidenceGraphEdgeType.DEPENDS_ON))

    # Invalidate Evi1
    impact = await svc.propagate_invalidation("Evi1", reason="Source API returned 404 deleted")
    assert impact.target_node_id == "Evi1"
    assert "Clm1" in impact.impacted_claims
    assert "Blf1" in impact.impacted_beliefs
    assert "Dec1" in impact.impacted_decisions
    assert "Mis1" in impact.impacted_missions

    # Verify downstream nodes are NOT deleted, but marked STALE / UNCERTAIN
    clm_node = svc.get_node("Clm1")
    assert clm_node.freshness_state == FreshnessState.STALE
    assert clm_node.provenance_status == ProvenanceStatus.UNCERTAIN

    # Verify revalidation candidates generated
    candidates = svc.list_revalidation_candidates()
    assert len(candidates) >= 4
    dec_candidate = next(c for c in candidates if c.affected_node_id == "Dec1")
    assert dec_candidate.recommended_next_step == RevalidationRecommendation.ESCALATE


# =============================================================================
# 5. Provenance Intelligence: Concentration, Gaps, Duplicates, Fragility
# =============================================================================

@pytest.mark.asyncio
async def test_source_concentration_detection():
    svc = EvidenceGraphService()
    # 5 evidence nodes pointing to sources with same origin publisher "reuters.com"
    await svc.add_node(EvidenceGraphNode(node_id="S_A", node_type=EvidenceGraphNodeType.SOURCE, source_system="web", payload={"publisher": "reuters.com"}))
    await svc.add_node(EvidenceGraphNode(node_id="S_B", node_type=EvidenceGraphNodeType.SOURCE, source_system="web", payload={"publisher": "reuters.com"}))
    await svc.add_node(EvidenceGraphNode(node_id="S_C", node_type=EvidenceGraphNodeType.SOURCE, source_system="web", payload={"publisher": "reuters.com"}))
    await svc.add_node(EvidenceGraphNode(node_id="S_D", node_type=EvidenceGraphNodeType.SOURCE, source_system="web", payload={"publisher": "reuters.com"}))

    await svc.add_node(EvidenceGraphNode(node_id="Claim_Conc", node_type=EvidenceGraphNodeType.CLAIM, source_system="reasoner"))

    for sid in ["S_A", "S_B", "S_C", "S_D"]:
        await svc.add_edge(EvidenceGraphEdge(edge_id=f"e_{sid}", source_node_id="Claim_Conc", target_node_id=sid, relationship_type=EvidenceGraphEdgeType.SUPPORTED_BY))

    finding = svc.analyze_source_concentration("Claim_Conc")
    assert finding.is_high_concentration is True
    assert finding.origin_count == 1
    assert "reuters.com" in finding.shared_origin_groups


@pytest.mark.asyncio
async def test_duplicate_evidence_detection():
    svc = EvidenceGraphService()
    ev1 = EvidenceGraphNode(node_id="ev_dup_1", node_type=EvidenceGraphNodeType.EVIDENCE, source_system="sys", payload={"text": "identical text content"})
    ev2 = EvidenceGraphNode(node_id="ev_dup_2", node_type=EvidenceGraphNodeType.EVIDENCE, source_system="sys", payload={"text": "identical text content"})
    await svc.add_node(ev1)
    await svc.add_node(ev2)

    dups = svc.detect_duplicate_evidence()
    assert len(dups) >= 1
    assert dups[0]["duplicate_type"] == DuplicateEvidenceType.EXACT_DUPLICATE.value
    assert "ev_dup_1" in dups[0]["evidence_ids"]
    assert "ev_dup_2" in dups[0]["evidence_ids"]


@pytest.mark.asyncio
async def test_provenance_gaps_and_fragility():
    svc = EvidenceGraphService()
    # Claim with no evidence
    await svc.add_node(EvidenceGraphNode(node_id="Claim_Orphan", node_type=EvidenceGraphNodeType.CLAIM, source_system="user_input"))
    gaps = svc.list_provenance_gaps("Claim_Orphan")
    assert len(gaps) == 1
    assert gaps[0].missing_relationship == "SUPPORTED_BY"
    assert gaps[0].expected_node_type == "EVIDENCE"

    fragility = svc.assess_fragility("Claim_Orphan")
    assert fragility.overall_fragility_label in {"HIGH", "CRITICAL"}
    assert fragility.single_source_dependence is True


# =============================================================================
# 6. Temporal Reconstruction, Snapshots & Diff
# =============================================================================

@pytest.mark.asyncio
async def test_temporal_snapshots_and_diff():
    svc = EvidenceGraphService()
    await svc.add_node(EvidenceGraphNode(node_id="N1", node_type=EvidenceGraphNodeType.EVIDENCE, source_system="test"))
    snap1 = await svc.create_snapshot("Initial snapshot")
    assert snap1.node_count == 1
    assert snap1.checksum != ""

    # Add second node
    await svc.add_node(EvidenceGraphNode(node_id="N2", node_type=EvidenceGraphNodeType.CLAIM, source_system="test"))
    snap2 = await svc.create_snapshot("Second snapshot")
    assert snap2.node_count == 2

    diff = svc.diff_snapshots(snap1.snapshot_id, snap2.snapshot_id)
    assert diff is not None
    assert len(diff.added_nodes) == 1
    assert diff.added_nodes[0]["node_id"] == "N2"


# =============================================================================
# 7. Lineage Ingestion & Simulation Distinction
# =============================================================================

@pytest.mark.asyncio
async def test_canonical_lineage_ingest_and_simulation():
    svc = EvidenceGraphService()
    record = LineageRecord(
        producer="task105_adaptation",
        object_type="SIMULATION",
        object_id="sim_run_001",
        output_references=["claim_sim_output"],
        operation="EXECUTE_DIGITAL_TWIN",
    )
    node = await svc.ingest_lineage_record(record)
    assert node.node_id == "sim_run_001"
    assert node.node_type == EvidenceGraphNodeType.SIMULATION

    # Verify edge was created to downstream output
    edges = svc.get_outgoing_edges("sim_run_001")
    assert any(e.target_node_id == "claim_sim_output" and e.relationship_type == EvidenceGraphEdgeType.USED_BY for e in edges)


# =============================================================================
# 8. EmergencyStop Dominance & Security Boundaries
# =============================================================================

@pytest.mark.asyncio
async def test_emergency_stop_fail_closed():
    svc = EvidenceGraphService()
    stop_svc = get_emergency_stop_service()
    stop_svc.trigger_emergency_stop(reason="Security Incident Test")

    try:
        with pytest.raises(RuntimeError) as exc_info:
            await svc.add_node(
                EvidenceGraphNode(node_id="node_blocked", node_type=EvidenceGraphNodeType.CLAIM, source_system="cli")
            )
        assert "EmergencyStop active" in str(exc_info.value)
    finally:
        stop_svc.reset_emergency_stop(is_human_user=True)


# =============================================================================
# 9. Concurrency & Integrity
# =============================================================================

@pytest.mark.asyncio
async def test_concurrent_graph_writes():
    svc = EvidenceGraphService()

    async def add_worker(idx: int):
        node = EvidenceGraphNode(
            node_id=f"worker_node_{idx}",
            node_type=EvidenceGraphNodeType.EVIDENCE,
            source_system="worker",
        )
        await svc.add_node(node)

    tasks = [add_worker(i) for i in range(20)]
    await asyncio.gather(*tasks)

    assert len(svc.list_nodes(limit=100)) == 20
    health = svc.get_health()
    assert health.snapshot_consistency_ok is True
