"""Cascade pattern detection, classification, and lifecycle management (Task 75)."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import logging
from typing import Any, Dict, List, Optional, Set

from app.propagation.schemas import (
    CascadeChain,
    CascadeStatus,
    CascadeType,
    FeedbackType,
    ImpactDimensions,
    PropagationEdge,
    RelationshipType,
    TriggerType,
    generate_uuid,
    utc_now,
)
from app.propagation.traversal import TraversalResult

logger = logging.getLogger("kairo.propagation.cascade")


def compute_cascade_fingerprint(
    origin_entity: str,
    trigger_type: str,
    path_nodes: List[str],
    cascade_type: str,
) -> str:
    """Deterministic hash fingerprint for materially equivalent cascades (Spec 56)."""
    raw = f"{origin_entity}|{trigger_type}|{','.join(path_nodes)}|{cascade_type}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


class CascadeDetector:
    """Identifies and classifies systemic cascades across 9 conceptual types with stable fingerprinting (Spec 11, 12, 29, 56, 58)."""

    def detect_cascades(
        self,
        traversal_result: TraversalResult,
        trigger_type: TriggerType = TriggerType.STATE_CHANGE,
    ) -> List[CascadeChain]:
        """Convert multi-hop traversed paths into categorized, ordered CascadeChains."""
        origin = traversal_result.origin_entity
        chains: List[CascadeChain] = []
        seen_fingerprints: Set[str] = set()

        # Find all terminal leaf paths or significant downstream nodes (depth >= 2)
        candidate_paths: List[List[str]] = []
        for node_id, node_meta in traversal_result.visited_nodes.items():
            if node_id == origin:
                continue
            path = node_meta.get("path", [])
            if len(path) >= 2:
                candidate_paths.append(path)

        # Sort paths by length descending to process deep cascades first
        candidate_paths.sort(key=lambda p: len(p), reverse=True)

        for path in candidate_paths:
            total_depth = len(path) - 1

            # Extract edges along this path
            path_edges: List[Dict[str, Any]] = []
            cumulative_delay = 0.0
            has_amplifying_relation = False
            has_resource_share = False
            has_security_breach = False
            has_schedule_blocker = False

            for i in range(len(path) - 1):
                src = path[i]
                tgt = path[i + 1]
                edge_match: Optional[PropagationEdge] = None
                for e in traversal_result.traversed_edges:
                    if e.source_entity == src and e.target_entity == tgt:
                        edge_match = e
                        break

                if edge_match:
                    rel_type = edge_match.relationship_type
                    delay = edge_match.temporal_delay.expected_delay_seconds
                    cumulative_delay += delay
                    path_edges.append({
                        "from": src,
                        "to": tgt,
                        "relationship": rel_type.value,
                        "epistemic": edge_match.epistemic_category.value,
                        "confidence": edge_match.confidence,
                        "delay_seconds": delay,
                    })

                    if rel_type in (RelationshipType.AMPLIFIES, RelationshipType.TRIGGERS):
                        has_amplifying_relation = True
                    if rel_type in (RelationshipType.SHARES_RESOURCE, RelationshipType.SHARES_FAILURE_DOMAIN):
                        has_resource_share = True
                    if rel_type in (RelationshipType.BLOCKS, RelationshipType.CONSTRAINS):
                        has_schedule_blocker = True
                else:
                    path_edges.append({"from": src, "to": tgt, "relationship": "UNKNOWN", "confidence": 0.5})

            # Check if this path participates in a detected feedback cycle
            feedback_type = FeedbackType.STABILIZING_FEEDBACK
            for cycle in traversal_result.cycles:
                if any(n in cycle for n in path):
                    cycle_key = "->".join(cycle)
                    feedback_type = traversal_result.feedback_types.get(cycle_key, FeedbackType.UNKNOWN_FEEDBACK)
                    break

            # Classify cascade type (Spec 12)
            if feedback_type == FeedbackType.AMPLIFYING_FEEDBACK or has_amplifying_relation:
                cascade_type = CascadeType.FEEDBACK_CASCADE
            elif has_resource_share:
                cascade_type = CascadeType.RESOURCE_CASCADE
            elif has_schedule_blocker:
                cascade_type = CascadeType.SCHEDULE_CASCADE
            elif trigger_type == TriggerType.FAILURE:
                cascade_type = CascadeType.FAILURE_CASCADE
            elif trigger_type == TriggerType.RESOURCE_DEPLETION:
                cascade_type = CascadeType.CAPACITY_CASCADE
            else:
                cascade_type = CascadeType.DEPENDENCY_CASCADE

            terminal_meta = traversal_result.visited_nodes.get(path[-1], {})
            terminal_impact = terminal_meta.get("impact", ImpactDimensions())
            likelihood = terminal_meta.get("confidence", 0.7)

            fingerprint = compute_cascade_fingerprint(origin, trigger_type.value, path, cascade_type.value)
            if fingerprint in seen_fingerprints:
                continue
            seen_fingerprints.add(fingerprint)

            chain = CascadeChain(
                chain_id=generate_uuid(),
                cascade_type=cascade_type,
                nodes=path,
                edges=path_edges,
                total_depth=total_depth,
                cumulative_delay_seconds=cumulative_delay,
                amplification_detected=has_amplifying_relation or (feedback_type == FeedbackType.AMPLIFYING_FEEDBACK),
                feedback_type=feedback_type,
                likelihood=likelihood,
                impact=terminal_impact,
                fingerprint=fingerprint,
                status=CascadeStatus.PROJECTED,
            )
            chains.append(chain)

        logger.info("Detected %d cascade chains originating from '%s'", len(chains), origin)
        return chains


# Global default detector
default_cascade_detector = CascadeDetector()
