"""Collective synthesis engine producing conflict-preserving, evidence-backed CollectiveResult (Task 64)."""

from __future__ import annotations

import logging
from typing import Any

from app.swarm.calibration import ConfidenceCalibrator
from app.swarm.schemas import (
    AgentResult,
    CollectiveObjective,
    CollectiveResult,
    ConsensusResult,
    DebateSession,
    DisagreementRecord,
    MinorityReport,
    PeerReview,
)

logger = logging.getLogger(__name__)


class CollectiveSynthesizer:
    """Combines diverse agent findings, peer critiques, and minority reports into a unified CollectiveResult (Spec 26, 27, 78)."""

    def __init__(self, calibrator: ConfidenceCalibrator | None = None) -> None:
        self.calibrator = calibrator or ConfidenceCalibrator()

    def synthesize(
        self,
        objective: CollectiveObjective,
        swarm_id: str,
        results: list[AgentResult],
        reviews: list[PeerReview],
        disagreements: list[DisagreementRecord],
        debates: list[DebateSession],
        consensus: ConsensusResult,
        minority_reports: list[MinorityReport],
    ) -> CollectiveResult:
        """Synthesize collective findings while preserving disagreements and minority viewpoints.

        Invariant: COLLECTIVE OUTPUT != VERIFIED REALITY. Verification status remains UNVERIFIED until verified.
        """
        # 1. Aggregate key findings from across all reporting agents
        key_findings: list[str] = []
        for r in results:
            for claim in r.claims:
                key_findings.append(f"[{r.role}] {claim.text}")

        # 2. Compile supporting evidence
        all_evidence: list[dict[str, Any]] = []
        for r in results:
            for ev in r.evidence:
                if ev not in all_evidence:
                    all_evidence.append(ev)

        # 3. Capture individual perspectives
        agent_perspectives: dict[str, str] = {f"{r.role} ({r.agent_id})": r.answer for r in results}

        # 4. Consolidate uncertainties, assumptions, risks, recommendations
        all_uncertainties = list({u for r in results for u in r.uncertainties})
        all_assumptions = list({a for r in results for a in r.assumptions})
        all_recommendations = list({rec for r in results for rec in r.recommendations})

        # Add minority recommendations
        for min_rep in minority_reports:
            all_recommendations.append(
                f"Contingency ({min_rep.dissenting_role}): {min_rep.divergence_from_majority}"
            )

        risks: list[str] = []
        for dis in disagreements:
            risks.append(f"Operational discrepancy: {dis.issue} ({dis.category.value})")
        for min_rep in minority_reports:
            risks.append(
                f"Failure condition flagged by {min_rep.dissenting_role}: {', '.join(min_rep.failure_scenario_conditions)}"
            )

        # 5. Extract independent lineage count
        lineage_roots = {ev.get("root_id", "src_unknown") for ev in all_evidence}

        # 6. Calibrate collective confidence
        raw_conf = consensus.confidence
        calibrated_conf = self.calibrator.calibrate_confidence(
            raw_confidence=raw_conf,
            evidence_count=len(all_evidence),
            independent_lineage_count=len(lineage_roots),
            has_disagreements=bool(minority_reports or any(d.status != "RESOLVED" for d in disagreements)),
            verification_passed=False,
        )

        # 7. Generate executive summary
        summary_lines = [
            f"Collective reasoning completed for objective: '{objective.goal}'.",
            f"Consensus Outcome: {consensus.outcome.value} (Consensus Score: {consensus.consensus_score:.2f}).",
            f"Primary alignment: {consensus.majority_opinion}",
        ]
        if minority_reports:
            summary_lines.append(
                f"Preserved {len(minority_reports)} minority position(s) safeguarding against failure conditions."
            )
        if debates:
            summary_lines.append(f"Debate resolved across {len(debates)} structured dialectical session(s).")
        executive_summary = " ".join(summary_lines)

        result = CollectiveResult(
            objective_id=objective.objective_id,
            swarm_id=swarm_id,
            goal=objective.goal,
            summary=executive_summary,
            key_findings=key_findings,
            supporting_evidence=all_evidence,
            agent_perspectives=agent_perspectives,
            consensus=consensus,
            minority_positions=minority_reports,
            disagreements=disagreements,
            uncertainties=all_uncertainties,
            assumptions=all_assumptions,
            risks=risks,
            recommendations=all_recommendations,
            confidence=calibrated_conf,
            verification_status="UNVERIFIED",
            affected_systems=objective.constraints or ["core_services"],
            provenance={
                "swarm_id": swarm_id,
                "objective_id": objective.objective_id,
                "agent_count": len(results),
                "lineage_roots": list(lineage_roots),
            },
        )
        logger.info(
            "COLLECTIVE_SYNTHESIS_COMPLETE: swarm_id=%s outcome=%s findings=%d confidence=%.2f",
            swarm_id,
            consensus.outcome.value,
            len(key_findings),
            calibrated_conf,
        )
        return result
