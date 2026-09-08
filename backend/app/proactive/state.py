"""State, priority, and lifecycle definitions for Proactive Intelligence."""

from enum import StrEnum


class InsightPriority(StrEnum):
    """Priority level for proactive insights.

    CRITICAL: Emergency stops, severe safety violations (application-controlled only).
    HIGH: Workflow failures, CI failures on main/prod, approval reminders/expirations.
    MEDIUM: Web monitor changes, branch CI changes, uncommitted repo changes.
    LOW: Routine completed workflows, informational notifications.
    """

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class InsightStatus(StrEnum):
    """Lifecycle status for a proactive insight."""

    NEW = "new"
    DELIVERED = "delivered"
    READ = "read"
    DISMISSED = "dismissed"
    EXPIRED = "expired"


class Actionability(StrEnum):
    """Actionability classification for surfaced insights."""

    INFORMATIONAL = "INFORMATIONAL"
    ACTION_REQUIRED = "ACTION_REQUIRED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"


class SourceType(StrEnum):
    """Event origin/category for proactive detection."""

    WORKFLOW = "WORKFLOW"
    GITHUB = "GITHUB"
    WEB_MONITOR = "WEB_MONITOR"
    APPROVAL = "APPROVAL"
    SYSTEM = "SYSTEM"
    SECURITY = "SECURITY"


PRIORITY_WEIGHTS = {
    InsightPriority.CRITICAL: 100,
    InsightPriority.HIGH: 75,
    InsightPriority.MEDIUM: 50,
    InsightPriority.LOW: 25,
}
