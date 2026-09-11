"""Resilience modeling, containment barrier analysis, counterfactual simulation, and recovery propagation (Task 75)."""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Any, Dict, List, Optional, Set

from app.propagation.schemas import (
    BoundaryType,
    ContainmentBoundary,
    ImpactDimensions,
    MitigationRecommendation,
    PropagationEdge,
    RedundancyState,
    RelationshipType,
    ResilienceAssessment,
    generate_uuid,
)
from app.propagation.snapshots import GraphSnapshot
from app.propagation.traversal import BoundedPropagationTraverser, TraversalResult

logger = logging.getLogger("kairo.propagation.resilience")


class ResilienceEngine:
    """Evaluates systemic resilience, identifies containment barriers, and performs counterfactual scenario analysis (Spec 16, 30-35)."""

    def __init__(self, traverser: Optional[BoundedPropagationTraverser] = None) -> None:
        self.traverser = traverser or BoundedPropagationTraverser()

    def assess_resilience(
        self,
        snapshot: GraphSnapshot,
        traversal_result: TraversalResult,
    ) -> ResilienceAssessment:
        """Compute multi-factor systemic resilience score and identify containment boundaries (Spec 16, 30)."""
        total_nodes = max(1, snapshot.node_count)
        total_edges = max(1, snapshot.edge_count)
        visited = traversal_result.visited_nodes

        # 1. Redundancy ratio: proportion of edges with FULL or PARTIAL redundancy
        redundant_edges = sum(
            1 for e in snapshot.get_edges()
            if e.redundancy_state in (RedundancyState.FULL, RedundancyState.PARTIAL)
        )
        redundancy_ratio = round(redundant_edges / total_edges, 3)

        # 2. Bottleneck concentration: fraction of visited nodes impacted
        visited_count = len(visited)
        bottleneck_concentration = round(min(1.0, visited_count / total_nodes), 3)

        # 3. Maximum dependency depth traversed
        max_depth = max((meta.get("depth", 0) for meta in visited.values()), default=0)

        # 4. Coupling density: average degree per node in snapshot
        coupling_density = round(min(1.0, (total_edges * 2) / (total_nodes * max(1, total_nodes - 1))), 3)

        # 5. Containment boundaries detection (Spec 30)
        boundaries: List[ContainmentBoundary] = []
        for edge in snapshot.get_edges():
            if edge.relationship_type == RelationshipType.SUPPRESSES:
                boundaries.append(
                    ContainmentBoundary(
                        entity_id=edge.target_entity,
                        boundary_type=BoundaryType.CIRCUIT_BREAKER,
                        effectiveness_estimate=edge.confidence,
                        is_active=True,
                        description=f"Suppressive damping relationship from {edge.source_entity} to {edge.target_entity}",
                    )
                )
            elif edge.relationship_type == RelationshipType.BLOCKS:
                boundaries.append(
                    ContainmentBoundary(
                        entity_id=edge.target_entity,
                        boundary_type=BoundaryType.WORKFLOW_GATE,
                        effectiveness_estimate=edge.confidence,
                        is_active=True,
                        description=f"Workflow barrier blocking propagation to {edge.target_entity}",
                    )
                )

        # 6. Composite resilience score: higher redundancy & lower blast radius -> higher resilience
        raw_resilience = (
            (1.0 - bottleneck_concentration) * 0.40
            + redundancy_ratio * 0.35
            + (1.0 - min(1.0, max_depth / 6.0)) * 0.15
            + (1.0 - coupling_density) * 0.10
        )
        resilience_score = round(max(0.05, min(0.95, raw_resilience)), 3)

        # Formulate interpretable findings
        findings: List[str] = []
        if redundancy_ratio > 0.5:
            findings.append(f"High redundancy coverage ({redundancy_ratio*100:.0f}%) dampens cascade propagation.")
        else:
            findings.append(f"Low redundancy coverage ({redundancy_ratio*100:.0f}%) increases single-point exposure.")

        if bottleneck_concentration > 0.4:
            findings.append(f"High blast radius: {visited_count} of {total_nodes} nodes reachable downstream.")
        else:
            findings.append(f"Contained blast radius: only {visited_count} of {total_nodes} nodes directly exposed.")

        if boundaries:
            findings.append(f"Detected {len(boundaries)} active containment boundaries stopping further cascade.")
        else:
            findings.append("No active circuit breakers or isolation boundaries detected along propagation path.")

        return ResilienceAssessment(
            systemic_resilience_score=resilience_score,
            redundancy_ratio=redundancy_ratio,
            bottleneck_concentration=bottleneck_concentration,
            max_dependency_depth=max_depth,
            coupling_density=coupling_density,
            containment_boundaries=boundaries,
            recovery_speed_estimate="FAST" if redundancy_ratio > 0.6 else "MODERATE" if redundancy_ratio > 0.2 else "SLOW",
            findings=findings,
        )

    def generate_mitigations(
        self,
        traversal_result: TraversalResult,
        resilience: ResilienceAssessment,
    ) -> List[MitigationRecommendation]:
        """Generate actionable, advisory-only mitigation recommendations (Spec 31, 71)."""
        mitigations: List[MitigationRecommendation] = []
        origin = traversal_result.origin_entity

        # Mitigation 1: Isolation of trigger component
        mitigations.append(
            MitigationRecommendation(
                action_type="ISOLATE_NODE",
                target_entity=origin,
                description=f"Isolate '{origin}' or enable circuit breaker to decouple downstream callers.",
                expected_risk_reduction=round(min(0.85, 0.5 + resilience.redundancy_ratio * 0.3), 2),
                estimated_effort="LOW",
                requires_approval=True,
                is_advisory_only=True,
            )
        )

        # Mitigation 2: Add redundancy for high-reach second-order targets
        for sec in traversal_result.second_order_effects[:3]:
            mitigations.append(
                MitigationRecommendation(
                    action_type="ADD_REDUNDANCY",
                    target_entity=sec.target_entity,
                    description=f"Provision standby replica or fallback route for second-order dependent '{sec.target_entity}'.",
                    expected_risk_reduction=0.45,
                    estimated_effort="MEDIUM",
                    requires_approval=True,
                    is_advisory_only=True,
                )
            )

        # Mitigation 3: Amplification dampening if cycles detected
        if traversal_result.cycles:
            mitigations.append(
                MitigationRecommendation(
                    action_type="DISABLE_AMPLIFICATION_LOOP",
                    target_entity=origin,
                    description="Implement exponential backoff or jitter to break retry storm / cyclic feedback amplification.",
                    expected_risk_reduction=0.75,
                    estimated_effort="LOW",
                    requires_approval=True,
                    is_advisory_only=True,
                )
            )

        return mitigations

    def simulate_counterfactual(
        self,
        origin_entity: str,
        snapshot: GraphSnapshot,
        intervention_type: str,
        target_entity: str,
    ) -> Dict[str, Any]:
        """Compare baseline propagation vs counterfactual scenario (Spec 32).
        
        CRITICAL INVARIANT: Simulation is NEVER represented as observed reality!
        """
        # Baseline propagation
        baseline_res = self.traverser.traverse(origin_entity, snapshot)

        # Create counterfactual graph copy
        cf_edges: List[PropagationEdge] = []
        for e in snapshot.get_edges():
            if intervention_type == "REMOVE_DEPENDENCY" and e.source_entity == target_entity:
                continue  # Sever outgoing link
            if intervention_type == "REMOVE_DEPENDENCY" and e.target_entity == target_entity:
                continue  # Sever incoming link
            if intervention_type == "ADD_REDUNDANCY" and e.target_entity == target_entity:
                # Upgrade edge to full redundancy
                upgraded_edge = PropagationEdge(
                    edge_id=e.edge_id,
                    source_entity=e.source_entity,
                    target_entity=e.target_entity,
                    relationship_type=e.relationship_type,
                    confidence=e.confidence,
                    redundancy_state=RedundancyState.FULL,
                    redundancy_alternatives=[f"{target_entity}_replica"],
                    temporal_delay=e.temporal_delay,
                )
                cf_edges.append(upgraded_edge)
            else:
                cf_edges.append(e)

        # Package modified counterfactual snapshot
        cf_snapshot = GraphSnapshot(
            snapshot_id=f"cf_{generate_uuid()[:8]}",
            tenant_id=snapshot.tenant_id,
            graph_version=snapshot.graph_version + 1,
            snapshot_timestamp=snapshot.snapshot_timestamp,
            entities=snapshot.get_entities(),
            edges=cf_edges,
            source_references=["counterfactual_simulation"],
        )

        cf_res = self.traverser.traverse(origin_entity, cf_snapshot)

        baseline_reach = len(baseline_res.visited_nodes)
        cf_reach = len(cf_res.visited_nodes)
        reach_delta = cf_reach - baseline_reach

        return {
            "intervention_type": intervention_type,
            "target_entity": target_entity,
            "baseline_nodes_affected": baseline_reach,
            "counterfactual_nodes_affected": cf_reach,
            "blast_radius_delta": reach_delta,
            "relative_risk_reduction": round(max(0.0, (baseline_reach - cf_reach) / max(1, baseline_reach)), 3),
            "epistemic_status": "SIMULATION_RESULT",  # Explicitly distinguished from reality!
        }

    def model_recovery_propagation(
        self,
        recovered_entity: str,
        snapshot: GraphSnapshot,
    ) -> Dict[str, Any]:
        """Model progressive recovery cascade when upstream component recovers (Spec 35)."""
        # Downstream nodes that recover following upstream stabilization
        downstream_recovery_order: List[Dict[str, Any]] = []
        visited: Set[str] = {recovered_entity}
        queue = [(recovered_entity, 0.0)]

        while queue:
            curr, delay = queue.pop(0)
            for edge in snapshot.get_outgoing_edges(curr):
                tgt = edge.target_entity
                if tgt not in visited:
                    visited.add(tgt)
                    step_delay = delay + edge.temporal_delay.expected_delay_seconds
                    downstream_recovery_order.append({
                        "entity": tgt,
                        "recovery_delay_seconds": step_delay,
                        "expected_state": "IMPROVED",
                    })
                    queue.append((tgt, step_delay))

        return {
            "origin_recovered": recovered_entity,
            "total_recovering_nodes": len(downstream_recovery_order),
            "recovery_order": downstream_recovery_order,
            "residual_impact_duration_seconds": max((r["recovery_delay_seconds"] for r in downstream_recovery_order), default=0.0),
        }


# Global default resilience engine
default_resilience_engine = ResilienceEngine()
