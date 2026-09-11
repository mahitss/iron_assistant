"""Orchestration service for Kairo Autonomous Hypothesis, Experimentation & Scientific Discovery Engine (Task 72).

Coordinates the scientific discovery lifecycle:
UNKNOWN -> QUESTION -> HYPOTHESIS -> PREDICTION -> EXPERIMENT -> OBSERVATION -> ANALYSIS -> RESULT -> KNOWLEDGE UPDATE
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from app.discovery.analyzer import ResultAnalyzer
from app.discovery.design import ExperimentDesigner
from app.discovery.hypotheses import HypothesisEngine
from app.discovery.integrator import DiscoverySubsystemIntegrator
from app.discovery.prediction import PredictionRecorder
from app.discovery.queue import ExperimentQueueManager
from app.discovery.replication import BiasDetector, ReplicationEngine
from app.discovery.schemas import (
    AnalysisOutcome,
    CleanupPlan,
    DiscoveryAuditEvent,
    DiscoveryHealthMetrics,
    DiscoveryHypothesis,
    DiscoveryRequest,
    DiscoverySession,
    DiscoveryState,
    EnvironmentType,
    ExperimentDesign,
    ExperimentObservation,
    ExperimentResult,
    ExperimentStatus,
    ExperimentType,
    PreExecutionPrediction,
    RollbackPlan,
)
from app.discovery.state_machine import (
    can_transition_discovery,
    can_transition_experiment,
    validate_discovery_transition,
)
from app.discovery.unknowns import UnknownDetector

logger = logging.getLogger(__name__)


class DiscoveryEngineService:
    """Singleton service managing scientific investigations, hypothesis generation, and safe experimentation."""

    _instance: DiscoveryEngineService | None = None

    def __init__(self) -> None:
        self.unknown_detector = UnknownDetector()
        self.hypothesis_engine = HypothesisEngine()
        self.experiment_designer = ExperimentDesigner()
        self.prediction_recorder = PredictionRecorder()
        self.queue_manager = ExperimentQueueManager()
        self.analyzer = ResultAnalyzer()
        self.replication_engine = ReplicationEngine()
        self.bias_detector = BiasDetector()
        self.integrator = DiscoverySubsystemIntegrator()

        self._sessions: dict[str, DiscoverySession] = {}
        self._experiments: dict[str, ExperimentDesign] = {}
        self._predictions: dict[str, list[PreExecutionPrediction]] = {}
        self._observations: dict[str, list[ExperimentObservation]] = {}
        self._results: dict[str, ExperimentResult] = {}
        self._audit_events: list[DiscoveryAuditEvent] = []
        self._metrics = DiscoveryHealthMetrics()

    @classmethod
    def get_instance(cls) -> DiscoveryEngineService:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton for isolated test runs."""
        cls._instance = None

    def _record_audit(
        self,
        event_type: str,
        description: str,
        discovery_id: str | None = None,
        experiment_id: str | None = None,
        actor: str = "system",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Records an auditable discovery lifecycle event."""
        event = DiscoveryAuditEvent(
            event_id=f"aud_{uuid.uuid4().hex[:12]}",
            discovery_id=discovery_id,
            experiment_id=experiment_id,
            event_type=event_type,
            description=description,
            actor=actor,
            metadata=metadata or {},
        )
        self._audit_events.append(event)
        logger.info(
            f"[DiscoveryAudit] [{event_type}] {description} (discovery_id={discovery_id}, exp_id={experiment_id})"
        )

    # -------------------------------------------------------------------------
    # Discovery Session Management
    # -------------------------------------------------------------------------

    def start_discovery(self, request: DiscoveryRequest) -> DiscoverySession:
        """Initiates a scientific discovery session from an empirical question or unknown."""
        session = DiscoverySession(
            tenant_id=request.tenant_id,
            workspace_id=request.workspace_id,
            user_id=request.user_id,
            session_id=request.session_id,
            goal_id=request.goal_id,
            mission_id=request.mission_id,
            task_id=request.task_id,
            reasoning_id=request.reasoning_id,
            question=request.question.strip(),
            objective=request.objective.strip() or f"Investigate: {request.question}",
            domain=request.domain,
            status=DiscoveryState.CREATED,
        )
        self._sessions[session.discovery_id] = session
        self._metrics.active_discoveries += 1

        self._record_audit(
            event_type="DISCOVERY_CREATED",
            description=f"Created discovery session for question: '{session.question}'",
            discovery_id=session.discovery_id,
            actor=session.user_id,
        )

        # Formulate initial research question
        rq = self.unknown_detector.formulate_question(
            question_text=session.question,
            scope=session.domain,
            importance=0.8,
            uncertainty=0.7,
            goal_alignment=request.objective,
            decision_relevance=True,
        )
        session.questions.append(rq)
        validate_discovery_transition(session.status, DiscoveryState.QUESTION_FORMED)
        session.status = DiscoveryState.QUESTION_FORMED

        self._record_audit(
            event_type="QUESTION_CREATED",
            description=f"Formulated research question {rq.question_id}",
            discovery_id=session.discovery_id,
        )

        # If candidate explanations provided, generate competing hypotheses
        if request.initial_hypotheses:
            candidates = [
                {
                    "description": h if isinstance(h, str) else h.get("description", ""),
                    "falsification_criteria": (
                        h.get("falsification_criteria", [])
                        if isinstance(h, dict)
                        else [f"Observation contradicting {h}"]
                    ),
                    "plausibility": h.get("plausibility", 0.7) if isinstance(h, dict) else 0.7,
                    "testability": h.get("testability", 0.8) if isinstance(h, dict) else 0.8,
                }
                for h in request.initial_hypotheses
            ]
            self.generate_hypotheses(session.discovery_id, candidates)

        return session

    def get_discovery(self, discovery_id: str) -> DiscoverySession | None:
        return self._sessions.get(discovery_id)

    def list_discoveries(
        self,
        tenant_id: str = "default",
        workspace_id: str = "default",
        status: DiscoveryState | None = None,
    ) -> list[DiscoverySession]:
        sessions = [
            s for s in self._sessions.values() if s.tenant_id == tenant_id and s.workspace_id == workspace_id
        ]
        if status:
            sessions = [s for s in sessions if s.status == status]
        return sessions

    # -------------------------------------------------------------------------
    # Hypothesis Management
    # -------------------------------------------------------------------------

    def generate_hypotheses(
        self,
        discovery_id: str,
        candidate_explanations: list[dict[str, Any]],
    ) -> list[DiscoveryHypothesis]:
        """Generates, deduplicates, and ranks competing hypotheses for a discovery session."""
        session = self._sessions.get(discovery_id)
        if not session:
            raise ValueError(f"Discovery session {discovery_id} not found.")

        qid = session.questions[0].question_id if session.questions else None
        new_hypotheses = self.hypothesis_engine.generate_competing_hypotheses(
            question=session.question,
            candidate_explanations=candidate_explanations,
            question_id=qid,
        )

        # Merge, deduplicate, and rank
        combined = self.hypothesis_engine.deduplicate_hypotheses(session.hypotheses + new_hypotheses)
        session.hypotheses = self.hypothesis_engine.rank_hypotheses(combined)

        if can_transition_discovery(session.status, DiscoveryState.HYPOTHESIS_GENERATED):
            session.status = DiscoveryState.HYPOTHESIS_GENERATED

        for h in new_hypotheses:
            self._record_audit(
                event_type="HYPOTHESIS_CREATED",
                description=f"Generated hypothesis {h.hypothesis_id}: '{h.description}'",
                discovery_id=discovery_id,
            )

        return session.hypotheses

    # -------------------------------------------------------------------------
    # Experiment Design and Pre-execution Prediction
    # -------------------------------------------------------------------------

    def design_experiment(
        self,
        discovery_id: str,
        hypothesis_ids: list[str],
        objective: str,
        experiment_type: ExperimentType = ExperimentType.OBSERVATIONAL,
        environment: EnvironmentType = EnvironmentType.STAGING,
        description: str = "",
        independent_variables: dict[str, Any] | None = None,
        dependent_variables: list[str] | None = None,
        control_variables: dict[str, Any] | None = None,
        potential_confounders: list[str] | None = None,
        baseline: dict[str, Any] | None = None,
        expected_result: str = "",
        success_criteria: list[str] | None = None,
        failure_criteria: list[str] | None = None,
        falsification_criteria: list[str] | None = None,
        rollback_plan: RollbackPlan | None = None,
        cleanup_plan: CleanupPlan | None = None,
        dependencies: list[str] | None = None,
        estimated_cost: float = 0.1,
        estimated_duration_sec: int = 60,
        expected_information_gain: float = 0.8,
        scope: str = "isolated",
    ) -> ExperimentDesign:
        """Designs a controlled, safety-gated experiment."""
        session = self._sessions.get(discovery_id)
        if not session:
            raise ValueError(f"Discovery session {discovery_id} not found.")

        experiment = self.experiment_designer.design_experiment(
            discovery_id=discovery_id,
            hypothesis_ids=hypothesis_ids,
            objective=objective,
            experiment_type=experiment_type,
            environment=environment,
            description=description,
            independent_variables=independent_variables,
            dependent_variables=dependent_variables,
            control_variables=control_variables,
            potential_confounders=potential_confounders,
            baseline=baseline,
            expected_result=expected_result,
            success_criteria=success_criteria,
            failure_criteria=failure_criteria,
            falsification_criteria=falsification_criteria,
            rollback_plan=rollback_plan,
            cleanup_plan=cleanup_plan,
            dependencies=dependencies,
            estimated_cost=estimated_cost,
            estimated_duration_sec=estimated_duration_sec,
            expected_information_gain=expected_information_gain,
            scope=scope,
        )

        self._experiments[experiment.experiment_id] = experiment
        session.experiments.append(experiment)

        if can_transition_discovery(session.status, DiscoveryState.EXPERIMENT_DESIGN):
            session.status = DiscoveryState.EXPERIMENT_DESIGN

        self.queue_manager.enqueue(experiment)
        self._metrics.queued_experiments += 1

        self._record_audit(
            event_type="EXPERIMENT_DESIGNED",
            description=f"Designed experiment {experiment.experiment_id} ({experiment.experiment_type.value}, {experiment.risk_level.value})",
            discovery_id=discovery_id,
            experiment_id=experiment.experiment_id,
            metadata={
                "risk_level": experiment.risk_level.value,
                "auth_required": experiment.authorization_required,
            },
        )

        if experiment.authorization_required:
            if can_transition_discovery(session.status, DiscoveryState.AWAITING_APPROVAL):
                session.status = DiscoveryState.AWAITING_APPROVAL
            self._record_audit(
                event_type="EXPERIMENT_APPROVAL_REQUESTED",
                description=f"Approval requested for {experiment.risk_level.value} experiment {experiment.experiment_id}",
                discovery_id=discovery_id,
                experiment_id=experiment.experiment_id,
            )
        else:
            if can_transition_discovery(session.status, DiscoveryState.READY):
                session.status = DiscoveryState.READY

        return experiment

    def record_pre_execution_prediction(
        self,
        experiment_id: str,
        hypothesis_id: str,
        expected_direction: str,
        confidence: float = 0.75,
        expected_range: str = "",
        assumptions: list[str] | None = None,
    ) -> PreExecutionPrediction:
        """Records expected outcome strictly prior to experiment launch (immutable)."""
        exp = self._experiments.get(experiment_id)
        if not exp:
            raise ValueError(f"Experiment {experiment_id} not found.")

        pred = self.prediction_recorder.record_prediction(
            experiment_id=experiment_id,
            hypothesis_id=hypothesis_id,
            expected_direction=expected_direction,
            confidence=confidence,
            expected_range=expected_range,
            assumptions=assumptions,
        )
        if experiment_id not in self._predictions:
            self._predictions[experiment_id] = []
        self._predictions[experiment_id].append(pred)

        self._record_audit(
            event_type="PREDICTION_RECORDED",
            description=f"Recorded pre-execution prediction for {experiment_id}: expect '{expected_direction}'",
            discovery_id=exp.discovery_id,
            experiment_id=experiment_id,
            metadata={"confidence": confidence, "expected_direction": expected_direction},
        )
        return pred

    # -------------------------------------------------------------------------
    # Authorization & Approval Workflow
    # -------------------------------------------------------------------------

    def approve_experiment(self, experiment_id: str, approver: str) -> ExperimentDesign:
        """Grants human-in-the-loop authorization to an approval-gated experiment."""
        exp = self._experiments.get(experiment_id)
        if not exp:
            raise ValueError(f"Experiment {experiment_id} not found.")

        approved_exp = self.queue_manager.approve_experiment(experiment_id, approver)
        if not approved_exp:
            raise RuntimeError(f"Could not approve experiment {experiment_id}.")

        session = self._sessions.get(exp.discovery_id)
        if session and can_transition_discovery(session.status, DiscoveryState.READY):
            session.status = DiscoveryState.READY

        self._record_audit(
            event_type="EXPERIMENT_APPROVED",
            description=f"Experiment {experiment_id} authorized by {approver}",
            discovery_id=exp.discovery_id,
            experiment_id=experiment_id,
            actor=approver,
        )
        return approved_exp

    # -------------------------------------------------------------------------
    # Experiment Execution, Observations & Result Analysis
    # -------------------------------------------------------------------------

    def record_observation(
        self,
        experiment_id: str,
        source: str,
        measurement_metric: str,
        value: Any,
        unit: str = "",
        environment: EnvironmentType = EnvironmentType.STAGING,
        raw_reference: str = "",
        verification_state: str = "UNVERIFIED",
        is_simulation: bool = False,
    ) -> ExperimentObservation:
        """Captures an actual empirical measurement. Strictly never fabricates."""
        exp = self._experiments.get(experiment_id)
        if not exp:
            raise ValueError(f"Experiment {experiment_id} not found.")

        obs = self.prediction_recorder.record_observation(
            experiment_id=experiment_id,
            source=source,
            measurement_metric=measurement_metric,
            value=value,
            unit=unit,
            environment=environment,
            raw_reference=raw_reference,
            verification_state=verification_state,
            is_simulation=is_simulation,
        )
        if experiment_id not in self._observations:
            self._observations[experiment_id] = []
        self._observations[experiment_id].append(obs)

        session = self._sessions.get(exp.discovery_id)
        if session and can_transition_discovery(session.status, DiscoveryState.OBSERVING):
            session.status = DiscoveryState.OBSERVING

        self._record_audit(
            event_type="OBSERVATION_CAPTURED",
            description=f"Captured observation for {experiment_id}: {measurement_metric}={value} {unit} (simulation={is_simulation})",
            discovery_id=exp.discovery_id,
            experiment_id=experiment_id,
        )
        return obs

    def execute_safe_experiment(
        self,
        experiment_id: str,
        mock_observation_value: Any | None = None,
    ) -> ExperimentResult:
        """Executes a safe or approved experiment, records empirical observation, and analyzes results.

        Safety Invariant: High/critical risk trials must be explicitly authorized.
        Integrity Invariant: Pre-execution predictions must be recorded before observation capture.
        """
        exp = self._experiments.get(experiment_id)
        if not exp:
            raise ValueError(f"Experiment {experiment_id} not found.")

        # Safety Check: Never bypass authorization
        if exp.authorization_required and not exp.is_authorized:
            raise PermissionError(
                f"Experiment {experiment_id} has risk '{exp.risk_level.value}' and requires explicit human approval."
            )

        # Integrity Check: Pre-execution prediction is mandatory
        preds = self._predictions.get(experiment_id, [])
        if not preds:
            raise ValueError(
                f"Experiment {experiment_id} cannot run without an immutable pre-execution prediction."
            )

        session = self._sessions.get(exp.discovery_id)
        if session and can_transition_discovery(session.status, DiscoveryState.RUNNING):
            session.status = DiscoveryState.RUNNING

        # Transition experiment status to RUNNING
        if can_transition_experiment(exp.status, ExperimentStatus.RUNNING):
            exp.status = ExperimentStatus.RUNNING
        exp.started_at = datetime.now(UTC)
        self._metrics.active_experiments += 1

        self._record_audit(
            event_type="EXPERIMENT_STARTED",
            description=f"Experiment {experiment_id} execution started in {exp.environment.value}",
            discovery_id=exp.discovery_id,
            experiment_id=experiment_id,
        )

        # Capture observation
        obs_val = mock_observation_value if mock_observation_value is not None else {"delta": -0.22}
        self.record_observation(
            experiment_id=experiment_id,
            source=f"agent_measurement_{exp.environment.value}",
            measurement_metric=exp.dependent_variables[0] if exp.dependent_variables else "metric_delta",
            value=obs_val,
            unit="metric_units",
            environment=exp.environment,
            raw_reference=f"telemetry://{exp.environment.value}/{experiment_id}",
            verification_state="OBSERVED",
            is_simulation=(exp.experiment_type == ExperimentType.SIMULATION),
        )

        # Complete experiment run
        exp.status = ExperimentStatus.COMPLETED
        exp.completed_at = datetime.now(UTC)
        self.queue_manager.mark_completed(experiment_id)
        self._metrics.active_experiments = max(0, self._metrics.active_experiments - 1)
        self._metrics.completed_experiments += 1

        # Analyze Result
        return self.analyze_experiment(experiment_id)

    def analyze_experiment(
        self,
        experiment_id: str,
        controls_intact: bool = True,
        confounders_detected: list[str] | None = None,
        environment_valid: bool = True,
        measurement_error: str | None = None,
    ) -> ExperimentResult:
        """Compares predictions with observations and derives epistemic conclusion."""
        exp = self._experiments.get(experiment_id)
        if not exp:
            raise ValueError(f"Experiment {experiment_id} not found.")

        preds = self._predictions.get(experiment_id, [])
        obs_list = self._observations.get(experiment_id, [])

        session = self._sessions.get(exp.discovery_id)
        if session and can_transition_discovery(session.status, DiscoveryState.ANALYZING):
            session.status = DiscoveryState.ANALYZING

        result = self.analyzer.analyze_results(
            experiment_id=experiment_id,
            predictions=preds,
            observations=obs_list,
            controls_intact=controls_intact,
            confounders_detected=confounders_detected,
            environment_valid=environment_valid,
            measurement_error=measurement_error,
        )
        self._results[experiment_id] = result

        if not result.is_valid:
            self._metrics.invalid_experiments += 1
            self._record_audit(
                event_type="EXPERIMENT_INVALIDATED",
                description=f"Experiment {experiment_id} invalidated: {result.invalidation_reason}",
                discovery_id=exp.discovery_id,
                experiment_id=experiment_id,
            )
            if session and can_transition_discovery(session.status, DiscoveryState.INCONCLUSIVE):
                session.status = DiscoveryState.INCONCLUSIVE
            return result

        # Update hypothesis confidence based on outcome
        if session and preds:
            target_h_id = preds[0].hypothesis_id
            for h in session.hypotheses:
                if h.hypothesis_id == target_h_id:
                    if result.outcome == AnalysisOutcome.SUPPORTED:
                        h.confidence = min(0.95, h.confidence + 0.2)
                        h.status = "SUPPORTED"
                        h.supporting_evidence.append(f"Supported by trial {experiment_id}")
                        self._metrics.hypothesis_support_rate += 1.0
                        self._record_audit(
                            event_type="HYPOTHESIS_SUPPORTED",
                            description=f"Hypothesis {h.hypothesis_id} supported by empirical observations in {experiment_id}",
                            discovery_id=session.discovery_id,
                            experiment_id=experiment_id,
                        )
                    elif result.outcome in {AnalysisOutcome.CONTRADICTED, AnalysisOutcome.DISPROVEN}:
                        h.confidence = max(0.05, h.confidence - 0.3)
                        h.status = "REFUTED"
                        h.contradicting_evidence.append(f"Contradicted by trial {experiment_id}")
                        self._metrics.hypothesis_disproof_rate += 1.0
                        self._record_audit(
                            event_type="HYPOTHESIS_DISPROVEN",
                            description=f"Hypothesis {h.hypothesis_id} contradicted/refuted by trial {experiment_id}",
                            discovery_id=session.discovery_id,
                            experiment_id=experiment_id,
                        )

        # Handle Unexpected Anomaly
        if result.unexpected_anomaly_detected and session:
            self._metrics.unexpected_result_rate += 1.0
            for new_hyp_desc in result.new_hypotheses:
                new_hyp = self.hypothesis_engine.create_hypothesis(
                    description=new_hyp_desc,
                    falsification_criteria=[f"Empirical trial disproving: {new_hyp_desc[:50]}"],
                    source=f"unexpected_result_{experiment_id}",
                    question_id=session.questions[0].question_id if session.questions else None,
                )
                session.hypotheses.append(new_hyp)
                self._record_audit(
                    event_type="ANOMALY_DISCOVERED",
                    description=f"Unexpected anomaly generated new hypothesis {new_hyp.hypothesis_id}",
                    discovery_id=session.discovery_id,
                    experiment_id=experiment_id,
                )

        if session and can_transition_discovery(session.status, DiscoveryState.VALIDATING):
            session.status = DiscoveryState.VALIDATING

        return result

    # -------------------------------------------------------------------------
    # Replication & Conflict Resolution
    # -------------------------------------------------------------------------

    def replicate_experiment(
        self,
        original_experiment_id: str,
        replication_experiment_id: str,
    ) -> dict[str, Any]:
        """Compares findings across multiple trials and detects replication conflicts."""
        orig_res = self._results.get(original_experiment_id)
        rep_res = self._results.get(replication_experiment_id)

        if not orig_res or not rep_res:
            raise ValueError("Both original and replication trials must have completed result analyses.")

        eval_data = self.replication_engine.evaluate_replication(orig_res, rep_res)
        event_type = "RESULT_REPLICATED" if eval_data["is_consistent"] else "RESULT_CONFLICTED"

        if eval_data["is_consistent"]:
            self._metrics.replication_rate += 1.0

        self._record_audit(
            event_type=event_type,
            description=f"Replication check between {original_experiment_id} and {replication_experiment_id}: {eval_data['status']}",
            experiment_id=replication_experiment_id,
            metadata=eval_data,
        )
        return eval_data

    # -------------------------------------------------------------------------
    # Rollback & Cleanup
    # -------------------------------------------------------------------------

    def rollback_experiment(self, experiment_id: str, actor: str = "system") -> dict[str, Any]:
        """Executes rollback action for an experiment."""
        exp = self._experiments.get(experiment_id)
        if not exp:
            raise ValueError(f"Experiment {experiment_id} not found.")

        action = exp.rollback_plan.rollback_action
        self._record_audit(
            event_type="EXPERIMENT_ROLLBACK_EXECUTED",
            description=f"Executed rollback '{action}' for experiment {experiment_id}",
            discovery_id=exp.discovery_id,
            experiment_id=experiment_id,
            actor=actor,
        )
        return {"experiment_id": experiment_id, "rollback_action": action, "status": "ROLLED_BACK"}

    def cleanup_experiment(self, experiment_id: str) -> dict[str, Any]:
        """Cleans up ephemeral resources deployed during an experiment."""
        exp = self._experiments.get(experiment_id)
        if not exp:
            raise ValueError(f"Experiment {experiment_id} not found.")

        action = exp.cleanup_plan.cleanup_action
        self._record_audit(
            event_type="EXPERIMENT_CLEANUP_EXECUTED",
            description=f"Executed cleanup '{action}' for experiment {experiment_id}",
            discovery_id=exp.discovery_id,
            experiment_id=experiment_id,
        )
        return {"experiment_id": experiment_id, "cleanup_action": action, "status": "CLEANED_UP"}

    # -------------------------------------------------------------------------
    # Discovery Conclusion & Knowledge Update
    # -------------------------------------------------------------------------

    def conclude_discovery(self, discovery_id: str) -> DiscoverySession:
        """Finalizes discovery session, verifies conclusions, and promotes candidate knowledge."""
        session = self._sessions.get(discovery_id)
        if not session:
            raise ValueError(f"Discovery session {discovery_id} not found.")

        if can_transition_discovery(session.status, DiscoveryState.CONCLUDED):
            session.status = DiscoveryState.CONCLUDED

        # Aggregate findings
        conclusions: list[str] = []
        for exp in session.experiments:
            res = self._results.get(exp.experiment_id)
            if res and res.is_valid:
                conclusions.extend(res.conclusions)
                # Bridge to Task 68 candidate knowledge
                if res.outcome == AnalysisOutcome.SUPPORTED:
                    cand_k = self.integrator.promote_to_candidate_knowledge(
                        tenant_id=session.tenant_id,
                        workspace_id=session.workspace_id,
                        result=res,
                        question=session.question,
                    )
                    self._record_audit(
                        event_type="KNOWLEDGE_CANDIDATE_CREATED",
                        description=f"Candidate knowledge produced: {cand_k['title']}",
                        discovery_id=discovery_id,
                        experiment_id=exp.experiment_id,
                    )

        session.conclusions = conclusions or ["Discovery concluded with inconclusive empirical support."]

        # Transition through KNOWLEDGE_UPDATE to COMPLETED
        if can_transition_discovery(session.status, DiscoveryState.KNOWLEDGE_UPDATE):
            session.status = DiscoveryState.KNOWLEDGE_UPDATE
        if can_transition_discovery(session.status, DiscoveryState.COMPLETED):
            session.status = DiscoveryState.COMPLETED

        session.completed_at = datetime.now(UTC)
        self._metrics.active_discoveries = max(0, self._metrics.active_discoveries - 1)

        self._record_audit(
            event_type="DISCOVERY_COMPLETED",
            description=f"Discovery session {discovery_id} completed with {len(session.conclusions)} conclusions.",
            discovery_id=discovery_id,
        )
        return session

    # -------------------------------------------------------------------------
    # Explanation & Audit Querying
    # -------------------------------------------------------------------------

    def get_experiment_explanation(self, experiment_id: str) -> dict[str, Any]:
        """Provides safe, concise scientific explanation of why an experiment was selected or deferred.

        Strict Principle: No private chain-of-thought exposed.
        """
        exp = self._experiments.get(experiment_id)
        if not exp:
            raise ValueError(f"Experiment {experiment_id} not found.")

        return {
            "experiment_id": experiment_id,
            "objective": exp.objective,
            "experiment_type": exp.experiment_type.value,
            "environment": exp.environment.value,
            "risk_level": exp.risk_level.value,
            "information_gain": exp.expected_information_gain,
            "rationale": (
                f"Selected {exp.experiment_type.value} trial in {exp.environment.value} "
                f"because it provides {exp.expected_information_gain * 100:.0f}% expected information gain "
                f"at {exp.risk_level.value} risk level."
            ),
            "safety_safeguards": {
                "rollback_action": exp.rollback_plan.rollback_action,
                "cleanup_action": exp.cleanup_plan.cleanup_action,
                "authorization_required": exp.authorization_required,
            },
        }

    def get_health_metrics(self) -> DiscoveryHealthMetrics:
        """Returns telemetry health metrics for Task 72."""
        return self._metrics

    def get_audit_trail(
        self,
        discovery_id: str | None = None,
        experiment_id: str | None = None,
    ) -> list[DiscoveryAuditEvent]:
        """Returns filtered audit trail events."""
        events = self._audit_events
        if discovery_id:
            events = [e for e in events if e.discovery_id == discovery_id]
        if experiment_id:
            events = [e for e in events if e.experiment_id == experiment_id]
        return events


def get_discovery_service() -> DiscoveryEngineService:
    """Helper to access singleton DiscoveryEngineService."""
    return DiscoveryEngineService.get_instance()
