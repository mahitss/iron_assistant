"""Provenance Intelligence Engine for Task 117.

Answers:
- Which evidence chains are weak or overly concentrated?
- Which claims depend on a single upstream source?
- Which verification results share the same underlying observation?
- Which evidence is duplicated?
- Where are provenance gaps?
- What is the fragility profile of this conclusion?

Core Invariant: Preserves uncertainty; never converts similarity into proof of copying.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import logging
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import uuid

from app.evidence_graph.domain import (
    DuplicateEvidenceType,
    EvidenceFragilityAssessment,
    EvidenceGraphEdge,
    EvidenceGraphEdgeType,
    EvidenceGraphNode,
    EvidenceGraphNodeType,
    FreshnessState,
    ImpactSeverity,
    IndependenceStatus,
    ProvenanceCompleteness,
    ProvenanceGap,
    SourceConcentrationFinding,
)
from app.evidence_graph.traversal_engine import TraversalEngine

logger = logging.getLogger(__name__)


class IntelligenceEngine:
    """Computes source concentration, independence, duplicate detection, gaps, and fragility."""

    def __init__(self, traversal_engine: Optional[TraversalEngine] = None):
        self.traversal = traversal_engine or TraversalEngine()

    def analyze_source_concentration(
        self,
        node_id: str,
        get_node_fn: Callable[[str], Optional[EvidenceGraphNode]],
        get_outgoing_edges_fn: Callable[[str], List[EvidenceGraphEdge]],
        get_incoming_edges_fn: Callable[[str], List[EvidenceGraphEdge]],
    ) -> SourceConcentrationFinding:
        """Detect if evidence supporting node_id is concentrated in one or few origins."""
        upstream = self.traversal.traverse_upstream(
            start_node_id=node_id,
            get_node_fn=get_node_fn,
            get_outgoing_edges_fn=get_outgoing_edges_fn,
            get_incoming_edges_fn=get_incoming_edges_fn,
            max_depth=12,
            max_nodes=300,
        )

        sources: List[Dict[str, Any]] = [
            n for n in upstream["nodes"]
            if n["node_type"] in {
                EvidenceGraphNodeType.SOURCE.value,
                EvidenceGraphNodeType.SOURCE_SNAPSHOT.value,
                EvidenceGraphNodeType.OBSERVATION.value,
            }
        ]

        # Group sources by publisher, domain, or common source ID
        origin_groups: Dict[str, List[str]] = defaultdict(list)
        for s in sources:
            payload = s.get("payload", {})
            origin_key = payload.get("publisher") or payload.get("domain") or payload.get("source_id") or s["node_id"]
            origin_groups[origin_key].append(s["node_id"])

        origin_count = len(origin_groups)
        depth = upstream.get("depth_reached", 1)
        independent_estimate = origin_count

        # If multiple sources map to a single origin or origin count == 1 with multiple evidence nodes
        is_high_concentration = False
        details = "Diverse independent sources."

        if len(sources) > 1 and origin_count == 1:
            is_high_concentration = True
            details = f"All {len(sources)} sources derive from a single origin: {list(origin_groups.keys())[0]}"
        elif len(sources) >= 4 and origin_count <= 2:
            is_high_concentration = True
            details = f"Apparent corroboration of {len(sources)} sources concentrated in only {origin_count} origins."
        elif len(sources) == 1:
            details = "Single upstream source dependency."

        return SourceConcentrationFinding(
            target_node_id=node_id,
            origin_count=origin_count,
            dependency_depth=depth,
            independent_source_estimate=independent_estimate,
            shared_origin_groups=dict(origin_groups),
            is_high_concentration=is_high_concentration,
            details=details,
        )

    def detect_single_source_dependency(
        self,
        node_id: str,
        get_node_fn: Callable[[str], Optional[EvidenceGraphNode]],
        get_outgoing_edges_fn: Callable[[str], List[EvidenceGraphEdge]],
        get_incoming_edges_fn: Callable[[str], List[EvidenceGraphEdge]],
    ) -> Tuple[bool, List[str]]:
        """Return True if node_id depends entirely on a single upstream source or has zero groundings."""
        finding = self.analyze_source_concentration(
            node_id, get_node_fn, get_outgoing_edges_fn, get_incoming_edges_fn
        )
        sources = [s for sublist in finding.shared_origin_groups.values() for s in sublist]
        is_single = len(sources) <= 1 or finding.origin_count <= 1
        return is_single, sources

    def detect_duplicate_evidence(
        self,
        evidence_nodes: List[EvidenceGraphNode],
    ) -> List[Dict[str, Any]]:
        """Identify exact or likely duplicate evidence using content hashes and normalized payloads."""
        duplicates: List[Dict[str, Any]] = []
        hash_map: Dict[str, List[str]] = defaultdict(list)

        for ev in evidence_nodes:
            # Use content_hash or compute from payload
            chash = ev.content_hash
            if not chash and ev.payload:
                payload_str = str(sorted(ev.payload.items()))
                chash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
            if chash:
                hash_map[chash].append(ev.node_id)

        for chash, node_ids in hash_map.items():
            if len(node_ids) > 1:
                duplicates.append({
                    "evidence_ids": node_ids,
                    "duplicate_type": DuplicateEvidenceType.EXACT_DUPLICATE.value,
                    "confidence": 1.0,
                    "content_hash": chash,
                    "reason": "Identical cryptographic content hash across evidence entries",
                })

        return duplicates

    def identify_provenance_gaps(
        self,
        node_id: str,
        get_node_fn: Callable[[str], Optional[EvidenceGraphNode]],
        get_outgoing_edges_fn: Callable[[str], List[EvidenceGraphEdge]],
        get_incoming_edges_fn: Callable[[str], List[EvidenceGraphEdge]],
    ) -> List[ProvenanceGap]:
        """Detect missing upstream sources, missing snapshots, unverified claims, or missing actors."""
        gaps: List[ProvenanceGap] = []
        target = get_node_fn(node_id)
        if not target:
            return gaps

        upstream = self.traversal.traverse_upstream(
            start_node_id=node_id,
            get_node_fn=get_node_fn,
            get_outgoing_edges_fn=get_outgoing_edges_fn,
            get_incoming_edges_fn=get_incoming_edges_fn,
            max_depth=6,
            max_nodes=100,
        )

        node_types_present = {n["node_type"] for n in upstream["nodes"]}

        # 1. Claim has no supporting evidence
        if target.node_type == EvidenceGraphNodeType.CLAIM:
            if EvidenceGraphNodeType.EVIDENCE.value not in node_types_present:
                gaps.append(
                    ProvenanceGap(
                        gap_id=f"gap-{uuid.uuid4().hex[:12]}",
                        affected_node_id=node_id,
                        missing_relationship="SUPPORTED_BY",
                        expected_node_type=EvidenceGraphNodeType.EVIDENCE.value,
                        reason="Claim has no direct or indirect supporting evidence registered in the graph.",
                        severity=ImpactSeverity.DIRECT,
                        recoverable=True,
                        acquisition_method="discover_evidence",
                    )
                )

        # 2. Evidence has no Source or Source Snapshot
        for n in upstream["nodes"]:
            if n["node_type"] == EvidenceGraphNodeType.EVIDENCE.value:
                ev_id = n["node_id"]
                ev_edges = get_outgoing_edges_fn(ev_id)
                has_source = any(
                    e.relationship_type in {
                        EvidenceGraphEdgeType.EXTRACTED_FROM,
                        EvidenceGraphEdgeType.DERIVED_FROM,
                        EvidenceGraphEdgeType.OBSERVED_FROM,
                    }
                    for e in ev_edges
                )
                if not has_source:
                    gaps.append(
                        ProvenanceGap(
                            gap_id=f"gap-{uuid.uuid4().hex[:12]}",
                            affected_node_id=ev_id,
                            missing_relationship="EXTRACTED_FROM",
                            expected_node_type=EvidenceGraphNodeType.SOURCE_SNAPSHOT.value,
                            reason=f"Evidence {ev_id} lacks upstream source snapshot or extraction lineage.",
                            severity=ImpactSeverity.POSSIBLE,
                            recoverable=True,
                            acquisition_method="acquire_source_snapshot",
                        )
                    )

        return gaps

    def assess_evidence_fragility(
        self,
        node_id: str,
        get_node_fn: Callable[[str], Optional[EvidenceGraphNode]],
        get_outgoing_edges_fn: Callable[[str], List[EvidenceGraphEdge]],
        get_incoming_edges_fn: Callable[[str], List[EvidenceGraphEdge]],
    ) -> EvidenceFragilityAssessment:
        """Compute multi-dimensional fragility profile for node_id."""
        target = get_node_fn(node_id)
        if not target:
            return EvidenceFragilityAssessment(
                node_id=node_id,
                overall_fragility_label="CRITICAL",
                dimension_findings={"error": "Node not found"},
            )

        # 1. Concentration & single-source
        concentration = self.analyze_source_concentration(
            node_id, get_node_fn, get_outgoing_edges_fn, get_incoming_edges_fn
        )
        is_single_source, _ = self.detect_single_source_dependency(
            node_id, get_node_fn, get_outgoing_edges_fn, get_incoming_edges_fn
        )
        conc_score = 1.0 if is_single_source else (0.7 if concentration.is_high_concentration else 0.2)

        # 2. Upstream traversal for depth and contradiction
        upstream = self.traversal.traverse_upstream(
            start_node_id=node_id,
            get_node_fn=get_node_fn,
            get_outgoing_edges_fn=get_outgoing_edges_fn,
            get_incoming_edges_fn=get_incoming_edges_fn,
            max_depth=10,
            max_nodes=150,
        )

        depth = upstream.get("depth_reached", 1)

        # Check contradictions
        contradictions_count = sum(
            1 for e in upstream["edges"] if e["relationship_type"] == EvidenceGraphEdgeType.CONTRADICTED_BY.value
        )
        contradiction_score = min(1.0, contradictions_count * 0.4)

        # Check transformations
        transformation_count = sum(
            1 for e in upstream["edges"] if e["relationship_type"] in {
                EvidenceGraphEdgeType.TRANSFORMED_FROM.value,
                EvidenceGraphEdgeType.SUMMARIZED_FROM.value,
            }
        )

        # 3. Gaps
        gaps = self.identify_provenance_gaps(
            node_id, get_node_fn, get_outgoing_edges_fn, get_incoming_edges_fn
        )
        gaps_count = len(gaps)
        completeness_score = max(0.0, 1.0 - (gaps_count * 0.35))
        if gaps_count > 0 and concentration.origin_count == 0:
            completeness_score = 0.0  # Zero groundings and explicit gaps

        # 4. Freshness
        freshness_score = 1.0
        if target.freshness_state == FreshnessState.STALE:
            freshness_score = 0.5
        elif target.freshness_state in {FreshnessState.EXPIRED, FreshnessState.INVALID}:
            freshness_score = 0.0

        # 5. Reproducibility
        reproducibility_score = 1.0
        if is_single_source or gaps_count > 0:
            reproducibility_score = 0.6

        # Composite overall label
        # Higher score = more fragile
        fragility_index = (
            (conc_score * 0.3)
            + ((1.0 - completeness_score) * 0.25)
            + ((1.0 - freshness_score) * 0.2)
            + (contradiction_score * 0.15)
            + (min(1.0, depth / 10.0) * 0.1)
        )

        if fragility_index >= 0.7:
            overall_label = "CRITICAL"
        elif fragility_index >= 0.45:
            overall_label = "HIGH"
        elif fragility_index >= 0.25:
            overall_label = "MEDIUM"
        else:
            overall_label = "LOW"

        dimension_findings = {
            "source_concentration": concentration.details,
            "single_source_dependent": is_single_source,
            "unresolved_gaps": [g.reason for g in gaps],
            "contradiction_edges_count": contradictions_count,
            "transformations_count": transformation_count,
            "calculated_fragility_index": round(fragility_index, 3),
        }

        return EvidenceFragilityAssessment(
            node_id=node_id,
            source_concentration_score=conc_score,
            provenance_completeness_score=completeness_score,
            freshness_score=freshness_score,
            reproducibility_score=reproducibility_score,
            dependency_depth=depth,
            contradiction_exposure_score=contradiction_score,
            single_source_dependence=is_single_source,
            transformation_count=transformation_count,
            unresolved_gaps_count=gaps_count,
            dimension_findings=dimension_findings,
            overall_fragility_label=overall_label,
        )
