"""Reconciliation Engine and Conflict Preservation (Task 54, Prompts #74-#79)."""

from __future__ import annotations

import uuid
from typing import Any

from app.environment.confidence import is_source_authoritative
from app.environment.schemas import NodeType, ReconciliationConflict
from app.environment.temporal import utc_now


class ReconciliationEngine:
    """Reconciles Digital Twin against authoritative observation sources while preserving conflicts."""

    @staticmethod
    def reconcile_observations(
        node_type: NodeType,
        resource_id: str,
        observation_a: dict[str, Any],  # {"source": str, "value": Any, "timestamp": str}
        observation_b: dict[str, Any],
    ) -> tuple[Any, ReconciliationConflict | None]:
        """Compares two observations. If conflict exists and neither or both are authoritative, preserves conflict."""
        val_a = observation_a.get("value")
        val_b = observation_b.get("value")
        src_a = observation_a.get("source", "unknown")
        src_b = observation_b.get("source", "unknown")

        if val_a == val_b:
            return val_a, None

        auth_a = is_source_authoritative(node_type, src_a)
        auth_b = is_source_authoritative(node_type, src_b)

        # Clear authority on one side: choose the authoritative source, but record observation
        if auth_a and not auth_b:
            return val_a, None
        if auth_b and not auth_a:
            return val_b, None

        # Prompt #78, #79: If sources disagree and authority is unclear or both claim authority:
        # PRESERVE CONFLICT. DO NOT SILENTLY RESOLVE.
        conflict = ReconciliationConflict(
            conflict_id=f"cnf_{uuid.uuid4().hex[:10]}",
            resource=resource_id,
            source_a=src_a,
            value_a=val_a,
            source_b=src_b,
            value_b=val_b,
            detected_at=utc_now(),
            resolved=False,
            resolution_notes="Disagreement between non-authoritative or co-authoritative telemetry sources; preserved for operator inspection.",
        )
        return val_a, conflict
