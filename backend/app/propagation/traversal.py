"""Bounded graph traversal and effect propagation engine (Task 75)."""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
import logging
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from app.propagation.schemas import (
    DirectEffect,
    EpistemicCategory,
    FeedbackType,
    ImpactDimensions,
    PropagationEdge,
    RedundancyState,
    RelationshipType,
    SecondOrderEffect,
    TemporalDelay,
    UncertaintyBreakdown,
)
from app.propagation.snapshots import GraphSnapshot

logger = logging.getLogger("kairo.propagation.traversal")


class TraversalResult:
    """Encapsulates the complete bounded traversal findings."""

    def __init__(
        self,
        origin_entity: str,
        visited_nodes: Dict[str, Dict[str, Any]],
        direct_effects: List[DirectEffect],
        second_order_effects: List[SecondOrderEffect],
        traversed_edges: List[PropagationEdge],
        cycles: List[List[str]],
        feedback_types: Dict[str, FeedbackType],
        is_truncated: bool = False,
        truncation_reason: Optional[str] = None,
        is_topology_complete: bool = True,
        disputed_edges: Optional[List[PropagationEdge]] = None,
        duration_seconds: float = 0.0,
        assumptions: Optional[List[str]] = None,
    ) -> None:
        self.origin_entity = origin_entity
        self.visited_nodes = visited_nodes
        self.direct_effects = direct_effects
        self.second_order_effects = second_order_effects
        self.traversed_edges = traversed_edges
        self.cycles = cycles
        self.feedback_types = feedback_types
        self.is_truncated = is_truncated
        self.truncation_reason = truncation_reason
        self.is_topology_complete = is_topology_complete
        self.disputed_edges = disputed_edges or []
        self.duration_seconds = duration_seconds
        self.assumptions = assumptions or []


