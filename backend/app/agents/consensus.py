"""Collaborative Consensus Derivation and Verification Superiority (Task 44)."""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from app.agents.evidence import CollaborativeEvidence, EvidencePool

logger = logging.getLogger("kairo.agents.consensus")


class ConsensusStatus(str, enum.Enum):
    """Classification of team agreement status (Spec 60)."""

    AGREED = "AGREED"                          # Unanimous agreement across all participants
    MAJORITY = "MAJORITY"                      # Numerical majority (requires evidence backing)
    EVIDENCE_SUPPORTED = "EVIDENCE_SUPPORTED"  # Supported by verified empirical proof
    CONFLICTED = "CONFLICTED"                  # Significant unresolved contradictions
    UNKNOWN = "UNKNOWN"                        # Inconclusive data


@dataclass
class ConsensusReport:
    """Structured report of team consensus.
    
    PRINCIPLE: Consensus is a derived state, NOT an authority (Spec 59, 61, 194).
    Ten agents agreeing does NOT replace verification.
    """

    status: ConsensusStatus
    confidence: float = 0.5
    supporting_agents: list[str] = field(default_factory=list)
    dissenting_agents: list[str] = field(default_factory=list)
    has_empirical_verification: bool = False
    verified_evidence_refs: list[str] = field(default_factory=list)
    synthesis_statement: str = ""
    topic: str = ""
    claim_counts: dict[str, int] = field(default_factory=dict)
    verified_claim: Optional[str] = None
    total_evidence: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value if hasattr(self.status, "value") else str(self.status),
            "confidence": round(self.confidence, 3),
            "supporting_agents": self.supporting_agents,
            "dissenting_agents": self.dissenting_agents,
            "has_empirical_verification": self.has_empirical_verification,
            "verified_evidence_refs": self.verified_evidence_refs,
            "synthesis_statement": self.synthesis_statement,
            "topic": self.topic,
            "claim_counts": self.claim_counts,
            "verified_claim": self.verified_claim,
            "total_evidence": self.total_evidence,
        }


class ConsensusEngine:
    """Evaluates agent positions and derives collective consensus (Specs 59-61, 194)."""

    def __init__(self, evidence_pool: Optional[EvidencePool] = None) -> None:
        self.evidence_pool = evidence_pool or EvidencePool()

    def evaluate(self, topic: str, evidence_ids: list[str]) -> ConsensusReport:
        """Derive consensus from evidence pool factoring in verified proof over vote count."""
        evidence_items: list[CollaborativeEvidence] = []
        for eid in evidence_ids:
            ev = self.evidence_pool.get(eid)
            if ev:
                evidence_items.append(ev)

        if not evidence_items:
            return ConsensusReport(
                status=ConsensusStatus.UNKNOWN,
                topic=topic,
                total_evidence=0,
                synthesis_statement=f"No evidence found for topic '{topic}'.",
            )

        claim_counts: dict[str, int] = {}
        verified_claims: list[str] = []

        for ev in evidence_items:
            claim_counts[ev.claim] = claim_counts.get(ev.claim, 0) + 1
            if ev.is_verified:
                verified_claims.append(ev.claim)

        # 1. Evidence-first: Verified evidence wins over vote count
        if verified_claims:
            chosen = verified_claims[0]
            return ConsensusReport(
                status=ConsensusStatus.EVIDENCE_SUPPORTED,
                topic=topic,
                confidence=0.98,
                has_empirical_verification=True,
                verified_claim=chosen,
                claim_counts=claim_counts,
                total_evidence=len(evidence_items),
                synthesis_statement=f"Verified empirical evidence supports: '{chosen}'",
            )

        # 2. Unanimous or Majority
        top_claim, top_count = max(claim_counts.items(), key=lambda item: item[1])
        if top_count == len(evidence_items):
            return ConsensusReport(
                status=ConsensusStatus.AGREED,
                topic=topic,
                confidence=0.75,
                claim_counts=claim_counts,
                total_evidence=len(evidence_items),
                synthesis_statement=f"Unanimous agreement on '{top_claim}'",
            )
        elif top_count > len(evidence_items) / 2:
            return ConsensusReport(
                status=ConsensusStatus.MAJORITY,
                topic=topic,
                confidence=0.60,
                claim_counts=claim_counts,
                total_evidence=len(evidence_items),
                synthesis_statement=f"Majority agreement on '{top_claim}'",
            )

        return ConsensusReport(
            status=ConsensusStatus.CONFLICTED,
            topic=topic,
            confidence=0.30,
            claim_counts=claim_counts,
            total_evidence=len(evidence_items),
            synthesis_statement="Conflicting unverified claims without consensus",
        )

    @staticmethod
    def evaluate_consensus(
        positions: list[dict[str, Any]],
        requires_verification: bool = True,
    ) -> ConsensusReport:
        """Legacy helper for backward compatibility with older positional dicts."""
        if not positions:
            return ConsensusReport(
                status=ConsensusStatus.UNKNOWN,
                confidence=0.0,
                supporting_agents=[],
                dissenting_agents=[],
                has_empirical_verification=False,
                synthesis_statement="No agent positions submitted.",
            )

        claim_buckets: dict[str, list[dict[str, Any]]] = {}
        for p in positions:
            key = p.get("claim_summary", "").strip().lower()
            claim_buckets.setdefault(key, []).append(p)

        total_agents = len(positions)
        verified_positions = [p for p in positions if p.get("is_verified") is True]
        has_verification = len(verified_positions) > 0

        top_claim, top_group = max(claim_buckets.items(), key=lambda item: len(item[1]))
        top_count = len(top_group)

        if has_verification:
            verified_bucket_claims = set(p.get("claim_summary", "").strip().lower() for p in verified_positions)
            if len(verified_bucket_claims) == 1:
                v_claim = next(iter(verified_bucket_claims))
                v_group = claim_buckets[v_claim]
                dissenters = [p.get("agent_id", "unknown") for p in positions if p not in v_group]
                supporters = [p.get("agent_id", "unknown") for p in v_group]
                ev_refs = [ref for p in v_group for ref in p.get("evidence_refs", [])]

                return ConsensusReport(
                    status=ConsensusStatus.EVIDENCE_SUPPORTED,
                    confidence=0.95,
                    supporting_agents=supporters,
                    dissenting_agents=dissenters,
                    has_empirical_verification=True,
                    verified_evidence_refs=ev_refs,
                    synthesis_statement=f"Evidence-supported consensus: '{v_claim}' backed by verified empirical proof.",
                )

        if top_count == total_agents:
            supporters = [p.get("agent_id", "unknown") for p in positions]
            return ConsensusReport(
                status=ConsensusStatus.AGREED,
                confidence=0.90 if has_verification else 0.70,
                supporting_agents=supporters,
                dissenting_agents=[],
                has_empirical_verification=has_verification,
                synthesis_statement=f"Unanimous agreement across all {total_agents} agents on '{top_claim}'.",
            )

        return ConsensusReport(
            status=ConsensusStatus.CONFLICTED,
            confidence=0.30,
            supporting_agents=[],
            dissenting_agents=[p.get("agent_id", "unknown") for p in positions],
            has_empirical_verification=has_verification,
            synthesis_statement="No majority consensus reached; contradictory claims detected.",
        )
