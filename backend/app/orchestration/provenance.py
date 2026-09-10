"""Provenance tracking, assignment rationales, and factor explanations for Orchestration (Task 59)."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from app.orchestration.schemas import (
    MatchingScore,
    ProviderAssignment,
    TaskCapabilityRequirement,
)

logger = logging.getLogger(__name__)


class OrchestrationProvenanceTracker:
    """Records and generates transparent explanations for provider and resource selections."""

    def __init__(self) -> None:
        self._provenance_records: dict[str, dict[str, Any]] = {}

    def record_selection_provenance(
        self,
        task_id: str,
        assignment: ProviderAssignment,
        evaluated_candidates: list[MatchingScore],
        requirement: TaskCapabilityRequirement,
    ) -> dict[str, Any]:
        """Record why a provider was selected and why alternative candidates were rejected."""
        alternatives = []
        for cand in evaluated_candidates:
            if cand.provider_name != assignment.provider_name:
                alternatives.append({
                    "provider": cand.provider_name,
                    "overall_score": cand.overall_score,
                    "is_authorized": cand.is_authorized,
                    "env_compatible": cand.environment_compatibility,
                    "rejection_reason": cand.rationale or "Lower composite score than selected provider.",
                })

        record = {
            "task_id": task_id,
            "selected_provider": assignment.provider_name,
            "provider_type": assignment.provider_type.value,
            "capability_id": assignment.capability_id,
            "confidence": assignment.confidence,
            "rationale": assignment.rationale,
            "required_capabilities": requirement.required_capabilities,
            "environment": requirement.environment,
            "alternatives_considered": alternatives,
        }

        # SHA-256 fingerprint
        canonical = json.dumps(record, sort_keys=True, default=str)
        record["fingerprint"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

        self._provenance_records[task_id] = record
        return record

    def explain_assignment(self, task_id: str) -> dict[str, Any]:
        """Return a structured human-readable explanation of provider selection."""
        record = self._provenance_records.get(task_id)
        if not record:
            return {
                "task_id": task_id,
                "found": False,
                "explanation": f"No provenance recorded for task '{task_id}'.",
            }

        alts_text = []
        for alt in record.get("alternatives_considered", []):
            alts_text.append(f"- {alt['provider']} (score {alt['overall_score']:.2f}): {alt['rejection_reason']}")

        explanation = (
            f"Task '{task_id}' was assigned to '{record['selected_provider']}' "
            f"because it matched required capabilities {record['required_capabilities']} "
            f"in environment '{record['environment']}'. "
            f"Rationale: {record['rationale']}."
        )

        return {
            "task_id": task_id,
            "found": True,
            "explanation": explanation,
            "selected_provider": record["selected_provider"],
            "alternatives": record.get("alternatives_considered", []),
            "fingerprint": record.get("fingerprint"),
        }


provenance_tracker = OrchestrationProvenanceTracker()
