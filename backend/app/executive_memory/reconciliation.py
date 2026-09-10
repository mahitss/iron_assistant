"""Authoritative source reconciliation and drift correction (INVARIANTS 124-126, 204, 205)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.executive_memory.schemas import ReconciliationReportSchema


class StateReconciler:
    """Reconciles synthesized executive state with authoritative system sources.
    INVARIANT 204: Authoritative systems always win.
    """

    def reconcile(
        self,
        scope_id: str | None = None,
        synthesized_state: dict[str, Any] | None = None,
        authoritative_state: dict[str, Any] | None = None,
        authoritative_sources: dict[str, Any] | None = None,
    ) -> ReconciliationReportSchema:
        """INVARIANT 124 & 204: Compares synthesized state with source systems and applies overrides."""
        synth = synthesized_state or {}
        auth = authoritative_state or authoritative_sources or {}

        drift_items = []
        discrepancies = []
        corrected_items = []
        reconciled_state = dict(synth)
        override_count = 0

        # Authoritative systems strictly win for all fields
        all_keys = set(synth.keys()).union(set(auth.keys()))
        for key in all_keys:
            synth_val = synth.get(key)
            auth_val = auth.get(key)
            if key in auth and synth_val != auth_val:
                drift_items.append({
                    "field": key,
                    "synthesized": synth_val,
                    "authoritative": auth_val,
                })
                discrepancies.append(key)
                corrected_items.append({
                    "field": key,
                    "resolved_value": auth_val,
                })
                reconciled_state[key] = auth_val
                override_count += 1
            elif key in auth:
                reconciled_state[key] = auth_val

        return ReconciliationReportSchema(
            drift_detected=len(drift_items) > 0,
            drift_items=drift_items,
            discrepancies=discrepancies,
            corrected_items=corrected_items,
            reconciled_state=reconciled_state,
            source_authoritative_overrides=override_count,
            timestamp=datetime.now(UTC),
        )
