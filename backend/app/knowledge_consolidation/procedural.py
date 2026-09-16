"""Procedural knowledge engine for KAIRO (Task 92 Phase 14).

Guarantees:
- Tracks prerequisites, operational steps, expected outcomes, and failure conditions
- Records execution validation history
- Integrates with capability infrastructure without creating a duplicate workflow engine
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.knowledge_consolidation.models import (
    MemoryEntity,
    MemoryStatus,
    MemoryType,
    ProceduralMemory,
    generate_id,
)


class ProceduralMemoryManager:
    """Manages creation, execution recording, and validation of procedural workflows."""

    def __init__(self) -> None:
        self._procedures: dict[str, ProceduralMemory] = {}

    def register_procedure(
        self,
        name: str,
        description: str,
        steps: list[dict[str, Any]],
        prerequisites: list[str] | None = None,
        expected_outputs: list[str] | None = None,
        failure_conditions: list[str] | None = None,
        capability_ref: str | None = None,
        tenant_id: str = "default",
        user_id: str = "default_user",
    ) -> tuple[MemoryEntity, ProceduralMemory]:
        """Register a new actionable procedure linked to an underlying MemoryEntity."""
        mem_id = generate_id("mem_prc")
        proc_id = generate_id("prc")

        proc = ProceduralMemory(
            procedure_id=proc_id,
            memory_id=mem_id,
            name=name,
            description=description,
            prerequisites=prerequisites or [],
            steps=steps,
            expected_outputs=expected_outputs or [],
            failure_conditions=failure_conditions or [],
            capability_ref=capability_ref,
        )
        self._procedures[proc_id] = proc

        memory = MemoryEntity(
            memory_id=mem_id,
            tenant_id=tenant_id,
            user_id=user_id,
            type=MemoryType.PROCEDURAL,
            content=f"Procedure '{name}': {description}",
            structured_representation={
                "procedure_id": proc_id,
                "step_count": len(steps),
                "capability_ref": capability_ref,
            },
            status=MemoryStatus.ACTIVE,
        )

        return memory, proc

    def record_execution(
        self, procedure_id: str, success: bool, output_summary: str, details: dict[str, Any] | None = None
    ) -> ProceduralMemory:
        """Record execution outcome and update validation history."""
        proc = self._procedures.get(procedure_id)
        if not proc:
            raise KeyError(f"Procedure '{procedure_id}' not found.")

        now = datetime.now(UTC)
        entry = {
            "timestamp": now.isoformat(),
            "success": success,
            "output_summary": output_summary,
            "details": details or {},
        }
        proc.validation_history.append(entry)

        if success:
            proc.last_successful_execution_at = now

        return proc

    def get_procedure(self, procedure_id: str) -> ProceduralMemory | None:
        """Retrieve procedural record by ID."""
        return self._procedures.get(procedure_id)

    def get_by_memory_id(self, memory_id: str) -> ProceduralMemory | None:
        """Retrieve procedural record by associated memory ID."""
        for p in self._procedures.values():
            if p.memory_id == memory_id:
                return p
        return None
