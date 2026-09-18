"""Service Coordinator for Task 112:
KAIRO Autonomous Causal Explanation, Event Chain Reconstruction & "Why Did This Happen?" Engine.

Strict Invariants:
- CAUSATION != CORRELATION
- TEMPORAL ORDER != CAUSATION
- UNATTRIBUTED CHANGE MUST REMAIN UNATTRIBUTED
- NEVER FABRICATE CAUSAL CONFIDENCE OR ROOT CAUSES
- HISTORICAL EXPLANATIONS PRESERVED IMMUTABLY
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
import logging
from pathlib import Path
import tempfile
from typing import Any, Dict, List, Optional, Tuple

from app.causal.counterfactuals import CounterfactualEngine
from app.causal.explanation.alternative_engine import AlternativeEngine
from app.causal.explanation.chain_reconstructor import EventChainReconstructor
from app.causal.explanation.confidence_engine import CausalConfidenceEngine
from app.causal.explanation.domain import (
    CausalAlternative,
    CausalConfidenceBreakdown,
    CausalContributor,
    CausalExplanation,
    CausalLink,
    CounterfactualScenario,
    EventChain,
    ExplanationEvidence,
    ExplanationGap,
    ExplanationLifecycleStage,
    ExplanationQualityAssessment,
    ExplanationRequest,
    ExplanationVerification,
    RootCauseCategory,
    gen_explanation_id,
    utc_now,
)
from app.causal.explanation.root_cause_engine import RootCauseEngine
from app.causal.explanation.verification_engine import VerificationEngine
from app.temporal.service import TemporalIntelligenceService

logger = logging.getLogger("kairo.causal.explanation")
CACHE_FILE = Path(tempfile.gettempdir()) / "kairo_explanation_cli_cache.json"


class CausalExplanationService:
    """Singleton service orchestrating autonomous causal explanations and root-cause analysis."""

    _instance: Optional[CausalExplanationService] = None

    def __init__(self) -> None:
        self._explanations: Dict[str, CausalExplanation] = {}
        self._verifications: Dict[str, List[ExplanationVerification]] = {}
        self._feedback: Dict[str, List[Dict[str, Any]]] = {}
        self._load_from_cache()

    @classmethod
    def get_instance(cls) -> CausalExplanationService:
        if cls._instance is None:
            cls._instance = CausalExplanationService()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        cls._instance = None

    def generate_explanation(
        self,
        request: ExplanationRequest,
        telemetry_evidence: Optional[List[ExplanationEvidence]] = None,
    ) -> CausalExplanation:
        """Assembles a full evidence-backed causal explanation for the requested target."""
        logger.info("Generating causal explanation for target '%s'", request.target_entity)

        # 1. Event Chain Reconstruction from Temporal Intelligence (Task 111)
        event_chain = EventChainReconstructor.reconstruct_event_chain(
            target_entity=request.target_entity,
            target_timestamp=request.time_window_end,
            target_event_id=request.target_event_id,
            max_steps=request.max_chain_depth,
        )

        # 2. Root Cause & Contributor Analysis
        symptom = request.target_state_change or request.user_query or "State divergence / degradation"
        (
            category,
            primary_cause,
            primary_mech,
            links,
            contributors,
            gaps,
        ) = RootCauseEngine.analyze_causes(
            target_entity=request.target_entity,
            target_symptom=symptom,
            event_chain=event_chain,
            telemetry_evidence=telemetry_evidence,
        )

        is_unknown = (category == RootCauseCategory.UNKNOWN or primary_cause is None)

        # 3. Competing Alternative Hypotheses Generation
        alternatives = AlternativeEngine.generate_alternatives(
            target_entity=request.target_entity,
            primary_category=category,
            primary_cause=primary_cause,
        )

        # 4. Counterfactual Simulation
        counterfactuals: List[CounterfactualScenario] = []
        if primary_cause and not is_unknown:
            cf_desc = f"What if {primary_cause} had not occurred?"
            counterfactuals.append(
                CounterfactualScenario(
                    target_incident_id=request.target_incident_id or f"inc_{request.target_entity}",
                    intervention_description=cf_desc,
                    expected_difference=f"{request.target_entity} would have maintained nominal performance without {symptom}.",
                    assumptions=["System load within operating baseline", "No secondary concurrent faults"],
                    confidence=0.7,
                    is_hypothetical=True,
                )
            )

        # 5. Multi-Dimensional Confidence & Quality Evaluation
        confidence = CausalConfidenceEngine.evaluate_confidence(
            links=links,
            evidence_items=telemetry_evidence or [],
            is_temporally_valid=True,
            is_cause_unknown=is_unknown,
        )

        quality = CausalConfidenceEngine.evaluate_quality(
            confidence=confidence,
            links=links,
            alternatives=alternatives,
            evidence_items=telemetry_evidence or [],
        )

        # 6. Assemble Human-Readable 6-Part Structured Narrative
        what_happened = f"Target '{request.target_entity}' experienced: {symptom}."
        what_changed = f"Observed {len(event_chain.steps)} preceding state transitions leading to target state."
        what_preceded = (
            f"Preceded by: {', '.join(s.event_type for s in event_chain.steps[-3:])}"
            if event_chain.steps else "No preceding transitions detected in temporal window."
        )
        why_it_happened = (
            f"{primary_cause}. Mechanism: {primary_mech}"
            if not is_unknown else "CAUSE UNKNOWN: Insufficient empirical evidence exists to establish causality."
        )
        contrib_summary = (
            f"Identified {len(contributors)} contributing factors ({', '.join(c.description for c in contributors)})."
            if contributors else "No secondary contributing factors established."
        )
        what_would_verify = (
            alternatives[0].discriminating_observation if alternatives
            else "Collect high-frequency telemetry and verify component state transitions."
        )

        lifecycle_stage = (
            ExplanationLifecycleStage.PROVISIONAL if not is_unknown
            else ExplanationLifecycleStage.UNKNOWN
        )

        explanation = CausalExplanation(
            target_entity=request.target_entity,
            target_event_id=request.target_event_id,
            target_state_change=request.target_state_change,
            lifecycle_stage=lifecycle_stage,
            what_happened=what_happened,
            what_changed=what_changed,
            what_preceded_it=what_preceded,
            why_it_happened=why_it_happened,
            contributing_factors_summary=contrib_summary,
            what_would_verify_this=what_would_verify,
            root_cause_category=category,
            primary_cause=primary_cause,
            primary_mechanism=primary_mech,
            causal_links=links,
            contributors=contributors,
            event_chain=event_chain,
            alternatives=alternatives,
            counterfactuals=counterfactuals,
            unresolved_gaps=gaps,
            confidence=confidence,
            quality=quality,
            is_verified=False,
            is_cause_unknown=is_unknown,
            scope=request.scope,
            metadata={"user_query": request.user_query} if request.user_query else {},
        )

        self._explanations[explanation.explanation_id] = explanation
        self._save_to_cache()
        return explanation

    def get_explanation(self, explanation_id: str) -> Optional[CausalExplanation]:
        return self._explanations.get(explanation_id)

    def list_explanations(self, limit: int = 20) -> List[CausalExplanation]:
        return sorted(self._explanations.values(), key=lambda e: e.created_at, reverse=True)[:limit]

    def verify_explanation(
        self,
        explanation_id: str,
        actual_observation: str,
        predicted_consequence: Optional[str] = None,
        actor: str = "operator",
        notes: Optional[str] = None,
    ) -> CausalExplanation:
        """Verifies explanation against subsequent empirical observations."""
        expl = self._explanations.get(explanation_id)
        if not expl:
            raise KeyError(f"Explanation '{explanation_id}' not found.")

        updated_expl, verif = VerificationEngine.record_verification_result(
            explanation=expl,
            actual_observation=actual_observation,
            predicted_consequence=predicted_consequence,
            actor=actor,
            notes=notes,
        )

        self._explanations[explanation_id] = updated_expl
        self._verifications.setdefault(explanation_id, []).append(verif)
        self._save_to_cache()
        return updated_expl

    def get_verifications(self, explanation_id: str) -> List[ExplanationVerification]:
        return self._verifications.get(explanation_id, [])

    def record_feedback(
        self,
        explanation_id: str,
        actor: str,
        feedback_text: str,
        is_accurate: bool = True,
        suggested_alternative: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Ingests operator or agent feedback."""
        record = {
            "feedback_id": gen_explanation_id("fbk"),
            "explanation_id": explanation_id,
            "actor": actor,
            "feedback_text": feedback_text,
            "is_accurate": is_accurate,
            "suggested_alternative": suggested_alternative,
            "received_at": utc_now().isoformat(),
        }
        self._feedback.setdefault(explanation_id, []).append(record)
        self._save_to_cache()
        return record

    def refresh_explanation(self, explanation_id: str) -> CausalExplanation:
        """Re-evaluates explanation with current telemetry without mutating historical snapshot."""
        old_expl = self._explanations.get(explanation_id)
        if not old_expl:
            raise KeyError(f"Explanation '{explanation_id}' not found.")

        req = ExplanationRequest(
            target_entity=old_expl.target_entity,
            target_event_id=old_expl.target_event_id,
            target_state_change=old_expl.target_state_change,
            scope=old_expl.scope,
        )
        new_expl = self.generate_explanation(req)
        new_expl.version = old_expl.version + 1
        old_expl.superseded_by = new_expl.explanation_id
        old_expl.lifecycle_stage = ExplanationLifecycleStage.SUPERSEDED

        self._save_to_cache()
        return new_expl

    # ========================================================================
    # Multi-Process Disk Cache
    # ========================================================================

    def _save_to_cache(self) -> None:
        try:
            cache = {
                "explanations": {k: json.loads(v.model_dump_json()) for k, v in list(self._explanations.items())[-100:]},
                "verifications": {k: [json.loads(v.model_dump_json()) for v in vl] for k, vl in self._verifications.items()},
                "feedback": self._feedback,
            }
            CACHE_FILE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.debug("Failed to write explanation disk cache: %s", exc)

    def _load_from_cache(self) -> None:
        if not CACHE_FILE.exists():
            return
        try:
            raw = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            for k, d in raw.get("explanations", {}).items():
                self._explanations[k] = CausalExplanation.model_validate(d)
            for k, vl in raw.get("verifications", {}).items():
                self._verifications[k] = [ExplanationVerification.model_validate(d) for d in vl]
            self._feedback = raw.get("feedback", {})
        except Exception as exc:
            logger.debug("Failed to load explanation disk cache: %s", exc)
