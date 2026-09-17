"""Situation lifecycle state machine, lineage-preserving merge/split, recurrence, and suppression for Task 99.

Enforces:
- Formal state transition matrix
- Merging never destroys lineage (preserves merged_from, merged_into, merge_reason)
- Splitting preserves lineage (split_from_id, audit records)
- Duplicate signals remain deduplicated with recurrence counters
- Suppression preserves raw underlying signals with auditable reasons
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from app.situational_awareness.domain import (
    CausalStatus,
    SignalRecord,
    SituationInterventionRecord,
    SituationLifecycleState,
    SituationPatternRecord,
    SituationRecord,
    SituationSeverity,
    SituationSuppressionRecord,
    SituationTimelineEntry,
    SituationType,
    generate_uuid,
    utc_now,
)

logger = logging.getLogger("kairo.situational_awareness.lifecycle")


# Legal State Machine Transitions (Section 2)
VALID_SITUATION_TRANSITIONS: dict[SituationLifecycleState, set[SituationLifecycleState]] = {
    SituationLifecycleState.DETECTED: {
        SituationLifecycleState.CORRELATING,
        SituationLifecycleState.FORMING,
        SituationLifecycleState.ACTIVE,
        SituationLifecycleState.ESCALATING,
        SituationLifecycleState.RESOLVED,
        SituationLifecycleState.SUPPRESSED,
        SituationLifecycleState.UNKNOWN,
    },
    SituationLifecycleState.CORRELATING: {
        SituationLifecycleState.FORMING,
        SituationLifecycleState.ACTIVE,
        SituationLifecycleState.ESCALATING,
        SituationLifecycleState.RESOLVED,
        SituationLifecycleState.SUPPRESSED,
        SituationLifecycleState.EXPIRED,
        SituationLifecycleState.UNKNOWN,
    },
    SituationLifecycleState.FORMING: {
        SituationLifecycleState.ACTIVE,
        SituationLifecycleState.ESCALATING,
        SituationLifecycleState.RESOLVED,
        SituationLifecycleState.SUPPRESSED,
        SituationLifecycleState.MERGED,
        SituationLifecycleState.UNKNOWN,
    },
    SituationLifecycleState.ACTIVE: {
        SituationLifecycleState.ESCALATING,
        SituationLifecycleState.INTERVENTION_PENDING,
        SituationLifecycleState.INTERVENTION_ACTIVE,
        SituationLifecycleState.OBSERVING,
        SituationLifecycleState.RESOLVING,
        SituationLifecycleState.RESOLVED,
        SituationLifecycleState.SUPPRESSED,
        SituationLifecycleState.MERGED,
        SituationLifecycleState.SPLIT,
        SituationLifecycleState.EXPIRED,
        SituationLifecycleState.UNKNOWN,
    },
    SituationLifecycleState.ESCALATING: {
        SituationLifecycleState.INTERVENTION_PENDING,
        SituationLifecycleState.INTERVENTION_ACTIVE,
        SituationLifecycleState.ACTIVE,
        SituationLifecycleState.RESOLVED,
        SituationLifecycleState.SUPPRESSED,
        SituationLifecycleState.UNKNOWN,
    },
    SituationLifecycleState.INTERVENTION_PENDING: {
        SituationLifecycleState.INTERVENTION_ACTIVE,
        SituationLifecycleState.ACTIVE,
        SituationLifecycleState.SUPPRESSED,
        SituationLifecycleState.UNKNOWN,
    },
    SituationLifecycleState.INTERVENTION_ACTIVE: {
        SituationLifecycleState.OBSERVING,
        SituationLifecycleState.RESOLVING,
        SituationLifecycleState.ACTIVE,
        SituationLifecycleState.UNKNOWN,
    },
    SituationLifecycleState.OBSERVING: {
        SituationLifecycleState.STABILIZING,
        SituationLifecycleState.RESOLVING,
        SituationLifecycleState.ACTIVE,
        SituationLifecycleState.ESCALATING,
        SituationLifecycleState.UNKNOWN,
    },
    SituationLifecycleState.STABILIZING: {
        SituationLifecycleState.RESOLVED,
        SituationLifecycleState.ACTIVE,
        SituationLifecycleState.UNKNOWN,
    },
    SituationLifecycleState.RESOLVING: {
        SituationLifecycleState.RESOLVED,
        SituationLifecycleState.ACTIVE,
        SituationLifecycleState.UNKNOWN,
    },
    SituationLifecycleState.RESOLVED: {
        SituationLifecycleState.ACTIVE,  # Reopened on recurring evidence
        SituationLifecycleState.UNKNOWN,
    },
    SituationLifecycleState.SUPPRESSED: {
        SituationLifecycleState.ACTIVE,  # Unsuppressed or cooldown expired
        SituationLifecycleState.EXPIRED,
        SituationLifecycleState.UNKNOWN,
    },
    SituationLifecycleState.EXPIRED: {
        SituationLifecycleState.UNKNOWN,
    },
    SituationLifecycleState.MERGED: set(),  # Terminal state for subsumed situation
    SituationLifecycleState.SPLIT: set(),   # Terminal state for subdivided parent
    SituationLifecycleState.UNKNOWN: {
        SituationLifecycleState.DETECTED,
        SituationLifecycleState.ACTIVE,
        SituationLifecycleState.RESOLVED,
    },
}


class SituationLifecycleManager:
    """Manages state transitions, lineage-preserving merges/splits, pattern recognition, and suppression."""

    def __init__(self) -> None:
        self._patterns: dict[str, SituationPatternRecord] = {}
        self._suppressions: dict[str, SituationSuppressionRecord] = {}

    def create_situation(
        self,
        situation_type: SituationType,
        title: str,
        summary: str = "",
        severity: SituationSeverity = SituationSeverity.MEDIUM,
        confidence: float = 1.0,
        initial_signals: Optional[list[SignalRecord]] = None,
        tenant_id: str = "default",
        project_id: Optional[str] = None,
        user_id: Optional[str] = None,
        lifecycle_state: Optional[SituationLifecycleState] = None,
        initial_state: Optional[SituationLifecycleState] = None,
    ) -> SituationRecord:
        """Creates a new canonical SituationRecord initialized with provenance and initial signals."""
        sigs = initial_signals or []
        sig_ids = [s.signal_id for s in sigs]
        entities: set[str] = set()
        for s in sigs:
            if s.subject:
                entities.add(s.subject)
            if s.entity:
                entities.add(s.entity)
        now = utc_now()
        start_state = initial_state or lifecycle_state or SituationLifecycleState.DETECTED
        sit = SituationRecord(
            situation_type=situation_type,
            title=title,
            summary=summary,
            severity=severity,
            confidence=confidence,
            lifecycle_state=start_state,
            signals=sigs,
            signal_ids=sig_ids,
            signal_count=len(sigs),
            first_signal_at=sigs[0].observed_at if sigs else now,
            last_signal_at=sigs[-1].observed_at if sigs else now,
            affected_entities=list(entities),
            scope=tenant_id,
            tenant_id=tenant_id,
            project_id=project_id,
            user_id=user_id or "default_user",
            created_at=now,
            updated_at=now,
        )
        sit.timeline.append(
            SituationTimelineEntry(
                event_type="SITUATION_CREATED",
                summary=f"Situation formed with initial severity {severity.value}. {summary}".strip(),
                timestamp=now,
            )
        )
        return sit

    def can_transition(
        self,
        from_state: SituationLifecycleState,
        to_state: SituationLifecycleState,
    ) -> bool:
        """Evaluates whether state transition satisfies the formal operational matrix."""
        if from_state == to_state:
            return True
        allowed = VALID_SITUATION_TRANSITIONS.get(from_state, set())
        return to_state in allowed

    def transition(
        self,
        situation: SituationRecord,
        target_state: SituationLifecycleState,
        reason: str = "",
    ) -> bool:
        """Executes an auditable lifecycle transition, updating timestamps and recording timeline entry."""
        if not self.can_transition(situation.lifecycle_state, target_state):
            logger.warning(
                "Illegal situation transition attempted: %s -> %s on %s",
                situation.lifecycle_state.value,
                target_state.value,
                situation.situation_id,
            )
            return False

        old_state = situation.lifecycle_state
        situation.lifecycle_state = target_state
        now = utc_now()
        situation.updated_at = now
        situation.version += 1

        if target_state == SituationLifecycleState.RESOLVED:
            situation.resolved_at = now

        situation.timeline.append(
            SituationTimelineEntry(
                event_type="LIFECYCLE_TRANSITION",
                summary=f"State transitioned from {old_state.value} to {target_state.value}. {reason}".strip(),
                timestamp=now,
            )
        )
        return True

    def transition_situation(
        self,
        situation: SituationRecord,
        target_state: SituationLifecycleState,
        actor: str = "",
        reason: str = "",
    ) -> bool:
        full_reason = f"[{actor}] {reason}".strip() if actor else reason
        return self.transition(situation, target_state, reason=full_reason)

    def record_and_check_pattern(self, situation: SituationRecord) -> Optional[SituationPatternRecord]:
        """Recognizes recurring patterns across situations based on entity and type fingerprinting."""
        ent = situation.affected_entities[0] if situation.affected_entities else "system"
        fp = hashlib.sha256(f"{ent}:{situation.situation_type.value}".encode()).hexdigest()[:12]
        now = utc_now()
        if fp in self._patterns:
            pat = self._patterns[fp]
            pat.recurrence_count += 1
            pat.last_observed_at = now
            return pat
        else:
            pat = SituationPatternRecord(
                pattern_id=f"pat_{fp}",
                pattern_name=f"Pattern: {situation.title}",
                situation_type=situation.situation_type,
                pattern_fingerprint=fp,
                recurrence_count=1,
                first_observed_at=now,
                last_observed_at=now,
            )
            self._patterns[fp] = pat
            return pat

    def is_suppressed(self, situation_id: str) -> bool:
        """Returns True if situation is actively suppressed."""
        supp = self._suppressions.get(situation_id)
        if not supp:
            return False
        if not supp.is_active:
            return False
        if supp.expires_at and utc_now() > supp.expires_at:
            supp.is_active = False
            return False
        return True

    def suppress_situation(
        self,
        situation: SituationRecord,
        reason: str,
        duration_seconds: Optional[float] = None,
        suppressed_by: str = "system",
    ) -> SituationSuppressionRecord:
        """Auditably suppresses a situation according to policy."""
        now = utc_now()
        exp = now + timedelta(seconds=duration_seconds) if duration_seconds else None
        supp = SituationSuppressionRecord(
            situation_id=situation.situation_id,
            reason=reason,
            suppressed_by=suppressed_by,
            suppressed_at=now,
            expires_at=exp,
            is_active=True,
        )
        self._suppressions[situation.situation_id] = supp
        self.transition(situation, SituationLifecycleState.SUPPRESSED, reason=f"Suppressed: {reason}")
        return supp

    # =========================================================================
    # MERGE & SPLIT (Section 8)
    # =========================================================================

    def merge_situations(
        self,
        primary: Optional[SituationRecord] = None,
        secondary: Optional[SituationRecord | list[SituationRecord]] = None,
        reason: str = "",
        *,
        primary_situation: Optional[SituationRecord] = None,
        subsumed_situations: Optional[list[SituationRecord]] = None,
    ) -> SituationRecord:
        """Merges secondary situation(s) into primary while strictly preserving audit lineage.

        Invariant: Never destroy secondary identity. Record merged_from_ids and merged_into_id.
        """
        main_primary = primary or primary_situation
        if not main_primary:
            raise ValueError("Primary situation required for merge")
        secondaries: list[SituationRecord] = []
        if subsumed_situations:
            secondaries.extend(subsumed_situations)
        elif isinstance(secondary, list):
            secondaries.extend(secondary)
        elif secondary is not None:
            secondaries.append(secondary)

        now = utc_now()
        for sec in secondaries:
            sec.lifecycle_state = SituationLifecycleState.MERGED
            sec.merged_into_id = main_primary.situation_id
            sec.updated_at = now
            sec.version += 1
            sec.timeline.append(
                SituationTimelineEntry(
                    event_type="SITUATION_MERGED_INTO",
                    summary=f"Merged into situation '{main_primary.situation_id}'. Reason: {reason}",
                    timestamp=now,
                )
            )

            if sec.situation_id not in main_primary.merged_from_ids:
                main_primary.merged_from_ids.append(sec.situation_id)

            existing_sig_ids = {s.signal_id for s in main_primary.signals}
            for sig in sec.signals:
                if sig.signal_id not in existing_sig_ids:
                    main_primary.signals.append(sig)
                    existing_sig_ids.add(sig.signal_id)

            for ent in sec.affected_entities:
                if ent not in main_primary.affected_entities:
                    main_primary.affected_entities.append(ent)

            for srv in sec.affected_services:
                if srv not in main_primary.affected_services:
                    main_primary.affected_services.append(srv)

            main_primary.last_signal_at = max(main_primary.last_signal_at, sec.last_signal_at)
            main_primary.timeline.append(
                SituationTimelineEntry(
                    event_type="SITUATION_MERGED_FROM",
                    summary=f"Subsumed situation '{sec.situation_id}'. Reason: {reason}",
                    timestamp=now,
                )
            )

        main_primary.signal_count = len(main_primary.signals)
        main_primary.source_count = len({s.source_type for s in main_primary.signals})
        main_primary.merge_reason = reason
        main_primary.updated_at = now
        main_primary.version += 1
        return main_primary

    def split_situation(
        self,
        parent: Optional[SituationRecord] = None,
        partition_a_signal_ids: Optional[list[str]] = None,
        partition_b_signal_ids: Optional[list[str]] = None,
        split_reason: str = "",
        *,
        parent_situation: Optional[SituationRecord] = None,
        sub_situation_specs: Optional[list[dict[str, Any]]] = None,
        reason: str = "",
    ) -> tuple[SituationRecord, SituationRecord] | list[SituationRecord]:
        """Splits parent situation into distinct situations when evidence diverges, preserving lineage."""
        main_parent = parent or parent_situation
        if not main_parent:
            raise ValueError("Parent situation required for split")
        actual_reason = split_reason or reason
        now = utc_now()

        # Mark parent as SPLIT
        main_parent.lifecycle_state = SituationLifecycleState.SPLIT
        main_parent.updated_at = now
        main_parent.version += 1
        main_parent.timeline.append(
            SituationTimelineEntry(
                event_type="SITUATION_SPLIT",
                summary=f"Situation split into independent situations. Reason: {actual_reason}",
                timestamp=now,
            )
        )

        if sub_situation_specs:
            children: list[SituationRecord] = []
            for spec in sub_situation_specs:
                child = SituationRecord(
                    situation_id=generate_uuid("sit"),
                    title=spec.get("title", f"{main_parent.title} (Sub)"),
                    summary=spec.get("summary", actual_reason),
                    situation_type=spec.get("situation_type", main_parent.situation_type),
                    lifecycle_state=SituationLifecycleState.DETECTED,
                    severity=spec.get("severity", main_parent.severity),
                    scope=main_parent.scope,
                    split_from_id=main_parent.situation_id,
                    parent_situation_id=main_parent.situation_id,
                    signals=[],
                    signal_count=0,
                    source_count=0,
                    created_at=now,
                    updated_at=now,
                )
                children.append(child)
            return children

        part_a = partition_a_signal_ids or []
        part_b = partition_b_signal_ids or []
        signals_a = [s for s in main_parent.signals if s.signal_id in part_a]
        child_a = SituationRecord(
            situation_id=generate_uuid("sit"),
            title=f"{main_parent.title} (Branch A)",
            summary=f"Split branch A from '{main_parent.situation_id}': {actual_reason}",
            situation_type=main_parent.situation_type,
            lifecycle_state=SituationLifecycleState.ACTIVE,
            severity=main_parent.severity,
            scope=main_parent.scope,
            split_from_id=main_parent.situation_id,
            parent_situation_id=main_parent.situation_id,
            signals=signals_a,
            signal_count=len(signals_a),
            source_count=len({s.source_type for s in signals_a}),
            affected_entities=list({s.subject for s in signals_a if s.subject}),
            created_at=now,
            updated_at=now,
        )

        signals_b = [s for s in main_parent.signals if s.signal_id in part_b]
        child_b = SituationRecord(
            situation_id=generate_uuid("sit"),
            title=f"{main_parent.title} (Branch B)",
            summary=f"Split branch B from '{main_parent.situation_id}': {actual_reason}",
            situation_type=main_parent.situation_type,
            lifecycle_state=SituationLifecycleState.ACTIVE,
            severity=main_parent.severity,
            scope=main_parent.scope,
            split_from_id=main_parent.situation_id,
            parent_situation_id=main_parent.situation_id,
            signals=signals_b,
            signal_count=len(signals_b),
            source_count=len({s.source_type for s in signals_b}),
            affected_entities=list({s.subject for s in signals_b if s.subject}),
            created_at=now,
            updated_at=now,
        )

        return child_a, child_b

    # =========================================================================
    # PATTERN RECOGNITION & RECURRENCE (Section 46, 47)
    # =========================================================================

    def track_recurrence_pattern(self, situation: SituationRecord) -> Optional[SituationPatternRecord]:
        """Calculates stable pattern identity across historical recurrences without collapsing independent incidents."""
        # Compute fingerprint based on situation_type + affected entities
        key_parts = [situation.situation_type.value, situation.scope]
        if situation.affected_entities:
            key_parts.extend(sorted(situation.affected_entities)[:3])
        elif situation.title:
            key_parts.append(situation.title[:30])

        fp = hashlib.sha256(":".join(key_parts).encode("utf-8")).hexdigest()[:16]
        now = utc_now()

        if fp in self._patterns:
            pat = self._patterns[fp]
            pat.recurrence_count += 1
            interval = (now - pat.last_observed_at).total_seconds()
            if pat.recurrence_count > 2:
                pat.average_interval_seconds = (
                    (pat.average_interval_seconds * (pat.recurrence_count - 2)) + interval
                ) / (pat.recurrence_count - 1)
            else:
                pat.average_interval_seconds = interval
            pat.last_observed_at = now
            if interval < 300:
                pat.trend = "ESCALATING"
            situation.recurrence_count = pat.recurrence_count
            return pat

        pat = SituationPatternRecord(
            pattern_id=f"pat_{fp}",
            pattern_name=f"Recurring {situation.situation_type.value} on {situation.affected_entities or [situation.title]}",
            situation_type=situation.situation_type,
            pattern_fingerprint=fp,
            recurrence_count=1,
            first_observed_at=now,
            last_observed_at=now,
            average_interval_seconds=0.0,
            trend="STABLE",
        )
        self._patterns[fp] = pat
        return pat

    # =========================================================================
    # SUPPRESSION & COOLDOWN (Section 22)
    # =========================================================================

    def suppress(
        self,
        situation: SituationRecord,
        reason: str,
        duration_seconds: Optional[float] = None,
        suppressed_by: str = "user",
    ) -> SituationSuppressionRecord:
        """Suppresses situation while keeping underlying signals fully auditable."""
        now = utc_now()
        exp = now + timedelta(seconds=duration_seconds) if duration_seconds else None

        supp = SituationSuppressionRecord(
            situation_id=situation.situation_id,
            reason=reason,
            suppressed_by=suppressed_by,
            suppressed_at=now,
            expires_at=exp,
            cooldown_seconds=duration_seconds,
            is_active=True,
        )
        self._suppressions[situation.situation_id] = supp
        self.transition(situation, SituationLifecycleState.SUPPRESSED, reason=f"Suppressed by {suppressed_by}: {reason}")
        return supp

    def is_suppressed(self, situation_id: str, now: Optional[datetime] = None) -> bool:
        """Checks whether situation is actively suppressed, expiring outdated suppressions."""
        supp = self._suppressions.get(situation_id)
        if not supp or not supp.is_active:
            return False
        current_time = now or utc_now()
        if supp.expires_at and current_time >= supp.expires_at:
            supp.is_active = False
            return False
        return True


# Global lifecycle manager instance
situation_lifecycle_manager = SituationLifecycleManager()
