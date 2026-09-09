"""Reference resolution engine adhering to priority hierarchy and context bounding (Spec 11-17, 35, 36, 67, 68)."""

import logging
import re
from typing import Any

from app.intent.schemas import IntentEntity, ResolutionMethod

logger = logging.getLogger("kairo.intent.references")


class ReferenceResolver:
    """
    Resolves deictic, anaphoric, and scoped references against bounded context.
    Priority Hierarchy (Spec 12):
    1. current message
    2. attached media
    3. current conversation
    4. active task
    5. current project
    6. recent relevant context
    7. world state
    8. long-term memory
    """

    PRONOUN_PATTERNS = {
        "this": re.compile(r"\bthis\b", re.IGNORECASE),
        "that": re.compile(r"\bthat\b", re.IGNORECASE),
        "it": re.compile(r"\bit\b", re.IGNORECASE),
        "the_repo": re.compile(r"\b(the\s+repo|the\s+repository)\b", re.IGNORECASE),
        "the_project": re.compile(r"\b(the\s+project)\b", re.IGNORECASE),
        "the_deployment": re.compile(r"\b(the\s+deployment|the\s+deploy)\b", re.IGNORECASE),
        "the_task": re.compile(r"\b(the\s+task|the\s+job|the\s+operation)\b", re.IGNORECASE),
        "previous_one": re.compile(r"\b(the\s+previous\s+one|the\s+last\s+one|the\s+prior\s+one)\b", re.IGNORECASE),
    }

    @classmethod
    def detect_references(cls, text: str) -> list[str]:
        """Identifies explicit reference keywords present in the user text."""
        detected = []
        for key, pattern in cls.PRONOUN_PATTERNS.items():
            if pattern.search(text):
                detected.append(key)
        return detected

    @classmethod
    def resolve_references(
        cls,
        text: str,
        attachments: list[dict[str, Any]] | None = None,
        session_context: dict[str, Any] | None = None,
        project_context: dict[str, Any] | None = None,
        active_task: dict[str, Any] | None = None,
        world_context: dict[str, Any] | None = None,
        recent_artifacts: list[dict[str, Any]] | None = None,
    ) -> tuple[dict[str, Any | None], list[dict[str, Any]], list[str]]:
        """
        Resolves detected references against bounded context.
        Returns:
            resolved_targets: dict of reference_key -> resolved target dict or None
            ambiguous_candidates: list of candidate dicts where resolution is ambiguous
            detected_refs: list of detected reference keys
        """
        detected_refs = cls.detect_references(text)
        resolved_targets: dict[str, Any | None] = {}
        ambiguous_candidates: list[dict[str, Any]] = []

        attachments = attachments or []
        session_context = session_context or {}
        recent_artifacts = recent_artifacts or []

        # 1. Resolve "this" (Priority: Attached media -> most recent explicit artifact)
        if "this" in detected_refs:
            if attachments:
                # Top priority: direct attachment
                resolved_targets["this"] = {
                    "type": "attachment",
                    "id": attachments[0].get("name", "attachment_0"),
                    "name": attachments[0].get("name", "attachment"),
                    "method": ResolutionMethod.EXPLICIT,
                }
            elif recent_artifacts:
                if len(recent_artifacts) == 1:
                    resolved_targets["this"] = {
                        "type": "artifact",
                        "id": recent_artifacts[0].get("id"),
                        "name": recent_artifacts[0].get("name"),
                        "method": ResolutionMethod.CONTEXT,
                    }
                else:
                    resolved_targets["this"] = None
                    ambiguous_candidates.append({
                        "reference": "this",
                        "candidates": [a.get("name") for a in recent_artifacts[:4]],
                        "reason": "Multiple recent artifacts match 'this'.",
                    })
            else:
                resolved_targets["this"] = None

        # 2. Resolve "the_repo" (Priority: Project repos -> Session active repo)
        if "the_repo" in detected_refs:
            repos = []
            if project_context:
                repos = project_context.get("repositories", [])
            elif session_context.get("repositories"):
                repos = session_context.get("repositories", [])

            if len(repos) == 1:
                resolved_targets["the_repo"] = {
                    "type": "repository",
                    "id": repos[0],
                    "name": repos[0],
                    "method": ResolutionMethod.CONTEXT,
                }
            elif len(repos) > 1:
                resolved_targets["the_repo"] = None
                ambiguous_candidates.append({
                    "reference": "the repo",
                    "candidates": repos,
                    "reason": f"Multiple active repositories exist: {', '.join(repos)}. Which repository?",
                })
            else:
                resolved_targets["the_repo"] = None

        # 3. Resolve "the_project"
        if "the_project" in detected_refs:
            if project_context and project_context.get("name"):
                resolved_targets["the_project"] = {
                    "type": "project",
                    "id": project_context.get("id"),
                    "name": project_context.get("name"),
                    "method": ResolutionMethod.CONTEXT,
                }
            else:
                resolved_targets["the_project"] = None

        # 4. Resolve "it" or "that"
        for pronoun in ("it", "that"):
            if pronoun in detected_refs:
                # If "this" was resolved to an attachment, "it" can refer to it
                if resolved_targets.get("this"):
                    resolved_targets[pronoun] = resolved_targets["this"]
                elif active_task:
                    resolved_targets[pronoun] = {
                        "type": "task",
                        "id": active_task.get("id"),
                        "name": active_task.get("title") or active_task.get("objective", "active_task"),
                        "method": ResolutionMethod.CONTEXT,
                    }
                elif project_context and len(project_context.get("repositories", [])) == 1:
                    resolved_targets[pronoun] = {
                        "type": "repository",
                        "id": project_context["repositories"][0],
                        "name": project_context["repositories"][0],
                        "method": ResolutionMethod.CONTEXT,
                    }
                else:
                    resolved_targets[pronoun] = None

        # 5. Resolve "the_task" or "previous_one"
        for t_ref in ("the_task", "previous_one"):
            if t_ref in detected_refs:
                if active_task:
                    resolved_targets[t_ref] = {
                        "type": "task",
                        "id": active_task.get("id"),
                        "name": active_task.get("title") or active_task.get("objective", "active_task"),
                        "method": ResolutionMethod.CONTEXT,
                    }
                elif session_context.get("recent_tasks") and len(session_context["recent_tasks"]) == 1:
                    t = session_context["recent_tasks"][0]
                    resolved_targets[t_ref] = {
                        "type": "task",
                        "id": t.get("id"),
                        "name": t.get("title", "previous_task"),
                        "method": ResolutionMethod.CONTEXT,
                    }
                elif session_context.get("recent_tasks") and len(session_context["recent_tasks"]) > 1:
                    resolved_targets[t_ref] = None
                    ambiguous_candidates.append({
                        "reference": t_ref,
                        "candidates": [t.get("title", t.get("id")) for t in session_context["recent_tasks"][:4]],
                        "reason": "Multiple recent tasks exist. Which task did you mean?",
                    })
                else:
                    resolved_targets[t_ref] = None

        return resolved_targets, ambiguous_candidates, detected_refs
