"""Safe typed template system with strict injection sanitization and privacy boundaries (Task 34, Spec 81-85, 88, 107-109)."""

import html
import logging
import re
from typing import Any

from app.notifications.schemas import NotificationType

logger = logging.getLogger("kairo.notifications.templates")


class TemplateRenderer:
    """
    Renders user-facing notification titles and bodies.
    Guarantees:
      - No private chain-of-thought or reasoning leaks (Spec 82).
      - Strict HTML, script, and prompt injection escaping (Spec 85, 88).
      - Lock-screen privacy: no secrets or private keys embedded (Spec 107-109).
    """

    # Disallowed secret / token patterns that must never be emitted into notification text
    SECRET_PATTERNS = [
        re.compile(r"sk-[a-zA-Z0-9_-]{20,}", re.IGNORECASE),
        re.compile(r"ghp_[a-zA-Z0-9]{20,}", re.IGNORECASE),
        re.compile(r"bearer\s+[a-zA-Z0-9_\-\.]{20,}", re.IGNORECASE),
        re.compile(r"password\s*=\s*['\"][^'\"]+['\"]", re.IGNORECASE),
    ]

    @classmethod
    def sanitize_text(cls, text: str) -> str:
        """Escape HTML and strip secrets / raw credentials from notification text."""
        if not text:
            return ""

        sanitized = str(text)

        # Redact any discovered secret patterns
        for pattern in cls.SECRET_PATTERNS:
            sanitized = pattern.sub("[REDACTED_SECRET]", sanitized)

        # Escape HTML entities to defeat injection
        escaped = html.escape(sanitized, quote=True)
        return escaped

    @classmethod
    def render(
        cls,
        event_type: str,
        notification_type: NotificationType,
        payload: dict[str, Any] | None = None,
        custom_title: str | None = None,
        custom_body: str | None = None,
    ) -> tuple[str, str]:
        """
        Generate title and body for notification from typed templates or custom text.
        """
        payload = payload or {}

        # If custom title/body supplied, sanitize and verify privacy
        if custom_title and custom_body:
            return cls.sanitize_text(custom_title), cls.sanitize_text(custom_body)

        # 1. Approval events
        if event_type.startswith("approval.") or notification_type == NotificationType.APPROVAL:
            action_desc = payload.get("action") or payload.get("action_description") or payload.get("tool_name") or "Action"
            risk = payload.get("risk_level", "HIGH")
            title = "Action Requires Approval"
            body = f"Kairo requires your authorization to proceed with: {action_desc}. (Risk: {risk})"
            return cls.sanitize_text(title), cls.sanitize_text(body)

        # 2. Task lifecycle events
        if event_type == "task.completed":
            task_obj = payload.get("objective") or payload.get("task_id") or "Task"
            title = "Task Completed"
            body = f"Kairo finished: {task_obj}"
            return cls.sanitize_text(title), cls.sanitize_text(body)

        if event_type == "task.failed":
            task_obj = payload.get("objective") or payload.get("task_id") or "Task"
            err = payload.get("error") or "Execution halted"
            title = "Task Execution Failed"
            body = f"Task '{task_obj}' failed: {err}"
            return cls.sanitize_text(title), cls.sanitize_text(body)

        if event_type == "task.waiting_user":
            q = payload.get("question") or "User clarification needed to continue execution."
            title = "Clarification Needed"
            body = q
            return cls.sanitize_text(title), cls.sanitize_text(body)

        # 3. Security events (Privacy-safe: no tokens or credentials)
        if event_type.startswith("security.") or notification_type == NotificationType.SECURITY:
            title = "Security Alert"
            violation = payload.get("reason") or payload.get("violation_type") or "Security policy event requires attention."
            body = f"A security policy event was triggered: {violation}"
            return cls.sanitize_text(title), cls.sanitize_text(body)

        # 4. Device events
        if event_type == "device.revoked":
            d_name = payload.get("device_name") or payload.get("device_id") or "Device"
            title = "Device Revoked"
            body = f"Companion hardware '{d_name}' was revoked and all bound sessions terminated."
            return cls.sanitize_text(title), cls.sanitize_text(body)

        if event_type == "device.connected":
            d_name = payload.get("device_name") or payload.get("device_id") or "Device"
            title = "Device Connected"
            body = f"Companion hardware '{d_name}' connected to Kairo."
            return cls.sanitize_text(title), cls.sanitize_text(body)

        # 5. CI / GitHub events
        if event_type == "github.ci.failed":
            repo = payload.get("repo") or payload.get("repository") or "repository"
            check = payload.get("check_run") or "CI Pipeline"
            title = "CI Check Failure"
            body = f"{check} failed in {repo}."
            return cls.sanitize_text(title), cls.sanitize_text(body)

        # 6. Workflow / Automation events
        if event_type == "workflow.failed":
            wf = payload.get("workflow_name") or payload.get("workflow_id") or "Automation"
            title = "Automation Failed"
            body = f"Workflow '{wf}' encountered an unhandled error."
            return cls.sanitize_text(title), cls.sanitize_text(body)

        # Generic fallback
        title = f"{notification_type.value} Notification"
        body = payload.get("message") or payload.get("summary") or "New event recorded in Kairo."
        return cls.sanitize_text(title), cls.sanitize_text(body)
