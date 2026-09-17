"""Autonomous World-State Reconstruction, State Estimation & Reality Synchronization Engine (Task 98).

Enforces:
- OBSERVATION != TRUTH
- EXPECTED STATE != ACTUAL STATE
- MISSING DATA != NO CHANGE
- STALE != CURRENT
- DRIFT != CAUSE
- CORRELATION != CAUSATION
- SIMULATION != REALITY
- EXECUTION != VERIFIED STATE
- UNKNOWN MUST REMAIN UNKNOWN
- CONFLICT MUST REMAIN VISIBLE
- HISTORICAL STATE MUST REMAIN RECONSTRUCTABLE
- UNATTRIBUTED CHANGE MUST NOT RECEIVE A FABRICATED ACTOR
- EMERGENCY STOP ALWAYS WINS
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta, timezone
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from app.events.bus import get_event_bus
from app.knowledge_graph.reasoning_engine import get_graph_reasoning_engine
from app.security.emergency_stop import get_emergency_stop_service
from app.world_state.domain import (
    CertaintyTier,
    DriftClassification,
    DriftSeverity,
    DriftStatus,
    DriftType,
    EpistemicCertainty,
    ExpectationMatchOutcome,
    ExpectedState,
    FreshnessState,
    RevalidationCandidate,
    StateAttributeRecord,
    StateConflictRecord,
    StateDiffType,
    StateDriftRecord,
    StateInvariantViolation,
    StateObservation,
    StateStatus,
    WorldScope,
    WorldStateDiff,
    WorldStateEntity,
    WorldStateSnapshot,
    generate_uuid,
    utc_now,
)
from app.world_state.drift_engine import DriftEngine
from app.world_state.lifecycle import InvariantEngine, StateLifecycleValidator

logger = logging.getLogger("kairo.world_state.reconciliation")


class WorldStateReconciliationEngine:
    """Core autonomous reality synchronization, state estimation, and drift reconciliation substrate."""

    def __init__(self) -> None:
        self._entities: dict[str, WorldStateEntity] = {}
        self._observations: list[StateObservation] = []
        self._expected_states: dict[str, ExpectedState] = {}
        self._conflicts: dict[str, StateConflictRecord] = {}
        self._revalidation_candidates: dict[str, RevalidationCandidate] = {}
        self._snapshots: dict[str, WorldStateSnapshot] = {}
        self._entity_history: dict[str, list[dict[str, Any]]] = {}
        self._canonical_aliases: dict[str, str] = {}
        self._known_transactions: list[dict[str, Any]] = []

        self._drift_engine = DriftEngine()
        self._emergency_stop = get_emergency_stop_service()
        self._event_bus = get_event_bus()
        self._lock = asyncio.Lock()

    def reset(self) -> None:
        """Reset internal in-memory state (primarily for isolated test fixtures)."""
        self._entities.clear()
        self._observations.clear()
        self._expected_states.clear()
        self._conflicts.clear()
        self._revalidation_candidates.clear()
        self._snapshots.clear()
        self._entity_history.clear()
        self._canonical_aliases.clear()
        self._known_transactions.clear()

    # =========================================================================
    # 1. ENTITY RESOLUTION & REGISTRATION (Phase 8)
    # =========================================================================

    def register_canonical_alias(self, alias: str, canonical_id: str) -> None:
        """Registers a verified alias mapping to a canonical entity identifier."""
        norm_alias = alias.strip().lower()
        self._canonical_aliases[norm_alias] = canonical_id

    def resolve_canonical_id(self, identifier: str) -> str:
        """Maps an identifier or alias to its canonical entity ID without ambiguous fuzzy merging."""
        norm_id = identifier.strip().lower()
        if norm_id in self._canonical_aliases:
            return self._canonical_aliases[norm_id]
        # Return direct identifier if no alias registered
        return identifier

    def register_entity(
        self,
        entity_id: str,
        canonical_name: Union[str, WorldScope] = "",
        scope: Union[WorldScope, str] = WorldScope.SYSTEM,
        status: StateStatus = StateStatus.CURRENT,
        sensitivity: str = "INTERNAL",
        expected_update_interval_seconds: float = 300.0,
        metadata: Optional[dict[str, Any]] = None,
        user_id: str = "default_user",
        project_id: Optional[str] = None,
        registered_at: Optional[datetime] = None,
    ) -> WorldStateEntity:
        """Declares an authorized entity in the world state substrate."""
        # Support flexible argument ordering for (entity_id, scope, canonical_name)
        if isinstance(canonical_name, WorldScope):
            actual_scope = canonical_name
            actual_name = str(scope) if scope is not None and not isinstance(scope, WorldScope) else entity_id
        elif isinstance(scope, WorldScope):
            actual_scope = scope
            actual_name = str(canonical_name) if canonical_name else entity_id
        else:
            try:
                actual_scope = WorldScope(str(canonical_name).upper())
                actual_name = str(scope) if scope is not None else entity_id
            except (ValueError, KeyError):
                try:
                    actual_scope = WorldScope(str(scope).upper())
                except (ValueError, KeyError):
                    actual_scope = WorldScope.SYSTEM
                actual_name = str(canonical_name) if canonical_name else entity_id

        canonical_id = self.resolve_canonical_id(entity_id)
        now = utc_now()
        reg_time = registered_at or now
        ent = WorldStateEntity(
            entity_id=canonical_id,
            canonical_name=actual_name,
            canonical_key=f"{actual_scope.value.lower()}:{actual_name.lower().replace(' ', '_')}",
            scope=actual_scope,
            status=status,
            epistemic_certainty=EpistemicCertainty.OBSERVED,
            confidence=1.0,
            observation_confidence=1.0,
            verification_confidence=1.0,
            freshness=FreshnessState.FRESH,
            last_observed_at=reg_time,
            next_expected_observation=reg_time + timedelta(seconds=expected_update_interval_seconds),
            expected_update_interval_seconds=expected_update_interval_seconds,
            attributes={},
            active_drift_ids=[],
            active_conflict_ids=[],
            provenance={"created_by": "registration", "timestamp": now.isoformat()},
            version=1,
            sensitivity=sensitivity,
            user_id=user_id,
            project_id=project_id,
            metadata=metadata or {},
        )
        self._entities[canonical_id] = ent
        self.register_canonical_alias(actual_name, canonical_id)
        self._record_history(ent, "ENTITY_REGISTERED", {"canonical_name": actual_name})
        return ent

    # =========================================================================
    # 2. OBSERVATION INGESTION & RECONCILIATION (Phases 3, 9, 34, 35)
    # =========================================================================

    async def ingest_observation(
        self,
        source: Union[StateObservation, str],
        source_id: str = "",
        entity_id: str = "",
        observed_value: Any = None,
        attribute_name: str = "state",
        observed_at: Optional[datetime] = None,
        confidence: float = 1.0,
        certainty: CertaintyTier = CertaintyTier.KNOWN,
        sensitivity: str = "INTERNAL",
        scope: WorldScope = WorldScope.SYSTEM,
        correlation_id: Optional[str] = None,
        provenance: Optional[dict[str, Any]] = None,
    ) -> Any:
        """Ingests and epistemically evaluates an observation from an authorized source."""
        now = utc_now()
        if isinstance(source, StateObservation):
            obs = source
            canonical_id = self.resolve_canonical_id(obs.canonical_id or obs.entity_id)
            scope = obs.scope
            sensitivity = obs.sensitivity
        else:
            canonical_id = self.resolve_canonical_id(entity_id)
            obs = StateObservation(
                observation_id=generate_uuid("obs"),
                source=source,
                source_id=source_id,
                entity_id=canonical_id,
                observed_value=observed_value,
                observed_at=observed_at or now,
                received_at=now,
                provenance=provenance or {"source": source, "source_id": source_id},
                confidence=confidence,
                certainty=certainty,
                freshness=FreshnessState.FRESH,
                sensitivity=sensitivity,
                validation_status="RAW",
                correlation_id=correlation_id,
                scope=scope,
            )

        self._observations.append(obs)

        # Check emergency stop
        if self._emergency_stop.is_stopped():
            logger.warning("Emergency stop active: Observation %s ingested in read-only mode; state mutation blocked.", obs.observation_id)
            return WorldStateEntity(
                entity_id=canonical_id,
                canonical_name=canonical_id,
                scope=scope,
                status=StateStatus.UNKNOWN,
                epistemic_certainty=EpistemicCertainty.UNKNOWN,
                confidence=0.0,
                observation_confidence=0.0,
                verification_confidence=0.0,
                freshness=FreshnessState.UNKNOWN,
            )

        # Update or create entity state
        entity = self._entities.get(canonical_id)
        if not entity:
            entity = self.register_entity(
                entity_id=canonical_id,
                canonical_name=canonical_id,
                scope=scope,
                status=StateStatus.CURRENT,
                sensitivity=sensitivity,
                registered_at=obs.observed_at,
            )

        # Reconcile attribute observation
        if isinstance(obs.observed_value, dict):
            for k, v in obs.observed_value.items():
                self._reconcile_attribute(entity, k, obs, value_override=v)
        else:
            self._reconcile_attribute(entity, attribute_name, obs)

        return entity

    def _reconcile_attribute(
        self,
        entity: WorldStateEntity,
        attr_name: str,
        obs: StateObservation,
        value_override: Any = None,
    ) -> None:
        """Reconciles incoming observation with existing attribute state, detecting conflicts."""
        now = utc_now()
        effective_value = value_override if value_override is not None else obs.observed_value
        existing_attr = entity.attributes.get(attr_name)

        if not existing_attr:
            # First observation of this attribute
            entity.attributes[attr_name] = StateAttributeRecord(
                attribute_name=attr_name,
                current_value=effective_value,
                previous_value=None,
                confidence=obs.confidence,
                certainty=obs.certainty,
                observed_at=obs.observed_at,
                valid_from=obs.observed_at,
                valid_until=None,
                source=obs.source_id or obs.source,
                evidence=[obs.observation_id],
                source_count=1,
            )
            entity.last_observed_at = obs.observed_at
            elapsed = (now - obs.observed_at).total_seconds()
            if elapsed > entity.expected_update_interval_seconds:
                entity.freshness = FreshnessState.STALE
            else:
                entity.freshness = FreshnessState.FRESH
            entity.next_expected_observation = obs.observed_at + timedelta(seconds=entity.expected_update_interval_seconds)
            entity.version += 1
            self._record_history(entity, "ATTRIBUTE_INITIALIZED", {"attribute": attr_name, "value": effective_value}, timestamp=obs.observed_at)
            return

        # Check for disagreement/conflict
        if existing_attr.current_value != effective_value:
            obs_src = obs.source_id or obs.source
            time_diff = abs((obs.observed_at - existing_attr.observed_at).total_seconds())

            # If two distinct sources disagree within a short time window (e.g. concurrent probes), record dialectic contradiction
            if existing_attr.source != obs_src and time_diff < 300:
                conflict_id = generate_uuid("conf")
                conflict = StateConflictRecord(
                    conflict_id=conflict_id,
                    entity_id=entity.entity_id,
                    attribute_name=attr_name,
                    observations=[
                        StateObservation(
                            source=existing_attr.source,
                            source_id=existing_attr.source,
                            entity_id=entity.entity_id,
                            observed_value=existing_attr.current_value,
                            observed_at=existing_attr.observed_at,
                            confidence=existing_attr.confidence,
                        ),
                        obs,
                    ],
                    resolution_state="OPEN",
                    detected_at=now,
                )
                self._conflicts[conflict_id] = conflict
                entity.active_conflict_ids.append(conflict_id)
                entity.status = StateStatus.CONFLICTED
                self._record_history(entity, "CONFLICT_DETECTED", {"conflict_id": conflict_id, "attribute": attr_name}, timestamp=obs.observed_at)
            else:
                # Value updated over time without active action transaction: detect drift
                prev = existing_attr.current_value
                existing_attr.previous_value = prev
                existing_attr.current_value = effective_value
                existing_attr.source = obs_src
                existing_attr.confidence = obs.confidence
                existing_attr.observed_at = obs.observed_at
                existing_attr.evidence.append(obs.observation_id)
                existing_attr.source_count += 1
                entity.version += 1

                # Check known action transactions
                tx = next((t for t in self._known_transactions if t.get("target_id") == entity.entity_id), None)
                drift = StateDriftRecord(
                    entity_id=entity.entity_id,
                    scope=entity.scope,
                    attribute_name=attr_name,
                    drift_type=DriftType.VALUE_DIVERGENCE,
                    severity=DriftSeverity.MEDIUM,
                    classification=DriftClassification.ACTIONABLE_DRIFT if tx else DriftClassification.UNATTRIBUTED_CHANGE,
                    status=DriftStatus.DETECTED,
                    expected_value=prev,
                    actual_value=effective_value,
                    attributed_source_type="ACTION_TRANSACTION" if tx else "UNATTRIBUTED_CHANGE",
                    attributed_source_id=tx.get("action_id") if tx else None,
                    evidence=[
                        f"Action '{tx.get('action_id')}' updated '{attr_name}'"
                        if tx else
                        f"Attribute '{attr_name}' changed from {prev} to {effective_value} without registered action transaction"
                    ],
                )
                self._drift_engine._active_drifts.append(drift)
                entity.active_drift_ids.append(drift.drift_id)
                self._record_history(entity, "ATTRIBUTE_CHANGED", {"attribute": attr_name, "value": effective_value, "prev": prev}, timestamp=obs.observed_at)
        else:
            # Corroborating observation reinforces confidence
            existing_attr.source_count += 1
            existing_attr.confidence = min(1.0, existing_attr.confidence + 0.02)
            existing_attr.observed_at = obs.observed_at
            existing_attr.evidence.append(obs.observation_id)
            entity.last_observed_at = now
            entity.freshness = FreshnessState.FRESH

    # =========================================================================
    # 3. EXPECTED STATE & DRIFT RECONCILIATION (Phases 4, 10, 19, 20)
    # =========================================================================

    def declare_expected_state(
        self,
        entity_id_or_expected: Union[ExpectedState, str],
        expected_value: Any = None,
        expected_by: str = "ActionTransaction",
        source_type: str = "ACTION_POSTCONDITION",
        source_id: str = "",
        tolerance: Any = 0.0,
        valid_from: Optional[datetime] = None,
        valid_until: Optional[datetime] = None,
        scope: WorldScope = WorldScope.SYSTEM,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ExpectedState:
        """Declares an explicit expected state postcondition or contract constraint."""
        if self._emergency_stop.is_stopped():
            raise RuntimeError("Emergency Stop active: Cannot declare expected state")

        if isinstance(entity_id_or_expected, ExpectedState):
            expected = entity_id_or_expected
            canonical_id = self.resolve_canonical_id(expected.canonical_id)
            expected.entity_id = canonical_id
            self._expected_states[canonical_id] = expected
            return expected

        canonical_id = self.resolve_canonical_id(entity_id_or_expected)
        now = utc_now()
        expected = ExpectedState(
            expected_id=generate_uuid("exp"),
            entity_id=canonical_id,
            expected_value=expected_value,
            expected_by=expected_by,
            source_type=source_type,
            source_id=source_id,
            tolerance=tolerance,
            valid_from=valid_from or now,
            valid_until=valid_until,
            scope=scope,
            metadata=metadata or {},
        )
        self._expected_states[canonical_id] = expected
        return expected

    def register_operational_transaction(
        self,
        transaction_id: str,
        target_id: str,
        transaction_type: str = "ACTION_TRANSACTION",
        expected_state: Optional[Any] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Registers an active operational action or transaction for change attribution."""
        self._known_transactions.append({
            "action_id": transaction_id,
            "transaction_id": transaction_id,
            "target_id": self.resolve_canonical_id(target_id),
            "type": transaction_type,
            "action_type": transaction_type,
            "expected_postconditions": expected_state or {},
            "expected_state": expected_state,
            "timestamp": utc_now().isoformat(),
            "metadata": metadata or {},
        })

    def register_action_transaction(
        self,
        action_id: str,
        action_type: str,
        target_entity_id: str,
        expected_postconditions: dict[str, Any],
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Alias registering an action transaction with explicit expected postconditions."""
        self._known_transactions.append({
            "action_id": action_id,
            "transaction_id": action_id,
            "target_id": self.resolve_canonical_id(target_entity_id),
            "type": action_type,
            "action_type": action_type,
            "expected_postconditions": expected_postconditions,
            "expected_state": expected_postconditions,
            "timestamp": utc_now().isoformat(),
            "metadata": metadata or {},
        })

    async def reconcile_expectations(
        self,
        entity_id: Optional[str] = None,
        causal_bridge: Optional[Any] = None,
    ) -> list[Tuple[ExpectedState, ExpectationMatchOutcome, list[StateDriftRecord]]]:
        """Compares declared expected states against current actual states, detecting and recording drift."""
        if self._emergency_stop.is_stopped():
            raise RuntimeError("Emergency Stop active: Cannot reconcile expectations")

        results: list[Tuple[ExpectedState, ExpectationMatchOutcome, list[StateDriftRecord]]] = []
        targets = [self.resolve_canonical_id(entity_id)] if entity_id else list(self._expected_states.keys())

        for ent_id in targets:
            expected = self._expected_states.get(ent_id)
            if not expected:
                continue

            actual_entity = self._entities.get(ent_id)
            if not actual_entity:
                results.append((expected, ExpectationMatchOutcome.UNKNOWN, []))
                continue

            drift_records: list[StateDriftRecord] = []
            exp_attrs = expected.expected_value if isinstance(expected.expected_value, dict) else {"state": expected.expected_value}
            tol_map = expected.tolerance if isinstance(expected.tolerance, dict) else {}
            default_tol = expected.tolerance if isinstance(expected.tolerance, (int, float)) else 0.0

            for attr_name, exp_val in exp_attrs.items():
                attr_rec = actual_entity.attributes.get(attr_name)
                act_val = attr_rec.value if attr_rec else None
                tol = tol_map.get(attr_name, default_tol)

                is_match = False
                if act_val is not None:
                    if isinstance(exp_val, (int, float)) and isinstance(act_val, (int, float)):
                        is_match = abs(exp_val - act_val) <= tol
                    else:
                        is_match = (exp_val == act_val)

                if not is_match:
                    severity = DriftSeverity.HIGH if attr_name in ("status", "security") or (isinstance(exp_val, (int, float)) and isinstance(act_val, (int, float)) and abs(exp_val - act_val) > 100) else DriftSeverity.MEDIUM
                    drift = StateDriftRecord(
                        entity_id=ent_id,
                        scope=expected.scope,
                        attribute_name=attr_name,
                        drift_type=DriftType.VALUE_DIVERGENCE if act_val is not None else DriftType.STATE_DRIFT,
                        severity=severity,
                        classification=DriftClassification.ACTIONABLE_DRIFT,
                        status=DriftStatus.DETECTED,
                        expected_value=exp_val,
                        actual_value=act_val,
                        evidence=[f"Attribute '{attr_name}' expected {exp_val} but observed {act_val}"],
                    )
                    self._drift_engine._active_drifts.append(drift)
                    actual_entity.active_drift_ids.append(drift.drift_id)
                    drift_records.append(drift)

            if drift_records:
                actual_entity.status = StateStatus.DRIFTED
                results.append((expected, ExpectationMatchOutcome.DRIFT_DETECTED, drift_records))
            else:
                results.append((expected, ExpectationMatchOutcome.MATCHED, []))

        return results

    async def verify_post_action(
        self,
        action_id: str,
        target_entity_id: Optional[str] = None,
        expected_postconditions: Optional[Any] = None,
    ) -> dict[str, Any]:
        """EXECUTION != VERIFIED STATE (Phase 20 & 31).
        Verifies if actual observed state satisfies expected postconditions."""
        tx = next((t for t in self._known_transactions if t.get("action_id") == action_id or t.get("transaction_id") == action_id), None)
        target_id = target_entity_id or (tx.get("target_id") if tx else None)
        if not target_id:
            return {"verified": False, "outcome": "UNKNOWN_ACTION", "mismatches": {}}

        canonical_id = self.resolve_canonical_id(target_id)
        entity = self._entities.get(canonical_id)
        if not entity:
            return {"verified": False, "outcome": "TARGET_ENTITY_NOT_FOUND", "mismatches": {}}

        postconditions = expected_postconditions or (tx.get("expected_postconditions") if tx else {})
        mismatches: dict[str, dict[str, Any]] = {}

        if isinstance(postconditions, dict):
            for k, exp_val in postconditions.items():
                attr_rec = entity.attributes.get(k)
                act_val = attr_rec.value if attr_rec else None
                if act_val != exp_val:
                    mismatches[k] = {"expected": exp_val, "actual": act_val}

        if mismatches:
            return {
                "verified": False,
                "outcome": "FAILED_POSTCONDITION_MISMATCH",
                "mismatches": mismatches,
            }

        return {
            "verified": True,
            "outcome": "VERIFIED_POSTCONDITION_MATCH",
            "mismatches": {},
        }

    # =========================================================================
    # 4. REVALIDATION & IMPACT PROPAGATION (Phases 29, 30)
    # =========================================================================

    def schedule_revalidation(
        self,
        entity_id: str,
        target_type: str,
        reason: str,
        drift_id: Optional[str] = None,
        priority: str = "NORMAL",
    ) -> RevalidationCandidate:
        """Schedules a bounded revalidation candidate for downstream dependencies."""
        cand_id = generate_uuid("rev")
        candidate = RevalidationCandidate(
            candidate_id=cand_id,
            entity_id=self.resolve_canonical_id(entity_id),
            target_type=target_type,
            reason=reason,
            drift_id=drift_id,
            priority=priority,
            created_at=utc_now(),
            status="PENDING",
        )
        self._revalidation_candidates[cand_id] = candidate
        logger.info("Scheduled revalidation candidate %s on %s: %s (priority: %s)", cand_id, entity_id, reason, priority)
        return candidate

    async def propagate_change_impact(
        self,
        modified_entity_id: Optional[str] = None,
        change_description: Optional[str] = None,
        entity_id: Optional[str] = None,
    ) -> list[str]:
        """Phase 30: Uses Task 97 Knowledge Graph reasoning to identify dependent entities requiring revalidation."""
        target_id = entity_id or modified_entity_id or ""
        canonical_id = self.resolve_canonical_id(target_id)
        kg_engine = get_graph_reasoning_engine()
        impacted_nodes: list[str] = []

        try:
            impact_res = kg_engine.analyze_downstream_impact(canonical_id, max_depth=4)
            for imp in impact_res.impacted_nodes:
                nid = imp.node_id if hasattr(imp, "node_id") else imp.get("node_id")
                if nid and nid != canonical_id:
                    impacted_nodes.append(nid)
                    # Mark stale in world state if present
                    if nid in self._entities:
                        self._entities[nid].status = StateStatus.STALE
                        self._entities[nid].freshness = FreshnessState.STALE
                        self.schedule_revalidation(
                            entity_id=nid,
                            target_type="DEPENDENT_ENTITY",
                            reason=f"Upstream entity '{canonical_id}' mutated ({change_description or 'state change'}); revalidation required.",
                            priority="HIGH",
                        )
        except Exception as ex:
            logger.debug("Knowledge graph propagation lookup skipped: %s", ex)

        # Always schedule revalidation for the primary mutated entity
        self.schedule_revalidation(
            entity_id=canonical_id,
            target_type="CAPABILITY" if "cap" in canonical_id else "STATE",
            reason=f"Primary entity mutated: {change_description or 'state change'}",
            priority="HIGH",
        )
        return impacted_nodes

    def get_entity(self, entity_id: str) -> Optional[WorldStateEntity]:
        """Looks up an entity by canonical ID or alias."""
        canonical_id = self.resolve_canonical_id(entity_id)
        return self._entities.get(canonical_id)

    def get_entities(self, scope: Optional[WorldScope] = None) -> list[WorldStateEntity]:
        """Returns registered entities, optionally filtered by operational scope."""
        if not scope or scope == WorldScope.SYSTEM:
            return list(self._entities.values())
        return [e for e in self._entities.values() if e.scope == scope]

    def get_conflicts(self, scope: Optional[WorldScope] = None) -> list[StateConflictRecord]:
        """Returns preserved dialectic contradictions, optionally filtered by scope."""
        if not scope or scope == WorldScope.SYSTEM:
            return list(self._conflicts.values())
        return [
            c for c in self._conflicts.values()
            if self._entities.get(c.entity_id) and self._entities[c.entity_id].scope == scope
        ]

    def get_revalidation_candidates(self, status: Optional[str] = None) -> list[RevalidationCandidate]:
        """Returns scheduled revalidation candidates, optionally filtered by status."""
        if not status:
            return list(self._revalidation_candidates.values())
        return [r for r in self._revalidation_candidates.values() if r.status == status]

    # =========================================================================
    # 5. SNAPSHOTS, DIFFS & HISTORICAL RECONSTRUCTION (Phases 31, 32, 33)
    # =========================================================================

    def create_snapshot(
        self,
        scope: WorldScope = WorldScope.SYSTEM,
        description: str = "",
        label: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> WorldStateSnapshot:
        """Captures an immutable, versioned reference snapshot of current active world state."""
        now = utc_now()
        scoped_entities = {
            eid: ent for eid, ent in self._entities.items()
            if scope == WorldScope.SYSTEM or ent.scope == scope
        }

        raw_state = {eid: e.model_dump(mode="json") for eid, e in scoped_entities.items()}
        state_hash = hashlib.sha256(json.dumps(raw_state, sort_keys=True).encode("utf-8")).hexdigest()

        snap_id = generate_uuid("snap")
        snap = WorldStateSnapshot(
            snapshot_id=snap_id,
            scope=scope,
            created_at=now,
            entity_count=len(scoped_entities),
            entities=raw_state,
            integrity_hash=state_hash,
            description=description or label or f"Snapshot of {scope.value} state",
        )
        self._snapshots[snap_id] = snap
        return snap

    def compute_diff(self, snapshot_a_id: str, snapshot_b_id: str) -> WorldStateDiff:
        """Computes structural differential (ADDED, REMOVED, CHANGED, UNCHANGED) between two snapshots."""
        snap_a = self._snapshots.get(snapshot_a_id)
        snap_b = self._snapshots.get(snapshot_b_id)
        if not snap_a or not snap_b:
            raise KeyError(f"Snapshot '{snapshot_a_id}' or '{snapshot_b_id}' not found.")

        keys_a = set(snap_a.entities.keys())
        keys_b = set(snap_b.entities.keys())

        added = list(keys_b - keys_a)
        removed = list(keys_a - keys_b)
        common = keys_a & keys_b

        changed: dict[str, dict[str, Any]] = {}
        unchanged: list[str] = []

        for k in common:
            ent_a_data = snap_a.entities[k]
            ent_b_data = snap_b.entities[k]
            diffs: dict[str, dict[str, Any]] = {}

            # Status check
            status_a = ent_a_data.get("status")
            status_b = ent_b_data.get("status")
            if status_a != status_b:
                diffs["status"] = {"old": status_a, "new": status_b}

            # Attribute checks
            attrs_a = ent_a_data.get("attributes", {})
            attrs_b = ent_b_data.get("attributes", {})
            all_attr_keys = set(attrs_a.keys()) | set(attrs_b.keys())

            for ak in all_attr_keys:
                rec_a = attrs_a.get(ak, {})
                rec_b = attrs_b.get(ak, {})
                va = rec_a.get("current_value") if isinstance(rec_a, dict) else getattr(rec_a, "current_value", rec_a)
                vb = rec_b.get("current_value") if isinstance(rec_b, dict) else getattr(rec_b, "current_value", rec_b)
                if va != vb:
                    diffs[ak] = {"old": va, "new": vb}

            if diffs:
                changed[k] = diffs
            else:
                unchanged.append(k)

        diff_id = generate_uuid("diff")
        return WorldStateDiff(
            diff_id=diff_id,
            from_state_id=snapshot_a_id,
            to_state_id=snapshot_b_id,
            added_entities=added,
            removed_entities=removed,
            changed_entities=changed,
            unchanged_entities=unchanged,
            detected_drift_ids=[],
            computed_at=utc_now(),
        )

    def reconstruct_historical_state(
        self,
        target_timestamp: datetime,
        scope: Optional[WorldScope] = None,
    ) -> dict[str, Any]:
        """Phase 33: Given timestamp T, reconstructs the best-supported state at T.
        Invariant: Never fill missing information with guesses. Missing state remains UNKNOWN!
        """
        def _to_utc(dt: datetime) -> datetime:
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)

        target_ts = _to_utc(target_timestamp)
        reconstructed_entities: dict[str, Any] = {}

        # Collect all entities in scope
        all_eids = set(self._entities.keys()) | set(self._entity_history.keys())
        for obs in self._observations:
            all_eids.add(obs.canonical_id)

        for eid in all_eids:
            ent = self._entities.get(eid)
            ent_scope = ent.scope if ent else WorldScope.SYSTEM
            if scope and ent_scope != scope and scope != WorldScope.SYSTEM:
                continue

            # Check history entries first
            history = self._entity_history.get(eid, [])
            valid_history = []
            for h in history:
                try:
                    ht = _to_utc(datetime.fromisoformat(h["timestamp"]))
                    if ht <= target_ts:
                        valid_history.append((ht, h))
                except Exception:
                    pass

            # Also check observations directly
            valid_obs = []
            for o in self._observations:
                if o.canonical_id == eid:
                    ot = _to_utc(o.observed_at)
                    if ot <= target_ts:
                        valid_obs.append((ot, o))

            if not valid_history and not valid_obs:
                reconstructed_entities[eid] = {
                    "entity_id": eid,
                    "status": StateStatus.UNKNOWN.value,
                    "epistemic_certainty": EpistemicCertainty.UNKNOWN.value,
                    "attributes": {},
                    "reason": "No observations recorded on or before requested timestamp.",
                }
                continue

            # Build reconstructed attributes up to target_ts
            attrs: dict[str, Any] = {}
            # If we have history entries with state_summary
            if valid_history:
                valid_history.sort(key=lambda x: x[0])
                latest_h = valid_history[-1][1]
                for k, v in latest_h.get("state_summary", {}).get("attributes", {}).items():
                    attrs[k] = {"value": v}

            # Overlay or seed from observations
            if valid_obs:
                valid_obs.sort(key=lambda x: x[0])
                for ot, o in valid_obs:
                    if isinstance(o.observed_value, dict):
                        for k, v in o.observed_value.items():
                            attrs[k] = {"value": v, "observed_at": ot.isoformat(), "confidence": o.confidence}
                    else:
                        attrs[o.attribute_name] = {"value": o.observed_value, "observed_at": ot.isoformat(), "confidence": o.confidence}

            reconstructed_entities[eid] = {
                "entity_id": eid,
                "status": StateStatus.CURRENT.value if attrs else StateStatus.UNKNOWN.value,
                "attributes": attrs,
                "as_of": target_ts.isoformat(),
            }

        result = {
            "requested_timestamp": target_timestamp.isoformat(),
            "scope": scope.value if scope else "ALL",
            "reconstructed_entities_count": len(reconstructed_entities),
            "entities": reconstructed_entities,
        }
        for eid, edata in reconstructed_entities.items():
            result[eid] = edata

        return result

    # =========================================================================
    # 6. FRESHNESS & INVARIANT AUDITING (Phases 18, 35)
    # =========================================================================

    def audit_freshness_and_invariants(
        self,
        now: Optional[datetime] = None,
        staleness_threshold_seconds: Optional[float] = None,
    ) -> list[StateInvariantViolation]:
        """Evaluates freshness policies across all entities and flags invariant breaches."""
        current_time = now or utc_now()
        violations: list[StateInvariantViolation] = []
        inv_engine = InvariantEngine()

        for entity in self._entities.values():
            elapsed = (current_time - entity.last_observed_at).total_seconds()
            threshold = staleness_threshold_seconds if staleness_threshold_seconds is not None else entity.expected_update_interval_seconds
            is_stale = elapsed > threshold
            if is_stale:
                entity.freshness = FreshnessState.STALE

            v = inv_engine.check_invariants(entity, self._entities, now=current_time)
            violations.extend(v)

            if is_stale:
                if entity.status == StateStatus.CURRENT:
                    entity.status = StateStatus.STALE

        return violations

    # =========================================================================
    # 7. INTERNAL HELPERS
    # =========================================================================

    def _record_history(
        self,
        entity: WorldStateEntity,
        action: str,
        details: dict[str, Any],
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Appends an immutable state transition to entity history."""
        effective_time = timestamp or utc_now()
        entry = {
            "version": entity.version,
            "action": action,
            "status": entity.status.value,
            "timestamp": effective_time.isoformat(),
            "details": details,
            "state_summary": {
                "status": entity.status.value,
                "confidence": entity.confidence,
                "attributes": {k: v.current_value for k, v in entity.attributes.items()},
            },
        }
        self._entity_history.setdefault(entity.entity_id, []).append(entry)


# Module-level singleton
_global_reconciliation_engine: Optional[WorldStateReconciliationEngine] = None


def get_world_state_reconciliation_engine() -> WorldStateReconciliationEngine:
    global _global_reconciliation_engine
    if _global_reconciliation_engine is None:
        _global_reconciliation_engine = WorldStateReconciliationEngine()
    return _global_reconciliation_engine
