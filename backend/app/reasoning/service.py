"""Main orchestration service for Kairo Autonomous Reasoning & Deliberation Engine (Task 71).

Coordinates:
- Structured problem decomposition (DAG depth <= 3)
- Hypothesis generation, falsification tests, and counterarguments
- Evidence evaluation, conflict detection, and source independence
- Dynamic assumption tracking and invalidation cascades
- Alternative generation and tradeoff matrix
- Bounded deliberation and cognitive budgeting
- Verification gating and safe, concise user-facing explanations (strictly no private chain-of-thought)
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from app.reasoning.assumptions import AssumptionTracker
from app.reasoning.budget import BudgetCoordinator
from app.reasoning.decomposer import ProblemDecomposer
from app.reasoning.deliberation import DeliberationEngine
from app.reasoning.evidence import EvidenceEvaluator
from app.reasoning.falsification import FalsificationEngine
from app.reasoning.graph import ReasoningGraphBuilder
from app.reasoning.hypotheses import HypothesisGenerator
from app.reasoning.integrator import ReasoningSubsystemIntegrator
from app.reasoning.schemas import (
    AssumptionStatus,
    ReasoningConclusion,
    ReasoningConfidence,
    ReasoningDepth,
    ReasoningEvidence,
    ReasoningHealthMetrics,
    ReasoningRequest,
    ReasoningSession,
    ReasoningState,
    ReasoningTraceEvent,
    UncertaintyType,
)
from app.reasoning.state_machine import ReasoningStateMachine

logger = logging.getLogger(__name__)


class ReasoningEngineService:
    """Singleton service driving autonomous deliberation workflows."""

    _instance: ReasoningEngineService | None = None

    def __init__(self) -> None:
        self.state_machine = ReasoningStateMachine()
        self.decomposer = ProblemDecomposer()
        self.hypothesis_gen = HypothesisGenerator()
        self.evidence_eval = EvidenceEvaluator()
        self.deliberator = DeliberationEngine()
        self.falsifier = FalsificationEngine()
        self.budget_coord = BudgetCoordinator()
        self.integrator = ReasoningSubsystemIntegrator()

        self._sessions: dict[str, ReasoningSession] = {}
        self._assumption_trackers: dict[str, AssumptionTracker] = {}

        # Telemetry metrics
        self._metrics = ReasoningHealthMetrics()
        self._latencies: list[float] = []

    @classmethod
    def get_instance(cls) -> ReasoningEngineService:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton for isolated unit test runs."""
        cls._instance = None

    def _record_trace(
        self,
        session: ReasoningSession,
        phase: ReasoningState,
        action: str,
        description: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record an auditable milestone event (strictly no private chain-of-thought)."""
        event = ReasoningTraceEvent(
            phase=phase,
            action=action,
            description=description,
            metadata=metadata or {},
        )
        session.trace_events.append(event)
        logger.info(f"[{session.reasoning_id}] [{phase.value}] {action}: {description}")

    def start_session(self, request: ReasoningRequest) -> ReasoningSession:
        """Execute autonomous deliberation from initiation through completion."""
        start_time = datetime.now(UTC)
        budget = request.budget or self.budget_coord.initialize_budget(request.depth)

        session = ReasoningSession(
            tenant_id=request.tenant_id,
            workspace_id=request.workspace_id,
            user_id=request.user_id,
            session_id=request.session_id,
            task_id=request.task_id,
            goal_id=request.goal_id,
            mission_id=request.mission_id,
            attention_id=request.attention_id,
            question=request.question,
            objective=request.objective or request.question,
            intent=request.intent,
            depth=request.depth,
            current_state=ReasoningState.CREATED,
            budget=budget,
        )
        self._sessions[session.reasoning_id] = session
        asm_tracker = AssumptionTracker()
        self._assumption_trackers[session.reasoning_id] = asm_tracker

        self._record_trace(
            session,
            ReasoningState.CREATED,
            "SESSION_INITIALIZED",
            f"Deliberation session initialized for question: '{request.question}'",
        )

        try:
            # 1. UNDERSTANDING
            self.state_machine.transition(session, ReasoningState.UNDERSTANDING)
            self._record_trace(
                session,
                ReasoningState.UNDERSTANDING,
                "ANALYZE_OBJECTIVE",
                f"Scope: {request.depth.value} depth, risk: {request.risk_level}",
            )

            # Register standard baseline assumptions
            asm1 = asm_tracker.register_assumption(
                description="Underlying platform metrics and baseline logs reflect actual operational status",
                initial_status=AssumptionStatus.UNVERIFIED,
            )
            session.assumptions.append(asm1)

            # 2. DECOMPOSING
            self.state_machine.transition(session, ReasoningState.DECOMPOSING)
            subproblems = self.decomposer.decompose(request.question, max_depth=budget.max_depth)
            session.subproblems = subproblems[: budget.max_subproblems]
            self._record_trace(
                session,
                ReasoningState.DECOMPOSING,
                "SUBPROBLEMS_GENERATED",
                f"Decomposed into {len(session.subproblems)} structured subproblems (depth <= {budget.max_depth})",
            )

            # 3. HYPOTHESIS_GENERATION
            self.state_machine.transition(session, ReasoningState.HYPOTHESIS_GENERATION)
            hyps = self.hypothesis_gen.generate_initial_hypotheses(request.question)
            for h in hyps:
                self.falsifier.formulate_falsifiers(h)
            session.hypotheses = hyps[: budget.max_hypotheses]
            self._record_trace(
                session,
                ReasoningState.HYPOTHESIS_GENERATION,
                "HYPOTHESES_FORMULATED",
                f"Generated {len(session.hypotheses)} candidate hypotheses with empirical falsification criteria",
            )

            # 4. EVIDENCE_COLLECTION
            self.state_machine.transition(session, ReasoningState.EVIDENCE_COLLECTION)
            context_evd = self.integrator.fetch_context_as_evidence(
                tenant_id=request.tenant_id,
                workspace_id=request.workspace_id,
                query=request.question,
                context_refs=request.context_refs,
            )
            session.evidence.extend(context_evd)
            self._record_trace(
                session,
                ReasoningState.EVIDENCE_COLLECTION,
                "EVIDENCE_GATHERED",
                f"Collected {len(session.evidence)} empirical evidence items",
            )

            # 5. EVIDENCE_EVALUATION
            self.state_machine.transition(session, ReasoningState.EVIDENCE_EVALUATION)
            for ev in session.evidence:
                self.evidence_eval.evaluate_reliability_and_freshness(ev)

            # Detect conflicts
            conflicts = self.evidence_eval.detect_conflicts(session.evidence)
            if conflicts:
                self._record_trace(
                    session,
                    ReasoningState.EVIDENCE_EVALUATION,
                    "CONFLICT_DETECTED",
                    f"Identified {len(conflicts)} empirical evidence conflicts",
                )

            # Test incoming evidence against falsifiers
            for h in session.hypotheses:
                for ev in session.evidence:
                    self.falsifier.test_evidence_against_falsifiers(h, ev)

            # Evaluate hypothesis status
            self.deliberator.evaluate_hypotheses(session.hypotheses, session.evidence)

            # 6. DELIBERATING
            self.state_machine.transition(session, ReasoningState.DELIBERATING)
            for h in session.hypotheses:
                self.deliberator.generate_counterarguments(h, session.evidence)

            session.alternatives = self.deliberator.generate_alternatives(
                request.question, session.hypotheses
            )
            self._record_trace(
                session,
                ReasoningState.DELIBERATING,
                "ALTERNATIVES_GENERATED",
                f"Evaluated tradeoffs across {len(session.alternatives)} alternative options",
            )

            # 7. CONCLUDING
            self.state_machine.transition(session, ReasoningState.CONCLUDING)
            concl, expl = self.deliberator.synthesize_conclusion(
                question=request.question,
                evaluated_hypotheses=session.hypotheses,
                assumptions=session.assumptions,
                evidence_pool=session.evidence,
            )
            session.conclusions = [concl]
            session.explanation = expl
            session.confidence = concl.confidence
            session.uncertainty_state = concl.uncertainty_state

            # Link assumption to conclusion for invalidation tracking
            for asm in session.assumptions:
                asm_tracker.link_conclusion(asm.assumption_id, concl.conclusion_id)

            # 8. VERIFYING (if applicable)
            if request.risk_level in ("HIGH", "CRITICAL") or request.depth in (
                ReasoningDepth.DEEP,
                ReasoningDepth.CRITICAL,
            ):
                self.state_machine.transition(session, ReasoningState.VERIFYING)
                self.integrator.verify_conclusion(concl, session.evidence)
                self._record_trace(
                    session,
                    ReasoningState.VERIFYING,
                    "INDEPENDENT_VERIFICATION",
                    f"Verification outcome: verified={concl.is_verified}, status={concl.status.value}",
                )

            # 9. COMPLETED
            self.state_machine.transition(session, ReasoningState.COMPLETED)
            session.completed_at = datetime.now(UTC)

            # Build reasoning graph
            graph_builder = ReasoningGraphBuilder()
            session.graph = graph_builder.build_from_session(session)

            # Persist to memory safely (no raw chain-of-thought)
            self.integrator.persist_to_memory(session)

            self._record_trace(
                session,
                ReasoningState.COMPLETED,
                "DELIBERATION_COMPLETED",
                f"Deliberation completed with confidence: {session.confidence.value}",
            )

            # Update operational metrics
            elapsed = (session.completed_at - start_time).total_seconds()
            self._update_metrics(session, elapsed, success=True)

        except Exception as err:
            logger.exception(f"Deliberation session {session.reasoning_id} failed: {err}")
            self.state_machine.transition(session, ReasoningState.FAILED)
            session.completed_at = datetime.now(UTC)
            self._record_trace(
                session,
                ReasoningState.FAILED,
                "DELIBERATION_FAILED",
                f"Deliberation failed: {err}",
            )
            self._update_metrics(session, 0.0, success=False)

        return session

    def get_session(self, reasoning_id: str) -> ReasoningSession | None:
        """Retrieve a session by its unique ID."""
        return self._sessions.get(reasoning_id)

    def list_sessions(
        self,
        tenant_id: str = "default",
        workspace_id: str = "default",
        limit: int = 50,
    ) -> list[ReasoningSession]:
        """List recent reasoning sessions matching tenant and workspace."""
        matches = [
            s for s in self._sessions.values() if s.tenant_id == tenant_id and s.workspace_id == workspace_id
        ]
        matches.sort(key=lambda s: s.created_at, reverse=True)
        return matches[:limit]

    def add_evidence(
        self,
        reasoning_id: str,
        evidence: ReasoningEvidence,
    ) -> ReasoningSession:
        """Ingest new empirical evidence into an active or completed deliberation.

        Enforces Popperian falsification and contradiction detection.
        """
        session = self._sessions.get(reasoning_id)
        if not session:
            raise KeyError(f"Reasoning session {reasoning_id} not found")

        # Evaluate reliability
        self.evidence_eval.evaluate_reliability_and_freshness(evidence)
        session.evidence.append(evidence)

        # Conflict check
        self.evidence_eval.detect_conflicts(session.evidence)

        # Falsification check against hypotheses
        falsified_any = False
        for h in session.hypotheses:
            refuted = self.falsifier.test_evidence_against_falsifiers(h, evidence)
            if refuted:
                falsified_any = True

        # Re-evaluate hypotheses
        self.deliberator.evaluate_hypotheses(session.hypotheses, session.evidence)

        # If a leading hypothesis was refuted, re-synthesize conclusion
        if falsified_any and session.conclusions:
            concl, expl = self.deliberator.synthesize_conclusion(
                question=session.question,
                evaluated_hypotheses=session.hypotheses,
                assumptions=session.assumptions,
                evidence_pool=session.evidence,
            )
            session.conclusions = [concl]
            session.explanation = expl
            session.confidence = concl.confidence
            session.uncertainty_state = concl.uncertainty_state

            self._record_trace(
                session,
                session.current_state,
                "EVIDENCE_FALSIFICATION_CASCADE",
                f"New evidence {evidence.evidence_id} refutation triggered conclusion re-synthesis",
            )

        # Rebuild graph
        builder = ReasoningGraphBuilder()
        session.graph = builder.build_from_session(session)
        session.updated_at = datetime.now(UTC)

        return session

    def invalidate_assumption(
        self,
        reasoning_id: str,
        assumption_id: str,
        reason: str,
    ) -> tuple[ReasoningSession, list[str]]:
        """Invalidate an assumption and cascade to dependent conclusions."""
        session = self._sessions.get(reasoning_id)
        if not session:
            raise KeyError(f"Reasoning session {reasoning_id} not found")

        asm_tracker = self._assumption_trackers.get(reasoning_id)
        if not asm_tracker:
            raise KeyError(f"Assumption tracker for {reasoning_id} not found")

        asm, affected = asm_tracker.invalidate_assumption(
            assumption_id=assumption_id,
            reason=reason,
            conclusions_pool=session.conclusions,
        )

        # Reflect in session assumptions
        for i, a in enumerate(session.assumptions):
            if a.assumption_id == assumption_id:
                session.assumptions[i] = asm

        # Update session uncertainty if leading conclusion was invalidated
        if affected:
            session.uncertainty_state = UncertaintyType.CONFLICTING
            session.confidence = ReasoningConfidence.LOW
            self._record_trace(
                session,
                session.current_state,
                "ASSUMPTION_INVALIDATED_CASCADE",
                f"Assumption {assumption_id} invalidated; broken conclusions: {affected}",
            )

        # Rebuild graph
        builder = ReasoningGraphBuilder()
        session.graph = builder.build_from_session(session)
        session.updated_at = datetime.now(UTC)

        return session, affected

    def verify_conclusion(self, reasoning_id: str) -> ReasoningConclusion:
        """Trigger independent empirical verification of the session's conclusion."""
        session = self._sessions.get(reasoning_id)
        if not session:
            raise KeyError(f"Reasoning session {reasoning_id} not found")
        if not session.conclusions:
            raise ValueError(f"Reasoning session {reasoning_id} has no conclusion to verify")

        concl = session.conclusions[0]
        verified = self.integrator.verify_conclusion(concl, session.evidence)
        self._record_trace(
            session,
            session.current_state,
            "MANUAL_VERIFICATION_TRIGGERED",
            f"Verification outcome: {verified}",
        )
        # Rebuild graph
        builder = ReasoningGraphBuilder()
        session.graph = builder.build_from_session(session)
        return concl

    def replay_session(self, reasoning_id: str) -> dict[str, Any]:
        """Auditable historical replay separating initial state from later additions."""
        session = self._sessions.get(reasoning_id)
        if not session:
            raise KeyError(f"Reasoning session {reasoning_id} not found")

        initial_events = [e for e in session.trace_events if e.phase != ReasoningState.COMPLETED]
        post_completion = [e for e in session.trace_events if e.timestamp > session.created_at]

        return {
            "reasoning_id": session.reasoning_id,
            "question": session.question,
            "created_at": session.created_at.isoformat(),
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "depth": session.depth.value,
            "total_trace_events": len(session.trace_events),
            "initial_trace_count": len(initial_events),
            "post_completion_trace_count": len(post_completion),
            "trace_events": [e.model_dump() for e in session.trace_events],
            "historical_evidence_count": len(session.evidence),
            "subproblems_count": len(session.subproblems),
            "hypotheses": [h.model_dump() for h in session.hypotheses],
            "conclusion": session.conclusions[0].model_dump() if session.conclusions else None,
            "explanation": session.explanation.model_dump() if session.explanation else None,
        }

    def get_health_metrics(self) -> ReasoningHealthMetrics:
        """Return operational health metrics and telemetry."""
        return self._metrics

    def _update_metrics(self, session: ReasoningSession, latency_sec: float, success: bool) -> None:
        """Update telemetry metrics."""
        if success:
            self._metrics.completed_count += 1
            self._latencies.append(latency_sec)
            self._metrics.average_reasoning_latency_sec = round(
                sum(self._latencies) / max(1, len(self._latencies)), 2
            )
        else:
            self._metrics.failed_count += 1

        self._metrics.total_hypotheses_generated += len(session.hypotheses)
        self._metrics.total_evidence_evaluated += len(session.evidence)
        self._metrics.contradictions_detected += sum(1 for e in session.evidence if e.is_conflict)
        self._metrics.assumptions_invalidated += sum(
            1 for a in session.assumptions if a.status == AssumptionStatus.INVALIDATED
        )
        self._metrics.active_reasoning_count = sum(
            1
            for s in self._sessions.values()
            if s.current_state
            not in (ReasoningState.COMPLETED, ReasoningState.FAILED, ReasoningState.ABORTED)
        )
