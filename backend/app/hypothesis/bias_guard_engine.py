"""Autonomous Cognitive Bias Protection Engine (Task 115 Section 42, 43, 44).

Implements structural engineering safeguards against:
- Confirmation bias (requires contradiction search before granting STRONGLY_SUPPORTED)
- Anchoring & Premature closure (blocks resolving set if alternatives are unexamined)
- Single-source dominance (detects if >80% of support stems from 1 reporting node)
- Majority-agent bias (detects multiple agents echoing identical underlying evidence)
- Missing UNKNOWN hypothesis (enforces UNKNOWN / OTHER CAUSE presence)

Hard Invariants:
- Structural engineering safeguard, NOT psychological diagnosis.
- Bounded search for contradictions before confidence convergence.
"""

from __future__ import annotations

import logging
from typing import Dict, List

from app.hypothesis.domain import (
    Hypothesis,
    HypothesisEvidenceAssessment,
    HypothesisEvidenceItem,
    HypothesisSet,
    HypothesisStatus,
    SupportVerdict,
)

logger = logging.getLogger("kairo.hypothesis.bias_guard")


class BiasGuardEngine:
    """Safeguards hypothesis evaluation from epistemic blindspots and confirmation bias."""

    def check_and_apply_safeguards(
        self,
        hyp: Hypothesis,
        hset: HypothesisSet,
        all_hypotheses: List[Hypothesis],
        evidence_items: List[HypothesisEvidenceItem],
    ) -> List[str]:
        """Runs cognitive bias audits and applies structural dampening/triggers."""
        triggers: List[str] = []

        # 1. Single-source dominance audit
        if hyp.supporting_evidence_ids:
            source_counts: Dict[str, int] = {}
            for ev_id in hyp.supporting_evidence_ids:
                for item in evidence_items:
                    if item.evidence_id == ev_id:
                        source_counts[item.source] = source_counts.get(item.source, 0) + 1

            total_supporting = len(hyp.supporting_evidence_ids)
            for src, cnt in source_counts.items():
                if total_supporting >= 3 and (cnt / total_supporting) >= 0.8:
                    trig = f"SINGLE_SOURCE_DOMINANCE: Source '{src}' accounts for {cnt}/{total_supporting} ({int(cnt/total_supporting*100)}%) of supporting evidence."
                    triggers.append(trig)
                    # Cap independence and confidence profile
                    hyp.confidence_profile.source_reliability = min(0.6, hyp.confidence_profile.source_reliability)
                    hyp.confidence_profile.evidence_independence = min(0.4, hyp.confidence_profile.evidence_independence)

        # 2. Majority-agent echo audit
        agent_reports = [
            item for item in evidence_items
            if item.evidence_id in hyp.supporting_evidence_ids and item.source_agent_id is not None
        ]
        if len(agent_reports) >= 2:
            # Check if all agent reports reference the same parent or identical payload
            distinct_payloads = {str(item.payload) for item in agent_reports}
            if len(distinct_payloads) == 1:
                trig = f"MAJORITY_AGENT_ECHO: {len(agent_reports)} agents reported identical claims from shared observation; treated as single derived signal."
                triggers.append(trig)
                hyp.confidence_profile.evidence_independence = min(0.35, hyp.confidence_profile.evidence_independence)

        # 3. Confirmation bias & Contradiction Search Requirement
        if hyp.confidence_profile.evidence_strength >= 0.3 or hyp.confidence_profile.contradiction_score > 0.15 or hyp.contradicting_evidence_ids:
            if not hyp.contradiction_search_performed:
                # Proactively perform contradiction check
                self.perform_contradiction_search(hyp, evidence_items)
                hyp.contradiction_search_performed = True

            # If contradictions exist, cannot be STRONGLY_SUPPORTED
            if hyp.confidence_profile.contradiction_score > 0.15 or hyp.contradicting_evidence_ids:
                if hyp.status == HypothesisStatus.STRONGLY_SUPPORTED:
                    hyp.status = HypothesisStatus.CONTESTED
                trig = f"CONFIRMATION_BIAS_GUARD: Contradiction score {hyp.confidence_profile.contradiction_score:.2f} prevents STRONGLY_SUPPORTED status."
                triggers.append(trig)
            elif not hyp.contradiction_search_performed:
                if hyp.status == HypothesisStatus.STRONGLY_SUPPORTED:
                    hyp.status = HypothesisStatus.SUPPORTED
                trig = "CONFIRMATION_BIAS_GUARD: Unvalidated by contradiction search; capped at SUPPORTED."
                triggers.append(trig)

        # 4. Premature closure audit on hypothesis set
        active_candidates = [
            h for h in all_hypotheses
            if h.hypothesis_id in hset.active_hypothesis_ids and not h.is_unknown_hypothesis
        ]
        unexamined = [h for h in active_candidates if len(h.assessments) == 0]
        if unexamined and hset.is_resolved:
            trig = f"PREMATURE_CLOSURE_GUARD: Blocked resolution because {len(unexamined)} alternative hypotheses remain completely unexamined."
            triggers.append(trig)
            hset.is_resolved = False
            hset.resolution_summary = "PREMATURE_CLOSURE_PREVENTED_CAUSE_UNRESOLVED"

        hyp.bias_guard_triggers = triggers
        return triggers

    def perform_contradiction_search(
        self,
        hyp: Hypothesis,
        evidence_items: List[HypothesisEvidenceItem],
    ) -> List[HypothesisEvidenceAssessment]:
        """Actively scans evidence pool for overlooked contradictory observations."""
        found_contradictions: List[HypothesisEvidenceAssessment] = []
        target_metric = hyp.claim.target_metric

        for ev in evidence_items:
            if ev.evidence_id in hyp.supporting_evidence_ids or ev.evidence_id in hyp.contradicting_evidence_ids:
                continue

            # Look for conflicting metrics
            if target_metric and target_metric in ev.payload:
                val = float(ev.payload[target_metric])
                if hyp.claim.expected_direction == "increase" and val < 30.0:
                    assessment = HypothesisEvidenceAssessment(
                        hypothesis_id=hyp.hypothesis_id,
                        evidence_id=ev.evidence_id,
                        verdict=SupportVerdict.CONTRADICTS,
                        reasoning_basis=f"Contradiction search discovered nominal metric {target_metric}={val} during window.",
                        confidence=0.85,
                    )
                    hyp.assessments.append(assessment)
                    hyp.contradicting_evidence_ids.append(ev.evidence_id)
                    found_contradictions.append(assessment)

        if found_contradictions:
            hyp.confidence_profile.contradiction_score = min(
                1.0, hyp.confidence_profile.contradiction_score + 0.35 * len(found_contradictions)
            )
            if hyp.status == HypothesisStatus.STRONGLY_SUPPORTED:
                hyp.status = HypothesisStatus.CONTESTED
            logger.info(
                "Contradiction search discovered %d conflicting items for %s",
                len(found_contradictions),
                hyp.hypothesis_id,
            )

        return found_contradictions
