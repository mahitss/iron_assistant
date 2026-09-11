"""Bottleneck and Single Point of Failure (SPoF) topological analysis (Task 75)."""

from __future__ import annotations

from collections import deque
import logging
from typing import Any, Dict, List, Optional, Set

from app.propagation.schemas import (
    BottleneckNode,
    CriticalityLevel,
    RedundancyState,
    ReversibilityLevel,
    SinglePointOfFailure,
    SubstitutabilityLevel,
)
from app.propagation.snapshots import GraphSnapshot

logger = logging.getLogger("kairo.propagation.bottlenecks")


class BottleneckAnalyzer:
    """Analyzes system topologies to detect bottlenecks and classify Single Points of Failure (Spec 13-15)."""

    def analyze(
        self,
        snapshot: GraphSnapshot,
        critical_path_entities: Optional[Set[str]] = None,
        resource_contention_map: Optional[Dict[str, float]] = None,
    ) -> tuple[List[BottleneckNode], List[SinglePointOfFailure]]:
        """Perform topological inspection for bottlenecks and single points of failure."""
        critical_nodes = critical_path_entities or set()
        contention_map = resource_contention_map or {}
        entities = snapshot.get_entities()

        # Step 1: Precompute downstream reach for each entity using BFS
        downstream_reach_map: Dict[str, Set[str]] = {}
        for node_id in entities:
            reachable: Set[str] = set()
            queue: deque[str] = deque([node_id])
            visited: Set[str] = {node_id}

            while queue:
                curr = queue.popleft()
                for edge in snapshot.get_outgoing_edges(curr):
                    tgt = edge.target_entity
                    if tgt not in visited:
                        visited.add(tgt)
                        reachable.add(tgt)
                        queue.append(tgt)

            downstream_reach_map[node_id] = reachable

        # Step 2: Compute flow centrality and dependency count
        bottlenecks: List[BottleneckNode] = []
        spofs: List[SinglePointOfFailure] = []

        total_nodes = max(1, snapshot.node_count)

        for node_id, node_meta in entities.items():
            incoming_edges = snapshot.get_incoming_edges(node_id)
            outgoing_edges = snapshot.get_outgoing_edges(node_id)
            downstream_set = downstream_reach_map.get(node_id, set())
            reach_count = len(downstream_set)
            in_degree = len(incoming_edges)
            out_degree = len(outgoing_edges)

            # Centrality score based on proportion of reachable topology
            centrality = round(reach_count / total_nodes, 3)

            # Failure propagation potential: combines reach and out_degree
            propagation_potential = round(min(1.0, (reach_count * 0.7 + out_degree * 0.3) / total_nodes), 3)

            # Resource contention index from orchestration integration if available
            contention_index = contention_map.get(node_id, 0.0)

            # Redundancy state from incoming/outgoing edges or node metadata
            redundancy_state = RedundancyState.REDUNDANCY_UNKNOWN
            substitutes: List[str] = []

            for edge in outgoing_edges:
                if edge.redundancy_state == RedundancyState.FULL:
                    redundancy_state = RedundancyState.FULL
                    substitutes.extend(edge.redundancy_alternatives)
                elif edge.redundancy_state == RedundancyState.PARTIAL and redundancy_state != RedundancyState.FULL:
                    redundancy_state = RedundancyState.PARTIAL
                    substitutes.extend(edge.redundancy_alternatives)
                elif edge.redundancy_state == RedundancyState.NONE and redundancy_state == RedundancyState.REDUNDANCY_UNKNOWN:
                    redundancy_state = RedundancyState.NONE

            is_critical_path = node_id in critical_nodes

            # SPoF Criticality classification (Spec 14)
            # Low: small reach or full redundancy
            # Medium: moderate reach or partial redundancy
            # High: high reach without redundancy
            # Critical: very high reach (>5 dependents or >40% of topology) with zero redundancy and critical path
            spof_crit = CriticalityLevel.LOW
            if redundancy_state == RedundancyState.FULL:
                spof_crit = CriticalityLevel.LOW
            elif reach_count >= 5 or (reach_count >= 3 and redundancy_state == RedundancyState.NONE):
                if is_critical_path or reach_count >= 8:
                    spof_crit = CriticalityLevel.CRITICAL
                else:
                    spof_crit = CriticalityLevel.HIGH
            elif reach_count >= 2:
                spof_crit = CriticalityLevel.MEDIUM
            else:
                spof_crit = CriticalityLevel.LOW

            # Register as Bottleneck if reach >= 2 or contention > 0.5 or out_degree >= 3
            if reach_count >= 2 or contention_index >= 0.5 or out_degree >= 3 or in_degree >= 3:
                bottlenecks.append(
                    BottleneckNode(
                        entity_id=node_id,
                        name=str(node_meta.get("name", node_id)),
                        downstream_reach=reach_count,
                        dependency_count=in_degree + out_degree,
                        centrality_score=centrality,
                        critical_path_participant=is_critical_path,
                        resource_contention_index=contention_index,
                        failure_propagation_potential=propagation_potential,
                        spof_criticality=spof_crit,
                        redundancy_state=redundancy_state,
                        substitutes=list(set(substitutes)),
                    )
                )

            # Register as SPoF if reach_count >= 2 and redundancy is not FULL
            if reach_count >= 2 and redundancy_state != RedundancyState.FULL:
                spofs.append(
                    SinglePointOfFailure(
                        entity_id=node_id,
                        criticality=spof_crit,
                        dependent_count=reach_count,
                        downstream_nodes=list(downstream_set),
                        redundancy_state=redundancy_state,
                        recovery_options=substitutes if substitutes else ["manual_restart", "failover_zone"],
                        substitutability=SubstitutabilityLevel.HIGH if substitutes else SubstitutabilityLevel.NONE,
                        reversibility=ReversibilityLevel.MODERATE,
                    )
                )

        # Sort bottlenecks by failure propagation potential descending
        bottlenecks.sort(key=lambda b: (b.failure_propagation_potential, b.downstream_reach), reverse=True)
        spofs.sort(key=lambda s: (s.dependent_count), reverse=True)

        logger.info(
            "Identified %d bottlenecks and %d single points of failure in graph of %d nodes",
            len(bottlenecks), len(spofs), snapshot.node_count,
        )
        return bottlenecks, spofs


# Global default bottleneck analyzer
default_bottleneck_analyzer = BottleneckAnalyzer()
