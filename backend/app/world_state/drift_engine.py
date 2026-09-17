"""Structured Drift Detection, Classification, Causal Linking & Change Attribution (Phases 10-15).

Enforces:
- DRIFT != CAUSE
- CORRELATION != CAUSATION
- UNATTRIBUTED CHANGE MUST NOT RECEIVE A FABRICATED ACTOR
- EXPECTED STATE != ACTUAL STATE
"""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Any, Dict, List, Optional, Tuple

from app.world_state.domain import (
    CausalEvidenceStatus,
    DriftClassification,
    DriftSeverity,
    DriftStatus,
    DriftType,
    ExpectedState,
    RevalidationCandidate,
    StateDriftRecord,
    StateObservation,
    WorldScope,
    WorldStateEntity,
    generate_uuid,
    utc_now,
)

logger = logging.getLogger("kairo.world_state.drift")


class DriftEngine:
    """Detects, classifies, and attributes reality drift between expected and actual state."""

    def __init__(self) -> None:
        self._drift_records: dict[str, StateDriftRecord] = {}
        self._active_drifts: list[StateDriftRecord] = []

    def record_drift(self, drift: StateDriftRecord) -> None:
        """Stores a detected drift record in memory."""
        self._drift_records[drift.drift_id] = drift
        if drift not in self._active_drifts:
            self._active_drifts.append(drift)

    def get_active_drifts(self, scope: Optional[WorldScope] = None) -> list[StateDriftRecord]:
        """Returns all active drift records, optionally filtered by scope."""
        drifts = self._active_drifts if self._active_drifts else list(self._drift_records.values())
        if not scope or scope == WorldScope.SYSTEM:
            return drifts
        return [d for d in drifts if d.scope == scope]

    def detect_drift(
        self,
        expected: ExpectedState,
        actual_entity: WorldStateEntity,
        attribute_name: Optional[str] = None,
        observed_value: Optional[Any] = None,
        known_transactions: Optional[list[dict[str, Any]]] = None,
        causal_bridge: Optional[Any] = None,
    ) -> Optional[StateDriftRecord]:
        """Compares expected state against actual entity attributes and returns a structured drift record if divergent."""
        exp_val = expected.expected_value
        act_val = None

        if observed_value is not None:
            act_val = observed_value
        elif attribute_name and attribute_name in actual_entity.attributes:
            act_val = actual_entity.attributes[attribute_name].current_value
        else:
            # Check metadata or default attribute
            act_val = actual_entity.metadata.get(attribute_name or "status", actual_entity.status.value)

        # Check equivalence with tolerance
        is_divergent, magnitude = self._evaluate_divergence(exp_val, act_val, expected.tolerance)
        if not is_divergent:
            return None

        # Determine drift type
        drift_type = self._determine_drift_type(attribute_name or "state", expected.source_type)

        # Determine severity and classification
        severity = self._assess_severity(drift_type, magnitude, expected, actual_entity)
        classification = self._classify_drift(drift_type, severity, expected, actual_entity)

        # Attribute change to active transactions or decisions
        source_type, source_id = self._attribute_change(actual_entity.entity_id, exp_val, act_val, known_transactions)

        # Causal linking
        causal_status = self._link_causal_evidence(actual_entity.entity_id, causal_bridge)

        drift_id = generate_uuid("drift")
        evidence = [
            f"Expected {exp_val} (source: {expected.source_type}:{expected.source_id}), but observed {act_val}.",
            f"Deviation magnitude: {magnitude:.3f} (tolerance: {expected.tolerance}).",
        ]

        record = StateDriftRecord(
            drift_id=drift_id,
            entity_id=actual_entity.entity_id,
            scope=actual_entity.scope,
            drift_type=drift_type,
            severity=severity,
            classification=classification,
            status=DriftStatus.DETECTED,
            expected_value=exp_val,
            actual_value=act_val,
            deviation_magnitude=magnitude,
            evidence=evidence,
            confidence=actual_entity.confidence,
            detected_at=utc_now(),
            causal_status=causal_status,
            attributed_source_type=source_type,
            attributed_source_id=source_id,
            revalidation_candidate_ids=[],
            metadata={"expected_by": expected.expected_by, "attribute": attribute_name or "state"},
        )

        self._drift_records[drift_id] = record
        actual_entity.active_drift_ids.append(drift_id)
        return record

    def _evaluate_divergence(self, expected: Any, actual: Any, tolerance: float) -> Tuple[bool, float]:
        """Evaluates whether expected and actual values diverge beyond tolerance."""
        if expected == actual:
            return False, 0.0

        # Numeric comparison
        if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
            diff = abs(expected - actual)
            if diff <= tolerance:
                return False, diff
            denom = max(abs(expected), 1.0)
            rel_diff = diff / denom
            return True, rel_diff

        # String or categorical comparison
        str_exp = str(expected).strip().lower()
        str_act = str(actual).strip().lower()
        if str_exp == str_act:
            return False, 0.0

        return True, 1.0

    def _determine_drift_type(self, attribute_name: str, source_type: str) -> DriftType:
        attr_lower = attribute_name.lower()
        if "config" in attr_lower or "setting" in attr_lower:
            return DriftType.CONFIGURATION_DRIFT
        if "version" in attr_lower or "capability" in attr_lower:
            return DriftType.CAPABILITY_DRIFT
        if "depend" in attr_lower:
            return DriftType.DEPENDENCY_DRIFT
        if "cpu" in attr_lower or "memory" in attr_lower or "resource" in attr_lower or "quota" in attr_lower:
            return DriftType.RESOURCE_DRIFT
        if "latency" in attr_lower or "throughput" in attr_lower or "error_rate" in attr_lower:
            return DriftType.PERFORMANCE_DRIFT
        if "schema" in attr_lower:
            return DriftType.SCHEMA_DRIFT
        if "env" in attr_lower or "host" in attr_lower or "network" in attr_lower:
            return DriftType.ENVIRONMENT_DRIFT
        if "policy" in attr_lower or "security" in attr_lower:
            return DriftType.POLICY_DRIFT
        return DriftType.STATE_DRIFT

    def _assess_severity(
        self,
        drift_type: DriftType,
        magnitude: float,
        expected: ExpectedState,
        actual_entity: WorldStateEntity,
    ) -> DriftSeverity:
        # Check critical domains
        if drift_type in (DriftType.POLICY_DRIFT, DriftType.CAPABILITY_DRIFT):
            return DriftSeverity.CRITICAL if magnitude > 0.5 else DriftSeverity.HIGH
        if drift_type == DriftType.RESOURCE_DRIFT:
            return DriftSeverity.HIGH if magnitude > 0.3 else DriftSeverity.MEDIUM
        if drift_type == DriftType.DEPENDENCY_DRIFT:
            return DriftSeverity.HIGH
        if magnitude >= 0.8:
            return DriftSeverity.HIGH
        if magnitude >= 0.3:
            return DriftSeverity.MEDIUM
        return DriftSeverity.LOW

    def _classify_drift(
        self,
        drift_type: DriftType,
        severity: DriftSeverity,
        expected: ExpectedState,
        actual_entity: WorldStateEntity,
    ) -> DriftClassification:
        if severity == DriftSeverity.CRITICAL:
            return DriftClassification.CRITICAL_DRIFT
        if expected.metadata.get("is_planned_migration", False):
            return DriftClassification.EXPECTED_CHANGE
        if severity == DriftSeverity.LOW and drift_type == DriftType.PERFORMANCE_DRIFT:
            return DriftClassification.BENIGN_DRIFT
        if expected.metadata.get("is_unexplained", False):
            return DriftClassification.UNKNOWN_DRIFT
        return DriftClassification.ACTIONABLE_DRIFT

    def _attribute_change(
        self,
        entity_id: str,
        expected_val: Any,
        actual_val: Any,
        known_transactions: Optional[list[dict[str, Any]]],
    ) -> Tuple[str, Optional[str]]:
        """Attributes state deviation to a known operational transaction, or strictly flags UNATTRIBUTED_CHANGE."""
        if not known_transactions:
            return "UNATTRIBUTED_CHANGE", None

        for txn in known_transactions:
            txn_target = txn.get("target_id") or txn.get("entity_id")
            if txn_target == entity_id:
                txn_type = txn.get("type", "ACTION_TRANSACTION")
                txn_id = txn.get("id") or txn.get("transaction_id")
                return txn_type, txn_id

        # Phase 15 Non-negotiable invariant: NEVER fabricate an actor
        return "UNATTRIBUTED_CHANGE", None

    def _link_causal_evidence(
        self,
        entity_id: str,
        causal_bridge: Optional[Any],
    ) -> CausalEvidenceStatus:
        """Consults the causal engine if available to verify true causal relationships vs mere correlation."""
        if not causal_bridge:
            return CausalEvidenceStatus.NO_EVIDENCE

        try:
            if hasattr(causal_bridge, "has_causal_evidence") and causal_bridge.has_causal_evidence(entity_id):
                return CausalEvidenceStatus.CAUSAL_EVIDENCE_AVAILABLE
            if hasattr(causal_bridge, "has_correlation") and causal_bridge.has_correlation(entity_id):
                return CausalEvidenceStatus.CORRELATION_ONLY
        except Exception as e:
            logger.debug("Causal evaluation exception for %s: %s", entity_id, e)

        return CausalEvidenceStatus.NO_EVIDENCE
