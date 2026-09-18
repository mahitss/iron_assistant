"""WorkingSetService for Task 110:
Authoritative coordinator for Cognitive Working Set assembly, budgeting, freshness, provenance,
leasing, invalidation, snapshots, and feedback.

Strict Invariants:
- EmergencyStop immediately halts and invalidates execution-related working sets.
- Context inclusion never grants permission or authorization (SecurityCenter remains sole authority).
- Absence from context != absence from reality.
- Immutable audit snapshots are created for reproducibility.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from app.context.budget_engine import BudgetEngine
from app.context.candidate_gathering_engine import CandidateGatheringEngine
from app.context.compression_engine import CompressionEngine
from app.context.dependency_engine import DependencyEngine
from app.context.freshness_engine import FreshnessEngine
from app.context.lease_and_lifecycle_engine import LeaseAndLifecycleEngine
from app.context.provenance_engine import ProvenanceEngine
from app.context.quality_and_feedback_engine import QualityAndFeedbackEngine
from app.context.relevance_engine import RelevanceEngine
from app.context.working_set_domain import (
    ContextAssemblyRequest,
    ContextBudget,
    ContextConflict,
    ContextFeedback,
    ContextGap,
    ContextItem,
    ContextQualityAssessment,
    ContextSection,
    ContextSectionType,
    ContextSnapshot,
    ItemInclusionSemantics,
    WorkingSet,
    WorkingSetLifecycle,
    gen_ctx_id,
    utc_now,
)

logger = logging.getLogger("kairo.context.working_set_service")


class WorkingSetService:
    """Singleton service orchestrating cognitive working sets and context lifecycles."""

    _instance: "WorkingSetService | None" = None

    def __init__(self):
        self._working_sets: Dict[str, WorkingSet] = {}
        self._snapshots: Dict[str, ContextSnapshot] = {}
        self._quality_assessments: Dict[str, ContextQualityAssessment] = {}
        self._feedback_records: Dict[str, List[ContextFeedback]] = {}
        self._audit_timeline: List[Dict[str, Any]] = []

    @classmethod
    def get_instance(cls) -> "WorkingSetService":
        """Singleton accessor."""
        if cls._instance is None:
            cls._instance = WorkingSetService()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton for testing."""
        cls._instance = None

    # ========================================================================
    # Core Assembly Pipeline
    # ========================================================================

    def assemble_working_set(
        self,
        request: ContextAssemblyRequest,
        mock_inputs: Optional[Dict[str, Any]] = None,
    ) -> WorkingSet:
        """Execute the 12-stage cognitive working set assembly pipeline."""
        start_time = utc_now()
        ws_id = gen_ctx_id("ws")

        # Invariant 20: EmergencyStop check
        is_emergency_stopped = False
        try:
            from app.security.emergency_stop import get_emergency_stop
            es = get_emergency_stop()
            if es and es.is_stopped():
                is_emergency_stopped = True
        except Exception:
            pass

        if is_emergency_stopped:
            # Emergency Stop fail-closed: immediately abort with invalid working set
            ws = WorkingSet(
                working_set_id=ws_id,
                tenant_id=request.tenant_id,
                user_scope=request.user_scope,
                operation_type=request.operation_type,
                operation_id=request.operation_id,
                request_id=request.request_id,
                session_id=request.session_id,
                conversation_id=request.conversation_id,
                objective=request.objective,
                lifecycle=WorkingSetLifecycle.INVALIDATED,
                budget=ContextBudget(max_tokens=request.token_budget),
                conflicts=[],
                gaps=[
                    ContextGap(
                        missing_information="EmergencyStop is active",
                        why_it_matters="Execution cognition halted fail-closed by system emergency stop",
                        expected_source="security_center",
                        severity="CRITICAL",
                        is_blocking=True,
                    )
                ],
            )
            self._working_sets[ws_id] = ws
            return ws

        # 1. Initialize Budget & Working Set skeleton
        budget = ContextBudget(
            budget_id=gen_ctx_id("cbgt"),
            max_tokens=request.token_budget,
            max_bytes=request.token_budget * 8,
            max_items=60,
            latency_budget_ms=request.latency_budget_ms,
        )

        working_set = WorkingSet(
            working_set_id=ws_id,
            version=1,
            tenant_id=request.tenant_id,
            user_scope=request.user_scope,
            operation_type=request.operation_type,
            operation_id=request.operation_id,
            request_id=request.request_id,
            session_id=request.session_id,
            conversation_id=request.conversation_id,
            objective=request.objective,
            mission_id=request.active_mission_id,
            goal_id=request.active_goal_id,
            situation_id=request.active_situation_id,
            decision_id=request.active_decision_id,
            action_transaction_id=request.active_action_transaction_id,
            agent_id=request.agent_id,
            lifecycle=WorkingSetLifecycle.ASSEMBLING,
            budget=budget,
            pinned_items=list(request.pinned_item_ids),
        )

        # 2. Gather candidates across subsystems
        raw_candidates = CandidateGatheringEngine.gather_candidates(request, mock_inputs)
        candidate_pool = {c.candidate_id: c for c in raw_candidates}

        # 3. Resolve Bounded Dependencies
        resolved_candidates, dependencies, truncated = DependencyEngine.resolve_dependencies(
            seed_candidates=raw_candidates,
            candidate_pool=candidate_pool,
        )

        # 4. Filter Forbidden Sources
        if request.forbidden_sources:
            resolved_candidates = [
                c for c in resolved_candidates if c.source_subsystem not in request.forbidden_sources
            ]

        # 5. Evaluate Freshness & Identify Conflicts
        conflicts: List[ContextConflict] = []
        if mock_inputs and "conflicts" in mock_inputs:
            for conf_data in mock_inputs["conflicts"]:
                conflicts.append(
                    ContextConflict(
                        conflict_id=gen_ctx_id("cconf"),
                        competing_item_ids=conf_data.get("competing_items", []),
                        conflict_dimension=conf_data.get("dimension", "FACTUAL"),
                        summary=conf_data.get("summary", "Unresolved factual divergence"),
                        severity=conf_data.get("severity", "MEDIUM"),
                    )
                )

        competing_ids_set = {cid for conf in conflicts for cid in conf.competing_item_ids}

        # 6. Score Relevance, Freshness & Generate ContextItems
        unfiltered_items: List[ContextItem] = []
        has_untrusted = False

        for cand in resolved_candidates:
            if cand.is_untrusted:
                has_untrusted = True

            freshness = FreshnessEngine.evaluate_freshness(
                source_timestamp=cand.source_timestamp,
                domain_volatility=cand.domain_volatility,
                requested_freshness_seconds=request.freshness_threshold_seconds,
            )

            has_conflict = cand.candidate_id in competing_ids_set or cand.source_id in competing_ids_set
            is_pinned = (cand.candidate_id in request.pinned_item_ids) or (cand.source_id in request.pinned_item_ids)

            relevance, components, inclusion = RelevanceEngine.score_candidate(
                candidate=cand,
                request=request,
                freshness_score=1.0 - freshness.staleness_score,
                has_conflict=has_conflict,
                is_pinned=is_pinned,
                is_required=(cand.source_subsystem == "intent"),
            )

            provenance = ProvenanceEngine.create_provenance(cand)
            token_est = CompressionEngine.estimate_tokens(cand.raw_content)

            # Map section
            section_type = self._map_section_type(cand.source_subsystem)

            unfiltered_items.append(
                ContextItem(
                    item_id=cand.candidate_id,
                    version=1,
                    section=section_type,
                    title=cand.title,
                    content=cand.raw_content,
                    structured_payload=cand.structured_data,
                    inclusion=inclusion,
                    relevance_score=relevance,
                    relevance_components=components,
                    confidence=0.9 if cand.is_untrusted else 1.0,
                    freshness=freshness,
                    provenance=provenance,
                    token_estimate=token_est,
                    character_count=len(cand.raw_content),
                    is_pinned=is_pinned,
                    is_untrusted=cand.is_untrusted,
                    dependencies=cand.dependencies,
                )
            )

        # 7. Apply Budget & Graceful Degradation Ladder
        working_set.lifecycle = WorkingSetLifecycle.VALIDATING
        included_items, exclusions, gaps, transformations = BudgetEngine.apply_budget(
            items=unfiltered_items,
            budget=budget,
        )

        # 8. Organize into Structured Sections
        sections_dict: Dict[str, ContextSection] = {}
        for section_type in ContextSectionType:
            sec_items = [i for i in included_items if i.section == section_type]
            sec_tokens = sum(i.token_estimate for i in sec_items)
            sections_dict[section_type.value] = ContextSection(
                section_type=section_type,
                title=section_type.value.replace("_", " ").title(),
                items=sec_items,
                total_tokens=sec_tokens,
                item_count=len(sec_items),
                is_empty=(len(sec_items) == 0),
            )

        # 9. Issue Short-Lived Validity Lease
        lease = LeaseAndLifecycleEngine.grant_lease(
            working_set_id=ws_id,
            version=1,
            ttl_seconds=60.0,
        )

        # 10. Measure latency and finalize stats
        end_time = utc_now()
        budget.actual_latency_ms = round((end_time - start_time).total_seconds() * 1000.0, 2)

        working_set.sections = sections_dict
        working_set.lease = lease
        working_set.conflicts = conflicts
        working_set.gaps = gaps
        working_set.exclusions = exclusions
        working_set.item_count = len(included_items)
        working_set.total_tokens = budget.used_tokens
        working_set.compressed_item_count = len(transformations)
        working_set.has_untrusted_content = has_untrusted
        working_set.lifecycle = WorkingSetLifecycle.READY
        working_set.updated_at = end_time

        # 11. Quality Assessment
        quality = QualityAndFeedbackEngine.evaluate_quality(working_set)
        working_set.quality_score = quality.composite_quality
        working_set.completeness_estimate = quality.completeness_score
        self._quality_assessments[ws_id] = quality

        # 12. Persist Immutable Context Snapshot
        snapshot = self._create_snapshot(working_set)
        self._snapshots[ws_id] = snapshot
        self._working_sets[ws_id] = working_set

        # Record timeline event
        self._audit_timeline.append({
            "event": "CONTEXT_READY",
            "working_set_id": ws_id,
            "operation_type": request.operation_type,
            "item_count": working_set.item_count,
            "total_tokens": working_set.total_tokens,
            "timestamp": end_time.isoformat(),
        })

        return working_set

    # ========================================================================
    # Helper & Query Methods
    # ========================================================================

    def get_working_set(self, working_set_id: str) -> Optional[WorkingSet]:
        """Retrieve active working set, evaluating lease status."""
        ws = self._working_sets.get(working_set_id)
        if ws and ws.lease:
            ws.lease = LeaseAndLifecycleEngine.evaluate_lease(ws.lease)
            if ws.lease.state.value in ("EXPIRED", "INVALIDATED") and ws.lifecycle == WorkingSetLifecycle.READY:
                ws.lifecycle = WorkingSetLifecycle.EXPIRED
        return ws

    def list_working_sets(self, user_scope: str = "default_user", tenant_id: str = "default") -> List[WorkingSet]:
        """List working sets matching tenant and user scope."""
        results = [
            ws for ws in self._working_sets.values()
            if ws.tenant_id == tenant_id and ws.user_scope == user_scope
        ]
        # Evaluate leases
        for ws in results:
            if ws.lease:
                ws.lease = LeaseAndLifecycleEngine.evaluate_lease(ws.lease)
        return sorted(results, key=lambda w: w.created_at, reverse=True)

    def refresh_working_set(
        self,
        working_set_id: str,
        sections_to_refresh: Optional[List[str]] = None,
        reason: str = "Manual refresh requested",
    ) -> WorkingSet:
        """Incrementally refresh and revalidate an existing working set."""
        ws = self.get_working_set(working_set_id)
        if not ws:
            raise KeyError(f"Working set '{working_set_id}' not found")

        updated_ws, new_version = LeaseAndLifecycleEngine.prepare_revalidation(
            working_set=ws,
            sections_to_refresh=sections_to_refresh or [],
            trigger_reason=reason,
        )
        updated_ws.lifecycle = WorkingSetLifecycle.READY

        # Create snapshot for updated version
        snapshot = self._create_snapshot(updated_ws)
        self._snapshots[working_set_id] = snapshot

        self._audit_timeline.append({
            "event": "CONTEXT_REFRESHED",
            "working_set_id": working_set_id,
            "version": new_version,
            "reason": reason,
            "timestamp": utc_now().isoformat(),
        })

        return updated_ws

    def invalidate_working_set(self, working_set_id: str, reason: str = "Manual invalidation") -> WorkingSet:
        """Explicitly invalidate a working set fail-closed."""
        ws = self.get_working_set(working_set_id)
        if not ws:
            raise KeyError(f"Working set '{working_set_id}' not found")

        invalidated_ws = LeaseAndLifecycleEngine.invalidate_working_set(ws, reason)

        self._audit_timeline.append({
            "event": "CONTEXT_INVALIDATED",
            "working_set_id": working_set_id,
            "reason": reason,
            "timestamp": utc_now().isoformat(),
        })

        return invalidated_ws

    def pin_item(self, working_set_id: str, item_id: str, reason: str = "User pin") -> WorkingSet:
        """Pin a specific context item within the working set."""
        ws = self.get_working_set(working_set_id)
        if not ws:
            raise KeyError(f"Working set '{working_set_id}' not found")

        for sec in ws.sections.values():
            for item in sec.items:
                if item.item_id == item_id:
                    item.is_pinned = True
                    item.inclusion = ItemInclusionSemantics.REQUIRED
                    if item_id not in ws.pinned_items:
                        ws.pinned_items.append(item_id)
                    ws.updated_at = utc_now()
                    return ws

        raise KeyError(f"Item '{item_id}' not found in working set '{working_set_id}'")

    def unpin_item(self, working_set_id: str, item_id: str) -> WorkingSet:
        """Unpin a previously pinned context item."""
        ws = self.get_working_set(working_set_id)
        if not ws:
            raise KeyError(f"Working set '{working_set_id}' not found")

        for sec in ws.sections.values():
            for item in sec.items:
                if item.item_id == item_id:
                    item.is_pinned = False
                    item.inclusion = ItemInclusionSemantics.OPTIONAL
                    if item_id in ws.pinned_items:
                        ws.pinned_items.remove(item_id)
                    ws.updated_at = utc_now()
                    return ws

        raise KeyError(f"Item '{item_id}' not found in working set '{working_set_id}'")

    def record_feedback(self, working_set_id: str, feedback: ContextFeedback) -> Dict[str, Any]:
        """Record usage feedback for a working set."""
        ws = self.get_working_set(working_set_id)
        if not ws:
            raise KeyError(f"Working set '{working_set_id}' not found")

        if working_set_id not in self._feedback_records:
            self._feedback_records[working_set_id] = []
        self._feedback_records[working_set_id].append(feedback)

        return QualityAndFeedbackEngine.process_feedback(ws, feedback)

    def get_snapshot(self, working_set_id: str) -> Optional[ContextSnapshot]:
        """Retrieve audit snapshot for a working set."""
        return self._snapshots.get(working_set_id)

    def get_quality_assessment(self, working_set_id: str) -> Optional[ContextQualityAssessment]:
        """Retrieve quality assessment for a working set."""
        return self._quality_assessments.get(working_set_id)

    def get_timeline(self, working_set_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve audit event timeline."""
        if working_set_id:
            return [e for e in self._audit_timeline if e.get("working_set_id") == working_set_id]
        return self._audit_timeline

    # ========================================================================
    # Internal Helpers
    # ========================================================================

    def _create_snapshot(self, working_set: WorkingSet) -> ContextSnapshot:
        """Generate deterministic immutable snapshot with SHA-256 fingerprint."""
        item_ids = [
            item.item_id
            for sec in working_set.sections.values()
            for item in sec.items
        ]
        source_versions = {
            item.item_id: item.provenance.source_version
            for sec in working_set.sections.values()
            for item in sec.items
        }

        fingerprint_material = f"{working_set.working_set_id}:{working_set.version}:{','.join(sorted(item_ids))}"
        snapshot_hash = hashlib.sha256(fingerprint_material.encode("utf-8")).hexdigest()

        return ContextSnapshot(
            snapshot_id=gen_ctx_id("csnap"),
            working_set_id=working_set.working_set_id,
            working_set_version=working_set.version,
            operation_type=working_set.operation_type,
            operation_id=working_set.operation_id,
            item_ids=item_ids,
            source_versions=source_versions,
            total_tokens=working_set.total_tokens,
            quality_score=working_set.quality_score,
            has_untrusted_content=working_set.has_untrusted_content,
            snapshot_hash=snapshot_hash,
            trace_id=working_set.trace_id,
        )

    def _map_section_type(self, source_subsystem: str) -> ContextSectionType:
        """Map originating subsystem to canonical section type."""
        mapping = {
            "intent": ContextSectionType.ACTIVE_INTENT,
            "attention": ContextSectionType.SYSTEM_STATE,
            "missions": ContextSectionType.CURRENT_MISSION,
            "world_state": ContextSectionType.RELEVANT_WORLD_STATE,
            "belief": ContextSectionType.RELEVANT_BELIEFS,
            "cognitive_memory": ContextSectionType.RELEVANT_MEMORY,
            "self_model": ContextSectionType.RELEVANT_SELF_STATE,
            "decision": ContextSectionType.RELEVANT_DECISIONS,
            "execution": ContextSectionType.RELEVANT_ACTION_STATE,
            "web_fetch": ContextSectionType.RECENT_EVENTS,
        }
        return mapping.get(source_subsystem, ContextSectionType.SYSTEM_STATE)
