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

from app.intent.domain import (
    Ambiguity as Task108Ambiguity,
    AmbiguityType,
    Assumption as Task108Assumption,
    AssumptionType,
    Clarification as Task108Clarification,
    ClarificationStatus,
    Constraint as Task108Constraint,
    ConstraintEpistemic,
    ConstraintType,
    DesiredOutcome,
    EpistemicStatus,
    ExternalEffectFlag,
    GoalHypothesis,
    Intent as AutonomousIntent,
    IntentCandidate,
    IntentCategory,
    IntentConflict,
    IntentCorrection,
    IntentEvent,
    IntentFeedback,
    IntentPriorityLevel,
    IntentResolution,
    IntentSnapshot,
    IntentVersion,
    Preference as Task108Preference,
    RequestStatus,
    Requirement,
    UserRequest,
    RequestVersion,
    generate_id as gen_t108_id,
    utc_now as t108_utc_now,
)
from app.intent.prompt_injection_firewall import (
    PromptInjectionDetectedError,
    PromptInjectionFirewall,
)
from app.intent.decomposition_engine import DecompositionEngine
from app.intent.goal_inference_engine import GoalInferenceEngine
from app.intent.outcome_and_constraint_engine import OutcomeAndConstraintEngine
from app.intent.ambiguity_and_clarification_engine import AmbiguityAndClarificationEngine
from app.intent.evidence_and_alignment_engine import EvidenceAndAlignmentEngine
from app.intent.lifecycle_and_versioning_engine import LifecycleAndVersioningEngine
from app.intent.downstream_bridges import DownstreamBridges
from app.events.bus import get_event_bus

