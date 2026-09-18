"""Provenance Graph & Source Dependency Engine for Task 116.
Manages W3C-PROV inspired DAGs, detects source dependencies, copy chains (A -> B -> C),
and circular citations/support (A -> B -> C -> A), preventing fake corroboration.
"""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timezone
import difflib
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

from app.claim_verification.domain import (
    EvidenceArtifact,
    IndependenceAssessment,
    ProvenanceLink,
    ProvenancePredicate,
    Source,
    SourceRelationship,
    SourceRelationshipType,
)


class ProvenanceEngine:
    """Manages the provenance lineage graph, detects copy chains and cycles,
    and assesses true independence of sources.
    """

    MAX_GRAPH_DEPTH = 16
    MAX_NODES_SEARCH = 250

    @classmethod
    def create_link(
        cls,
        from_type: str,
        from_id: str,
        to_type: str,
        to_id: str,
        predicate: ProvenancePredicate = ProvenancePredicate.DERIVED_FROM,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ProvenanceLink:
        """Construct an immutable directed provenance link."""
        return ProvenanceLink(
            link_id=f"prov_{uuid.uuid4().hex[:10]}",
            from_entity_type=from_type,
            from_entity_id=from_id,
            to_entity_type=to_type,
            to_entity_id=to_id,
            predicate=predicate,
            metadata=metadata or {},
            created_at=datetime.now(timezone.utc),
        )

    @classmethod
    def detect_copy_and_derivation(
        cls,
        source_a: Source,
        source_b: Source,
        artifacts_a: List[EvidenceArtifact],
        artifacts_b: List[EvidenceArtifact],
    ) -> Optional[SourceRelationship]:
        """Inspect textual similarities, metadata, and publisher/owner overlap to detect copy/derivation."""
        if source_a.source_id == source_b.source_id:
            return None

        # 1. Direct owner/publisher common origin
        if source_a.publisher and source_a.publisher == source_b.publisher:
            return SourceRelationship(
                relationship_id=f"rel_{uuid.uuid4().hex[:10]}",
                source_a_id=source_a.source_id,
                source_b_id=source_b.source_id,
                relationship_type=SourceRelationshipType.COMMON_ORIGIN,
                confidence=0.9,
                justification=f"Sources share common publisher/owner '{source_a.publisher}'",
                observed_at=datetime.now(timezone.utc),
            )

        # 2. Textual overlap between artifacts
        max_similarity = 0.0
        for art_a in artifacts_a:
            for art_b in artifacts_b:
                if not art_a.content_text or not art_b.content_text:
                    continue
                # If exact hash matches
                if art_a.content_hash == art_b.content_hash:
                    return SourceRelationship(
                        relationship_id=f"rel_{uuid.uuid4().hex[:10]}",
                        source_a_id=source_a.source_id,
                        source_b_id=source_b.source_id,
                        relationship_type=SourceRelationshipType.DIRECT_COPY,
                        confidence=0.98,
                        justification="Exact content SHA-256 hash match between extracted evidence artifacts",
                        observed_at=datetime.now(timezone.utc),
                    )

                matcher = difflib.SequenceMatcher(None, art_a.content_text, art_b.content_text)
                ratio = matcher.ratio()
                if ratio > max_similarity:
                    max_similarity = ratio

        if max_similarity >= 0.88:
            return SourceRelationship(
                relationship_id=f"rel_{uuid.uuid4().hex[:10]}",
                source_a_id=source_a.source_id,
                source_b_id=source_b.source_id,
                relationship_type=SourceRelationshipType.DIRECT_COPY,
                confidence=float(max_similarity),
                justification=f"High textual similarity ({max_similarity:.2f}) indicates verbatim or near-verbatim copy",
                observed_at=datetime.now(timezone.utc),
            )
        elif max_similarity >= 0.75:
            return SourceRelationship(
                relationship_id=f"rel_{uuid.uuid4().hex[:10]}",
                source_a_id=source_a.source_id,
                source_b_id=source_b.source_id,
                relationship_type=SourceRelationshipType.DERIVATION,
                confidence=float(max_similarity),
                justification=f"Substantial textual similarity ({max_similarity:.2f}) indicates derivation",
                observed_at=datetime.now(timezone.utc),
            )

        return None

    @classmethod
    def detect_circular_dependencies(
        cls,
        links: List[ProvenanceLink],
        relationships: List[SourceRelationship],
    ) -> List[List[str]]:
        """Detect cycles in the provenance and citation graph (e.g. A -> B -> C -> A).
        Returns list of cycles found.
        """
        adj: Dict[str, Set[str]] = defaultdict(set)

        # Populate from provenance links
        for link in links:
            # Directed edge from to_entity_id -> from_entity_id (dependency: from depends on to)
            if link.predicate in (
                ProvenancePredicate.DERIVED_FROM,
                ProvenancePredicate.TRANSFORMED_FROM,
                ProvenancePredicate.COPIED_FROM,
                ProvenancePredicate.DEPENDS_ON,
            ):
                adj[link.from_entity_id].add(link.to_entity_id)

        # Populate from source relationships (e.g. citations, direct copy)
        for rel in relationships:
            if rel.relationship_type in (
                SourceRelationshipType.DIRECT_COPY,
                SourceRelationshipType.CITATION,
                SourceRelationshipType.DERIVATION,
            ):
                adj[rel.source_b_id].add(rel.source_a_id)

        # Standard Tarjan or DFS cycle finder
        cycles: List[List[str]] = []
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        path: List[str] = []

        def dfs(node: str) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in adj.get(node, set()):
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycle = list(path[cycle_start:]) + [neighbor]
                    cycles.append(cycle)

            rec_stack.remove(node)
            path.pop()

        for n in list(adj.keys()):
            if n not in visited:
                dfs(n)

        return cycles

    @classmethod
    def assess_source_independence(
        cls,
        source_ids: List[str],
        relationships: List[SourceRelationship],
        links: List[ProvenanceLink],
    ) -> IndependenceAssessment:
        """Evaluate whether a set of sources are truly independent or form copy/citation chains."""
        if len(source_ids) <= 1:
            return IndependenceAssessment(
                source_ids=source_ids,
                is_independent=True,
                independence_score=1.0,
                detected_relationships=[],
                dependency_chains=[],
                cycles=[],
                justification="Single or zero sources evaluated",
            )

        detected_rels: List[str] = []
        dep_chains: List[str] = []
        is_dep = False
        deduction = 0.0

        # Check explicit relationships
        rel_map: Dict[Tuple[str, str], SourceRelationship] = {}
        for r in relationships:
            rel_map[(r.source_a_id, r.source_b_id)] = r
            rel_map[(r.source_b_id, r.source_a_id)] = r

        for i in range(len(source_ids)):
            for j in range(i + 1, len(source_ids)):
                s_a, s_b = source_ids[i], source_ids[j]
                rel = rel_map.get((s_a, s_b))
                if rel:
                    detected_rels.append(f"{s_a} <-> {s_b}: {rel.relationship_type.value} ({rel.justification})")
                    if rel.relationship_type in (
                        SourceRelationshipType.DIRECT_COPY,
                        SourceRelationshipType.COMMON_ORIGIN,
                        SourceRelationshipType.SHARED_DATASET,
                    ):
                        is_dep = True
                        deduction += 0.5
                    elif rel.relationship_type in (
                        SourceRelationshipType.CITATION,
                        SourceRelationshipType.DERIVATION,
                    ):
                        is_dep = True
                        deduction += 0.35
                    elif rel.relationship_type == SourceRelationshipType.POSSIBLY_DEPENDENT:
                        deduction += 0.2

        # Check circular dependencies
        cycles = cls.detect_circular_dependencies(links, relationships)
        if cycles:
            is_dep = True
            deduction += 0.6
            for c in cycles:
                dep_chains.append(" -> ".join(c))

        final_score = max(0.0, min(1.0, 1.0 - deduction))
        is_independent = (final_score >= 0.75 and not is_dep and len(cycles) == 0)

        justification = (
            "Sources demonstrate verified independent provenance without copy or common origin links"
            if is_independent
            else f"Sources exhibit dependent or circular relationships (score={final_score:.2f}, dependencies={len(detected_rels)}, cycles={len(cycles)})"
        )

        return IndependenceAssessment(
            source_ids=source_ids,
            is_independent=is_independent,
            independence_score=final_score,
            detected_relationships=detected_rels,
            dependency_chains=dep_chains,
            cycles=cycles,
            justification=justification,
        )

    @classmethod
    def trace_evidence_lineage(
        cls,
        evidence_id: str,
        links: List[ProvenanceLink],
        max_depth: int = MAX_GRAPH_DEPTH,
    ) -> List[Dict[str, Any]]:
        """Trace lineage path from root source down to evidence artifact."""
        lineage: List[Dict[str, Any]] = []
        queue: deque[Tuple[str, int, List[str]]] = deque([(evidence_id, 0, [evidence_id])])
        visited: Set[str] = {evidence_id}

        # Index links by to_entity_id (incoming)
        incoming_links: Dict[str, List[ProvenanceLink]] = defaultdict(list)
        for l in links:
            incoming_links[l.from_entity_id].append(l)

        while queue:
            curr_id, depth, path = queue.popleft()
            if depth >= max_depth:
                continue

            for link in incoming_links.get(curr_id, []):
                next_id = link.to_entity_id
                lineage.append({
                    "from_type": link.from_entity_type,
                    "from_id": link.from_entity_id,
                    "predicate": link.predicate.value,
                    "to_type": link.to_entity_type,
                    "to_id": link.to_entity_id,
                    "depth": depth,
                    "metadata": link.metadata,
                })
                if next_id not in visited:
                    visited.add(next_id)
                    queue.append((next_id, depth + 1, path + [next_id]))

        return lineage
