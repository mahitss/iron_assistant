"""MissingContextDetector: Identifies absent information without fabricating data (Task 69)."""

import logging

from app.context.universal_schemas import (
    ContextPriorityTier,
    ContextRequest,
    MissingContextItem,
    UniversalContextItem,
    UniversalContextType,
)

logger = logging.getLogger("kairo.context.missing")


class MissingContextDetector:
    """Identifies absent context necessary for complete, safe, and accurate task execution."""

    @classmethod
    def detect_missing_context(
        cls,
        request: ContextRequest,
        selected_items: list[UniversalContextItem],
    ) -> list[MissingContextItem]:
        """Examine query intent, task type, and retrieved items to flag critical missing elements."""
        missing: list[MissingContextItem] = []
        text_full = f"{request.query} {request.intent or ''} {request.task_type or ''}".lower()
        selected_types = {item.context_type for item in selected_items}
        all_content = " ".join(item.content.lower() for item in selected_items)

        # 1. Debugging / Error task missing logs
        if any(w in text_full for w in ["debug", "failure", "failed", "crash", "bug", "error", "exception"]):
            has_logs = any(
                w in all_content for w in ["traceback", "stacktrace", "error log", "exit code", "exception:"]
            )
            if not has_logs:
                missing.append(
                    MissingContextItem(
                        category="Execution Logs & Stacktrace",
                        description="Task requests error investigation but no detailed runtime logs or stacktraces were found in context",
                        importance=ContextPriorityTier.HIGH,
                        potential_sources=["system_logs", "observability_engine", "recent_incidents"],
                        impact="May result in generalized diagnosis without concrete error provenance",
                    )
                )

        # 2. Deployment / Production task missing configuration
        if any(w in text_full for w in ["deploy", "release", "production", "infrastructure"]):
            has_config = bool(
                selected_types.intersection(
                    {UniversalContextType.ENVIRONMENT_CONTEXT, UniversalContextType.PROCEDURAL_CONTEXT}
                )
            )
            if not has_config or "config" not in all_content:
                missing.append(
                    MissingContextItem(
                        category="Target Environment Configuration",
                        description="Deployment inquiry lacks explicit environment configuration and deployment manifest",
                        importance=ContextPriorityTier.CRITICAL,
                        potential_sources=["environment_twin", "digital_twin", "repo_manifests"],
                        impact="Action could target incorrect cluster or apply unintended environment flags",
                    )
                )

        # 3. Decision / Planning task missing constraints
        if any(w in text_full for w in ["decide", "choose", "recommend", "architect", "strategy"]):
            has_constraints = any(
                w in all_content
                for w in ["budget", "deadline", "sla", "constraint", "policy", "security rule"]
            )
            if not has_constraints:
                missing.append(
                    MissingContextItem(
                        category="Operational Constraints & SLAs",
                        description="Strategic or architectural decision requested without explicit cost, deadline, or SLA constraints",
                        importance=ContextPriorityTier.NORMAL,
                        potential_sources=["policy_engine", "workspace_settings", "user_preferences"],
                        impact="Recommendation may not fit operational or financial boundaries",
                    )
                )

        return missing
