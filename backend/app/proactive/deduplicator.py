"""Insight deduplication based on stable SHA-256 fingerprints and configurable time windows."""

import hashlib
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.proactive.models import ProactiveInsight
from app.proactive.schemas import CandidateInsight

logger = logging.getLogger("kairo.proactive.deduplicator")


class InsightDeduplicator:
    """Computes stable fingerprints for candidate insights and suppresses duplicates within a sliding window."""

    @classmethod
    def compute_fingerprint(cls, candidate: CandidateInsight) -> str:
        """Compute deterministic SHA-256 fingerprint from user, source, resource, and category."""
        components = [
            candidate.user_id,
            str(candidate.source_type),
            str(candidate.source_id or ""),
            candidate.category,
        ]
        raw_key = ":".join(components)
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    @classmethod
    async def is_duplicate(
        cls,
        candidate: CandidateInsight,
        fingerprint: str,
        db_session: AsyncSession,
        dedup_window_seconds: int | None = None,
    ) -> bool:
        """Check if an insight with this fingerprint was already surfaced to the user recently."""
        settings = get_settings()
        window = (
            dedup_window_seconds
            if dedup_window_seconds is not None
            else getattr(settings, "KAIRO_PROACTIVE_DEDUP_WINDOW_SECONDS", 3600)
        )
        cutoff = datetime.now(UTC) - timedelta(seconds=window)

        query = (
            select(ProactiveInsight.id)
            .where(
                ProactiveInsight.user_id == candidate.user_id,
                ProactiveInsight.fingerprint == fingerprint,
                ProactiveInsight.created_at >= cutoff,
                ProactiveInsight.status.in_(["new", "delivered", "read"]),
            )
            .limit(1)
        )

        res = await db_session.execute(query)
        duplicate_id = res.scalar_one_or_none()
        if duplicate_id:
            logger.info(
                "Suppressed duplicate insight for user=%s source=%s category=%s (existing=%s)",
                candidate.user_id,
                candidate.source_type,
                candidate.category,
                duplicate_id,
            )
            return True

        return False
