"""Executive Memory Service - Central orchestrator for long-horizon continuity and state synthesis.

Implements INVARIANTS 1-240:
- Grounded state synthesis without duplicate truth
- Authoritative system supremacy
- Temporal as-of reconstruction with zero future leakage
- Open-loop and blocker lifecycle tracking with causal grounding
- Canonical continuity queries
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.executive_memory.blockers import BlockerManager
from app.executive_memory.checkpoints import CheckpointManager
from app.executive_memory.commitments import CommitmentTracker
from app.executive_memory.context import ContextSynthesisEngine
from app.executive_memory.continuity import ContinuityEngine
from app.executive_memory.decisions import DecisionHistoryManager
from app.executive_memory.dependencies import DependencyManager
from app.executive_memory.evaluation import ExecutiveMemoryEvaluator
from app.executive_memory.goals import GoalContinuityManager
from app.executive_memory.history import AttemptHistoryManager
from app.executive_memory.milestones import MilestoneManager
from app.executive_memory.next_actions import NextActionEngine
from app.executive_memory.open_loops import OpenLoopManager
from app.executive_memory.outcomes import OutcomeHistoryTracker
from app.executive_memory.priorities import PriorityEngine
from app.executive_memory.privacy import ExecutivePrivacyGuard
from app.executive_memory.projects import ProjectContinuityManager
from app.executive_memory.provenance import ExecutiveProvenanceTracker
from app.executive_memory.ranking import ExecutiveRankingEngine
from app.executive_memory.reconciliation import StateReconciler
from app.executive_memory.retention import HistoryRetentionEngine
from app.executive_memory.retrieval import ExecutiveRetrievalEngine
from app.executive_memory.safety import ExecutiveSafetyGuard
from app.executive_memory.schemas import (
    BlockerSchema,
    BlockerStatus,
    CheckpointSchema,
    ContinuityQueryResponse,
    ExecutiveBriefSchema,
    ExecutiveMemoryMetricsSchema,
    ExecutiveStateSchema,
    ExecutiveStateScope,
    MilestoneSchema,
    MilestoneStatus,
    NextActionSchema,
    OpenLoopSchema,
    OpenLoopStatus,
    ProjectLifecycleState,
    ReconciliationReportSchema,
    TimelineEventSchema,
    TimelineEventType,
)
from app.executive_memory.snapshots import SnapshotManager
from app.executive_memory.state import ExecutiveStateManager
from app.executive_memory.state_reconstruction import StateReconstructor
from app.executive_memory.summaries import ExecutiveSummaryManager
from app.executive_memory.tasks import TaskContinuityManager
from app.executive_memory.temporal import TemporalEngine
from app.executive_memory.timeline import TimelineEngine


class ExecutiveMemoryService:
    """Central orchestrator for Executive Memory, Long-Horizon Context, and Continuity Engine."""

    def __init__(self) -> None:
        self.temporal_engine = TemporalEngine()
        self.provenance_tracker = ExecutiveProvenanceTracker()
        self.safety_guard = ExecutiveSafetyGuard()
        self.timeline_engine = TimelineEngine()
        self.state_reconstructor = StateReconstructor(timeline_engine=self.timeline_engine)

        self.project_mgr = ProjectContinuityManager()
        self.goal_mgr = GoalContinuityManager()
        self.task_mgr = TaskContinuityManager()
        self.decision_mgr = DecisionHistoryManager()
        self.milestone_mgr = MilestoneManager()
        self.open_loop_mgr = OpenLoopManager()
        self.blocker_mgr = BlockerManager()
        self.commitment_tracker = CommitmentTracker()
        self.outcome_tracker = OutcomeHistoryTracker()
        self.history_mgr = AttemptHistoryManager()
        self.summary_mgr = ExecutiveSummaryManager()
        self.snapshot_mgr = SnapshotManager()
        self.checkpoint_mgr = CheckpointManager()
        self.priority_engine = PriorityEngine()
        self.next_action_engine = NextActionEngine(open_loop_mgr=self.open_loop_mgr)
        self.dependency_mgr = DependencyManager()
        self.context_engine = ContextSynthesisEngine()
        self.retrieval_engine = ExecutiveRetrievalEngine(timeline_engine=self.timeline_engine)
        self.ranking_engine = ExecutiveRankingEngine()
        self.reconciler = StateReconciler()
        self.privacy_guard = ExecutivePrivacyGuard()
        self.retention_engine = HistoryRetentionEngine()
        self.evaluator = ExecutiveMemoryEvaluator()

        self.state_mgr = ExecutiveStateManager(
            open_loop_mgr=self.open_loop_mgr,
            blocker_mgr=self.blocker_mgr,
            next_action_engine=self.next_action_engine,
        )

        self.continuity_engine = ContinuityEngine(
            timeline_engine=self.timeline_engine,
            state_reconstructor=self.state_reconstructor,
            project_mgr=self.project_mgr,
            goal_mgr=self.goal_mgr,
            decision_mgr=self.decision_mgr,
            open_loop_mgr=self.open_loop_mgr,
            blocker_mgr=self.blocker_mgr,
            next_action_engine=self.next_action_engine,
        )

    # --------------------------------------------------------------------------
    # 1. Timeline and Historical Reconstruction
    # --------------------------------------------------------------------------

    def record_timeline_event(
        self,
        event_type: TimelineEventType,
        source: str,
        description_reference: str,
        project_id: str | None = None,
        actor: str = "kairo",
        impact: str = "MEDIUM",
        timestamp: datetime | None = None,
        provenance: dict[str, Any] | None = None,
    ) -> TimelineEventSchema:
        """Records a timeline event with deduplication and invalidates stale snapshots/summaries."""
        event = self.timeline_engine.record_event(
            event_type=event_type,
            source=source,
            description_reference=description_reference,
            project_id=project_id,
            actor=actor,
            impact=impact,
            timestamp=timestamp,
            provenance=provenance,
        )
        # Invalidate snapshot and summary if related to project
        if project_id:
            self.snapshot_mgr.invalidate_snapshot(
                project_id, reason=f"New timeline event: {event_type.value}"
            )
            self.summary_mgr.invalidate_summary(
                project_id, reason=f"New timeline event: {event_type.value}"
            )
        return event

    def list_timeline_events(
        self,
        project_id: str | None = None,
        event_type: TimelineEventType | None = None,
        as_of: datetime | None = None,
        limit: int = 100,
    ) -> list[TimelineEventSchema]:
        """Lists events ordered chronologically, respecting as_of cutoffs."""
        return self.timeline_engine.list_events(
            project_id=project_id, event_type=event_type, as_of=as_of, limit=limit
        )

    def reconstruct_as_of(
        self, as_of: datetime, project_id: str | None = None
    ) -> dict[str, Any]:
        """Reconstructs state as of a historical date without future leakage."""
        return self.state_reconstructor.reconstruct_as_of(as_of=as_of, project_id=project_id)

    # --------------------------------------------------------------------------
    # 2. Executive State Synthesis
    # --------------------------------------------------------------------------

    def synthesize_current_state(
        self,
        scope: ExecutiveStateScope = ExecutiveStateScope.PROJECT,
        scope_id: str | None = None,
        authoritative_sources: dict[str, Any] | None = None,
    ) -> ExecutiveStateSchema:
        """Derives current state strictly from authoritative subsystems."""
        return self.state_mgr.synthesize_current_state(
            scope=scope, scope_id=scope_id, authoritative_sources=authoritative_sources
        )

    def get_latest_state(self) -> ExecutiveStateSchema | None:
        return self.state_mgr.get_latest_state()

    # --------------------------------------------------------------------------
    # 3. Continuity Queries (The 8 Canonical Questions)
    # --------------------------------------------------------------------------

    def answer_continuity_query(
        self,
        question_type: str,
        project_id: str | None = None,
        as_of: datetime | None = None,
        target_id: str | None = None,
        explicit_user_intent: str | None = None,
    ) -> ContinuityQueryResponse:
        """Answers canonical continuity query grounded in verifiable evidence."""
        return self.continuity_engine.answer_continuity_query(
            question_type=question_type,
            project_id=project_id,
            as_of=as_of,
            target_id=target_id,
            explicit_user_intent=explicit_user_intent,
        )

    # --------------------------------------------------------------------------
    # 4. Open Loops
    # --------------------------------------------------------------------------

    def create_open_loop(
        self,
        description: str,
        owner: str = "kairo",
        source: str = "tasks",
        priority: str = "MEDIUM",
        due_at: datetime | None = None,
        dependencies: list[str] | None = None,
        scope: str = "PROJECT",
        project_id: str | None = None,
    ) -> OpenLoopSchema:
        return self.open_loop_mgr.create_open_loop(
            description=description,
            owner=owner,
            source=source,
            priority=priority,
            due_at=due_at,
            dependencies=dependencies,
            scope=scope,
            project_id=project_id,
        )

    def update_open_loop_status(
        self,
        loop_id: str,
        status: OpenLoopStatus,
        evidence: str | None = None,
    ) -> OpenLoopSchema:
        return self.open_loop_mgr.update_status(
            loop_id=loop_id, status=status, evidence=evidence
        )

    def close_open_loop(self, loop_id: str, evidence: str) -> OpenLoopSchema:
        return self.open_loop_mgr.close_loop(loop_id=loop_id, evidence=evidence)

    def list_open_loops(
        self,
        project_id: str | None = None,
        status: OpenLoopStatus | None = None,
        include_stale: bool = True,
        check_staleness: bool = True,
    ) -> list[OpenLoopSchema]:
        return self.open_loop_mgr.list_open_loops(
            project_id=project_id,
            status=status,
            include_stale=include_stale,
            check_staleness=check_staleness,
        )

    # --------------------------------------------------------------------------
    # 5. Blockers
    # --------------------------------------------------------------------------

    def create_blocker(
        self,
        description: str,
        affected_tasks: list[str],
        source: str,
        severity: str = "MEDIUM",
        owner: str | None = None,
        causality_evidence: str | None = None,
        project_id: str | None = None,
    ) -> BlockerSchema:
        return self.blocker_mgr.create_blocker(
            description=description,
            affected_tasks=affected_tasks,
            source=source,
            severity=severity,
            owner=owner,
            causality_evidence=causality_evidence,
            project_id=project_id,
        )

    def resolve_blocker(self, blocker_id: str, resolution_evidence: str) -> BlockerSchema:
        return self.blocker_mgr.resolve_blocker(
            blocker_id=blocker_id, resolution_evidence=resolution_evidence
        )

    def list_blockers(
        self,
        project_id: str | None = None,
        active_only: bool = True,
    ) -> list[BlockerSchema]:
        return self.blocker_mgr.list_blockers(
            project_id=project_id, active_only=active_only
        )

    # --------------------------------------------------------------------------
    # 6. Milestones
    # --------------------------------------------------------------------------

    def create_milestone(
        self,
        project_id: str,
        criteria: str,
        goal_id: str | None = None,
        due_at: datetime | None = None,
    ) -> MilestoneSchema:
        return self.milestone_mgr.create_milestone(
            project_id=project_id, criteria=criteria, goal_id=goal_id, due_at=due_at
        )

    def achieve_milestone(
        self, milestone_id: str, verification_evidence: str
    ) -> MilestoneSchema:
        return self.milestone_mgr.achieve_milestone(
            milestone_id=milestone_id, verification_evidence=verification_evidence
        )

    def list_milestones(self, project_id: str | None = None) -> list[MilestoneSchema]:
        return self.milestone_mgr.list_milestones(project_id=project_id)

    # --------------------------------------------------------------------------
    # 7. Decisions and Next Actions
    # --------------------------------------------------------------------------

    def record_decision(
        self,
        summary: str,
        rationale: str,
        decider: str = "user",
        project_id: str | None = None,
        affected_tasks: list[str] | None = None,
        affected_projects: list[str] | None = None,
        supersedes_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.decision_mgr.record_decision(
            summary=summary,
            rationale=rationale,
            decider=decider,
            project_id=project_id,
            affected_tasks=affected_tasks,
            affected_projects=affected_projects,
            supersedes_id=supersedes_id,
            context=context,
        )

    def generate_next_actions(
        self,
        project_id: str | None = None,
        explicit_user_intent: str | None = None,
    ) -> list[NextActionSchema]:
        return self.next_action_engine.generate_from_open_loops(
            project_id=project_id, explicit_user_intent=explicit_user_intent
        )

    # --------------------------------------------------------------------------
    # 8. Briefings and Summaries
    # --------------------------------------------------------------------------

    def generate_executive_brief(
        self,
        project_id: str,
        current_status: str,
        recent_progress: list[dict[str, Any]] | None = None,
        open_work: list[dict[str, Any]] | None = None,
        blockers: list[dict[str, Any]] | None = None,
        decisions: list[dict[str, Any]] | None = None,
        risks: list[dict[str, Any]] | None = None,
        next_actions: list[dict[str, Any]] | None = None,
    ) -> ExecutiveBriefSchema:
        return self.summary_mgr.generate_brief(
            project_id=project_id,
            current_status=current_status,
            recent_progress=recent_progress,
            open_work=open_work,
            blockers=blockers,
            decisions=decisions,
            risks=risks,
            next_actions=next_actions,
        )

    def get_executive_brief(self, project_id: str) -> ExecutiveBriefSchema | None:
        return self.summary_mgr.get_latest_brief(project_id=project_id)

    # --------------------------------------------------------------------------
    # 9. Checkpoints and Resumption
    # --------------------------------------------------------------------------

    def create_checkpoint(
        self,
        workflow_id: str,
        goal: str,
        state: dict[str, Any],
        progress: str,
        dependencies: list[str],
        authorization: dict[str, Any],
        next_step: str,
    ) -> CheckpointSchema:
        return self.checkpoint_mgr.create_checkpoint(
            workflow_id=workflow_id,
            goal=goal,
            state=state,
            progress=progress,
            dependencies=dependencies,
            authorization=authorization,
            next_step=next_step,
        )

    def resume_checkpoint(
        self, checkpoint_id: str, current_authoritative_state: dict[str, Any]
    ) -> dict[str, Any]:
        return self.checkpoint_mgr.resume(
            checkpoint_id=checkpoint_id,
            current_authoritative_state=current_authoritative_state,
        )

    # --------------------------------------------------------------------------
    # 10. Reconciliation & Metrics
    # --------------------------------------------------------------------------

    def reconcile(
        self,
        scope_id: str,
        synthesized_state: dict[str, Any],
        authoritative_state: dict[str, Any],
    ) -> ReconciliationReportSchema:
        return self.reconciler.reconcile(
            scope_id=scope_id,
            synthesized_state=synthesized_state,
            authoritative_state=authoritative_state,
        )

    def get_metrics(self) -> ExecutiveMemoryMetricsSchema:
        return self.evaluator.get_metrics()


# Global singleton instance
executive_memory_service = ExecutiveMemoryService()