class BoundedPropagationTraverser:
    """Traverses dependency and causal graphs with strict computational boundaries and explainable probabilities (Spec 7-10, 23-28)."""

    def __init__(
        self,
        max_depth: int = 4,
        max_nodes: int = 100,
        max_edges: int = 250,
        timeout_seconds: float = 2.0,
    ) -> None:
        self.max_depth = max_depth
        self.max_nodes = max_nodes
        self.max_edges = max_edges
        self.timeout_seconds = timeout_seconds

    def traverse(
        self,
        origin_entity: str,
        snapshot: GraphSnapshot,
        initial_confidence: float = 1.0,
        initial_impact: Optional[ImpactDimensions] = None,
        is_topology_complete: bool = True,
        regime_factor: float = 1.0,
    ) -> TraversalResult:
        """Execute bounded BFS/DFS graph traversal from origin_entity.
        
        Depth 0: Trigger itself.
        Depth 1: Direct effects.
        Depth 2: Second-order effects.
        Depth 3+: Higher-order cascade.
        """
        start_time = time.perf_counter()
        base_impact = initial_impact or ImpactDimensions(operational_impact=0.8, reliability_impact=0.7)

        # Invariant checks: origin must exist in snapshot or we log topology warning
        if not snapshot.has_node(origin_entity):
            logger.warning("Origin entity '%s' not explicitly present in snapshot nodes; proceeding with dynamic root.", origin_entity)

        # visited: node_id -> {depth, path, confidence, cumulative_delay, relationship, epistemic, impact, uncertainty}
        visited: Dict[str, Dict[str, Any]] = {
            origin_entity: {
                "depth": 0,
                "path": [origin_entity],
                "confidence": initial_confidence,
                "cumulative_delay": 0.0,
                "relationship": "TRIGGER",
                "epistemic": EpistemicCategory.OBSERVED_RELATIONSHIP.value,
                "impact": base_impact,
                "uncertainty": 0.05,
            }
        }

        direct_effects: List[DirectEffect] = []
        second_order_effects: List[SecondOrderEffect] = []
        traversed_edges: List[PropagationEdge] = []
        disputed_edges: List[PropagationEdge] = []
        cycles: List[List[str]] = []
        feedback_types: Dict[str, FeedbackType] = {}
        assumptions: List[str] = [
            "Propagation assumes weakest-link confidence decay along multi-hop dependency paths.",
            "Conditional independence assumed across non-adjacent dependencies unless causal DAG specifies mediation."
        ]

        is_truncated = False
        truncation_reason: Optional[str] = None
        edges_examined = 0

        # BFS queue: (curr_node, current_depth, current_confidence, path, cumulative_delay, current_impact)
        queue: deque[Tuple[str, int, float, List[str], float, ImpactDimensions]] = deque([
            (origin_entity, 0, initial_confidence, [origin_entity], 0.0, base_impact)
        ])

        while queue:
            # Check timeout limit (Spec 10)
            elapsed = time.perf_counter() - start_time
            if elapsed >= self.timeout_seconds:
                is_truncated = True
                truncation_reason = f"PROPAGATION_TRUNCATED: Traversal exceeded time budget of {self.timeout_seconds:.2f}s."
                logger.warning(truncation_reason)
                break

            curr_node, depth, cur_confidence, path, cum_delay, cur_impact = queue.popleft()

            # Check node limit (Spec 10)
            if len(visited) > self.max_nodes:
                is_truncated = True
                truncation_reason = f"PROPAGATION_TRUNCATED: Traversal exceeded max nodes limit ({self.max_nodes})."
                logger.warning(truncation_reason)
                break

            # Depth limit check
            if depth >= self.max_depth:
                continue

            outgoing = snapshot.get_outgoing_edges(curr_node)
            for edge in outgoing:
                edges_examined += 1
                if edges_examined > self.max_edges:
                    is_truncated = True
                    truncation_reason = f"PROPAGATION_TRUNCATED: Traversal exceeded max edges limit ({self.max_edges})."
                    logger.warning(truncation_reason)
                    break

                target = edge.target_entity

                # Disputed edge check (Spec 26)
                if edge.is_disputed:
                    disputed_edges.append(edge)

                # Cycle detection (Spec 28)
                if target in path:
                    # Found a cycle: target -> ... -> curr_node -> target
                    cycle_start_idx = path.index(target)
                    cycle_path = path[cycle_start_idx:] + [target]
                    cycles.append(cycle_path)

                    # Classify feedback loop
                    cycle_key = "->".join(cycle_path)
                    if edge.relationship_type in (RelationshipType.AMPLIFIES, RelationshipType.TRIGGERS):
                        feedback_types[cycle_key] = FeedbackType.AMPLIFYING_FEEDBACK
                    elif edge.relationship_type in (RelationshipType.SUPPRESSES, RelationshipType.BLOCKS):
                        feedback_types[cycle_key] = FeedbackType.STABILIZING_FEEDBACK
                    else:
                        feedback_types[cycle_key] = FeedbackType.UNKNOWN_FEEDBACK
                    continue  # Do not loop infinitely

                # Spec 23 & 27: Weakest-link probability decay with regime factor & depth penalty
                # P(B|A) is bounded by minimum link confidence * edge confidence
                effective_edge_conf = edge.confidence * min(1.0, regime_factor)
                next_confidence = round(min(cur_confidence, effective_edge_conf) * (0.95 ** depth), 3)

                # Spec 27: Uncertainty increases with depth, low edge confidence, or unknown timing
                step_uncertainty = (1.0 - edge.confidence) * 0.4 + (depth * 0.08)
                if not edge.temporal_delay.is_known:
                    step_uncertainty += 0.15
                accumulated_uncertainty = min(1.0, round(visited[curr_node]["uncertainty"] + step_uncertainty, 3))

                # Redundancy damping (Spec 15): If target has full redundancy, reduce downstream severity
                redundancy_multiplier = 1.0
                if edge.redundancy_state == RedundancyState.FULL:
                    redundancy_multiplier = 0.35  # Significant severity reduction
                elif edge.redundancy_state == RedundancyState.PARTIAL:
                    redundancy_multiplier = 0.70
                elif edge.redundancy_state == RedundancyState.REDUNDANCY_UNKNOWN:
                    redundancy_multiplier = 1.0
                    accumulated_uncertainty = min(1.0, accumulated_uncertainty + 0.10)

                # Impact propagation across dimensions (Spec 17)
                step_delay = edge.temporal_delay.expected_delay_seconds
                next_cum_delay = cum_delay + step_delay
                next_impact = ImpactDimensions(
                    operational_impact=round(min(1.0, cur_impact.operational_impact * effective_edge_conf * redundancy_multiplier), 3),
                    resource_impact=round(min(1.0, cur_impact.resource_impact * 0.9 * redundancy_multiplier), 3),
                    schedule_impact_seconds=cur_impact.schedule_impact_seconds + step_delay,
                    reliability_impact=round(min(1.0, cur_impact.reliability_impact * effective_edge_conf * redundancy_multiplier), 3),
                    security_impact=round(min(1.0, cur_impact.security_impact * redundancy_multiplier), 3),
                    financial_impact=None,  # Never fabricated (Spec 18)
                    user_impact=round(min(1.0, cur_impact.user_impact * effective_edge_conf * redundancy_multiplier), 3),
                    strategic_impact=round(min(1.0, cur_impact.strategic_impact * 0.85), 3),
                )

                new_path = path + [target]
                traversed_edges.append(edge)

                # Register or update visited node
                if target not in visited or visited[target]["confidence"] < next_confidence:
                    visited[target] = {
                        "node": target,
                        "depth": depth + 1,
                        "path": new_path,
                        "confidence": next_confidence,
                        "cumulative_delay": next_cum_delay,
                        "relationship": edge.relationship_type.value,
                        "epistemic": edge.epistemic_category.value,
                        "impact": next_impact,
                        "uncertainty": accumulated_uncertainty,
                        "redundancy_state": edge.redundancy_state.value,
                    }
                    queue.append((target, depth + 1, next_confidence, new_path, next_cum_delay, next_impact))

                # Categorize Depth 1 vs Depth 2 effects (Spec 8, 9)
                if depth == 0:
                    direct_effects.append(
                        DirectEffect(
                            target_entity=target,
                            relationship_type=edge.relationship_type,
                            epistemic_category=edge.epistemic_category,
                            confidence=next_confidence,
                            expected_direction="DEGRADATION" if edge.relationship_type != RelationshipType.SUPPRESSES else "CONTAINED",
                            expected_magnitude=next_impact.operational_impact,
                            impact=next_impact,
                            temporal_delay=edge.temporal_delay,
                            uncertainty=accumulated_uncertainty,
                            evidence=edge.evidence,
                        )
                    )
                elif depth == 1:
                    explanation_prefix = "Because "
                    if edge.epistemic_category == EpistemicCategory.CAUSAL_RELATIONSHIP:
                        explanation_prefix += f"{curr_node} causally affects {target}"
                    elif edge.relationship_type == RelationshipType.DEPENDS_ON:
                        explanation_prefix += f"{target} depends on {curr_node}"
                    else:
                        explanation_prefix += f"{curr_node} influences {target} ({edge.relationship_type.value})"
                    explanation = f"{explanation_prefix}, {target} may be indirectly affected following {origin_entity} change."

                    second_order_effects.append(
                        SecondOrderEffect(
                            intermediate_entity=curr_node,
                            target_entity=target,
                            path=new_path,
                            confidence=next_confidence,
                            explanation=explanation,
                            temporal_delay=edge.temporal_delay,
                            uncertainty=accumulated_uncertainty,
                        )
                    )

            if is_truncated:
                break

        total_duration = time.perf_counter() - start_time
        return TraversalResult(
            origin_entity=origin_entity,
            visited_nodes=visited,
            direct_effects=direct_effects,
            second_order_effects=second_order_effects,
            traversed_edges=traversed_edges,
            cycles=cycles,
            feedback_types=feedback_types,
            is_truncated=is_truncated,
            truncation_reason=truncation_reason,
            is_topology_complete=is_topology_complete,
            disputed_edges=disputed_edges,
            duration_seconds=total_duration,
            assumptions=assumptions,
        )


# Global default traverser
default_traverser = BoundedPropagationTraverser()
