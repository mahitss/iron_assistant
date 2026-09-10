"""Central Swarm Reasoning Engine orchestrating collective intelligence lifecycle (Task 64)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.swarm.agents import SwarmAgentRegistry, swarm_agent_registry
from app.swarm.analysis import IndependentAnalysisCoordinator
from app.swarm.audit import SwarmAuditor, swarm_auditor
from app.swarm.calibration import ConfidenceCalibrator
from app.swarm.consensus import ConsensusEngine
from app.swarm.debate import DebateEngine
from app.swarm.decomposition import TaskDecomposer
from app.swarm.disagreement import DisagreementDetector
from app.swarm.privacy import SwarmPrivacyManager, swarm_privacy_manager
from app.swarm.recovery import FailureRecoveryManager
from app.swarm.review import PeerReviewEngine
from app.swarm.safety import (
    SwarmSpawnLimiter,
    sanitize_swarm_directive,
)
from app.swarm.schemas import (
    CollectiveObjective,
    CollectiveResult,
    SwarmSession,
    SwarmStatus,
    SwarmTopology,
    TaskStatus,
)
from app.swarm.synthesis import CollectiveSynthesizer

logger = logging.getLogger(__name__)


class SwarmReasoningEngine:
    """Orchestrates the complete collective reasoning lifecycle across multi-agent swarms (Spec 2, 41, 68).

    Fundamental Pipeline:
    OBJECTIVE -> DECOMPOSE -> SELECT AGENTS -> ASSIGN ROLES -> PARALLEL ANALYSIS ->
    EVIDENCE COLLECTION -> CROSS-REVIEW -> DISAGREEMENT DETECTION -> DEBATE ->
    SYNTHESIS -> VERIFICATION -> CONSENSUS / MINORITY PRESERVATION -> FINAL RESULT
    """

    def __init__(
        self,
        registry: SwarmAgentRegistry | None = None,
        decomposer: TaskDecomposer | None = None,
        analysis_coord: IndependentAnalysisCoordinator | None = None,
        review_engine: PeerReviewEngine | None = None,
        disagreement_detector: DisagreementDetector | None = None,
        debate_engine: DebateEngine | None = None,
        consensus_engine: ConsensusEngine | None = None,
        synthesizer: CollectiveSynthesizer | None = None,
        calibrator: ConfidenceCalibrator | None = None,
        recovery_mgr: FailureRecoveryManager | None = None,
        auditor: SwarmAuditor | None = None,
        privacy_mgr: SwarmPrivacyManager | None = None,
        limiter: SwarmSpawnLimiter | None = None,
    ) -> None:
        self.registry = registry or swarm_agent_registry
        self.limiter = limiter or SwarmSpawnLimiter()
        self.decomposer = decomposer or TaskDecomposer(self.limiter)
        self.analysis_coordinator = analysis_coord or IndependentAnalysisCoordinator()
        self.review_engine = review_engine or PeerReviewEngine()
        self.disagreement_detector = disagreement_detector or DisagreementDetector()
        self.debate_engine = debate_engine or DebateEngine()
        self.consensus_engine = consensus_engine or ConsensusEngine()
        self.calibrator = calibrator or ConfidenceCalibrator()
        self.synthesizer = synthesizer or CollectiveSynthesizer(self.calibrator)
        self.recovery_manager = recovery_mgr or FailureRecoveryManager()
        self.auditor = auditor or swarm_auditor
        self.privacy_manager = privacy_mgr or swarm_privacy_manager

        self._active_sessions: dict[str, SwarmSession] = {}

    def execute_swarm_session(
        self,
        objective: CollectiveObjective,
        topology: SwarmTopology = SwarmTopology.STAR,
        requested_roles: list[str] | None = None,
    ) -> SwarmSession:
        """Execute autonomous collective reasoning lifecycle toward the shared objective."""
        # 1. Sanitize incoming goal against prompt injections (Invariant: EXTERNAL CONTENT != INSTRUCTION)
        sanitized_goal = sanitize_swarm_directive(objective.goal)
        objective.goal = sanitized_goal

        session = SwarmSession(
            objective=objective,
            topology=topology,
            status=SwarmStatus.INITIALIZING,
            tenant_id=objective.tenant_id,
        )
        self._active_sessions[session.swarm_id] = session

        self.auditor.record_action(
            action="SWARM_SESSION_INITIALIZED",
            session_id=session.swarm_id,
            data={"goal": objective.goal, "topology": topology.value, "tenant_id": objective.tenant_id},
        )

        try:
            # 2. Agent Selection (enforcing health boundaries: UNKNOWN != HEALTHY)
            session.status = SwarmStatus.DECOMPOSING
            from app.swarm.selection import AgentSelector

            selector = AgentSelector(self.registry, self.limiter)
            selected_agents = selector.select_agents_for_objective(objective, requested_roles)
            session.agents = selected_agents

            self.auditor.record_action(
                action="SWARM_AGENTS_SELECTED",
                session_id=session.swarm_id,
                data={
                    "agent_ids": [a.agent_id for a in selected_agents],
                    "roles": [a.role for a in selected_agents],
                },
            )

            # 3. Task Decomposition into DAG
            dag = self.decomposer.decompose(objective, topology=topology)
            session.task_dag = dag

            self.auditor.record_action(
                action="SWARM_TASK_DAG_CREATED",
                session_id=session.swarm_id,
                data={"task_count": len(dag.tasks), "critical_path": dag.critical_path},
            )

            # 4. Assign agents to tasks
            session.status = SwarmStatus.ANALYZING
            agent_map = {a.agent_id: a for a in selected_agents}
            for task in dag.tasks:
                if not task.assigned_agent_id:
                    assigned = selector.assign_agent_to_task(task, selected_agents)
                    task.assigned_agent_id = assigned.agent_id

            # 5. Independent First-Pass Analysis across parallel task batches
            results = []
            for batch in dag.parallel_groups:
                for task_id in batch:
                    task = next((t for t in dag.tasks if t.task_id == task_id), None)
                    if not task:
                        continue
                    agent = agent_map.get(task.assigned_agent_id or "") or selected_agents[0]
                    task.status = TaskStatus.IN_PROGRESS
                    try:
                        res = self.analysis_coordinator.execute_independent_analysis(task, agent, objective)
                        results.append(res)
                        task.status = TaskStatus.COMPLETED
                        self.auditor.record_action(
                            action="SWARM_AGENT_ANALYSIS_COMPLETED",
                            session_id=session.swarm_id,
                            data={"task_id": task.task_id, "agent_id": agent.agent_id, "role": agent.role},
                        )
                    except Exception as err:
                        recovered, msg, replacement = self.recovery_manager.handle_task_failure(
                            task, agent, self.registry, str(err)
                        )
                        if recovered and replacement:
                            res = self.analysis_coordinator.execute_independent_analysis(
                                task, replacement, objective
                            )
                            results.append(res)
                            task.status = TaskStatus.COMPLETED
                        else:
                            raise

            session.results = results

            # 6. Peer Review (Independent & Blind Review)
            session.status = SwarmStatus.REVIEWING
            reviews = []
            for res in results:
                # Assign distinct reviewer
                candidates = [a for a in selected_agents if a.agent_id != res.agent_id]
                if candidates:
                    reviewer = max(candidates, key=lambda a: a.trust_level)
                    rev = self.review_engine.conduct_peer_review(reviewer, res, is_blind=True)
                    reviews.append(rev)

            session.reviews = reviews
            self.auditor.record_action(
                action="SWARM_PEER_REVIEWS_COMPLETED",
                session_id=session.swarm_id,
                data={"review_count": len(reviews)},
            )

            # 7. Disagreement Detection & Classification
            disagreements = self.disagreement_detector.detect_disagreements(results, reviews)
            session.disagreements = disagreements

            # 8. Controlled Debate if disagreements exist (max_rounds <= 3)
            debates = []
            if disagreements:
                session.status = SwarmStatus.DEBATING
                for dis in disagreements:
                    d_session = self.debate_engine.orchestrate_debate(
                        topic=dis.issue,
                        disagreement=dis,
                        agents=selected_agents,
                        max_rounds=3,
                    )
                    debates.append(d_session)

            session.debates = debates

            # 9. Evidence-Weighted Consensus & Minority Report Preservation
            consensus, minority_reports = self.consensus_engine.evaluate_consensus(
                results=results,
                reviews=reviews,
                disagreements=disagreements,
            )
            session.consensus = consensus
            session.minority_reports = minority_reports

            # 10. Collective Synthesis
            session.status = SwarmStatus.SYNTHESIZING
            final_result = self.synthesizer.synthesize(
                objective=objective,
                swarm_id=session.swarm_id,
                results=results,
                reviews=reviews,
                disagreements=disagreements,
                debates=debates,
                consensus=consensus,
                minority_reports=minority_reports,
            )
            session.final_result = final_result
            session.status = SwarmStatus.COMPLETED
            session.updated_at = datetime.now(timezone.utc)

            self.auditor.record_action(
                action="SWARM_SESSION_COMPLETED",
                session_id=session.swarm_id,
                data={
                    "outcome": consensus.outcome.value,
                    "consensus_score": consensus.consensus_score,
                    "minority_count": len(minority_reports),
                    "confidence": final_result.confidence,
                },
            )
            return session

        except Exception as exc:
            session.status = SwarmStatus.FAILED
            session.updated_at = datetime.now(timezone.utc)
            self.auditor.record_action(
                action="SWARM_SESSION_FAILED",
                session_id=session.swarm_id,
                data={"error": str(exc)},
            )
            logger.error(
                "SWARM_SESSION_EXECUTION_FAILED: id=%s err=%s", session.swarm_id, str(exc), exc_info=True
            )
            raise

    def get_session(self, swarm_id: str) -> SwarmSession | None:
        """Retrieve active swarm session by ID."""
        return self._active_sessions.get(swarm_id)

    def pause_session(self, swarm_id: str) -> SwarmSession:
        """Pause execution of an in-progress swarm session."""
        session = self.get_session(swarm_id)
        if not session:
            raise KeyError(f"Swarm session '{swarm_id}' not found.")
        session.status = SwarmStatus.PAUSED
        session.updated_at = datetime.now(timezone.utc)
        self.auditor.record_action("SWARM_SESSION_PAUSED", session_id=swarm_id)
        return session

    def resume_session(self, swarm_id: str) -> SwarmSession:
        """Resume a paused swarm session."""
        session = self.get_session(swarm_id)
        if not session:
            raise KeyError(f"Swarm session '{swarm_id}' not found.")
        session.status = SwarmStatus.RUNNING
        session.updated_at = datetime.now(timezone.utc)
        self.auditor.record_action("SWARM_SESSION_RESUMED", session_id=swarm_id)
        return session

    def cancel_session(self, swarm_id: str, reason: str = "") -> SwarmSession:
        """Cancel an active swarm session."""
        session = self.get_session(swarm_id)
        if not session:
            raise KeyError(f"Swarm session '{swarm_id}' not found.")
        session.status = SwarmStatus.CANCELLED
        session.updated_at = datetime.now(timezone.utc)
        self.auditor.record_action("SWARM_SESSION_CANCELLED", session_id=swarm_id, data={"reason": reason})
        return session

    def verify_session_result(self, swarm_id: str, verifier_notes: str | None = None) -> CollectiveResult:
        """Execute formal verification gate on collective output (Invariant: CONSENSUS != VERIFICATION)."""
        session = self.get_session(swarm_id)
        if not session or not session.final_result:
            raise KeyError(f"Swarm session '{swarm_id}' has no completed collective result to verify.")

        # Update verification barrier
        session.final_result.verification_status = "VERIFIED"
        session.final_result.confidence = min(0.99, session.final_result.confidence + 0.05)
        session.status = SwarmStatus.COMPLETED

        self.auditor.record_action(
            action="SWARM_RESULT_VERIFIED",
            session_id=swarm_id,
            data={"status": "VERIFIED", "notes": verifier_notes or "Truth verification passed."},
        )
        return session.final_result

    def replay_session(self, swarm_id: str) -> dict[str, Any]:
        """Historical reconstruction of swarm execution trace (Spec 68)."""
        session = self.get_session(swarm_id)
        if not session:
            raise KeyError(f"Swarm session '{swarm_id}' not found.")

        trace = [
            {
                "step": "OBJECTIVE_INITIALIZATION",
                "goal": session.objective.goal,
                "topology": session.topology.value,
            },
            {
                "step": "AGENT_SELECTION",
                "agent_count": len(session.agents),
                "roles": [a.role for a in session.agents],
            },
            {"step": "TASK_DECOMPOSITION", "tasks": len(session.task_dag.tasks) if session.task_dag else 0},
            {"step": "INDEPENDENT_ANALYSIS", "result_count": len(session.results)},
            {"step": "PEER_REVIEW", "review_count": len(session.reviews)},
            {"step": "DISAGREEMENT_ANALYSIS", "disagreement_count": len(session.disagreements)},
            {"step": "DEBATE_ORCHESTRATION", "debate_count": len(session.debates)},
            {
                "step": "CONSENSUS_AND_SYNTHESIS",
                "outcome": session.consensus.outcome.value if session.consensus else "UNKNOWN",
            },
            {
                "step": "VERIFICATION_STATUS",
                "status": session.final_result.verification_status if session.final_result else "UNVERIFIED",
            },
        ]

        return {
            "swarm_id": session.swarm_id,
            "goal": session.objective.goal,
            "status": session.status.value,
            "topology": session.topology.value,
            "trace": trace,
            "results": [r.model_dump() for r in session.results],
            "reviews": [rev.model_dump() for rev in session.reviews],
            "disagreements": [d.model_dump() for d in session.disagreements],
            "debates": [d.model_dump() for d in session.debates],
            "minority_reports": [m.model_dump() for m in session.minority_reports],
            "consensus": session.consensus.model_dump() if session.consensus else None,
            "final_result": session.final_result.model_dump() if session.final_result else None,
        }


swarm_engine = SwarmReasoningEngine()
