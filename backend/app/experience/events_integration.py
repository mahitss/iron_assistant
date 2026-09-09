"""Event Bus Integration for Kairo Long-Term Experience and Learning.

Handles publishing and subscription for experience lifecycle events:
- experience.candidate.created
- experience.validated
- experience.updated
- experience.superseded
- experience.deleted
- feedback.created
- feedback.processed
- learning.review.requested

Enforces safety invariant: Event Bus cannot turn experience or learning candidates
into permissions, approvals, or security policy alterations.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.events.bus import event_bus
from app.events.schemas import Event, EventSource
from app.experience.models import ExperienceRecord, UserFeedbackRecord
from app.experience.safety import sanitize_content
from app.experience.schemas import (
    CandidateStatus,
    ConfidenceLevel,
    ExperienceScope,
    ExperienceStatus,
    ExperienceType,
    FeedbackType,
)

logger = logging.getLogger("kairo.experience.events")


async def publish_experience_event(
    event_type: str,
    payload: Dict[str, Any],
    user_id: Optional[str] = None,
    project_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    causation_id: Optional[str] = None,
) -> None:
    """Publish an experience lifecycle event onto the unified Event Bus."""
    try:
        sanitized_payload = sanitize_content(payload)
        event = Event(
            event_type=event_type,
            source=EventSource.EXPERIENCE,
            user_id=user_id,
            project_id=project_id,
            correlation_id=correlation_id or Event().correlation_id,
            causation_id=causation_id,
            payload=sanitized_payload,
        )
        await event_bus.publish(event)
        logger.debug("Published experience event: %s", event_type)
    except Exception as exc:
        logger.warning("Failed to publish experience event %s: %s", event_type, exc)


async def publish_feedback_event(
    event_type: str,
    payload: Dict[str, Any],
    user_id: str,
    project_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> None:
    """Publish a feedback lifecycle event onto the unified Event Bus."""
    try:
        sanitized_payload = sanitize_content(payload)
        event = Event(
            event_type=event_type,
            source=EventSource.FEEDBACK,
            user_id=user_id,
            project_id=project_id,
            correlation_id=correlation_id or Event().correlation_id,
            payload=sanitized_payload,
        )
        await event_bus.publish(event)
        logger.debug("Published feedback event: %s", event_type)
    except Exception as exc:
        logger.warning("Failed to publish feedback event %s: %s", event_type, exc)


async def handle_project_updated_event(event: Event) -> None:
    """When a project updates (e.g. repo changes, branch switches),

    decay or mark project experiences STALE to avoid outdated context.
    """
    project_id = event.project_id or event.payload.get("project_id")
    if not project_id:
        return

    logger.info("Project update received for %s; marking prior experience STALE", project_id)
    try:
        from app.experience.service import ExperienceService

        service = ExperienceService()
        stale_count = await service.mark_stale_on_project_change(
            project_id=project_id,
        )
        logger.info("Marked %d experiences STALE for project %s", stale_count, project_id)
    except Exception as exc:
        logger.error("Error updating stale experiences on project update: %s", exc)


async def handle_feedback_created_event(event: Event) -> None:
    """Process newly submitted feedback.

    If negative feedback accumulates on a skill or automation, flag learning review.
    Does NOT autonomously alter security or routing policies.
    """
    user_id = event.user_id
    payload = event.payload or {}
    feedback_type = payload.get("feedback_type")
    skill_name = payload.get("skill")
    automation_id = payload.get("automation_id")

    # If user provided negative feedback or correction
    if feedback_type in (FeedbackType.NEGATIVE.value, FeedbackType.CORRECTION.value):
        logger.info("Negative/correction feedback logged: skill=%s, automation=%s", skill_name, automation_id)

        # Emit learning review requested event if relevant
        if skill_name or automation_id:
            await publish_experience_event(
                event_type="learning.review.requested",
                payload={
                    "reason": f"Feedback received on {skill_name or automation_id}",
                    "feedback_type": feedback_type,
                    "target": skill_name or automation_id,
                },
                user_id=user_id,
                project_id=event.project_id,
                correlation_id=event.correlation_id,
            )


def register_experience_subscribers(bus: Any = None) -> None:
    """Register experience and learning subscribers onto the Event Bus."""
    target_bus = bus or event_bus

    # 1. Project updates -> Stale decay
    for pattern in ["project.updated", "project.file.changed", "knowledge.code.superseded"]:
        target_bus.subscribe(
            pattern=pattern,
            handler=handle_project_updated_event,
            name=f"experience_decay_{pattern}",
            priority=45,
            system_wide=True,
        )

    # 2. Feedback created -> Evaluation & Review flagging
    target_bus.subscribe(
        pattern="feedback.created",
        handler=handle_feedback_created_event,
        name="experience_feedback_processor",
        priority=40,
        system_wide=True,
    )

    logger.info("Experience and learning EventBus subscribers registered.")
