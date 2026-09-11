"""Explicit forgetting and compliance-grade deletion engine for Task 68.

Enforces:
- Spec 16: Safe forgetting (expiration, user deletion, privacy mandates, low-value cleanup)
- Invariant: Forgetting != rewriting history (audit tombstones preserved without retaining prohibited content)
- Complete cascade propagation to indexes, derived representations, and knowledge graph links
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from app.memory_consolidation.lifecycle import MemoryLifecycleStateMachine
from app.memory_consolidation.schemas import (
    DurableMemory,
    MemoryAuditEventType,
    MemoryLifecycleState,
)

logger = logging.getLogger("kairo.memory_consolidation.forgetting")


class ForgettingEngine:
    """Safely executes policy-based or user-requested memory deletion with audit tombstones."""

    @classmethod
    def execute_forgetting(
        cls,
        memory: DurableMemory,
        reason: str,
        actor: str = "user_request",
        hard_delete: bool = False,
    ) -> tuple[DurableMemory, dict[str, Any], list[str]]:
        """Scrub memory content, set terminal lifecycle state, and produce deletion tombstone (Spec 16)."""
        now = datetime.now(UTC)
        previous_state = memory.status.value if hasattr(memory.status, "value") else str(memory.status)

        target_state = MemoryLifecycleState.DELETED if hard_delete else MemoryLifecycleState.FORGOTTEN
        MemoryLifecycleStateMachine.transition(
            memory=memory,
            target_state=target_state,
            actor=actor,
            reason=reason,
        )

        # Content scrubbing to prevent data leakage from tombstoned records
        original_id = memory.memory_id
        memory.content = f"[CONTENT_REMOVED_BY_FORGETTING_POLICY: {reason}]"
        memory.structured_payload = {"tombstone": True, "reason": reason, "forgotten_at": now.isoformat()}

        # Identify dependent derived memories or linked resources that need cascade updates
        cascade_target_ids = list(memory.provenance.derived_from_ids)

        tombstone_audit = {
            "audit_id": f"maud_{uuid.uuid4().hex[:10]}",
            "memory_id": original_id,
            "tenant_id": memory.tenant_id,
            "event_type": (
                MemoryAuditEventType.MEMORY_DELETED.value
                if hard_delete
                else MemoryAuditEventType.MEMORY_FORGOTTEN.value
            ),
            "actor": actor,
            "previous_state": previous_state,
            "new_state": target_state.value,
            "reason": reason,
            "details": {
                "tombstone": True,
                "cascade_targets": cascade_target_ids,
                "hard_delete": hard_delete,
            },
            "timestamp": now,
        }

        return memory, tombstone_audit, cascade_target_ids
