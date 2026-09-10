"""Explicit user correction processing and scope disambiguation (INVARIANTS 22-24, 121)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
import uuid

from app.learning.schemas import CorrectionRecordSchema, GeneralizationScope


class CorrectionHandler:
    """Processes explicit user corrections, determines applicability scope, and resolves ambiguity."""

    def __init__(self) -> None:
        # correction_id -> CorrectionRecordSchema
        self._corrections: dict[str, CorrectionRecordSchema] = {}

    def handle_correction(
        self,
        target_action: str,
        user_directive: str,
        scope_hint: str | None = None,
    ) -> CorrectionRecordSchema:
        """INVARIANT 22-24: Handles explicit negative directives like 'Don't do that again'.
        Detects whether scope is ambiguous and prompts for clarification when necessary.
        """
        directive_clean = user_directive.strip()
        is_ambiguous = False
        clarification_prompt = None

        if not scope_hint:
            # Check if directive specifies scope keywords
            d_lower = directive_clean.lower()
            if "in this project" in d_lower:
                resolved_scope = GeneralizationScope.PROJECT
            elif "in this repository" in d_lower or "in this repo" in d_lower:
                resolved_scope = GeneralizationScope.REPOSITORY
            elif "for this task" in d_lower:
                resolved_scope = GeneralizationScope.TASK
            elif any(w in d_lower for w in ["never", "always", "ever", "again"]):
                # INVARIANT 24: Ask when ambiguous rather than assuming global
                is_ambiguous = True
                resolved_scope = GeneralizationScope.TASK  # Default to narrowest
                clarification_prompt = (
                    f"You instructed: '{directive_clean}'. Does this apply only to this task, "
                    "this project, or all future interactions?"
                )
            else:
                resolved_scope = GeneralizationScope.TASK
        else:
            try:
                resolved_scope = GeneralizationScope(scope_hint)
            except ValueError:
                resolved_scope = GeneralizationScope.PROJECT

        cid = f"cor_{uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC)
        record = CorrectionRecordSchema(
            correction_id=cid,
            target_action=target_action,
            user_directive=directive_clean,
            scope=resolved_scope,
            is_ambiguous=is_ambiguous,
            clarification_prompt=clarification_prompt,
            applied=True,
            timestamp=now,
        )
        self._corrections[cid] = record
        return record

    def get_correction(self, correction_id: str) -> CorrectionRecordSchema | None:
        return self._corrections.get(correction_id)

    def list_corrections(self, target_action: str | None = None) -> list[CorrectionRecordSchema]:
        results = list(self._corrections.values())
        if target_action:
            results = [c for c in results if c.target_action == target_action]
        return results
