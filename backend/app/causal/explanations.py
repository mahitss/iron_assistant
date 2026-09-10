"""Causal explanation engine, user Q&A router, and prevention/mitigation recommendations (Task 55)."""

from __future__ import annotations

from typing import Any

from app.causal.safety import CausalSafetyGuard
from app.causal.schemas import (
    CausalExplanation,
    CausalGraph,
    RootCauseAnalysis,
    RootCauseStatus,
)


class CausalExplanationEngine:
    """Generates structured causal explanations and answers natural language causal inquiries."""

    @staticmethod
    def generate_explanation(
        incident_name: str,
        what_happened: str,
        why_it_happened: str,
        evidence_list: list[str],
        alternatives: list[str],
        uncertainty: str,
        test_plan: list[str],
        confidence_label: str = "MEDIUM",
        is_verified: bool = False,
    ) -> CausalExplanation:
        """Prompt #100, #101, #102, #144: Build 6-part causal explanation with secret scrubbing."""
        scrubbed_what = CausalSafetyGuard.scrub_text(what_happened)
        scrubbed_why = CausalSafetyGuard.scrub_text(why_it_happened)
        scrubbed_evidence = [CausalSafetyGuard.scrub_text(ev) for ev in evidence_list]
        scrubbed_alts = [CausalSafetyGuard.scrub_text(alt) for alt in alternatives]
        scrubbed_uncertainty = CausalSafetyGuard.scrub_text(uncertainty)
        scrubbed_tests = [CausalSafetyGuard.scrub_text(t) for t in test_plan]

        return CausalExplanation(
            incident=incident_name,
            what_happened=scrubbed_what,
            why_it_likely_happened=scrubbed_why,
            evidence_summary=scrubbed_evidence,
            alternatives=scrubbed_alts,
            uncertainty=scrubbed_uncertainty,
            suggested_testing=scrubbed_tests,
            confidence=confidence_label,
            is_verified=is_verified,
        )

    @staticmethod
    def answer_user_question(
        question: str,
        analysis: RootCauseAnalysis,
        graph: CausalGraph | None = None,
    ) -> dict[str, Any]:
        """Prompt #103-#110: Answer user causal queries with calibrated uncertainty."""
        q_lower = question.lower().strip()

        # "What is the root cause?" / "What caused it?"
        if any(term in q_lower for term in ["root cause", "what caused it", "why did this fail", "what caused the outage"]):
            if analysis.status == RootCauseStatus.VERIFIED and analysis.root_cause:
                answer = f"The verified root cause is: {analysis.root_cause}."
                status_label = "VERIFIED"
            elif analysis.status in (RootCauseStatus.LIKELY, RootCauseStatus.SUPPORTED) and analysis.root_cause:
                answer = (
                    f"The most likely cause is: {analysis.root_cause}. "
                    "Note: This is currently LIKELY based on observations, but has not yet been verified via controlled intervention."
                )
                status_label = "LIKELY"
            elif analysis.surviving_causes:
                answer = f"Investigation ongoing. Candidate causes under evaluation: {', '.join(analysis.surviving_causes)}."
                status_label = "POSSIBLE"
            else:
                answer = "The root cause is currently UNKNOWN. Insufficient empirical evidence exists to establish causality."
                status_label = "UNKNOWN"

            return {
                "question": question,
                "answer": answer,
                "status": status_label,
                "root_cause": analysis.root_cause,
                "contributing_factors": analysis.contributing_factors,
            }

        # "How sure are you?"
        if any(term in q_lower for term in ["how sure", "confidence", "certainty"]):
            conf_pct = round(analysis.confidence * 100, 1)
            verified_note = "Status: VERIFIED." if analysis.status == RootCauseStatus.VERIFIED else "Status: UNVERIFIED (Likely/Investigating)."
            return {
                "question": question,
                "answer": f"Current confidence is {conf_pct}% ({analysis.status.value}). {verified_note}",
                "confidence_score": analysis.confidence,
                "status": analysis.status.value,
            }

        # "What evidence do you have?"
        if any(term in q_lower for term in ["what evidence", "evidence", "proof"]):
            ev_summaries = [f"{ev.type.value} from {ev.source} (strength: {ev.strength.value})" for ev in analysis.evidence]
            return {
                "question": question,
                "answer": f"Identified {len(analysis.evidence)} empirical evidence item(s): {'; '.join(ev_summaries) if ev_summaries else 'None'}.",
                "evidence_count": len(analysis.evidence),
                "items": ev_summaries,
            }

        # "What else could have caused it?" / "Alternatives"
        if any(term in q_lower for term in ["what else", "alternatives", "alternative explanations"]):
            return {
                "question": question,
                "answer": (
                    f"Competing hypotheses considered: {analysis.candidate_causes}. "
                    f"Eliminated causes: {[e.get('cause') for e in analysis.eliminated_causes]}."
                ),
                "candidate_causes": analysis.candidate_causes,
                "eliminated_causes": analysis.eliminated_causes,
            }

        # "How could we test that?"
        if any(term in q_lower for term in ["how could we test", "test that", "intervention"]):
            return {
                "question": question,
                "answer": (
                    "To test this hypothesis safely: 1. Formulate a canary configuration or traffic rollback; "
                    "2. Verify through policy/authorization approval; 3. Compare telemetry against baseline."
                ),
                "proposed_steps": [
                    "Isolate candidate service",
                    "Simulate or stage controlled intervention",
                    "Monitor latency and error telemetry",
                ],
            }

        # "What are the contributing factors?"
        if "contributing" in q_lower:
            return {
                "question": question,
                "answer": (
                    f"Identified contributing factors: {analysis.contributing_factors or 'None isolated'}. "
                    "These factors exacerbated or enabled the failure without being the primary root cause."
                ),
                "contributing_factors": analysis.contributing_factors,
            }

        # Default fallback
        return {
            "question": question,
            "answer": f"Causal assessment for {analysis.incident_id}: Root cause is {analysis.root_cause or 'UNKNOWN'} with status {analysis.status.value}.",
            "analysis_id": analysis.analysis_id,
        }

    @staticmethod
    def generate_remediation_and_prevention(
        analysis: RootCauseAnalysis,
    ) -> dict[str, Any]:
        """Prompt #117, #118, #119: Separate prevention, mitigation, and recovery."""
        root = analysis.root_cause or "unidentified component"

        return {
            "incident_id": analysis.incident_id,
            "root_cause": analysis.root_cause,
            "recovery": [
                f"Restart or failover '{root}' to restore baseline operational availability.",
                "Drain in-flight requests and verify downstream queue clearance.",
            ],
            "mitigation": [
                f"Apply temporary rate-limiting or concurrency clamps on '{root}'.",
                "Enable circuit breaker pattern to prevent cascade failure.",
            ],
            "prevention": [
                f"Implement automated circuit breakers and bulkhead isolation upstream of '{root}'.",
                "Establish strict telemetry alert thresholds for early saturation detection.",
                "Enforce canary deployment verification before 100% traffic progression.",
            ],
            "disclaimer": (
                "Prevention recommendations mitigate risk based on observed mechanisms, "
                "but are not guaranteed prevention against future distinct failure modes (Prompt #118)."
            ),
        }
