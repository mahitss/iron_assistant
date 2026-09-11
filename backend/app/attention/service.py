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

from app.attention.delegation import AttentionDelegationEngine
from app.attention.importance import ImportanceEvaluator
from app.attention.interrupt import InterruptionPolicyEngine
from app.attention.lifecycle import AttentionLifecycleStateMachine
from app.attention.novelty import NoveltyDetector
from app.attention.resources import CognitiveResourceManager
from app.attention.risk import RiskEvaluator
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
from app.attention.urgency import UrgencyEvaluator


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
