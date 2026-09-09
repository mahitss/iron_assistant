"""Master Intent Understanding, Goal Extraction & Motivation Engine Service (Task 48)."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from app.intent.ambiguity import Ambiguity, AmbiguityAnalyzer
from app.intent.assumptions import Assumption, AssumptionTracker
from app.intent.clarification import ClarificationManager, ClarificationRequest
from app.intent.classifier import CommandClassifier
from app.intent.confidence import ConfidenceEstimator
from app.intent.constraints import ConstraintEngine, DiscoveredConstraint
from app.intent.context import ContextSnapshot, IntentContextManager, TemporalContextResolver
from app.intent.dialogue import DialogueStateManager
from app.intent.entities import EntityExtractor
from app.intent.evaluation import IntentEvaluator
from app.intent.goals import Goal, GoalManager
from app.intent.intent_graph import IntentGraph
from app.intent.motivation import MotivationEngine, MotivationSignal, TradeoffAnalysis
from app.intent.objectives import Objective, ObjectiveExtractor
from app.intent.parser import IntentParser
from app.intent.preferences import PreferenceResolver, UserPreference
from app.intent.priorities import IntentPrioritizer, IntentPriorityNode
from app.intent.provenance import IntentProvenanceTracker
from app.intent.resolution import SafeResolver
from app.intent.safety import IntentSafetyGuard, IntentSecurityViolation
from app.intent.schemas import (
    AmbiguityLevel,
    AmbiguityReport,
    GoalStatus,
    IntentDetailedResponse,
    IntentEntity,
    IntentStatus,
    IntentType,
    UrgencyLevel,
)
from app.intent.scope import IntentScope, ScopeExtractor
from app.intent.urgency import UrgencyExtractor

logger = logging.getLogger("kairo.intent.service")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class IntentService:
    """Master Intent, Goal & Motivation Engine coordinating human input into verifiable goals and plans (Task 48)."""

    def __init__(self) -> None:
        self.goals = GoalManager()
        self.assumptions = AssumptionTracker()
        self.clarifications = ClarificationManager()
        self.dialogue = DialogueStateManager()
        self.contexts = IntentContextManager()
        self.preferences = PreferenceResolver()
        self.confidence_calibrator = ConfidenceEstimator()
        self.evaluator = IntentEvaluator()

        # In-memory storage for active intents: intent_id -> dict
        self._intents: Dict[str, Dict[str, Any]] = {}
        # intent_id -> IntentGraph
        self._graphs: Dict[str, IntentGraph] = {}

    def parse_and_understand(
        self,
        raw_text: str,
        user_id: str = "default_user",
        session_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        project_id: Optional[str] = None,
        environment: str = "DEVELOPMENT",
        user_timezone: str = "UTC",
        source: str = "DIRECT_USER",
    ) -> Dict[str, Any]:
        """Core parsing and understanding pipeline (Spec 1-50).
        
        INPUT -> PARSE -> EXTRACT -> SEPARATE FACT/INFERENCE -> AMBIGUITY -> AUTHORITY -> CREATE GOAL
        """
        # 1. Security Check: Prompt injection and external instruction validation (Spec 163-166)
        IntentSafetyGuard.validate_raw_input_safety(raw_text, source=source)

        # 2. Typo correction (Spec 161, 162)
        clean_text, corrections = SafeResolver.correct_obvious_typos(raw_text)

        # 3. Context & Staleness (Spec 25-28)
        ctx = self.contexts.capture_context(
            user_id=user_id,
            conversation_id=conversation_id,
            project_id=project_id,
            environment=environment,
        )

        # 4. Multi-Intent Detection & Classification (Spec 4-8)
        sub_clauses = IntentParser.split_multi_intents(clean_text)
        classified_sub_intents: List[tuple[IntentType, str]] = []
        for clause in sub_clauses:
            itype = CommandClassifier.classify_deterministic(clause)
            classified_sub_intents.append((itype, clause))

        ordered_intents = IntentPrioritizer.prioritize_multi_intents(classified_sub_intents)
        primary_intent_type = ordered_intents[0].intent_type if ordered_intents else IntentType.REQUEST

        # 5. Extract Entities & Pronoun Resolution (Spec 29-32)
        entities = EntityExtractor.extract_entities(clean_text)
        is_destructive = primary_intent_type in (IntentType.DELETE, IntentType.CANCEL)
        resolved_pronoun, is_pronoun_ambiguous = EntityExtractor.resolve_pronouns(
            clean_text, entities, is_destructive_action=is_destructive
        )
        if resolved_pronoun and resolved_pronoun not in entities:
            entities.append(resolved_pronoun)

        # 6. Extract Constraints & Negations (Spec 15-19, 97)
        constraints = ConstraintEngine.discover_constraints(clean_text)
        conflicts = ConstraintEngine.check_conflicts(constraints)

        # 7. Extract Objectives & Success Criteria (Spec 11-14)
        objectives = ObjectiveExtractor.extract_objectives(clean_text)

        # 8. Extract Scope & Urgency (Spec 39-45)
        scope = ScopeExtractor.extract_scope(clean_text, current_project=project_id, current_env=environment)
        urgency = UrgencyExtractor.extract_urgency(clean_text)
        deadline_str = UrgencyExtractor.extract_deadline(clean_text)

        # 9. Extract Motivations (Spec 76-80)
        motivations = MotivationEngine.detect_motivation(clean_text)

        # 10. Ambiguity & Consequence-Aware Clarification (Spec 55-62, 111)
        ambiguous_candidates = []
        if is_pronoun_ambiguous:
            ambiguous_candidates.append({
                "field": "target_entity",
                "reason": "Pronoun reference cannot be safely resolved for consequential operation without clarification.",
                "candidates": [e.name for e in entities],
            })
        if scope.is_ambiguous:
            ambiguous_candidates.append({
                "field": "scope",
                "reason": "Broad wildcard scope specified; confirm target boundaries.",
                "candidates": ["current_project", "all_projects"],
            })

        ambiguity_report = AmbiguityAnalyzer.analyze(
            intent_type=primary_intent_type,
            risk_level=IntentSafetyGuard.__dict__.get("risk", "NORMAL"),
            ambiguous_candidates=ambiguous_candidates,
            target={"name": entities[0].name} if entities else None,
        )

        # 11. Formulate Intent Status
        if ambiguity_report.ambiguous or is_pronoun_ambiguous or conflicts:
            status = IntentStatus.NEEDS_CLARIFICATION
        else:
            status = IntentStatus.INTERPRETED

        intent_id = f"intent_{uuid.uuid4().hex[:10]}"

        # 12. Create Clarification Request if needed (Spec 58-62)
        clarification_req = None
        if status == IntentStatus.NEEDS_CLARIFICATION:
            clarification_req = self.clarifications.create_request(
                intent_id=intent_id,
                question=ambiguity_report.reason or "Please clarify your intended target.",
                reason="Unambiguous target required for safe execution.",
                affected_decision="target_selection",
                options=[opt.value for opt in ambiguity_report.resolution_options if opt.value],
                is_destructive=is_destructive,
            )

        # 13. Create Goal if interpreted safely (Spec 9-14)
        goal = None
        if status != IntentStatus.NEEDS_CLARIFICATION:
            goal = self.goals.create_goal(
                intent_id=intent_id,
                description=clean_text,
                desired_state={"target_action": primary_intent_type.value},
                success_criteria=[obj.to_dict() for obj in objectives],
                scope=scope.to_dict(),
                constraints=[c.to_dict() for c in constraints],
                priority=urgency,
                owner=user_id,
            )

        # 14. Track Assumptions (Spec 50-54)
        assumption_records = []
        if not deadline_str:
            a = self.assumptions.record_assumption(
                statement="No strict deadline specified; standard scheduling assumed.",
                source="DEFAULT",
                confidence=0.9,
                impact="LOW",
            )
            assumption_records.append(a)

        # 15. Track Provenance (Spec 145, 146)
        provenance = IntentProvenanceTracker.create_provenance_record(
            intent_id=intent_id,
            sources={
                "raw_text": "EXPLICIT_USER",
                "scope": "CONTEXT",
                "objectives": "EXPLICIT_USER" if objectives else "INFERENCE",
                "urgency": "EXPLICIT_USER" if urgency != UrgencyLevel.NORMAL else "SYSTEM_DEFAULT",
            },
        )

        # 16. Build Intent Graph (Spec 74)
        graph = IntentGraph(intent_id=intent_id, goal_id=goal.goal_id if goal else None)
        if goal:
            graph.build_from_goal(goal.to_dict())
        self._graphs[intent_id] = graph

        # 17. Track Dialogue turn (Spec 91-96)
        if session_id:
            self.dialogue.record_turn(
                session_id=session_id,
                user_input=raw_text,
                intent_id=intent_id,
                goal_id=goal.goal_id if goal else None,
            )

        # 18. Store Intent
        intent_record = {
            "intent_id": intent_id,
            "source": source,
            "raw_input": raw_text,
            "normalized_intent": clean_text,
            "intent_type": primary_intent_type,
            "sub_intents": [n.to_dict() for n in ordered_intents],
            "goal": goal.to_dict() if goal else None,
            "objectives": [obj.to_dict() for obj in objectives],
            "constraints": [c.to_dict() for c in constraints],
            "entities": [e.model_dump() for e in entities],
            "scope": scope.to_dict(),
            "urgency": urgency,
            "deadline": deadline_str,
            "ambiguity": ambiguity_report.model_dump(),
            "clarification_request": clarification_req.to_dict() if clarification_req else None,
            "assumptions": [a.to_dict() for a in assumption_records],
            "motivations": [m.to_dict() for m in motivations],
            "provenance": provenance,
            "confidence": ConfidenceEstimator.estimate(
                has_ambiguity=(status == IntentStatus.NEEDS_CLARIFICATION),
            ),
            "status": status,
            "created_at": utc_now().isoformat(),
        }
        self._intents[intent_id] = intent_record

        logger.info("Understood intent %s: type=%s, status=%s, urgency=%s", intent_id, primary_intent_type.value, status.value, urgency.value)
        return intent_record

    def get_intent(self, intent_id: str) -> Optional[Dict[str, Any]]:
        return self._intents.get(intent_id)

    def list_intents(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return list(self._intents.values())

    def answer_clarification(self, clarification_id: str, answer: str) -> Dict[str, Any]:
        """Enforce Spec 58-62: Process user answer and advance intent state."""
        req = self.clarifications.answer_clarification(clarification_id, answer)
        if not req:
            raise KeyError(f"Clarification request {clarification_id} not found")

        intent = self._intents.get(req.intent_id)
        if intent:
            intent["status"] = IntentStatus.CONFIRMED
            # Formulate goal upon clarification
            goal = self.goals.create_goal(
                intent_id=req.intent_id,
                description=f"{intent['normalized_intent']} (Clarified: {answer})",
                desired_state={"clarified_target": answer},
                owner=intent.get("provenance", {}).get("user_id", "default_user"),
            )
            intent["goal"] = goal.to_dict()

        return {
            "clarification_id": clarification_id,
            "status": "ANSWERED",
            "intent_id": req.intent_id,
            "updated_intent_status": IntentStatus.CONFIRMED.value,
        }

    def apply_user_correction(
        self,
        session_id: str,
        intent_id: str,
        correction_text: str,
        revised_objective: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Enforce Spec 67-69: Handle 'That's not what I meant' without defensive behavior."""
        old_intent = self._intents.get(intent_id)
        if old_intent:
            self.confidence_calibrator.record_correction(intent_id, old_intent.get("confidence", 0.8))

        # Formulate new revised intent
        new_text = revised_objective or f"{old_intent.get('raw_input', '')} (Correction: {correction_text})" if old_intent else correction_text
        revised = self.parse_and_understand(raw_text=new_text, session_id=session_id)

        # Update dialogue state
        dialogue_resp = self.dialogue.handle_user_correction(
            session_id=session_id,
            correction_text=correction_text,
            revised_intent_id=revised["intent_id"],
        )
        return {
            "correction_result": dialogue_resp,
            "revised_intent": revised,
        }

    def revoke_intent(self, intent_id: str, user_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """Enforce Spec 186, 187: Cancel active intent and propagate cancellation to child goals."""
        intent = self._intents.get(intent_id)
        if not intent:
            raise KeyError(f"Intent {intent_id} not found")

        IntentSafetyGuard.enforce_user_isolation(
            requesting_user_id=user_id,
            intent_user_id=intent.get("provenance", {}).get("user_id", user_id),
        )

        intent["status"] = IntentStatus.CANCELLED
        # Cancel associated goal if present
        goal_data = intent.get("goal")
        if goal_data and "goal_id" in goal_data:
            g = self.goals.get_goal(goal_data["goal_id"])
            if g:
                g.cancel(reason=reason)

        logger.info("Revoked intent %s for user %s: reason='%s'", intent_id, user_id, reason or "None")
        return {
            "intent_id": intent_id,
            "status": IntentStatus.CANCELLED.value,
            "message": "Intent and associated planned goals have been revoked.",
        }

    def get_intent_graph(self, intent_id: str) -> Dict[str, Any]:
        graph = self._graphs.get(intent_id)
        if not graph:
            graph = IntentGraph(intent_id=intent_id)
        return graph.to_dict()

    def get_health_metrics(self) -> Dict[str, Any]:
        return {
            "intents_total": len(self._intents),
            "goals_active": len(self.goals.list_goals(status=GoalStatus.ACTIVE)),
            "pending_clarifications": len(self.clarifications.get_pending_clarifications()),
            "calibration_ratio": round(self.confidence_calibrator.calibration_ratio, 3),
            "evaluation_metrics": self.evaluator.compute_accuracy_metrics(),
        }


_intent_service_instance: Optional[IntentService] = None


def get_intent_service() -> IntentService:
    """Retrieve or initialize singleton instance of IntentService."""
    global _intent_service_instance
    if _intent_service_instance is None:
        _intent_service_instance = IntentService()
    return _intent_service_instance

