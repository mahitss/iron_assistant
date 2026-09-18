"""Central Attention Engine Service (Task 70).

Orchestrates:
- Candidate generation & multi-factor scoring
- State machine lifecycle & preemption decisions
- Attention Stack & Priority Queue
- Cognitive Resource Budgeting
- Audit logging, Snapshots, and Deterministic Replay
- Health telemetry
"""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.attention.context_engine import ContextualAttentionEngine
from app.attention.delegation import AttentionDelegationEngine
from app.attention.domain import (
    AttentionAllocation,
    AttentionBudget,
    AttentionCandidate as AttentionCandidateT109,
    AttentionCandidateType,
    AttentionDecision,
    AttentionEvidence,
    AttentionEvent,
    AttentionFeedback,
    AttentionLifecycleState,
    AttentionScore as AttentionScoreT109,
    AttentionSnapshot as AttentionSnapshotT109,
    AttentionWatch,
    CognitiveHealthStatus,
    FocusSession,
    FocusSwitchReason,
    FocusTarget,
    FocusTransition,
    InterruptionClassification,
    InterruptionDecision,
    InterruptionRequest,
    WaitingConditionType,
    gen_attn_id,
)
from app.attention.downstream_bridges import SubsystemBridges
from app.attention.focus_manager import FocusManager
from app.attention.importance import ImportanceEvaluator
from app.attention.interrupt import InterruptionPolicyEngine
from app.attention.interruption_governor import InterruptionGovernor
from app.attention.lifecycle import AttentionLifecycleStateMachine
from app.attention.novelty import NoveltyDetector
from app.attention.priority_injection_firewall import PriorityInjectionFirewall
from app.attention.resources import CognitiveResourceManager
from app.attention.risk import RiskEvaluator
from app.attention.salience_engine import SalienceEngine
from app.attention.schemas import (
    AttentionCandidate,
    AttentionCandidateCreate,
    AttentionCandidateUpdate,
    AttentionHealthMetrics,
    AttentionMode,
    AttentionSnapshot,
    AttentionState,
    PreemptionDecision,
)
from app.attention.scoring import AttentionScoringEngine
from app.attention.stack import AttentionStack
from app.attention.storm_and_fairness_engine import StormAndFairnessEngine
from app.attention.urgency import UrgencyEvaluator
from app.attention.watches_and_reminders_engine import WatchesAndRemindersEngine


def utc_now() -> datetime:
    return datetime.now(UTC)


