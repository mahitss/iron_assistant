"""Agent Disagreement Modeling, Evidence-First Resolution, and Blind Review (Task 44)."""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Optional, Union
import uuid

from app.agents.evidence import CollaborativeEvidence, EvidencePool

logger = logging.getLogger("kairo.agents.disagreement")


def utc_now() -> datetime:
    return datetime.now(UTC)


class DisagreementStatus(str, enum.Enum):
    """Lifecycle states of an identified agent disagreement (Spec 52)."""

    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"
    UNRESOLVED = "UNRESOLVED"


@dataclass
class DisagreementClaim:
    """Individual assertion submitted by an agent in a disagreement."""

    claim_id: str
    agent_id: str
    agent_role: str
    statement: str
    evidence_ids: list[str] = field(default_factory=list)
    has_verified_proof: bool = False
    confidence: float = 1.0


class Disagreement:
    """A tracked dispute or contradiction between specialist agents (Spec 51)."""

    def __init__(
        self,
        disagreement_id: Optional[str] = None,
        subject: str = "",
        participants: Optional[list[str]] = None,
        claims: Optional[Union[dict[str, str], list[DisagreementClaim], list[dict[str, Any]]]] = None,
        evidence: Optional[dict[str, list[str]]] = None,
        severity: str = "MEDIUM",
        status: DisagreementStatus = DisagreementStatus.OPEN,
        collaboration_id: str = "",
        resolution: Optional[Union[str, dict[str, Any]]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.disagreement_id = disagreement_id or f"dis_{uuid.uuid4().hex[:10]}"
        self.subject = subject
        self.participants = participants or []
        self.severity = severity
        self.status = status
        self.collaboration_id = collaboration_id
        self.resolution = resolution
        self.created_at = created_at or utc_now()
        self.updated_at = updated_at or utc_now()
        self.evidence = evidence or {}

        # Parse claims
        self.claims: list[DisagreementClaim] = []
        if isinstance(claims, dict):
            for agent_id, stmt in claims.items():
                ev_ids = self.evidence.get(agent_id, [])
                self.claims.append(
                    DisagreementClaim(
                        claim_id=f"clm_{uuid.uuid4().hex[:8]}",
                        agent_id=agent_id,
                        agent_role="SPECIALIST",
                        statement=stmt,
                        evidence_ids=ev_ids,
                    )
                )
        elif isinstance(claims, list):
            for c in claims:
                if isinstance(c, DisagreementClaim):
                    self.claims.append(c)
                elif isinstance(c, dict):
                    self.claims.append(
                        DisagreementClaim(
                            claim_id=c.get("claim_id") or f"clm_{uuid.uuid4().hex[:8]}",
                            agent_id=c.get("agent_id", "unknown"),
                            agent_role=c.get("agent_role", "SPECIALIST"),
                            statement=c.get("statement", ""),
                            evidence_ids=c.get("evidence_ids", []),
                            has_verified_proof=c.get("has_verified_proof", False),
                            confidence=c.get("confidence", 1.0),
                        )
                    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "disagreement_id": self.disagreement_id,
            "collaboration_id": self.collaboration_id,
            "subject": self.subject,
            "participants": self.participants,
            "claims": [
                {
                    "claim_id": c.claim_id,
                    "agent_id": c.agent_id,
                    "agent_role": c.agent_role,
                    "statement": c.statement,
                    "evidence_ids": c.evidence_ids,
                    "has_verified_proof": c.has_verified_proof,
                    "confidence": c.confidence,
                }
                for c in self.claims
            ],
            "severity": self.severity,
            "status": self.status.value,
            "resolution": self.resolution,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class DisagreementResolver:
    """Resolves agent disputes using evidence-first analysis and blind independent review (Specs 53-58)."""

    def __init__(self, evidence_pool: Optional[EvidencePool] = None) -> None:
        self.evidence_pool = evidence_pool or EvidencePool()
        self._disagreements: dict[str, Disagreement] = {}

    def register(self, disagreement: Disagreement) -> None:
        self._disagreements[disagreement.disagreement_id] = disagreement

    def get(self, disagreement_id: str) -> Optional[Disagreement]:
        return self._disagreements.get(disagreement_id)

    def resolve(self, disagreement: Disagreement) -> Disagreement:
        """Resolve disagreement using evidence-first hierarchy (Spec 53, 54).
        
        PRINCIPLE: 3 unverified agent votes cannot defeat 1 agent with verified empirical evidence.
        """
        verified_claims: list[tuple[DisagreementClaim, CollaborativeEvidence]] = []
        unverified_claims: list[DisagreementClaim] = []

        for claim in disagreement.claims:
            has_verified = False
            for ev_id in claim.evidence_ids:
                ev = self.evidence_pool.get(ev_id)
                if ev and ev.is_verified:
                    verified_claims.append((claim, ev))
                    has_verified = True
                    break
            if not has_verified:
                unverified_claims.append(claim)

        if verified_claims:
            winning_claim, winning_ev = verified_claims[0]
            summary = (
                f"Resolved in favor of claim: '{winning_claim.statement}' "
                f"based on verified evidence {winning_ev.evidence_id} ({winning_ev.verification_source or 'empirical'}). "
                f"Defeated {len(unverified_claims)} unverified claims."
            )
            disagreement.status = DisagreementStatus.RESOLVED
            disagreement.resolution = summary
            logger.info("Disagreement %s resolved evidence-first: %s", disagreement.disagreement_id, summary)
        else:
            disagreement.status = DisagreementStatus.ESCALATED
            disagreement.resolution = "No verified empirical evidence provided; escalated to independent reviewer."

        disagreement.updated_at = utc_now()
        self._disagreements[disagreement.disagreement_id] = disagreement
        return disagreement

    def prepare_blind_review_context(self, disagreement: Disagreement) -> dict[str, Any]:
        """Prepare anonymized review context stripping agent IDs and authority metadata (Spec 57, 58)."""
        anonymized_claims = []
        for idx, claim in enumerate(disagreement.claims, start=1):
            anonymized_claims.append({
                "claimant_pseudonym": f"claimant_{idx}",
                "statement": claim.statement,
                "evidence_ids": claim.evidence_ids,
            })

        return {
            "disagreement_id": disagreement.disagreement_id,
            "subject": disagreement.subject,
            "severity": disagreement.severity,
            "claims": anonymized_claims,
            "note": "Agent identities, reputations, and conversational metadata have been stripped for blind review.",
        }
