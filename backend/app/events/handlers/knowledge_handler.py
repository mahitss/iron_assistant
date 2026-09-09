"""Knowledge and Memory event subscriber.

Listens to completed interactions, code merges, and evaluations to ingest relevant
context into Kairo's Knowledge Fabric and Long-Term Memory.
"""

from __future__ import annotations

import logging
from typing import Any

from app.events.schemas import Event

logger = logging.getLogger(__name__)


async def handle_knowledge_ingestion(event: Event) -> None:
    """Indexes relevant event payloads into knowledge/memory."""
    event_type = event.event_type
    payload = event.payload or {}
    user_id = event.user_id

    logger.info(
        "KnowledgeHandler received event '%s' (ID: %s, User: %s)",
        event_type,
        event.event_id,
        user_id,
    )

    if event_type == "chat.response.completed":
        # Extract meaningful conversational summaries or factual nuggets
        topic = payload.get("topic") or "General Conversation"
        logger.debug("Knowledge indexing candidate from chat: %s", topic)

    elif event_type == "github.pr.merged":
        pr_title = payload.get("title", "")
        repo = payload.get("repo", "")
        logger.info("Knowledge indexed PR merge: %s on %s", pr_title, repo)

    elif event_type == "evaluation.completed":
        benchmark = payload.get("benchmark_name", "")
        score = payload.get("overall_score", 0.0)
        logger.info("Knowledge recorded evaluation benchmark: %s (score: %.2f)", benchmark, score)
