"""Self-report and introspection console handling the 5 core self-knowledge inquiries (INVARIANTS 74-78)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.metacognition.capabilities import CapabilityManager
from app.metacognition.failures import FailureClassifier
from app.metacognition.limitations import LimitationDetector
from app.metacognition.schemas import IntrospectionResponseSchema
from app.metacognition.uncertainty import UncertaintyModel


class IntrospectionConsole:
    """Answers user inquiries regarding capabilities, limitations, uncertainty, actions, and failures."""

    def __init__(
        self,
        capability_manager: CapabilityManager,
        limitation_detector: LimitationDetector,
        uncertainty_model: UncertaintyModel,
        failure_classifier: FailureClassifier,
    ) -> None:
        self.capability_manager = capability_manager
        self.limitation_detector = limitation_detector
        self.uncertainty_model = uncertainty_model
        self.failure_classifier = failure_classifier

    def answer_what_can_you_do(self) -> IntrospectionResponseSchema:
        """INVARIANT 74: Answers 'What can you do?' strictly from verified capability registry."""
        caps = self.capability_manager.list_capabilities()
        available = [c.name for c in caps if c.state in ("AVAILABLE", "RESTRICTED")]
        degraded = [f"{c.name} (DEGRADED: {c.degradation_reason})" for c in caps if c.state == "DEGRADED"]

        ans = (
            f"Currently verified available operational capabilities ({len(available)}): {', '.join(available)}.\n"
        )
        if degraded:
            ans += f"Degraded capabilities ({len(degraded)}): {'; '.join(degraded)}."

        return IntrospectionResponseSchema(
            question_type="WHAT_CAN_YOU_DO",
            grounded_answer=ans.strip(),
            verifiable_evidence=[{"total_registered": len(caps), "available": available}],
            confidence=1.0,
        )

    def answer_why_cant_you_do_this(self, task_or_cap: str) -> IntrospectionResponseSchema:
        """INVARIANT 75: Answers 'Why can't you do this?' from actual limitations."""
        active_limits = self.limitation_detector.list_active_limitations()
        matching = [l for l in active_limits if task_or_cap.lower() in l.description.lower() or task_or_cap.lower() in l.category.lower()]

        if matching:
            reasons = [f"[{l.category}] {l.description}" for l in matching]
            ans = f"Cannot execute '{task_or_cap}' due to active operational limitations:\n" + "\n".join(reasons)
        else:
            ans = f"No specific limitation matches '{task_or_cap}'. Please verify required permissions or inputs."

        return IntrospectionResponseSchema(
            question_type="WHY_CANT_YOU",
            grounded_answer=ans,
            verifiable_evidence=[{"matching_limitations_count": len(matching)}],
            confidence=0.9,
            limitations_referenced=[l.limitation_id for l in matching],
        )

    def answer_how_sure_are_you(self, subject: str) -> IntrospectionResponseSchema:
        """INVARIANT 76: Returns calibrated uncertainty and confidence."""
        uncs = self.uncertainty_model.get_uncertainties(subject)
        if uncs:
            u = uncs[0]
            ans = f"Uncertainty detected on subject '{subject}': type '{u.uncertainty_type}', confidence {u.confidence:.2f}, impact '{u.impact}'."
            conf = u.confidence
        else:
            ans = f"Subject '{subject}' has no recorded uncertainty. Operating under high confidence based on verified knowledge."
            conf = 0.95

        return IntrospectionResponseSchema(
            question_type="HOW_SURE",
            grounded_answer=ans,
            verifiable_evidence=[{"uncertainty_records": len(uncs)}],
            confidence=conf,
        )

    def answer_did_you_actually_do_it(self, action_name: str, execution_log: Optional[Dict[str, Any]] = None) -> IntrospectionResponseSchema:
        """INVARIANT 77: Returns verified execution state without false completion claims."""
        if execution_log and execution_log.get("verified"):
            ans = f"Yes. Action '{action_name}' was executed and verified at {execution_log.get('timestamp', 'unknown time')}."
            conf = 1.0
            ev = [execution_log]
        else:
            ans = f"Action '{action_name}' is NOT verified as executed in current telemetry."
            conf = 0.0
            ev = []

        return IntrospectionResponseSchema(
            question_type="DID_YOU_DO_IT",
            grounded_answer=ans,
            verifiable_evidence=ev,
            confidence=conf,
        )

    def answer_what_went_wrong(self, task_id: Optional[str] = None) -> IntrospectionResponseSchema:
        """INVARIANT 78: Returns verified/supported failure details without inventing causes."""
        failures = self.failure_classifier.list_failures(task_id=task_id)
        if failures:
            f = failures[-1]
            ans = f"Action '{f.action}' failed: [{f.failure_type}] {f.cause} (Certainty: {f.certainty})."
            ev = f.evidence
        else:
            ans = "No recorded failure telemetry found for this context."
            ev = []

        return IntrospectionResponseSchema(
            question_type="WHAT_WENT_WRONG",
            grounded_answer=ans,
            verifiable_evidence=ev,
            confidence=0.95 if failures else 0.5,
        )
