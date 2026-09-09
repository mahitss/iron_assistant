"""Collaborative Evidence, Fact vs Opinion Classification, and Provenance (Task 44)."""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Optional
import uuid

from app.security.redaction import ArgumentSanitizer

logger = logging.getLogger("kairo.agents.evidence")


def utc_now() -> datetime:
    return datetime.now(UTC)


class FactType(str, enum.Enum):
    """Rigorous epistemic classification of agent claims (Spec 28).
    
    Prevents hallucinated certainty and clearly separates empirical observations
    from reasoning inferences or subjective recommendations.
    """

    FACT = "FACT"                      # Direct tool or empirical observation
    INFERENCE = "INFERENCE"            # Logical deduction derived from facts
    HYPOTHESIS = "HYPOTHESIS"          # Unverified plausible conjecture
    RECOMMENDATION = "RECOMMENDATION"  # UX or procedural suggested action


@dataclass
class CollaborativeEvidence:
    """A verified or observed piece of evidence shared across collaborating agents (Spec 27, 29)."""

    evidence_id: str
    fact_type: FactType
    claim: str
    producer_agent_id: str
    source_uri: str = ""
    sources: list[str] = field(default_factory=list)
    contract_id: str = ""
    producer_model_profile: str = "default"
    model_id: str = "default"
    observation_data: dict[str, Any] = field(default_factory=dict)
    is_verified: bool = False
    verification_strategy: str | None = None
    verification_source: str | None = None
    confidence_score: float = 1.0
    scope: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self):
        if self.sources and not self.source_uri:
            self.source_uri = self.sources[0]
        elif self.source_uri and not self.sources:
            self.sources = [self.source_uri]
        if self.model_id != "default" and self.producer_model_profile == "default":
            self.producer_model_profile = self.model_id
        elif self.producer_model_profile != "default" and self.model_id == "default":
            self.model_id = self.producer_model_profile
        if self.verification_source and not self.verification_strategy:
            self.verification_strategy = self.verification_source
        elif self.verification_strategy and not self.verification_source:
            self.verification_source = self.verification_strategy

    @property
    def timestamp(self) -> datetime:
        return self.created_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "fact_type": self.fact_type.value,
            "claim": self.claim,
            "source_uri": self.source_uri,
            "sources": self.sources,
            "producer_agent_id": self.producer_agent_id,
            "contract_id": self.contract_id,
            "producer_model_profile": self.producer_model_profile,
            "observation_data": self.observation_data,
            "is_verified": self.is_verified,
            "verification_strategy": self.verification_strategy,
            "confidence_score": round(self.confidence_score, 3),
            "scope": self.scope,
            "created_at": self.created_at.isoformat(),
        }


class EvidencePool:
    """Maintains collaborative evidence and detects false consensus or source collusion (Spec 99-103)."""

    def __init__(self) -> None:
        self._items: dict[str, CollaborativeEvidence] = {}

    def add(self, evidence: CollaborativeEvidence) -> None:
        self._items[evidence.evidence_id] = evidence

    def get(self, evidence_id: str) -> CollaborativeEvidence | None:
        return self._items.get(evidence_id)

    def get_all(self) -> list[CollaborativeEvidence]:
        return list(self._items.values())

    def register_evidence(
        self,
        fact_type: FactType,
        claim: str,
        source_uri: str,
        producer_agent_id: str,
        producer_model_profile: str = "default",
        observation_data: dict[str, Any] | None = None,
        is_verified: bool = False,
        verification_strategy: str | None = None,
        scope: dict[str, Any] | None = None,
    ) -> CollaborativeEvidence:
        """Register sanitized evidence with source and model lineage."""
        clean_obs = ArgumentSanitizer.sanitize(observation_data or {})
        ev = CollaborativeEvidence(
            evidence_id=f"ev_{uuid.uuid4().hex[:10]}",
            fact_type=fact_type,
            claim=claim,
            source_uri=source_uri,
            producer_agent_id=producer_agent_id,
            producer_model_profile=producer_model_profile,
            observation_data=clean_obs,
            is_verified=is_verified,
            verification_strategy=verification_strategy,
            scope=scope or {},
        )
        self.add(ev)
        return ev

    def calculate_diversity(self, evidence_ids: list[str]) -> dict[str, Any]:
        """Verify empirical diversity to prevent false consensus (Specs 100-103)."""
        selected = [self._items[eid] for eid in evidence_ids if eid in self._items]
        if not selected:
            return {
                "unique_sources_count": 0,
                "unique_models_count": 0,
                "independence_score": 0.0,
                "is_diverse": False,
            }

        all_sources: set[str] = set()
        for e in selected:
            for s in e.sources:
                all_sources.add(s)
            if e.source_uri:
                all_sources.add(e.source_uri)

        unique_models = set(e.model_id for e in selected)
        unique_agents = set(e.producer_agent_id for e in selected)

        total_claims = len(selected)
        source_ratio = len(all_sources) / max(total_claims, 1)
        model_ratio = len(unique_models) / max(total_claims, 1)
        independence_score = (source_ratio * 0.6) + (model_ratio * 0.4)

        return {
            "total_claims": total_claims,
            "unique_agents_count": len(unique_agents),
            "unique_sources_count": len(all_sources),
            "unique_models_count": len(unique_models),
            "independence_score": round(independence_score, 3),
            "is_diverse": len(all_sources) >= 2 and len(unique_models) >= 2,
            "has_shared_source_collusion": len(unique_agents) > 1 and len(all_sources) == 1,
        }

    def evaluate_source_diversity(self, evidence_ids: list[str]) -> dict[str, Any]:
        return self.calculate_diversity(evidence_ids)

    def list_evidence(self, fact_type: FactType | None = None) -> list[CollaborativeEvidence]:
        items = list(self._items.values())
        if fact_type:
            items = [i for i in items if i.fact_type == fact_type]
        return items
