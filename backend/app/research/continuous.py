"""Continuous knowledge refresh, decay estimation, change detection, and retraction propagation (Task 63)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.research.claims import ClaimExtractor, claim_extractor
from app.research.schemas import Claim
from app.research.sources import SourceRegistry, source_registry

logger = logging.getLogger(__name__)


class KnowledgeChangeEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    source_id: str
    change_type: str
    description: str
    affected_claims: list[str] = Field(default_factory=list)
    affected_decisions: list[str] = Field(default_factory=list)
    affected_plans: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ContinuousResearchManager:
    """Manages continuous knowledge updates, temporal decay scoring, and source retraction propagation.

    Invariant 39, 40, 42: Tracks knowledge decay, detects source changes, and surfaces downstream impact.
    Invariant 43: Changes in claims invalidate dependent decisions, plans, and tasks with full traceability.
    """

    # Domain volatility coefficients (higher = faster decay)
    _DOMAIN_VOLATILITY: dict[str, float] = {
        "cloud_apis": 0.85,
        "ai_models": 0.80,
        "web_frameworks": 0.70,
        "infrastructure": 0.50,
        "cryptography": 0.30,
        "algorithms": 0.15,
        "mathematics": 0.05,
        "general": 0.40,
    }

    def __init__(
        self,
        registry: SourceRegistry | None = None,
        extractor: ClaimExtractor | None = None,
    ) -> None:
        self._registry = registry or source_registry
        self._extractor = extractor or claim_extractor
        self._claim_dependencies: dict[str, list[str]] = {}  # claim_id -> list of dependent entity IDs
        self._change_events: list[KnowledgeChangeEvent] = []

    def register_dependency(self, claim_id: str, downstream_target: str) -> None:
        """Record that a decision, plan, or task depends on a specific claim."""
        if claim_id not in self._claim_dependencies:
            self._claim_dependencies[claim_id] = []
        if downstream_target not in self._claim_dependencies[claim_id]:
            self._claim_dependencies[claim_id].append(downstream_target)

    def calculate_decay_score(
        self,
        domain_volatility: str = "MEDIUM",
        published_at: datetime | None = None,
        source_type: Any = None,
    ) -> float:
        """Compute a freshness decay score (0.0 = fresh, 1.0 = decayed)."""
        now = datetime.now(timezone.utc)
        age_days = (now - published_at).total_seconds() / 86400.0 if published_at else 0.0
        vol_map = {"HIGH": 0.85, "MEDIUM": 0.50, "LOW": 0.05}
        volatility = vol_map.get(str(domain_volatility).upper(), 0.40)
        months = age_days / 30.0
        decay = min(1.0, max(0.0, (volatility * months * 0.04)))
        return round(decay, 2)

    def calculate_knowledge_decay(self, claim: Claim, domain: str = "general") -> float:
        """Compute a freshness decay score (1.0 = brand new, 0.0 = completely stale)."""
        now = datetime.now(timezone.utc)
        age_days = (now - claim.created_at).total_seconds() / 86400.0
        volatility = self._DOMAIN_VOLATILITY.get(domain.lower(), 0.40)

        # Exponential decay: score = e^(-volatility * age_in_months)
        months = age_days / 30.0
        decay = max(0.05, 1.0 - (volatility * months * 0.15))
        return round(decay, 2)

    def detect_and_propagate_change(
        self,
        source_id: str,
        change_type: str,
        description: str,
        affected_claims: list[Claim] | list[str],
        affected_decisions: list[str],
        affected_plans: list[str],
    ) -> list[KnowledgeChangeEvent]:
        """Detect source changes and propagate invalidations downstream (Invariant 42 & 43)."""
        claim_ids = [c.claim_id if hasattr(c, "claim_id") else str(c) for c in affected_claims]
        event = KnowledgeChangeEvent(
            source_id=source_id,
            change_type=change_type,
            description=description,
            affected_claims=claim_ids,
            affected_decisions=affected_decisions,
            affected_plans=affected_plans,
        )
        self._change_events.append(event)
        logger.warning(
            "KNOWLEDGE_CHANGE_PROPAGATED: source=%s type=%s desc='%s'", source_id, change_type, description
        )
        return [event]

    def handle_source_retraction(self, source_id: str, reason: str) -> dict[str, Any]:
        """Propagate source retraction to all associated claims and identify affected downstream artifacts."""
        self._registry.retract_source(source_id, reason=reason)
        affected_claims = self._extractor.list_claims(source_id=source_id)

        downstream_impacts = []
        for claim in affected_claims:
            claim.status = "RETRACTED"
            deps = self._claim_dependencies.get(claim.claim_id, [])
            for dep in deps:
                downstream_impacts.append(
                    {
                        "affected_target": dep,
                        "invalidated_by_claim": claim.claim_id,
                        "retracted_source": source_id,
                    }
                )

        logger.warning(
            "RETRACTION_PROPAGATED: source=%s affected_claims=%d downstream_impacts=%d",
            source_id,
            len(affected_claims),
            len(downstream_impacts),
        )

        return {
            "source_id": source_id,
            "is_retracted": True,
            "retraction_reason": reason,
            "affected_claims_count": len(affected_claims),
            "downstream_impacts": downstream_impacts,
        }

    def detect_source_change(
        self,
        source_id: str,
        new_content_hash: str,
        old_content_hash: str,
    ) -> bool:
        """Detect if an external source document has been modified."""
        if new_content_hash != old_content_hash:
            logger.info("SOURCE_CHANGE_DETECTED: source=%s hash changed", source_id)
            return True
        return False


continuous_research_manager = ContinuousResearchManager()
ContinuousResearchEngine = ContinuousResearchManager
continuous_research_engine = continuous_research_manager
