"""Source registry, trust evaluation, primary/secondary distinction, and citation dependency graph (Task 63)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.research.schemas import Source, SourceTrustLevel, SourceType

logger = logging.getLogger(__name__)


class SourceRegistry:
    """Maintains source catalog, evaluates authority, freshness, and manages retractions.

    Invariant 6: Do not simply assign official = always true.
    Invariant 7: Prefer primary evidence over derivative secondary reporting.
    Invariant 44: Retracted sources are marked, not silently erased from history.
    """

    # Base authority scores by source type
    _AUTHORITY_WEIGHTS: dict[SourceType, float] = {
        SourceType.ACADEMIC_PAPER: 0.95,
        SourceType.GOVERNMENT_PUBLICATION: 0.92,
        SourceType.OFFICIAL_DOCUMENTATION: 0.90,
        SourceType.TECHNICAL_REPORT: 0.85,
        SourceType.DATASET: 0.88,
        SourceType.DATABASE: 0.85,
        SourceType.INTERNAL_SYSTEM: 0.82,
        SourceType.BOOK: 0.80,
        SourceType.COMPANY_DOCUMENTATION: 0.75,
        SourceType.REPOSITORY: 0.75,
        SourceType.API: 0.80,
        SourceType.NEWS: 0.60,
        SourceType.USER_DOCUMENT: 0.70,
        SourceType.FORUM: 0.35,
        SourceType.WEB_PAGE: 0.50,
    }

    def __init__(self) -> None:
        self._sources: dict[str, Source] = {}
        self._seed_default_sources()

    def _seed_default_sources(self) -> None:
        """Seed representative canonical reference sources."""
        now = datetime.now(timezone.utc)
        defaults = [
            Source(
                source_id="src_kairo_arch_doc",
                source_type=SourceType.OFFICIAL_DOCUMENTATION,
                title="Kairo Autonomous Systems Architecture Manual",
                publisher="Kairo Core Engineering",
                author="Architecture Committee",
                url_or_reference="docs://kairo/architecture/overview.md",
                published_at=now,
                domain="kairo.internal",
                trust_level=SourceTrustLevel.PRIMARY_VERIFIED,
                authority_score=0.92,
                freshness_score=1.0,
                relevance_score=1.0,
                is_primary=True,
            ),
            Source(
                source_id="src_distributed_consensus_paper",
                source_type=SourceType.ACADEMIC_PAPER,
                title="Consensus Protocols and Verification in High-Throughput Replicated State Machines",
                publisher="Journal of Distributed Computing",
                author="Dr. E. Dijkstra et al.",
                url_or_reference="https://doi.org/10.1145/example.12345",
                published_at=datetime(2025, 6, 15, tzinfo=timezone.utc),
                domain="academics",
                trust_level=SourceTrustLevel.PEER_REVIEWED,
                authority_score=0.96,
                freshness_score=0.88,
                relevance_score=0.90,
                is_primary=True,
            ),
        ]
        for s in defaults:
            self._sources[s.source_id] = s

    def register_source(
        self,
        title_or_source: str | Source | None = None,
        source_type: SourceType | str | None = None,
        url_or_reference: str = "",
        publisher: str = "Unknown",
        author: str = "Unknown",
        published_at: datetime | None = None,
        is_primary: bool = False,
        citations: list[str] | None = None,
        lineage: list[str] | None = None,
        domain: str = "general",
        *,
        title: str | None = None,
        source_id: str | None = None,
        **kwargs: Any,
    ) -> Source:
        """Register a new source and compute its initial authority and freshness scores."""
        now = datetime.now(timezone.utc)

        if isinstance(title_or_source, Source):
            source = title_or_source
            if source.authority_score == 0.5 and source.source_type in self._AUTHORITY_WEIGHTS:
                source.authority_score = round(self._AUTHORITY_WEIGHTS[source.source_type], 2)
            if source.freshness_score == 1.0 and source.published_at:
                age_days = (now - source.published_at).total_seconds() / 86400.0
                if age_days > 730:
                    source.freshness_score = 0.60
                elif age_days > 365:
                    source.freshness_score = 0.75
                elif age_days > 90:
                    source.freshness_score = 0.90
            self._sources[source.source_id] = source
            return source

        resolved_title = title if title is not None else (title_or_source or "Untitled Source")

        if isinstance(source_type, str):
            try:
                resolved_source_type = SourceType(source_type)
            except Exception:
                try:
                    resolved_source_type = SourceType[source_type.upper()]
                except Exception:
                    resolved_source_type = SourceType.OFFICIAL_DOCUMENTATION
        else:
            resolved_source_type = source_type or SourceType.OFFICIAL_DOCUMENTATION

        auth_score = self._AUTHORITY_WEIGHTS.get(resolved_source_type, 0.50)

        # Freshness score decays over time
        freshness = 1.0
        if published_at:
            age_days = (now - published_at).total_seconds() / 86400.0
            if age_days > 730:  # > 2 years
                freshness = 0.60
            elif age_days > 365:  # > 1 year
                freshness = 0.75
            elif age_days > 90:  # > 3 months
                freshness = 0.90

        # Trust level assignment
        if is_primary and auth_score >= 0.90:
            trust_level = SourceTrustLevel.PRIMARY_VERIFIED
        elif resolved_source_type == SourceType.ACADEMIC_PAPER:
            trust_level = SourceTrustLevel.PEER_REVIEWED
        elif auth_score >= 0.70:
            trust_level = SourceTrustLevel.REPUTABLE_SECONDARY
        else:
            trust_level = SourceTrustLevel.COMMUNITY

        source_kwargs: dict[str, Any] = {
            "source_type": resolved_source_type,
            "title": resolved_title,
            "publisher": publisher,
            "author": author,
            "url_or_reference": url_or_reference,
            "published_at": published_at or now,
            "retrieved_at": now,
            "domain": domain,
            "trust_level": trust_level,
            "authority_score": round(auth_score, 2),
            "freshness_score": round(freshness, 2),
            "relevance_score": 0.85,
            "is_primary": is_primary,
            "citations": citations or [],
            "lineage": lineage or [],
        }
        if source_id:
            source_kwargs["source_id"] = source_id

        source = Source(**source_kwargs)
        self._sources[source.source_id] = source
        logger.info(
            "SOURCE_REGISTERED: id=%s type=%s auth=%.2f fresh=%.2f primary=%s",
            source.source_id,
            source.source_type,
            source.authority_score,
            source.freshness_score,
            source.is_primary,
        )
        return source

    def get_source(self, source_id: str) -> Source | None:
        """Retrieve source by ID."""
        return self._sources.get(source_id)

    def list_sources(self) -> list[Source]:
        """List all active or historical sources."""
        return list(self._sources.values())

    def retract_source(self, source_id: str, reason: str) -> Source:
        """Mark a source as retracted without deleting the historical record.

        Invariant 44: A retracted source remains in the audit trail but is flagged so dependent claims are updated.
        """
        source = self._sources.get(source_id)
        if not source:
            raise KeyError(f"Source '{source_id}' not found.")

        source.is_retracted = True
        source.trust_level = SourceTrustLevel.UNVERIFIED
        source.provenance["retraction_reason"] = reason
        source.provenance["retracted_at"] = datetime.now(timezone.utc).isoformat()
        logger.warning("SOURCE_RETRACTED: id=%s reason='%s'", source_id, reason)
        return source


class SourceDependencyGraph:
    """Tracks citation lineages, builds source DAGs, and detects circular reporting and false consensus.

    Invariant 8: Five derivative articles repeating one original source are recognized as one lineage, not five independent confirmations.
    """

    def __init__(self, registry: SourceRegistry | None = None) -> None:
        self._registry = registry or source_registry
        self._citations: dict[str, set[str]] = {}  # source_id -> set of cited source_ids

    def add_citation(self, citing_source_id: str, cited_source_id: str) -> None:
        """Record that citing_source references cited_source."""
        if citing_source_id not in self._citations:
            self._citations[citing_source_id] = set()
        self._citations[citing_source_id].add(cited_source_id)

    def get_lineage_roots(self, source_id: str) -> list[str]:
        """Retrieve lineage root(s) for a given source."""
        return [self.get_primary_root(source_id)]

    def get_primary_root(self, source_id: str) -> str:
        """Traverse the citation chain upwards to find the primary originating source."""
        visited: set[str] = set()
        current = source_id

        while current:
            if current in visited:
                break  # Break cycle
            visited.add(current)
            cited_sources = self._citations.get(current, set())
            if not cited_sources:
                break
            # Follow first primary source or first cited source
            next_source = None
            for s_id in cited_sources:
                src = self._registry.get_source(s_id)
                if src and src.is_primary:
                    next_source = s_id
                    break
            if not next_source:
                next_source = next(iter(cited_sources))
            current = next_source

        return current

    def detect_circular_reporting(self, source_ids: list[str] | None = None) -> list[tuple[str, ...]]:
        """Detect circular citation chains (e.g. A cites B and B cites A, or A -> B -> C -> A)."""
        nodes = set(source_ids) if source_ids else set(self._citations.keys())
        for cited in self._citations.values():
            nodes.update(cited)

        cycles: list[tuple[str, ...]] = []
        visited: set[str] = set()
        rec_stack: list[str] = []

        def dfs(node: str) -> None:
            visited.add(node)
            rec_stack.append(node)
            for neighbor in self._citations.get(node, set()):
                if source_ids and neighbor not in source_ids:
                    continue
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in rec_stack:
                    idx = rec_stack.index(neighbor)
                    cycle = tuple(rec_stack[idx:])
                    min_idx = cycle.index(min(cycle))
                    canonical = cycle[min_idx:] + cycle[:min_idx]
                    if canonical not in cycles:
                        cycles.append(canonical)
            rec_stack.pop()

        for n in list(nodes):
            if n not in visited:
                dfs(n)

        return cycles

    def compute_source_independence_groups(self, source_ids: list[str]) -> list[list[str]]:
        """Group sources by their common primary lineage root to eliminate redundant derivative weight."""
        groups: dict[str, list[str]] = {}
        for s_id in source_ids:
            root = self.get_primary_root(s_id)
            if root not in groups:
                groups[root] = []
            groups[root].append(s_id)
        return list(groups.values())


source_registry = SourceRegistry()
source_dependency_graph = SourceDependencyGraph(registry=source_registry)
