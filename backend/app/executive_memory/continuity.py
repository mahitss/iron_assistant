"""Core continuity query engine answering the 8 canonical continuity questions (INVARIANTS 79-93, 195-201)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.executive_memory.blockers import BlockerManager
from app.executive_memory.decisions import DecisionHistoryManager
from app.executive_memory.goals import GoalContinuityManager
from app.executive_memory.next_actions import NextActionEngine
from app.executive_memory.open_loops import OpenLoopManager
from app.executive_memory.projects import ProjectContinuityManager
from app.executive_memory.schemas import ContinuityQueryResponse, UncertaintyLevel
from app.executive_memory.state_reconstruction import StateReconstructor
from app.executive_memory.temporal import TemporalEngine
from app.executive_memory.timeline import TimelineEngine


class ContinuityEngine:
    """Answers the 8 core continuity questions grounded in authoritative historical evidence."""

    def __init__(
        self,
        timeline_engine: TimelineEngine,
        state_reconstructor: StateReconstructor,
        project_mgr: ProjectContinuityManager,
        goal_mgr: GoalContinuityManager,
        decision_mgr: DecisionHistoryManager,
        open_loop_mgr: OpenLoopManager,
        blocker_mgr: BlockerManager,
        next_action_engine: NextActionEngine,
    ) -> None:
        self.timeline_engine = timeline_engine
        self.state_reconstructor = state_reconstructor
        self.project_mgr = project_mgr
        self.goal_mgr = goal_mgr
        self.decision_mgr = decision_mgr
        self.open_loop_mgr = open_loop_mgr
        self.blocker_mgr = blocker_mgr
        self.next_action_engine = next_action_engine

    def answer_continuity_query(
        self,
        question_type: str,
        project_id: str | None = None,
        as_of: datetime | None = None,
        target_id: str | None = None,
        explicit_user_intent: str | None = None,
    ) -> ContinuityQueryResponse:
        q_norm = question_type.upper().strip()

        # 1. WHAT_WERE_WE_DOING / WHERE_DID_WE_STOP
        if q_norm in ("WHAT_WERE_WE_DOING", "WHERE_DID_WE_STOP", "WHAT_IS_HAPPENING"):
            events = self.timeline_engine.list_events(project_id=project_id)
            recent_evs = events[-5:] if events else []
            loops = self.open_loop_mgr.list_open_loops(project_id=project_id)
            blockers = self.blocker_mgr.list_blockers(active_only=True)
            next_acts = self.next_action_engine.list_next_actions(project_id=project_id)

            last_state = recent_evs[-1].model_dump() if recent_evs else None
            answer_text = (
                f"Recent activity involved '{recent_evs[-1].description_reference}'."
                if recent_evs
                else "No prior project activity recorded."
            )
            return ContinuityQueryResponse(
                question=question_type,
                answer=answer_text,
                last_meaningful_state=last_state,
                recent_progress=[e.model_dump() for e in recent_evs],
                open_loops=[l.model_dump() for l in loops],
                blockers=[b.model_dump() for b in blockers],
                next_actions=[a.model_dump() for a in next_acts],
                provenance={"source": "TIMELINE_AND_LOOPS"},
                uncertainty=UncertaintyLevel.KNOWN if recent_evs else UncertaintyLevel.UNKNOWN,
                confidence_level=UncertaintyLevel.KNOWN if recent_evs else UncertaintyLevel.UNKNOWN,
                authoritative_sources=["TimelineEngine", "OpenLoopManager"],
            )

        # 2. WHY_DID_WE_DO_IT (PURPOSE RECONSTRUCTION)
        elif q_norm == "WHY_DID_WE_DO_IT":
            # Trace target decision or goal
            decisions = self.decision_mgr.list_decisions(project_id=project_id)
            if decisions:
                target_dec = decisions[-1]
                rationale = target_dec.get("rationale")
                if rationale and rationale != "UNKNOWN":
                    return ContinuityQueryResponse(
                        question=question_type,
                        answer=f"Rationale for '{target_dec.get('decision_text')}': {rationale}",
                        recent_progress=decisions,
                        provenance={"decision_id": target_dec.get("decision_id")},
                        uncertainty=UncertaintyLevel.KNOWN,
                        confidence_level=UncertaintyLevel.KNOWN,
                        authoritative_sources=["DecisionHistoryManager"],
                    )
            # INVARIANT 87: If rationale missing, explicitly state UNKNOWN
            return ContinuityQueryResponse(
                question=question_type,
                answer="Causal rationale for this action is UNKNOWN in recorded decisions.",
                provenance={"source": "DECISION_HISTORY"},
                uncertainty=UncertaintyLevel.UNKNOWN,
                confidence_level=UncertaintyLevel.UNKNOWN,
                authoritative_sources=["DecisionHistoryManager"],
            )

        # 3. WHAT_CHANGED
        elif q_norm == "WHAT_CHANGED":
            cutoff = TemporalEngine.ensure_utc(as_of) if as_of else (datetime.now(UTC) - datetime.resolution)
            events = self.timeline_engine.list_events(project_id=project_id, since=as_of)
            pivots = self.project_mgr.list_pivots(project_id=project_id) if project_id else []
            return ContinuityQueryResponse(
                question=question_type,
                answer=f"Detected {len(events)} event(s) and {len(pivots)} project pivot(s) since specified point.",
                recent_progress=[e.model_dump() for e in events],
                provenance={"event_count": len(events), "pivots": pivots},
                uncertainty=UncertaintyLevel.KNOWN,
                confidence_level=UncertaintyLevel.KNOWN,
                authoritative_sources=["TimelineEngine", "ProjectContinuityManager"],
            )

        # 4. WHAT_REMAINS
        elif q_norm == "WHAT_REMAINS":
            loops = self.open_loop_mgr.list_open_loops(project_id=project_id)
            blockers = self.blocker_mgr.list_blockers(project_id=project_id, active_only=True)
            remaining_desc = ", ".join(l.description for l in loops) if loops else "No remaining open loops."
            return ContinuityQueryResponse(
                question=question_type,
                answer=f"Remaining unfinished work: {remaining_desc} ({len(blockers)} active blocker(s)).",
                open_loops=[l.model_dump() for l in loops],
                blockers=[b.model_dump() for b in blockers],
                provenance={"source": "OPEN_LOOPS_AND_BLOCKERS"},
                uncertainty=UncertaintyLevel.KNOWN,
                confidence_level=UncertaintyLevel.KNOWN,
                authoritative_sources=["OpenLoopManager", "BlockerManager"],
            )

        # 5. WHAT_IS_BLOCKING_US / WHAT_ARE_WE_WAITING_FOR
        elif q_norm in ("WHAT_IS_BLOCKING_US", "WHAT_ARE_WE_WAITING_FOR", "BLOCKERS"):
            blockers = self.blocker_mgr.list_blockers(project_id=project_id, active_only=True)
            loops = self.open_loop_mgr.list_open_loops(project_id=project_id, waiting_only=True)
            block_desc = ", ".join(b.description for b in blockers) if blockers else "Zero active blockers."
            return ContinuityQueryResponse(
                question=question_type,
                answer=f"Current blockers: {block_desc}",
                blockers=[b.model_dump() for b in blockers],
                open_loops=[l.model_dump() for l in loops],
                provenance={"source": "BLOCKER_MANAGER"},
                uncertainty=UncertaintyLevel.KNOWN,
                confidence_level=UncertaintyLevel.KNOWN,
                authoritative_sources=["BlockerManager"],
            )

        # 6. WHAT_NEXT / WHAT_SHOULD_HAPPEN_NEXT (NEXT OBJECTIVE)
        elif q_norm in ("WHAT_NEXT", "WHAT_SHOULD_HAPPEN_NEXT", "NEXT_ACTION"):
            next_acts = self.next_action_engine.list_next_actions(project_id=project_id)
            loops = self.open_loop_mgr.list_open_loops(project_id=project_id)
            top_obj = explicit_user_intent or (next_acts[0].objective if next_acts else (f"Address: {loops[0].description}" if loops else "No pending actions."))
            return ContinuityQueryResponse(
                question=question_type,
                answer=f"Next objective: {top_obj}",
                next_actions=[a.model_dump() for a in next_acts],
                open_loops=[l.model_dump() for l in loops[:3]],
                provenance={"source": "NEXT_ACTIONS_ENGINE"},
                uncertainty=UncertaintyLevel.KNOWN if (next_acts or explicit_user_intent or loops) else UncertaintyLevel.UNKNOWN,
                confidence_level=UncertaintyLevel.KNOWN if (next_acts or explicit_user_intent or loops) else UncertaintyLevel.UNKNOWN,
                authoritative_sources=["NextActionEngine", "OpenLoopManager"],
            )

        # 7. WHAT_WAS_TRUE (AS-OF HISTORICAL QUERY)
        elif q_norm in ("WHAT_WAS_TRUE", "WHAT_WAS_TRUE_AT_TIME", "HISTORICAL_STATE"):
            if not as_of:
                as_of = datetime.now(UTC)
            reconstructed = self.state_reconstructor.reconstruct_state_as_of(
                cutoff_timestamp=as_of,
                project_id=project_id,
            )
            return ContinuityQueryResponse(
                question=question_type,
                answer=f"Reconstructed historical state as of {as_of.isoformat()}.",
                last_meaningful_state=reconstructed.model_dump(),
                provenance=reconstructed.provenance,
                uncertainty=UncertaintyLevel.SUPPORTED,
                confidence_level=UncertaintyLevel.SUPPORTED,
                authoritative_sources=["StateReconstructor", "TimelineEngine"],
            )

        return ContinuityQueryResponse(
            question=question_type,
            answer=f"Unknown question type '{question_type}'. Supported: WHAT_WERE_WE_DOING, WHY_DID_WE_DO_IT, WHERE_DID_WE_STOP, WHAT_CHANGED, WHAT_IS_HAPPENING, WHAT_REMAINS, WHAT_NEXT, WHAT_WAS_TRUE, WHAT_IS_BLOCKING_US",
            uncertainty=UncertaintyLevel.UNKNOWN,
            confidence_level=UncertaintyLevel.UNKNOWN,
        )
