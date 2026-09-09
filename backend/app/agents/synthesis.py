"""Multi-agent result synthesis, provenance tracing, and conflict preservation (Task 44)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Optional
import uuid

from app.agents.evidence import CollaborativeEvidence, EvidencePool

logger = logging.getLogger("kairo.agents.synthesis")


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class SynthesizedFinding:
    """An individual synthesized finding grounded in explicit contributing evidence (Spec 63)."""

    summary: str
    contributing_agent_ids: list[str] = field(default_factory=list)
    supporting_evidence_refs: list[str] = field(default_factory=list)
    is_verified: bool = False
    confidence: float = 1.0

    @property
    def evidence_refs(self) -> list[str]:
        return self.supporting_evidence_refs


@dataclass
class CollectiveSynthesisResult:
    """Unified synthesis of multi-agent collaboration with preserved conflicts and uncertainty (Spec 62, 65)."""

    collaboration_id: str
    parent_goal: str
    status: str  # SUCCESS, PARTIAL, FAILED, INCONCLUSIVE
    findings: list[SynthesizedFinding] = field(default_factory=list)
    unresolved_conflicts: list[str] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)
    recommended_next_actions: list[str] = field(default_factory=list)
    synthesis_id: str = field(default_factory=lambda: f"syn_{uuid.uuid4().hex[:8]}")
    created_at: datetime = field(default_factory=utc_now)

    @property
    def session_id(self) -> str:
        return self.collaboration_id

    @property
    def goal(self) -> str:
        return self.parent_goal

    @property
    def recommendation(self) -> str:
        if self.recommended_next_actions:
            return self.recommended_next_actions[0]
        return "Proceed with verified evidence."

    @property
    def is_verified(self) -> bool:
        return any(f.is_verified for f in self.findings) if self.findings else False

    def to_dict(self) -> dict[str, Any]:
        return {
            "synthesis_id": self.synthesis_id,
            "collaboration_id": self.collaboration_id,
            "parent_goal": self.parent_goal,
            "status": self.status,
            "findings": [
                {
                    "summary": f.summary,
                    "contributing_agent_ids": f.contributing_agent_ids,
                    "supporting_evidence_refs": f.supporting_evidence_refs,
                    "is_verified": f.is_verified,
                    "confidence": round(f.confidence, 3),
                }
                for f in self.findings
            ],
            "unresolved_conflicts": self.unresolved_conflicts,
            "uncertainties": self.uncertainties,
            "recommended_next_actions": self.recommended_next_actions,
            "created_at": self.created_at.isoformat(),
        }


class SynthesisEngine:
    """Synthesizes collaborative agent outputs without hallucination or conflict suppression (Specs 62-66)."""

    def __init__(self, evidence_pool: Optional[EvidencePool] = None) -> None:
        self.evidence_pool = evidence_pool or EvidencePool()

    def synthesize(
        self,
        session_id: str = "",
        goal: str = "",
        agent_result_ids: Optional[list[str]] = None,
        collaboration_id: Optional[str] = None,
        parent_goal: Optional[str] = None,
        agent_results: Optional[list[dict[str, Any]]] = None,
        known_conflicts: Optional[list[str]] = None,
    ) -> CollectiveSynthesisResult:
        """Combine specialist outputs while strictly preserving conflict points and evidence citations."""
        cid = collaboration_id or session_id
        p_goal = parent_goal or goal

        findings: list[SynthesizedFinding] = []
        uncertainties: list[str] = []
        conflicts = list(known_conflicts or [])
        completed_count = 0

        # If evidence pool has items, pull evidence for this session
        all_evidence = self.evidence_pool.get_all()
        for ev in all_evidence:
            findings.append(
                SynthesizedFinding(
                    summary=ev.claim,
                    contributing_agent_ids=[ev.producer_agent_id],
                    supporting_evidence_refs=[ev.evidence_id],
                    is_verified=ev.is_verified,
                    confidence=0.95 if ev.is_verified else 0.70,
                )
            )

        # Process agent_results if provided
        seen_summaries: dict[str, SynthesizedFinding] = {f.summary.lower(): f for f in findings}

        for res in agent_results or []:
            status = res.get("status", "UNKNOWN")
            agent_id = res.get("agent_id", "unknown_agent")

            if status == "SUCCESS":
                completed_count += 1
            elif status in ["FAILED", "BLOCKED"]:
                uncertainties.append(f"Agent '{agent_id}' failed: {res.get('error', 'Unspecified error')}")

            for out in res.get("outputs", []):
                summary = out.get("summary", "").strip()
                if not summary:
                    continue

                clean_key = summary.lower()
                ev_refs = out.get("evidence_refs", [])
                is_verif = out.get("is_verified", False)

                if clean_key in seen_summaries:
                    existing = seen_summaries[clean_key]
                    if agent_id not in existing.contributing_agent_ids:
                        existing.contributing_agent_ids.append(agent_id)
                    for ref in ev_refs:
                        if ref not in existing.supporting_evidence_refs:
                            existing.supporting_evidence_refs.append(ref)
                    if is_verif:
                        existing.is_verified = True
                else:
                    finding = SynthesizedFinding(
                        summary=summary,
                        contributing_agent_ids=[agent_id],
                        supporting_evidence_refs=list(ev_refs),
                        is_verified=is_verif,
                        confidence=out.get("confidence", 1.0),
                    )
                    seen_summaries[clean_key] = finding
                    findings.append(finding)

            for c in res.get("detected_conflicts", []):
                if c not in conflicts:
                    conflicts.append(c)

        agg_status = "SUCCESS" if findings and not conflicts else "PARTIAL"

        return CollectiveSynthesisResult(
            collaboration_id=cid,
            parent_goal=p_goal,
            status=agg_status,
            findings=findings,
            unresolved_conflicts=conflicts,
            uncertainties=uncertainties,
            recommended_next_actions=["Proceed to independent verification." if agg_status == "SUCCESS" else "Resolve conflicts before proceeding."],
        )