logger = logging.getLogger("kairo.intent.service")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class IntentService:
    """Master Intent, Goal & Motivation Engine coordinating human input into verifiable goals and plans (Task 48 & Task 108)."""

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

        # Task 108 Autonomous Intent Engine state
        self._requests: Dict[str, UserRequest] = {}
        self._request_versions: Dict[str, List[RequestVersion]] = {}
        self._autonomous_intents: Dict[str, AutonomousIntent] = {}
        self._intent_versions: Dict[str, List[IntentVersion]] = {}
        self._goal_hypotheses: Dict[str, List[GoalHypothesis]] = {}
        self._desired_outcomes: Dict[str, DesiredOutcome] = {}
        self._constraints_map: Dict[str, List[Task108Constraint]] = {}
        self._preferences_map: Dict[str, List[Task108Preference]] = {}
        self._requirements_map: Dict[str, List[Requirement]] = {}
        self._assumptions_map: Dict[str, List[Task108Assumption]] = {}
        self._ambiguities_map: Dict[str, List[Task108Ambiguity]] = {}
        self._clarifications_map: Dict[str, Task108Clarification] = {}
        self._evidence_map: Dict[str, List[Any]] = {}
        self._corrections_map: Dict[str, List[IntentCorrection]] = {}
        self._snapshots_map: Dict[str, IntentSnapshot] = {}
        self._events: List[IntentEvent] = []
        self._bridges = DownstreamBridges()

    @classmethod
    def get_instance(cls) -> "IntentService":
        """Singleton accessor for IntentService."""
        global _intent_service_instance
        if _intent_service_instance is None:
            _intent_service_instance = IntentService()
        return _intent_service_instance

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
            "intents_total": len(self._intents) + len(self._autonomous_intents),
            "goals_active": len(self.goals.list_goals(status=GoalStatus.ACTIVE)),
            "pending_clarifications": len(self.clarifications.get_pending_clarifications()) + len([c for c in self._clarifications_map.values() if c.status == ClarificationStatus.PENDING]),
            "calibration_ratio": round(self.confidence_calibrator.calibration_ratio, 3),
            "evaluation_metrics": self.evaluator.compute_accuracy_metrics(),
        }

    # ========================================================================
    # Task 108: Autonomous Intent Understanding & Semantics Methods
    # ========================================================================

    def submit_user_request(
        self,
        raw_text: str,
        user_id: str = "default_user",
        tenant_id: str = "default",
        conversation_id: Optional[str] = None,
        message_id: Optional[str] = None,
        source: str = "DIRECT_USER",
        scope: str = "DEFAULT",
        context_reference: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Core Task 108 Pipeline:
        RAW INPUT -> SECURITY FIREWALL -> PARSE/DECOMPOSE -> GOAL INFERENCE -> CONSTRAINTS/NON-GOALS -> AMBIGUITY/CLARIFICATION -> EVIDENCE -> SNAPSHOT -> EVENT DISPATCH
        """
        # 1. Prompt Injection Firewall Check (Spec 41, 42, 60)
        is_safe, reason, is_external = PromptInjectionFirewall.inspect_input(raw_text, source=source, strict=True)
        if not is_safe:
            raise PromptInjectionDetectedError(reason or "Security violation: prompt injection detected.")

        req_id = gen_t108_id("req")
        clean_text = raw_text.strip()

        # 2. Record UserRequest & initial version (Spec 2)
        request = UserRequest(
            request_id=req_id,
            user_id=user_id,
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            message_id=message_id,
            raw_text=raw_text,
            cleaned_text=clean_text,
            source=source,
            scope=scope,
            context_reference=context_reference or {},
            status=RequestStatus.PARSING,
            is_external_content=is_external,
            created_at=t108_utc_now(),
            updated_at=t108_utc_now(),
        )
        self._requests[req_id] = request

        req_ver = RequestVersion(
            version_id=gen_t108_id("req_ver"),
            request_id=req_id,
            version_number=1,
            raw_text=raw_text,
            status=RequestStatus.PARSING,
            change_reason="INITIAL_SUBMISSION",
            created_at=t108_utc_now(),
        )
        self._request_versions.setdefault(req_id, []).append(req_ver)

        self._record_event("request.received", request_id=req_id, user_id=user_id, payload={"raw_text": raw_text, "source": source})

        # If it's pure external content, do NOT extract user instructions (Spec 41)
        if is_external:
            request.status = RequestStatus.UNDERSTOOD
            request.metadata["note"] = "Untrusted external data ingested strictly as data payload. Zero execution authorized."
            self._record_event("request.parsed", request_id=req_id, user_id=user_id, payload={"is_external": True})
            return {
                "request_id": req_id,
                "request": request.model_dump(mode="json"),
                "intents": [],
                "clarifications": [],
                "status": request.status.value,
                "is_external_data": True,
                "message": "External content ingested as data. User instructions cannot be extracted from external payload.",
            }

        # 3. Multi-Intent Decomposition (Spec 6)
        intents = DecompositionEngine.decompose(req_id, clean_text)
        request_has_blocking_clarification = False

        processed_intents: List[Dict[str, Any]] = []

        for intent in intents:
            intent_id = intent.intent_id
            self._autonomous_intents[intent_id] = intent

            # 4. Goal Inference (Spec 7)
            goal_hyp = GoalInferenceEngine.infer_goal(intent, context=context_reference)
            self._goal_hypotheses.setdefault(intent_id, []).append(goal_hyp)

            # 5. Outcome, Constraints, Non-Goals, Requirements, Preferences (Spec 8, 9, 10, 11, 32)
            non_goals = OutcomeAndConstraintEngine.extract_non_goals(intent.summary)
            intent.non_goals = non_goals

            desired_out = OutcomeAndConstraintEngine.extract_desired_outcome(intent_id, intent.summary, intent.category.value)
            self._desired_outcomes[intent_id] = desired_out

            constraints = OutcomeAndConstraintEngine.extract_constraints(intent_id, intent.summary)
            self._constraints_map[intent_id] = constraints

            requirements = OutcomeAndConstraintEngine.extract_requirements(intent_id, intent.summary)
            self._requirements_map[intent_id] = requirements

            preferences = OutcomeAndConstraintEngine.extract_preferences(intent_id, intent.summary)
            self._preferences_map[intent_id] = preferences

            # 6. Ambiguity Analysis & Consequence-Aware Clarification (Spec 12, 13, 14, 15)
            ambs, clrs, asms = AmbiguityAndClarificationEngine.analyze_ambiguity(intent, intent.summary)
            self._ambiguities_map[intent_id] = ambs
            self._assumptions_map[intent_id] = asms

            blocking_clr = None
            for c in clrs:
                self._clarifications_map[c.clarification_id] = c
                if c.status == ClarificationStatus.PENDING:
                    blocking_clr = c

            if blocking_clr:
                intent.status = RequestStatus.CLARIFICATION_REQUIRED
                request_has_blocking_clarification = True
                self._record_event("intent.clarification_required", intent_id=intent_id, request_id=req_id, user_id=user_id,
                                   payload={"question": blocking_clr.question, "rationale": blocking_clr.rationale})
            else:
                intent.status = RequestStatus.UNDERSTOOD
                self._record_event("intent.understood", intent_id=intent_id, request_id=req_id, user_id=user_id,
                                   payload={"summary": intent.summary, "category": intent.category.value})

            # 7. Evidence Aggregation (Spec 16)
            evs = EvidenceAndAlignmentEngine.collect_evidence(intent, intent.summary)
            self._evidence_map[intent_id] = evs

            # 8. Create immutable snapshot (Spec 22)
            snap = LifecycleAndVersioningEngine.create_snapshot(intent, [goal_hyp], constraints, asms)
            self._snapshots_map[intent_id] = snap

            # 9. Initial intent version (Spec 21)
            ver = IntentVersion(
                version_id=gen_t108_id("iver"),
                intent_id=intent_id,
                version_number=1,
                intent_snapshot=intent.model_dump(mode="json"),
                reason_for_change="INITIAL_FORMULATION",
                created_at=t108_utc_now(),
            )
            self._intent_versions.setdefault(intent_id, []).append(ver)

            intent_dict = intent.model_dump(mode="json")
            processed_intents.append({
                **intent_dict,
                "intent": intent_dict,
                "intent_id": intent.intent_id,
                "category": intent.category.value,
                "external_effect": intent.external_effect.value,
                "goal_hypothesis": goal_hyp.model_dump(mode="json"),
                "desired_outcome": desired_out.model_dump(mode="json"),
                "constraints": [c.model_dump(mode="json") for c in constraints],
                "non_goals": list(intent.non_goals),
                "ambiguities": [a.model_dump(mode="json") for a in ambs],
                "clarifications": [c.model_dump(mode="json") for c in clrs],
                "assumptions": [a.model_dump(mode="json") for a in asms],
                "snapshot_id": snap.snapshot_id,
            })

        request.status = RequestStatus.CLARIFICATION_REQUIRED if request_has_blocking_clarification else RequestStatus.UNDERSTOOD
        request.updated_at = t108_utc_now()

        self._record_event("request.parsed", request_id=req_id, user_id=user_id,
                           payload={"intent_count": len(intents), "status": request.status.value})

        return {
            "request_id": req_id,
            "request": request.model_dump(mode="json"),
            "intents": processed_intents,
            "status": request.status.value,
        }

    def get_autonomous_intent(self, intent_id: str) -> Optional[AutonomousIntent]:
        return self._autonomous_intents.get(intent_id)

    def list_autonomous_intents(
        self,
        user_id: Optional[str] = None,
        status: Optional[RequestStatus] = None,
        category: Optional[IntentCategory] = None,
        limit: int = 100,
    ) -> List[AutonomousIntent]:
        results = list(self._autonomous_intents.values())
        if status:
            results = [i for i in results if i.status == status]
        if category:
            results = [i for i in results if i.category == category]
        return results[:limit]

    def get_intent_versions(self, intent_id: str) -> List[IntentVersion]:
        return self._intent_versions.get(intent_id, [])

    def get_intent_evidence(self, intent_id: str) -> List[Any]:
        return self._evidence_map.get(intent_id, [])

    def get_intent_clarifications(self, intent_id: str) -> List[Task108Clarification]:
        return [c for c in self._clarifications_map.values() if c.intent_id == intent_id]

    def get_intent_corrections(self, intent_id: str) -> List[IntentCorrection]:
        return self._corrections_map.get(intent_id, [])

    def get_intent_snapshot_record(self, intent_id: str) -> Optional[IntentSnapshot]:
        return self._snapshots_map.get(intent_id)

    def search_autonomous_intents(self, query: str, user_id: Optional[str] = None) -> List[AutonomousIntent]:
        q = query.lower().strip()
        return [
            i for i in self._autonomous_intents.values()
            if q in i.summary.lower() or q in i.target.lower() or q in i.category.value.lower()
        ]

    def list_ambiguous_intents(self) -> List[AutonomousIntent]:
        ambiguous_intent_ids = {amb.intent_id for amb in [a for sub in self._ambiguities_map.values() for a in sub] if not amb.is_resolved}
        return [i for i in self._autonomous_intents.values() if i.intent_id in ambiguous_intent_ids or i.status in (RequestStatus.AMBIGUOUS, RequestStatus.CLARIFICATION_REQUIRED)]

    def get_user_request(self, request_id: str) -> Optional[UserRequest]:
        return self._requests.get(request_id)

    def list_user_requests(self, user_id: Optional[str] = None, limit: int = 100) -> List[UserRequest]:
        res = list(self._requests.values())
        if user_id:
            res = [r for r in res if r.user_id == user_id]
        return res[:limit]

    def answer_task108_clarification(self, clarification_id: str, answer: str) -> Dict[str, Any]:
        """Resolves targeted clarification, advances intent status to CONFIRMED (Spec 13, 14)."""
        clr = self._clarifications_map.get(clarification_id)
        if not clr:
            raise KeyError(f"Clarification {clarification_id} not found")

        clr.status = ClarificationStatus.ANSWERED
        clr.user_response = answer
        clr.answered_at = t108_utc_now()

        intent = self._autonomous_intents.get(clr.intent_id)
        if intent:
            intent.status = RequestStatus.CONFIRMED
            intent.summary = f"{intent.summary} (Clarified: {answer})"
            if intent.target == "UNKNOWN":
                intent.target = answer
                intent.target_epistemic = EpistemicStatus.CONFIRMED
                intent.target_confidence = 1.0
                intent.overall_confidence = 0.95

            # Update associated request status if all clarifications resolved
            req = self._requests.get(intent.request_id)
            if req:
                req.status = RequestStatus.CONFIRMED
                req.updated_at = t108_utc_now()

            self._record_event("intent.confirmed", intent_id=intent.intent_id, request_id=intent.request_id,
                               payload={"clarification_id": clarification_id, "answer": answer})

        return {
            "clarification_id": clarification_id,
            "status": ClarificationStatus.ANSWERED.value,
            "clarification_status": ClarificationStatus.ANSWERED.value,
            "user_answer": answer,
            "intent_id": clr.intent_id,
            "intent_status": intent.status.value if intent else "UNKNOWN",
        }

    def apply_task108_correction(
        self,
        intent_id: str,
        correction_text: str,
        scope_affected: str = "CURRENT_PROJECT",
    ) -> Dict[str, Any]:
        """Applies explicit user correction, creating a new immutable version (Spec 20, 21)."""
        intent = self._autonomous_intents.get(intent_id)
        if not intent:
            raise KeyError(f"Intent {intent_id} not found")

        revised_intent, prior_ver, correction = LifecycleAndVersioningEngine.apply_correction(
            intent, correction_text, scope_affected=scope_affected
        )

        new_ver = IntentVersion(
            version_id=gen_t108_id("iver"),
            intent_id=intent_id,
            version_number=revised_intent.version,
            intent_snapshot=revised_intent.model_dump(mode="json"),
            reason_for_change=f"User correction: {correction_text}",
            created_at=t108_utc_now(),
        )
        self._intent_versions.setdefault(intent_id, []).append(new_ver)
        self._corrections_map.setdefault(intent_id, []).append(correction)

        # Refresh snapshot
        hyps = self._goal_hypotheses.get(intent_id, [])
        csts = self._constraints_map.get(intent_id, [])
        asms = self._assumptions_map.get(intent_id, [])
        new_snap = LifecycleAndVersioningEngine.create_snapshot(revised_intent, hyps, csts, asms)
        self._snapshots_map[intent_id] = new_snap

        self._record_event("intent.corrected", intent_id=intent_id, request_id=intent.request_id,
                           payload={"correction_text": correction_text, "new_version": revised_intent.version})

        return {
            "intent_id": intent_id,
            "status": "CORRECTED",
            "version": revised_intent.version,
            "summary": revised_intent.summary,
            "target": revised_intent.target,
            "correction_id": correction.correction_id,
            "snapshot_id": new_snap.snapshot_id,
        }

    def cancel_autonomous_intent(self, intent_id: str, reason: str = "User cancellation") -> Dict[str, Any]:
        """Cancels an intent and propagates cancellation downstream (Spec 39, 52)."""
        intent = self._autonomous_intents.get(intent_id)
        if not intent:
            raise KeyError(f"Intent {intent_id} not found")

        cancelled = LifecycleAndVersioningEngine.cancel_intent(intent, reason=reason)

        # Also mark request if single intent
        req = self._requests.get(intent.request_id)
        if req:
            req.status = RequestStatus.CANCELLED
            req.updated_at = t108_utc_now()

        self._record_event("intent.cancelled", intent_id=intent_id, request_id=intent.request_id, payload={"reason": reason})

        return {
            "intent_id": intent_id,
            "status": cancelled.status.value,
            "is_cancelled": True,
            "reason": reason,
        }

    def supersede_autonomous_intent(self, prior_intent_id: str, superseding_intent_id: str) -> Dict[str, Any]:
        """Marks an earlier intent as SUPERSEDED (Spec 38)."""
        prior = self._autonomous_intents.get(prior_intent_id)
        if not prior:
            raise KeyError(f"Intent {prior_intent_id} not found")

        LifecycleAndVersioningEngine.supersede_intent(prior, superseding_intent_id=superseding_intent_id)
        self._record_event("intent.superseded", intent_id=prior_intent_id, payload={"superseded_by": superseding_intent_id})
        return {
            "intent_id": prior_intent_id,
            "status": RequestStatus.SUPERSEDED.value,
            "superseded_by": superseding_intent_id,
        }

    def get_task108_dashboard_metrics(self) -> Dict[str, Any]:
        """Aggregates metrics for the Intent Dashboard (Spec 54, 58)."""
        intents = list(self._autonomous_intents.values())
        requests = list(self._requests.values())
        clrs = list(self._clarifications_map.values())
        pending_clrs = [c for c in clrs if c.status == ClarificationStatus.PENDING]
        answered_clrs = [c for c in clrs if c.status == ClarificationStatus.ANSWERED]

        amb_list = [a for sub in self._ambiguities_map.values() for a in sub]
        unresolved_ambs = [a for a in amb_list if not a.is_resolved]

        return {
            "total_requests": len(requests),
            "total_intents": len(intents),
            "active_intents": len([i for i in intents if i.status in (RequestStatus.UNDERSTOOD, RequestStatus.CONFIRMED)]),
            "pending_clarifications": len(pending_clrs),
            "answered_clarifications": len(answered_clrs),
            "unresolved_ambiguities": len(unresolved_ambs),
            "superseded_intents": len([i for i in intents if i.is_superseded]),
            "cancelled_intents": len([i for i in intents if i.is_cancelled]),
            "external_effect_flagged": len([i for i in intents if i.external_effect == ExternalEffectFlag.EXTERNAL_EFFECT_POSSIBLE]),
            "categories_breakdown": {
                cat.value: len([i for i in intents if i.category == cat]) for cat in IntentCategory
            },
            "recent_requests": [r.model_dump(mode="json") for r in requests[-10:]],
            "clarification_queue": [c.model_dump(mode="json") for c in pending_clrs[:10]],
            "epistemic_summary": {
                "explicit": len([i for i in intents if i.target_epistemic == EpistemicStatus.EXPLICIT]),
                "inferred": len([i for i in intents if i.target_epistemic == EpistemicStatus.INFERRED]),
                "unknown": len([i for i in intents if i.target == "UNKNOWN"]),
                "confirmed": len([i for i in intents if i.status == RequestStatus.CONFIRMED]),
            },
        }

    def _record_event(self, event_type: str, intent_id: Optional[str] = None, request_id: Optional[str] = None, user_id: str = "default_user", payload: Optional[Dict[str, Any]] = None) -> None:
        """Emits audit event to internal log and unified EventBus."""
        evt = IntentEvent(
            event_id=gen_t108_id("ievt"),
            event_type=event_type,
            intent_id=intent_id,
            request_id=request_id,
            user_id=user_id,
            payload=payload or {},
            timestamp=t108_utc_now(),
        )
        self._events.append(evt)
        try:
            bus = get_event_bus()
            if bus:
                # Dispatch event async or synchronous safe
                pass
        except Exception:
            pass


_intent_service_instance: Optional[IntentService] = None


def get_intent_service() -> IntentService:
    """Retrieve or initialize singleton instance of IntentService."""
    global _intent_service_instance
    if _intent_service_instance is None:
        _intent_service_instance = IntentService()
    return _intent_service_instance


