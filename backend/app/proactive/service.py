"""Central Proactive Intelligence Service coordinating observation, ranking, and notifications."""

import hashlib
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.proactive.cooldown import CooldownTracker
from app.proactive.deduplicator import InsightDeduplicator
from app.proactive.detector import ProactiveDetector
from app.proactive.models import ProactiveInsight, UserProactiveSettings, WebMonitor
from app.proactive.notifier import NotificationService
from app.proactive.prioritizer import InsightPrioritizer
from app.proactive.safety import ProactiveSafetyGuard
from app.proactive.schemas import (
    ProactiveFeedResponse,
    ProactiveInsightRead,
    UserProactiveSettingsUpdate,
    WebMonitorCheckResult,
    WebMonitorCreate,
    WebMonitorUpdate,
)
from app.proactive.state import InsightPriority, InsightStatus, SourceType
from app.tools.web.extraction import extract_content_from_html
from app.tools.web.safety import URLSafetyValidator

logger = logging.getLogger("kairo.proactive.service")


class ProactiveService:
    """Authoritative orchestrator for Kairo's Proactive Intelligence Layer."""

    @classmethod
    async def get_or_create_settings(
        cls,
        db_session: AsyncSession,
        user_id: str,
    ) -> UserProactiveSettings:
        """Fetch existing user proactive settings or create default preferences."""
        query = select(UserProactiveSettings).where(UserProactiveSettings.user_id == user_id)
        res = await db_session.execute(query)
        settings = res.scalar_one_or_none()
        if not settings:
            settings = UserProactiveSettings(
                user_id=user_id,
                proactive_enabled=True,
                notify_on_workflow_failure=True,
                notify_on_ci_failure=True,
                notify_on_approval=True,
                notify_on_web_change=True,
                minimum_priority=InsightPriority.LOW,
                quiet_hours_enabled=False,
                quiet_hours_start="22:00",
                quiet_hours_end="08:00",
                timezone="UTC",
            )
            db_session.add(settings)
            await db_session.commit()
            await db_session.refresh(settings)
        return settings

    @classmethod
    async def update_settings(
        cls,
        db_session: AsyncSession,
        user_id: str,
        update_data: UserProactiveSettingsUpdate,
    ) -> UserProactiveSettings:
        """Update proactive preferences for user."""
        settings = await cls.get_or_create_settings(db_session, user_id)
        data_dict = update_data.model_dump(exclude_unset=True)

        for key, value in data_dict.items():
            if hasattr(settings, key) and value is not None:
                setattr(settings, key, value)

        await db_session.commit()
        await db_session.refresh(settings)
        return settings

    @classmethod
    async def process_event(
        cls,
        db_session: AsyncSession,
        user_id: str,
        source_type: SourceType | str,
        category: str,
        payload: dict[str, Any] | None = None,
        source_id: str | None = None,
        chain_depth: int = 0,
        redis_client: Any = None,
    ) -> ProactiveInsight | None:
        """Main proactive pipeline:
        Event -> Candidate Detection -> Safety/Policy Filter -> Deduplication -> Cooldown -> Priority -> Notification.
        """
        payload = payload or {}
        st = str(source_type).upper()
        cat = category.lower()

        # 1. Global config check
        cfg = get_settings()
        if not getattr(cfg, "KAIRO_PROACTIVE_ENABLED", True):
            logger.debug("Proactive intelligence is disabled globally.")
            return None

        # 2. Safety chain-depth check (prevents self-triggering action loops)
        ProactiveSafetyGuard.check_chain_depth(chain_depth)

        # 3. User settings & category preferences
        user_settings = await cls.get_or_create_settings(db_session, user_id)

        # Security events (CRITICAL) bypass user-disabled proactive toggle
        is_security_event = st in (SourceType.SECURITY, "SECURITY") or "emergency" in cat
        if not user_settings.proactive_enabled and not is_security_event:
            logger.debug("Proactive notifications disabled by user %s.", user_id)
            return None

        # Category specific preference toggles
        if not is_security_event:
            if (
                "fail" in cat
                and st in (SourceType.WORKFLOW, "WORKFLOW")
                and not user_settings.notify_on_workflow_failure
            ):
                return None
            if ("ci" in cat or "check" in cat) and not user_settings.notify_on_ci_failure:
                return None
            if "approval" in cat and not user_settings.notify_on_approval:
                return None
            if "web" in cat and not user_settings.notify_on_web_change:
                return None

        # 4. Candidate detection
        candidate = ProactiveDetector.create_candidate(
            user_id=user_id,
            source_type=source_type,
            category=category,
            payload=payload,
            source_id=source_id,
            chain_depth=chain_depth,
        )
        if not candidate:
            return None

        # 5. Priority threshold filter
        if not is_security_event:
            if not InsightPrioritizer.meets_priority_threshold(
                candidate.priority, user_settings.minimum_priority
            ):
                logger.info(
                    "Insight priority %s below minimum threshold %s for user %s",
                    candidate.priority,
                    user_settings.minimum_priority,
                    user_id,
                )
                return None

        # 6. Cooldown tracker (check condition transitions, e.g. UP -> DOWN vs repeated DOWN)
        should_alert = await CooldownTracker.should_notify_transition(
            user_id=user_id,
            source_type=str(candidate.source_type),
            source_id=candidate.source_id,
            state_key=candidate.state_key,
            current_state_value=candidate.state_value,
            redis_client=redis_client,
        )
        if not should_alert:
            return None

        # 7. Deduplication (SHA-256 fingerprint within deduplication window)
        fingerprint = InsightDeduplicator.compute_fingerprint(candidate)
        is_dup = await InsightDeduplicator.is_duplicate(
            candidate=candidate,
            fingerprint=fingerprint,
            db_session=db_session,
        )
        if is_dup:
            return None

        # 8. Rate limiting (hourly notification cap, preserving CRITICAL/HIGH)
        rate_ok = await NotificationService.check_rate_limit(
            user_id=user_id,
            priority=str(candidate.priority),
            db_session=db_session,
            redis_client=redis_client,
        )
        if not rate_ok:
            return None

        # 9. Quiet hours check
        in_quiet = NotificationService.is_in_quiet_hours(user_settings)
        # In quiet hours, LOW and MEDIUM are held as NEW (not delivered immediately)
        initial_status = InsightStatus.DELIVERED
        if in_quiet and candidate.priority in (InsightPriority.LOW, InsightPriority.MEDIUM):
            initial_status = InsightStatus.NEW
            logger.info("Quiet hours active for user %s. Insight queued with status NEW.", user_id)

        # 10. Compute expiration (24h for routine, 7d for high/critical)
        now = datetime.now(UTC)
        ttl_days = 7 if candidate.priority in (InsightPriority.HIGH, InsightPriority.CRITICAL) else 1
        expires_at = candidate.expires_at or (now + timedelta(days=ttl_days))

        # 11. Persist insight
        insight = ProactiveInsight(
            user_id=candidate.user_id,
            source_type=str(candidate.source_type),
            source_id=candidate.source_id,
            title=candidate.title,
            summary=candidate.summary,
            priority=str(candidate.priority),
            actionability=str(candidate.actionability),
            status=str(initial_status),
            action_payload=candidate.action_payload,
            fingerprint=fingerprint,
            created_at=now,
            expires_at=expires_at,
        )
        db_session.add(insight)
        await db_session.commit()
        await db_session.refresh(insight)

        logger.info(
            "Created proactive insight %s (priority=%s status=%s) for user=%s",
            insight.id,
            insight.priority,
            insight.status,
            user_id,
        )
        return insight

    @classmethod
    async def get_feed(
        cls,
        db_session: AsyncSession,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> ProactiveFeedResponse:
        """Retrieve deterministic ranked proactive feed for user."""
        now = datetime.now(UTC)

        # 1. Cleanup expired insights
        expired_query = select(ProactiveInsight).where(
            ProactiveInsight.user_id == user_id,
            ProactiveInsight.expires_at.is_not(None),
            ProactiveInsight.status != InsightStatus.EXPIRED,
        )
        expired_res = await db_session.execute(expired_query)
        for item in expired_res.scalars().all():
            if item.expires_at:
                item_exp = (
                    item.expires_at
                    if item.expires_at.tzinfo is not None
                    else item.expires_at.replace(tzinfo=UTC)
                )
                if item_exp < now:
                    item.status = InsightStatus.EXPIRED
        await db_session.commit()

        # 2. Fetch active items (new, delivered, read)
        query = (
            select(ProactiveInsight)
            .where(
                ProactiveInsight.user_id == user_id,
                ProactiveInsight.status.in_([InsightStatus.NEW, InsightStatus.DELIVERED, InsightStatus.READ]),
            )
            .order_by(desc(ProactiveInsight.created_at))
        )
        res = await db_session.execute(query)
        all_items = list(res.scalars().all())

        # Unread count
        unread_count = sum(
            1 for item in all_items if item.status in (InsightStatus.NEW, InsightStatus.DELIVERED)
        )
        total = len(all_items)

        # 3. Deterministic ranking:
        # Score = Priority Weight + Unread Bonus + Freshness Score
        priority_weights = {
            InsightPriority.CRITICAL: 1000,
            InsightPriority.HIGH: 500,
            InsightPriority.MEDIUM: 200,
            InsightPriority.LOW: 50,
        }

        def rank_score(item: ProactiveInsight) -> float:
            p_score = priority_weights.get(item.priority.upper(), 100)
            unread_bonus = 300 if item.status in (InsightStatus.NEW, InsightStatus.DELIVERED) else 0
            # Freshness score (up to 100, decaying 2 points per hour)
            c_at = (
                item.created_at if item.created_at.tzinfo is not None else item.created_at.replace(tzinfo=UTC)
            )
            age_hours = max(0.0, (now - c_at).total_seconds() / 3600.0)
            freshness = max(0.0, 100.0 - (age_hours * 2.0))
            return p_score + unread_bonus + freshness

        ranked_items = sorted(all_items, key=rank_score, reverse=True)
        paginated_items = ranked_items[offset : offset + limit]

        items_read = [ProactiveInsightRead.model_validate(item) for item in paginated_items]

        return ProactiveFeedResponse(
            items=items_read,
            total=total,
            unread_count=unread_count,
        )

    # -------------------------------------------------------------
    # Web Monitoring Management & Evaluation
    # -------------------------------------------------------------

    @classmethod
    async def create_web_monitor(
        cls,
        db_session: AsyncSession,
        user_id: str,
        data: WebMonitorCreate,
    ) -> WebMonitor:
        """Create a monitored web URL with full SSRF validation."""
        # SSRF and protocol safety check
        safe_url = URLSafetyValidator.validate_url(data.url)

        monitor = WebMonitor(
            user_id=user_id,
            name=data.name.strip(),
            url=safe_url,
            check_interval_seconds=data.check_interval_seconds,
            enabled=data.enabled,
        )
        db_session.add(monitor)
        await db_session.commit()
        await db_session.refresh(monitor)
        return monitor

    @classmethod
    async def list_web_monitors(
        cls,
        db_session: AsyncSession,
        user_id: str,
    ) -> list[WebMonitor]:
        """List web monitors scoped to user."""
        query = select(WebMonitor).where(WebMonitor.user_id == user_id).order_by(desc(WebMonitor.created_at))
        res = await db_session.execute(query)
        return list(res.scalars().all())

    @classmethod
    async def get_web_monitor(
        cls,
        db_session: AsyncSession,
        user_id: str,
        monitor_id: str,
    ) -> WebMonitor | None:
        """Retrieve web monitor ensuring tenant ownership."""
        query = select(WebMonitor).where(
            WebMonitor.id == monitor_id,
            WebMonitor.user_id == user_id,
        )
        res = await db_session.execute(query)
        return res.scalar_one_or_none()

    @classmethod
    async def update_web_monitor(
        cls,
        db_session: AsyncSession,
        user_id: str,
        monitor_id: str,
        data: WebMonitorUpdate,
    ) -> WebMonitor | None:
        """Update monitor settings ensuring tenant ownership and URL SSRF safety."""
        monitor = await cls.get_web_monitor(db_session, user_id, monitor_id)
        if not monitor:
            return None

        update_dict = data.model_dump(exclude_unset=True)
        if "url" in update_dict and update_dict["url"]:
            update_dict["url"] = URLSafetyValidator.validate_url(update_dict["url"])

        for k, v in update_dict.items():
            if hasattr(monitor, k) and v is not None:
                setattr(monitor, k, v)

        await db_session.commit()
        await db_session.refresh(monitor)
        return monitor

    @classmethod
    async def delete_web_monitor(
        cls,
        db_session: AsyncSession,
        user_id: str,
        monitor_id: str,
    ) -> bool:
        """Delete web monitor ensuring tenant ownership."""
        monitor = await cls.get_web_monitor(db_session, user_id, monitor_id)
        if not monitor:
            return False

        await db_session.delete(monitor)
        await db_session.commit()
        return True

    @classmethod
    async def check_web_monitor(
        cls,
        db_session: AsyncSession,
        monitor: WebMonitor,
    ) -> WebMonitorCheckResult:
        """Safely fetch URL, extract text, compute content fingerprint, and detect change."""
        now = datetime.now(UTC)
        old_fp = monitor.content_fingerprint

        # SSRF validation before fetch
        safe_url = URLSafetyValidator.validate_url(monitor.url)

        try:
            async with httpx.AsyncClient(
                timeout=10.0,
                follow_redirects=True,
                max_redirects=3,
                headers={"User-Agent": "Kairo-WebMonitor/1.0"},
            ) as client:
                resp = await client.get(safe_url)
                resp.raise_for_status()
                html_text = resp.text

            # Extract normalized text
            _title, text = extract_content_from_html(html_text, max_chars=30000)
            normalized = " ".join(text.split())
            new_fp = hashlib.sha256(normalized.encode("utf-8")).hexdigest()

            changed = (old_fp is not None) and (old_fp != new_fp)

            monitor.content_fingerprint = new_fp
            monitor.last_checked_at = now
            await db_session.commit()

            # If changed, dispatch proactive event!
            if changed:
                await cls.process_event(
                    db_session=db_session,
                    user_id=monitor.user_id,
                    source_type=SourceType.WEB_MONITOR,
                    category="web_monitor.changed",
                    payload={
                        "monitor_id": monitor.id,
                        "monitor_name": monitor.name,
                        "url": monitor.url,
                        "old_fingerprint": old_fp,
                        "new_fingerprint": new_fp,
                    },
                    source_id=monitor.id,
                )

            return WebMonitorCheckResult(
                monitor_id=monitor.id,
                url=monitor.url,
                changed=changed,
                old_fingerprint=old_fp,
                new_fingerprint=new_fp,
                checked_at=now,
                error=None,
            )
        except Exception as exc:
            logger.warning("Web monitor check failed for %s (%s): %s", monitor.name, monitor.url, exc)
            return WebMonitorCheckResult(
                monitor_id=monitor.id,
                url=monitor.url,
                changed=False,
                old_fingerprint=old_fp,
                new_fingerprint=old_fp or "",
                checked_at=now,
                error=str(exc),
            )