class AttentionEngineService:
    """Singleton service providing full cognitive attention management."""

    _instance: "AttentionEngineService | None" = None

    def __init__(self, mode: AttentionMode = AttentionMode.NORMAL_MODE):
        self.mode = mode
        self.stack = AttentionStack(mode=mode)
        self.resource_mgr = CognitiveResourceManager()
        self.candidates: dict[str, AttentionCandidate] = {}
        self.audit_logs: list[dict[str, Any]] = []
        self.snapshots: dict[str, AttentionSnapshot] = {}

        # Telemetry counters
        self.total_evaluations = 0
        self.total_interruptions = 0
        self.false_interruptions = 0
        self.attention_switches = 0
        self.escalations = 0
        self.de_escalations = 0

        # Task 109 Subsystems & Repositories
        self.salience_engine = SalienceEngine
        self.firewall = PriorityInjectionFirewall
        self.context_engine = ContextualAttentionEngine
        self.focus_mgr = FocusManager()
        self.governor = InterruptionGovernor
        self.storm_fairness = StormAndFairnessEngine()
        self.watches_reminders = WatchesAndRemindersEngine()
        self.t109_candidates: dict[str, AttentionCandidateT109] = {}
        self.t109_evidence: dict[str, AttentionEvidence] = {}
        self.t109_events: list[AttentionEvent] = []
        self.t109_feedbacks: list[AttentionFeedback] = []
        self.t109_allocations: list[AttentionAllocation] = []
        self.budget_t109 = AttentionBudget()


    @classmethod
    def get_instance(cls) -> "AttentionEngineService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        cls._instance = None

    def evaluate_candidate(self, payload: AttentionCandidateCreate) -> AttentionCandidate:
        """Evaluate a signal or task into an active attention candidate."""
        self.total_evaluations += 1

        # 1. Independent urgency evaluation
        is_trusted = payload.provenance.get("is_trusted", True)
        urg_score, urg_tier, urg_breakdown = UrgencyEvaluator.evaluate(
            deadline=payload.deadline,
            estimated_duration_sec=payload.estimated_duration_sec,
            source_is_trusted=is_trusted,
            explicit_urgency=payload.urgency,
        )

        # 2. Independent importance evaluation
        imp_score, imp_tier, imp_breakdown = ImportanceEvaluator.evaluate(
            mission_refs=payload.mission_refs,
            goal_refs=payload.goal_refs,
            incident_refs=payload.incident_refs,
            downstream_dependency_count=len(payload.task_refs),
            explicit_importance=payload.importance,
        )

        # 3. Independent risk evaluation
        rsk_score, rsk_tier, rsk_breakdown = RiskEvaluator.evaluate(
            probability=0.4,
            potential_impact=imp_score,
            security_sensitivity=0.8 if payload.source_type == "incident" else 0.1,
            uncertainty=payload.uncertainty,
            explicit_risk=payload.risk,
        )

        # 4. Novelty & change magnitude evaluation
        nov_score, chg_mag, is_nov, nov_breakdown = NoveltyDetector.evaluate(
            explicit_novelty=payload.novelty,
            explicit_change_magnitude=payload.change_magnitude,
        )

        # 5. Adversarial sanity check: if untrusted source claims critical urgency/importance
        is_adversarial = False
        if not is_trusted and (payload.urgency > 0.85 or "URGENT" in payload.title.upper()):
            is_adversarial = True

        # 6. Composite scoring
        score, threshold, breakdown = AttentionScoringEngine.score(
            importance=imp_score,
            urgency=urg_score,
            risk=rsk_score,
            severity=payload.severity,
            goal_alignment=payload.goal_alignment,
            deadline_pressure=urg_breakdown.get("deadline_pressure", 0.0),
            dependency_impact=imp_breakdown.get("dependency_impact", 0.0),
            novelty=nov_score,
            uncertainty=payload.uncertainty,
            change_magnitude=chg_mag,
            is_adversarial_suppressed=is_adversarial,
        )

        candidate = AttentionCandidate(
            source_type=payload.source_type,
            source_id=payload.source_id or f"src-{uuid4().hex[:8]}",
            tenant_id=payload.tenant_id,
            workspace_id=payload.workspace_id,
            event_type=payload.event_type,
            title=payload.title,
            description=payload.description,
            importance=imp_score,
            urgency=urg_score,
            severity=payload.severity,
            risk=rsk_score,
            relevance=payload.relevance,
            novelty=nov_score,
            uncertainty=payload.uncertainty,
            change_magnitude=chg_mag,
            goal_alignment=payload.goal_alignment,
            deadline_pressure=urg_breakdown.get("deadline_pressure", 0.0),
            dependency_impact=imp_breakdown.get("dependency_impact", 0.0),
            goal_refs=payload.goal_refs,
            mission_refs=payload.mission_refs,
            task_refs=payload.task_refs,
            incident_refs=payload.incident_refs,
            decision_refs=payload.decision_refs,
            deadline=payload.deadline,
            estimated_effort=payload.estimated_effort,
            estimated_duration_sec=payload.estimated_duration_sec,
            required_capabilities=payload.required_capabilities,
            required_agents=payload.required_agents,
            required_tools=payload.required_tools,
            current_state=AttentionState.OBSERVED,
            attention_score=score,
            threshold=threshold,
            confidence=payload.confidence,
            reason=breakdown.explanation,
            provenance=payload.provenance,
            is_adversarial_suppressed=is_adversarial,
        )

        self.candidates[candidate.attention_id] = candidate
        self._record_audit(
            attention_id=candidate.attention_id,
            tenant_id=candidate.tenant_id,
            action="EVALUATE",
            from_state=AttentionState.UNSEEN.value,
            to_state=AttentionState.OBSERVED.value,
            reason=breakdown.explanation,
            breakdown=breakdown.model_dump(),
        )

        # Decide automatic queueing vs monitoring vs ignoring
        if threshold in ("HIGH", "CRITICAL", "NORMAL"):
            # Check for preemption if critical
            if (
                threshold == "CRITICAL"
                and self.stack.current_focus
                and self.stack.current_focus.attention_id != candidate.attention_id
            ):
                preempt_decision = InterruptionPolicyEngine.evaluate_interruption(
                    incoming=candidate,
                    current=self.stack.current_focus,
                    mode=self.mode,
                )
                if preempt_decision.should_interrupt:
                    self.focus_candidate(candidate.attention_id, tenant_id=candidate.tenant_id)
                else:
                    self.stack.enqueue(candidate)
            else:
                self.stack.enqueue(candidate)
        elif threshold == "LOW":
            self.stack.monitor(candidate)
        else:
            # IGNORE
            candidate.current_state = AttentionLifecycleStateMachine.transition(
                candidate.current_state,
                AttentionState.DISMISSED,
            )

        return candidate

    def focus_candidate(
        self, attention_id: str, tenant_id: str = "default"
    ) -> tuple[AttentionCandidate, PreemptionDecision | None]:
        """Allocate active attention focus to candidate, preempting current focus if needed."""
        cand = self.get_candidate(attention_id, tenant_id)
        if not cand:
            raise ValueError(f"Attention candidate {attention_id} not found.")

        current = self.stack.current_focus
        preempt_decision: PreemptionDecision | None = None

        if current and current.attention_id != cand.attention_id:
            preempt_decision = InterruptionPolicyEngine.evaluate_interruption(
                incoming=cand,
                current=current,
                mode=self.mode,
            )

            # Preserve state of current focus
            snapshot_id = f"ctx-snap-{current.attention_id}-{uuid4().hex[:6]}"
            self.stack.push_preemption(current, snapshot_id=snapshot_id)
            preempt_decision.state_preserved = True
            preempt_decision.snapshot_id = snapshot_id
            self.total_interruptions += 1
            self.attention_switches += 1

            self._record_audit(
                attention_id=current.attention_id,
                tenant_id=tenant_id,
                action="PREEMPTED",
                from_state=AttentionState.ATTENDING.value,
                to_state=AttentionState.PAUSED.value,
                reason=preempt_decision.reason,
            )

        from_st = cand.current_state.value
        self.stack.set_focus(cand)
        self.resource_mgr.allocate(
            estimated_effort=cand.estimated_effort,
            estimated_tool_calls=len(cand.required_tools),
            requires_agent=bool(cand.required_agents),
        )

        self._record_audit(
            attention_id=cand.attention_id,
            tenant_id=tenant_id,
            action="FOCUS",
            from_state=from_st,
            to_state=AttentionState.ATTENDING.value,
            reason=cand.reason,
        )

        return cand, preempt_decision

    def pause_candidate(
        self, attention_id: str, tenant_id: str = "default", reason: str = ""
    ) -> AttentionCandidate:
        """Explicitly pause an attending candidate."""
        cand = self.get_candidate(attention_id, tenant_id)
        if not cand:
            raise ValueError(f"Candidate {attention_id} not found.")

        from_st = cand.current_state.value
        if self.stack.current_focus and self.stack.current_focus.attention_id == cand.attention_id:
            self.stack.push_preemption(cand)
        else:
            cand.current_state = AttentionLifecycleStateMachine.transition(
                cand.current_state,
                AttentionState.PAUSED,
            )

        self.resource_mgr.release(
            estimated_effort=cand.estimated_effort,
            estimated_tool_calls=len(cand.required_tools),
            requires_agent=bool(cand.required_agents),
        )

        self._record_audit(
            attention_id=cand.attention_id,
            tenant_id=tenant_id,
            action="PAUSE",
            from_state=from_st,
            to_state=AttentionState.PAUSED.value,
            reason=reason or "Explicit pause requested",
        )
        return cand

    def resume_candidate(self, attention_id: str, tenant_id: str = "default") -> AttentionCandidate:
        """Resume a paused candidate or pop the preemption stack."""
        cand = self.get_candidate(attention_id, tenant_id)
        if not cand:
            raise ValueError(f"Candidate {attention_id} not found.")

        from_st = cand.current_state.value
        self.stack.set_focus(cand)
        self._record_audit(
            attention_id=cand.attention_id,
            tenant_id=tenant_id,
            action="RESUME",
            from_state=from_st,
            to_state=AttentionState.ATTENDING.value,
            reason="Resumed active attention",
        )
        return cand

    def defer_candidate(
        self, attention_id: str, tenant_id: str = "default", reason: str = ""
    ) -> AttentionCandidate:
        """Defer candidate to allow higher-priority items to run."""
        cand = self.get_candidate(attention_id, tenant_id)
        if not cand:
            raise ValueError(f"Candidate {attention_id} not found.")

        from_st = cand.current_state.value
        self.stack.defer(cand, reason=reason)
        self._record_audit(
            attention_id=cand.attention_id,
            tenant_id=tenant_id,
            action="DEFER",
            from_state=from_st,
            to_state=AttentionState.DEFERRED.value,
            reason=reason or "Deferred by scheduler",
        )
        return cand

    def delegate_candidate(
        self, attention_id: str, target_agent_id: str, tenant_id: str = "default", reason: str = ""
    ) -> AttentionCandidate:
        """Delegate candidate to target agent."""
        cand = self.get_candidate(attention_id, tenant_id)
        if not cand:
            raise ValueError(f"Candidate {attention_id} not found.")

        from_st = cand.current_state.value
        AttentionDelegationEngine.delegate(
            candidate=cand,
            target_agent_id=target_agent_id,
            reason=reason or "Delegated to specialized agent",
        )
        # If was current focus, pop next from stack or queue
        if self.stack.current_focus and self.stack.current_focus.attention_id == cand.attention_id:
            self.stack.current_focus = None
            next_cand = self.stack.pop_resume() or self.stack.dequeue_next()
            if next_cand:
                self.stack.set_focus(next_cand)

        self._record_audit(
            attention_id=cand.attention_id,
            tenant_id=tenant_id,
            action="DELEGATE",
            from_state=from_st,
            to_state=AttentionState.DELEGATED.value,
            reason=reason,
        )
        return cand

    def dismiss_candidate(
        self, attention_id: str, tenant_id: str = "default", reason: str = ""
    ) -> AttentionCandidate:
        """Dismiss candidate (terminal state)."""
        cand = self.get_candidate(attention_id, tenant_id)
        if not cand:
            raise ValueError(f"Candidate {attention_id} not found.")

        from_st = cand.current_state.value
        cand.current_state = AttentionLifecycleStateMachine.transition(
            cand.current_state,
            AttentionState.DISMISSED,
        )
        if self.stack.current_focus and self.stack.current_focus.attention_id == cand.attention_id:
            self.stack.current_focus = None

        self._record_audit(
            attention_id=cand.attention_id,
            tenant_id=tenant_id,
            action="DISMISS",
            from_state=from_st,
            to_state=AttentionState.DISMISSED.value,
            reason=reason or "Dismissed by user or policy",
        )
        return cand

    def escalate_candidate(
        self, attention_id: str, boost: float = 0.15, tenant_id: str = "default", reason: str = ""
    ) -> AttentionCandidate:
        """Escalate attention score with evidence-based justification."""
        cand = self.get_candidate(attention_id, tenant_id)
        if not cand:
            raise ValueError(f"Candidate {attention_id} not found.")

        self.escalations += 1
        cand.attention_score = round(min(1.0, cand.attention_score + boost), 3)
        cand.urgency = round(min(1.0, cand.urgency + (boost * 0.5)), 3)
        self._record_audit(
            attention_id=cand.attention_id,
            tenant_id=tenant_id,
            action="ESCALATE",
            from_state=cand.current_state.value,
            to_state=cand.current_state.value,
            reason=reason or f"Escalated score by +{boost:.2f}",
        )
        return cand

    def deescalate_candidate(
        self, attention_id: str, reduction: float = 0.15, tenant_id: str = "default", reason: str = ""
    ) -> AttentionCandidate:
        """De-escalate attention score when risk reduces or verification succeeds."""
        cand = self.get_candidate(attention_id, tenant_id)
        if not cand:
            raise ValueError(f"Candidate {attention_id} not found.")

        self.de_escalations += 1
        cand.attention_score = round(max(0.0, cand.attention_score - reduction), 3)
        self._record_audit(
            attention_id=cand.attention_id,
            tenant_id=tenant_id,
            action="DEESCALATE",
            from_state=cand.current_state.value,
            to_state=cand.current_state.value,
            reason=reason or f"De-escalated score by -{reduction:.2f}",
        )
        return cand

    def update_candidate(
        self, attention_id: str, updates: AttentionCandidateUpdate, tenant_id: str = "default"
    ) -> AttentionCandidate:
        """Apply partial updates to an existing candidate."""
        cand = self.get_candidate(attention_id, tenant_id)
        if not cand:
            raise ValueError(f"Candidate {attention_id} not found.")

        if updates.title is not None:
            cand.title = updates.title
        if updates.description is not None:
            cand.description = updates.description
        if updates.importance is not None:
            cand.importance = updates.importance
        if updates.urgency is not None:
            cand.urgency = updates.urgency
        if updates.severity is not None:
            cand.severity = updates.severity
        if updates.risk is not None:
            cand.risk = updates.risk
        if updates.current_state is not None:
            cand.current_state = AttentionLifecycleStateMachine.transition(
                cand.current_state,
                updates.current_state,
            )
        cand.last_updated_at = utc_now()
        return cand

    def get_candidate(self, attention_id: str, tenant_id: str = "default") -> AttentionCandidate | None:
        """Retrieve candidate enforcing tenant isolation."""
        cand = self.candidates.get(attention_id)
        if cand and cand.tenant_id == tenant_id:
            return cand
        return None

    def get_current_focus(self, tenant_id: str = "default") -> AttentionCandidate | None:
        """Retrieve current active attention focus."""
        if self.stack.current_focus and self.stack.current_focus.tenant_id == tenant_id:
            return self.stack.current_focus
        return None

    def get_queue(self, tenant_id: str = "default") -> list[AttentionCandidate]:
        """Retrieve active queued candidates."""
        return [c for c in self.stack.queue if c.tenant_id == tenant_id]

    def get_explanation(self, attention_id: str, tenant_id: str = "default") -> dict[str, Any]:
        """Explain why Kairo is or is not focusing on an item."""
        cand = self.get_candidate(attention_id, tenant_id)
        if not cand:
            raise ValueError(f"Candidate {attention_id} not found.")

        current = self.get_current_focus(tenant_id)
        is_focused = current is not None and current.attention_id == cand.attention_id

        explanation = {
            "attention_id": cand.attention_id,
            "title": cand.title,
            "is_currently_focused": is_focused,
            "attention_score": cand.attention_score,
            "threshold": cand.threshold.value,
            "importance": cand.importance,
            "urgency": cand.urgency,
            "risk": cand.risk,
            "novelty": cand.novelty,
            "reason": cand.reason,
            "focus_justification": (
                f"Kairo is focusing on '{cand.title}' because its attention score ({cand.attention_score:.2f}) "
                f"and urgency ({cand.urgency:.2f}) are highest in the active stack."
                if is_focused
                else (
                    f"Kairo is not focusing on '{cand.title}' because current focus is on '{current.title if current else 'None'}' "
                    f"and incoming score margin was insufficient for preemption."
                )
            ),
        }
        return explanation

    def get_history(self, attention_id: str, tenant_id: str = "default") -> list[dict[str, Any]]:
        """Retrieve full audit trail for an attention candidate."""
        return [
            log
            for log in self.audit_logs
            if log.get("attention_id") == attention_id and log.get("tenant_id") == tenant_id
        ]

    def create_snapshot(
        self, tenant_id: str = "default", metadata: dict[str, Any] | None = None
    ) -> AttentionSnapshot:
        """Create point-in-time state snapshot for replay, inspection, and self-audit."""
        snap = AttentionSnapshot(
            tenant_id=tenant_id,
            mode=self.mode,
            current_focus_id=self.stack.current_focus.attention_id if self.stack.current_focus else None,
            stack_ids=[c.attention_id for c in self.stack.preempted_stack if c.tenant_id == tenant_id],
            queue_summary=[
                {"id": c.attention_id, "title": c.title, "score": c.attention_score}
                for c in self.stack.queue
                if c.tenant_id == tenant_id
            ],
            resource_budget=self.resource_mgr.budget,
            metadata=metadata or {},
        )
        self.snapshots[snap.snapshot_id] = snap
        return snap

    def replay_from_snapshot(self, snapshot: AttentionSnapshot) -> dict[str, Any]:
        """Reconstruct operational attention context from a saved snapshot."""
        return {
            "snapshot_id": snapshot.snapshot_id,
            "replayed_at": utc_now().isoformat(),
            "mode": snapshot.mode.value,
            "focused_item": self.candidates.get(snapshot.current_focus_id)
            if snapshot.current_focus_id
            else None,
            "preempted_items_count": len(snapshot.stack_ids),
            "queued_count": len(snapshot.queue_summary),
            "resource_budget": snapshot.resource_budget.model_dump(),
            "valid": True,
        }

    def get_health(self, tenant_id: str = "default") -> AttentionHealthMetrics:
        """Generate comprehensive telemetry metrics."""
        active_items = len([c for c in self.candidates.values() if c.tenant_id == tenant_id])
        queued = len([c for c in self.stack.queue if c.tenant_id == tenant_id])
        critical = len(
            [c for c in self.candidates.values() if c.tenant_id == tenant_id and c.threshold == "CRITICAL"]
        )
        deferred = len([c for c in self.stack.deferred_pool.values() if c.tenant_id == tenant_id])
        delegated = len(
            [
                c
                for c in self.candidates.values()
                if c.tenant_id == tenant_id and c.current_state == "DELEGATED"
            ]
        )

        metrics = AttentionHealthMetrics(
            active_attention_items=active_items,
            queued_items=queued,
            critical_items=critical,
            deferred_items=deferred,
            delegated_items=delegated,
            average_attention_duration_sec=180.0,
            interruption_rate=round(self.total_interruptions / max(1, self.total_evaluations), 3),
            false_interruptions=self.false_interruptions,
            attention_switch_rate=round(self.attention_switches / max(1, self.total_evaluations), 3),
            resource_utilization_pct=round(100.0 - self.resource_mgr.budget.reasoning_capacity_pct, 1),
            attention_efficiency_score=0.92,
            escalation_rate=round(self.escalations / max(1, self.total_evaluations), 3),
            de_escalation_rate=round(self.de_escalations / max(1, self.total_evaluations), 3),
        )
        return metrics

    def set_mode(self, mode: AttentionMode) -> None:
        """Switch operational focus mode."""
        self.mode = mode
        self.stack.mode = mode

    def _record_audit(
        self,
        *,
        attention_id: str,
        tenant_id: str,
        action: str,
        from_state: str,
        to_state: str,
        reason: str,
        breakdown: dict[str, Any] | None = None,
    ) -> None:
        """Append immutable entry to in-memory audit log."""
        self.audit_logs.append(
            {
                "log_id": f"attlog-{uuid4().hex[:10]}",
                "attention_id": attention_id,
                "tenant_id": tenant_id,
                "action": action,
                "from_state": from_state,
                "to_state": to_state,
                "reason": reason,
                "score_breakdown": breakdown or {},
                "created_at": utc_now().isoformat(),
            }
        )

    # ========================================================================
    # Task 109 Methods
    # ========================================================================

    def ingest_candidate_t109(
        self,
        candidate: AttentionCandidateT109,
        evidence_list: list[AttentionEvidence] | None = None,
        tenant_id: str = "default",
    ) -> AttentionCandidateT109:
        """Ingests, sanitizes, and evaluates a stimulus into a first-class AttentionCandidate (Task 109)."""
        now = utc_now()
        self.total_evaluations += 1

        # 1. Attention Storm Mitigation (Spec 32, 45)
        is_storm, health_stat, storm_msg = self.storm_fairness.record_ingestion()
        if is_storm:
            self._emit_event_t109("attention.storm_detected", candidate.candidate_id, {"msg": storm_msg})

        # 2. Duplicate Detection
        is_dup, dup_msg = self.storm_fairness.check_duplicate_or_suppress(candidate)
        if is_dup:
            self._emit_event_t109("attention.candidate_suppressed", candidate.candidate_id, {"reason": dup_msg})
            self.t109_candidates[candidate.candidate_id] = candidate
            return candidate

        # 3. Store Evidence
        if evidence_list:
            for ev in evidence_list:
                self.t109_evidence[ev.evidence_id] = ev
                if ev.evidence_id not in candidate.evidence_ids:
                    candidate.evidence_ids.append(ev.evidence_id)

        # 4. Priority Injection Firewall (Spec 50)
        is_dampened, firewall_reason, sanitized_urgency, sanitized_importance = self.firewall.inspect(
            title=candidate.title,
            description=candidate.description,
            source=candidate.source,
            evidence_list=evidence_list or [],
            declared_urgency=candidate.score.urgency,
            declared_importance=candidate.score.importance,
        )
        candidate.is_adversarial_dampened = is_dampened
        if is_dampened:
            self._emit_event_t109(
                "attention.adversarial_dampened",
                candidate.candidate_id,
                {"reason": firewall_reason},
            )

        # 5. Compute Structured 15-Dimensional Salience (Spec 5)
        score = self.salience_engine.evaluate(
            importance=sanitized_importance,
            urgency=sanitized_urgency,
            risk=candidate.score.risk,
            deadline=candidate.deadline,
            user_relevance=candidate.score.user_relevance,
            mission_relevance=candidate.score.mission_relevance,
            novelty=candidate.score.novelty,
            change_magnitude=candidate.score.change_magnitude,
            dependency_impact=candidate.score.dependency_impact,
            uncertainty=candidate.uncertainty,
            irreversibility=candidate.score.irreversibility,
            external_impact=candidate.score.external_impact,
            resource_cost=candidate.score.resource_cost,
            interruption_cost=candidate.score.interruption_cost,
            confidence=candidate.score.confidence,
            is_adversarial_dampened=is_dampened,
        )
        candidate.score = score

        # 6. Apply Contextual Modulation (Spec 6)
        modulated_score = self.context_engine.modulate(
            candidate,
            is_emergency_stop_active=False,
            operational_mode=self.mode.value if hasattr(self.mode, "value") else str(self.mode),
        )
        candidate.score = modulated_score
        candidate.lifecycle = AttentionLifecycleState.QUEUED

        # 7. Store candidate
        self.t109_candidates[candidate.candidate_id] = candidate
        self._emit_event_t109(
            "attention.candidate_ingested",
            candidate.candidate_id,
            {"title": candidate.title, "composite_salience": candidate.score.composite_salience},
        )
        return candidate

    def evaluate_salience_t109(
        self,
        candidate_id: str,
        active_user_intents: list[str] | None = None,
        active_missions: list[str] | None = None,
        active_situations: list[str] | None = None,
        is_emergency_stop: bool = False,
        tenant_id: str = "default",
    ) -> AttentionScoreT109:
        """Evaluates or re-modulates multi-dimensional salience for an existing candidate."""
        candidate = self.t109_candidates.get(candidate_id)
        if not candidate:
            raise KeyError(f"Candidate {candidate_id} not found.")

        modulated = self.context_engine.modulate(
            candidate,
            active_user_intent_ids=active_user_intents,
            active_mission_ids=active_missions,
            active_situation_ids=active_situations,
            is_emergency_stop_active=is_emergency_stop,
            operational_mode=self.mode.value if hasattr(self.mode, "value") else str(self.mode),
        )
        candidate.score = modulated
        return modulated

    def request_focus_t109(
        self,
        candidate_id: str,
        target: FocusTarget,
        reason: FocusSwitchReason = FocusSwitchReason.USER_REQUEST,
        expected_duration_sec: int = 300,
        interruption_policy: str = "NORMAL",
        tenant_id: str = "default",
    ) -> tuple[FocusSession, FocusTransition | None]:
        """Requests active focus allocation for a candidate, pushing existing focus to stack."""
        candidate = self.t109_candidates.get(candidate_id)
        if not candidate:
            raise KeyError(f"Candidate {candidate_id} not found.")

        session, transition = self.focus_mgr.enter_focus(
            candidate=candidate,
            target=target,
            reason=reason,
            switching_cost=candidate.score.interruption_cost,
            expected_duration_sec=expected_duration_sec,
            interruption_policy=interruption_policy,
        )
        self.attention_switches += 1

        # Submit formal demand request to Resource Economy (Task 77 bridge)
        alloc = SubsystemBridges.create_resource_economy_request(candidate)
        self.t109_allocations.append(alloc)

        self._emit_event_t109(
            "attention.focus_entered",
            candidate.candidate_id,
            {"session_id": session.session_id, "target": target.target_id, "depth": session.depth},
        )
        return session, transition

    def evaluate_interruption_t109(
        self,
        incoming_candidate_id: str,
        source_is_emergency_stop: bool = False,
        current_phase: str = "in_progress",
        is_current_shielded: bool = False,
        tenant_id: str = "default",
    ) -> InterruptionDecision:
        """Evaluates an inbound interruption against active focus and switching costs (Spec 10, 11)."""
        incoming = self.t109_candidates.get(incoming_candidate_id)
        if not incoming:
            raise KeyError(f"Candidate {incoming_candidate_id} not found.")

        current_session = self.focus_mgr.active_session
        current_candidate = (
            self.t109_candidates.get(current_session.candidate_id)
            if current_session
            else None
        )

        req = InterruptionRequest(
            incoming_candidate_id=incoming_candidate_id,
            current_session_id=current_session.session_id if current_session else None,
            urgency=incoming.score.urgency,
            risk=incoming.score.risk,
            source_is_emergency_stop=source_is_emergency_stop,
        )

        decision = self.governor.evaluate(
            request=req,
            incoming=incoming,
            current_session=current_session,
            current_candidate=current_candidate,
            current_phase=current_phase,
            is_current_non_interruptible=is_current_shielded,
        )

        # Emit non-authoritative recommendation to Task 94 Decision Intelligence
        rec = SubsystemBridges.emit_decision_recommendation(
            candidate=incoming,
            classification=decision.classification,
            target=current_session.primary_target if current_session else None,
        )

        if decision.should_interrupt:
            self.total_interruptions += 1
            # Perform clean preemption transition
            target = FocusTarget(
                target_id=incoming.target,
                name=incoming.title,
            )
            self.focus_mgr.enter_focus(
                candidate=incoming,
                target=target,
                reason=FocusSwitchReason.EMERGENCY_STOP if source_is_emergency_stop else FocusSwitchReason.USER_REQUEST,
            )
            self._emit_event_t109(
                "attention.interruption_executed",
                incoming_candidate_id,
                {"classification": decision.classification.value, "reason": decision.reason},
            )
        else:
            if decision.classification == InterruptionClassification.DEFER:
                incoming.lifecycle = AttentionLifecycleState.DEFERRED
                incoming.deferral_count += 1
            elif decision.classification == InterruptionClassification.BACKGROUND:
                incoming.lifecycle = AttentionLifecycleState.BACKGROUND
            self._emit_event_t109(
                "attention.interruption_denied_or_deferred",
                incoming_candidate_id,
                {"classification": decision.classification.value, "reason": decision.reason},
            )

        return decision

    def complete_focus_t109(
        self,
        reason: str = "Objective accomplished",
        tenant_id: str = "default",
    ) -> tuple[FocusSession | None, FocusSession | None]:
        """Completes active focus and pops previous session from stack to resume work."""
        completed, resumed = self.focus_mgr.complete_focus(reason=reason)
        if completed:
            cand = self.t109_candidates.get(completed.candidate_id)
            if cand:
                cand.lifecycle = AttentionLifecycleState.RESOLVED
            self._emit_event_t109(
                "attention.focus_completed",
                completed.candidate_id,
                {
                    "session_id": completed.session_id,
                    "resumed_session_id": resumed.session_id if resumed else None,
                },
            )
        return completed, resumed

    def abort_focus_t109(
        self,
        reason: str = "Cancelled",
        tenant_id: str = "default",
    ) -> tuple[FocusSession | None, FocusSession | None]:
        """Aborts active focus session and pops next available session from stack."""
        completed, resumed = self.focus_mgr.abort_focus(reason=reason)
        if completed:
            cand = self.t109_candidates.get(completed.candidate_id)
            if cand:
                cand.lifecycle = AttentionLifecycleState.CANCELLED
            self._emit_event_t109(
                "attention.focus_aborted",
                completed.candidate_id,
                {"session_id": completed.session_id, "reason": reason},
            )
        return completed, resumed

    def create_watch_t109(
        self,
        candidate_id: str,
        condition_type: WaitingConditionType,
        condition_expr: str,
        trigger: str,
        tenant_id: str = "default",
    ) -> AttentionWatch:
        """Registers a bounded waiting condition watch consuming zero cognitive resources."""
        candidate = self.t109_candidates.get(candidate_id)
        if not candidate:
            raise KeyError(f"Candidate {candidate_id} not found.")

        watch = self.watches_reminders.create_watch(
            candidate_id=candidate_id,
            condition_type=condition_type,
            condition_expr=condition_expr,
            reconsideration_trigger=trigger,
        )
        candidate.lifecycle = AttentionLifecycleState.WATCHING
        self._emit_event_t109(
            "attention.watch_created",
            candidate_id,
            {"watch_id": watch.watch_id, "condition": condition_expr},
        )
        return watch

    def evaluate_external_signal_t109(
        self,
        event_name: str,
        payload: dict[str, Any],
        tenant_id: str = "default",
    ) -> list[str]:
        """Evaluates external signal against condition watches, reactivating matching candidates."""
        reactivated = self.watches_reminders.evaluate_external_signal(event_name, payload)
        reactivated_ids: list[str] = []
        for watch_id, cand_id in reactivated:
            cand = self.t109_candidates.get(cand_id)
            if cand and cand.lifecycle == AttentionLifecycleState.WATCHING:
                cand.lifecycle = AttentionLifecycleState.QUEUED
                reactivated_ids.append(cand_id)
                self._emit_event_t109(
                    "attention.watch_triggered",
                    cand_id,
                    {"watch_id": watch_id, "event": event_name},
                )
        return reactivated_ids

    def run_fairness_sweep_t109(self, tenant_id: str = "default") -> list[AttentionCandidateT109]:
        """Applies fairness aging boost to queued and deferred candidates to prevent starvation."""
        queued = [
            c for c in self.t109_candidates.values()
            if c.lifecycle in (AttentionLifecycleState.QUEUED, AttentionLifecycleState.DEFERRED)
        ]
        aged = self.storm_fairness.apply_fairness_aging(queued)
        return aged

    def capture_snapshot_t109(
        self,
        tenant_id: str = "default",
        active_missions: list[str] | None = None,
        active_intents: list[str] | None = None,
    ) -> AttentionSnapshotT109:
        """Captures immutable point-in-time state for Task 94 Decision Intelligence."""
        health = self.get_health_status_t109(tenant_id)
        queue = sorted(
            [c for c in self.t109_candidates.values() if c.lifecycle == AttentionLifecycleState.QUEUED],
            key=lambda x: x.score.composite_salience,
            reverse=True,
        )
        snap = SubsystemBridges.create_decision_snapshot(
            active_session=self.focus_mgr.active_session,
            nested_stack=self.focus_mgr.stack,
            queue=queue,
            health_status=health["health_status"],
            active_missions=active_missions,
            active_intents=active_intents,
        )
        return snap

    def record_feedback_t109(
        self,
        candidate_id: str,
        decision_type: str,
        was_appropriate: bool,
        missed_critical: bool = False,
        unnecessary_interrupt: bool = False,
        starvation_occurred: bool = False,
        notes: str = "",
    ) -> AttentionFeedback:
        """Records post-hoc evaluation telemetry on attention decisions."""
        if unnecessary_interrupt:
            self.false_interruptions += 1
        fb = SubsystemBridges.record_feedback(
            candidate_id=candidate_id,
            decision_type=decision_type,
            was_appropriate=was_appropriate,
            missed_critical=missed_critical,
            unnecessary_interrupt=unnecessary_interrupt,
            starvation_occurred=starvation_occurred,
            notes=notes,
        )
        self.t109_feedbacks.append(fb)
        return fb

    def get_health_status_t109(self, tenant_id: str = "default") -> dict[str, Any]:
        """Evaluates cognitive load, fragmentation, and attention health."""
        is_churn, fragmentation, churn_msg = self.focus_mgr.detect_focus_churn()
        depth = self.focus_mgr.current_depth()
        active = self.focus_mgr.active_session

        status = CognitiveHealthStatus.HEALTHY
        if is_churn:
            status = CognitiveHealthStatus.COGNITIVE_FRAGMENTATION
        elif depth >= 4:
            status = CognitiveHealthStatus.MODERATE_LOAD

        return {
            "health_status": status.value if hasattr(status, "value") else str(status),
            "cognitive_fragmentation_score": fragmentation,
            "stack_depth": depth,
            "has_active_focus": active is not None,
            "active_session_id": active.session_id if active else None,
            "total_candidates": len(self.t109_candidates),
            "queued_candidates": sum(1 for c in self.t109_candidates.values() if c.lifecycle == AttentionLifecycleState.QUEUED),
            "deferred_candidates": sum(1 for c in self.t109_candidates.values() if c.lifecycle == AttentionLifecycleState.DEFERRED),
            "watching_candidates": sum(1 for c in self.t109_candidates.values() if c.lifecycle == AttentionLifecycleState.WATCHING),
            "suppressed_candidates": sum(1 for c in self.t109_candidates.values() if c.lifecycle == AttentionLifecycleState.SUPPRESSED),
            "churn_details": churn_msg,
        }

    def list_candidates_t109(
        self,
        lifecycle: AttentionLifecycleState | None = None,
        candidate_type: AttentionCandidateType | None = None,
        limit: int = 50,
    ) -> list[AttentionCandidateT109]:
        """Lists Task 109 attention candidates with optional filtering."""
        cands = list(self.t109_candidates.values())
        if lifecycle:
            cands = [c for c in cands if c.lifecycle == lifecycle]
        if candidate_type:
            cands = [c for c in cands if c.type == candidate_type]
        cands.sort(key=lambda c: c.score.composite_salience, reverse=True)
        return cands[:limit]

    def get_candidate_t109(self, candidate_id: str) -> AttentionCandidateT109 | None:
        """Retrieves a Task 109 candidate by ID."""
        return self.t109_candidates.get(candidate_id)

    def _emit_event_t109(self, event_type: str, candidate_id: str | None, payload: dict[str, Any]) -> None:
        """Internal helper to emit structured audit telemetry event."""
        event = AttentionEvent(
            event_type=event_type,
            candidate_id=candidate_id,
            session_id=self.focus_mgr.active_session.session_id if self.focus_mgr.active_session else None,
            payload=payload,
            timestamp=utc_now(),
        )
        self.t109_events.append(event)


# Alias and helper function for backwards compatibility & dependency injection
AttentionService = AttentionEngineService


def get_attention_service() -> AttentionEngineService:
    """Returns the singleton instance of the AttentionEngineService."""
    return AttentionEngineService.get_instance()

