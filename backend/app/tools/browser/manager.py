"""BrowserManager coordinating active BrowserSession pool and Playwright process lifecycle."""

import asyncio
import logging

from playwright.async_api import Browser, Playwright, async_playwright

from app.core.config import Settings, get_settings
from app.tools.browser.session import BrowserSession

logger = logging.getLogger("kairo.tools.browser.manager")


class BrowserManager:
    """Manages browser sessions, enforcing concurrency limits, isolation, and lifecycle cleanup."""

    def __init__(self, settings: Settings | None = None) -> None:
        cfg = settings or get_settings()
        self.settings = cfg
        self.enabled = cfg.KAIRO_BROWSER_ENABLED
        self.headless = cfg.KAIRO_BROWSER_HEADLESS
        self.max_sessions = cfg.KAIRO_BROWSER_MAX_SESSIONS
        self.session_timeout = cfg.KAIRO_BROWSER_SESSION_TIMEOUT_SECONDS
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None

        self._sessions: dict[str, BrowserSession] = {}
        self._lock = asyncio.Lock()

    async def _ensure_browser_running(self) -> Browser:
        """Lazy-initialize singleton Playwright instance and Chromium browser."""
        if self._browser is None or not self._browser.is_connected():
            if self._playwright is None:
                self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ],
            )
            logger.info("Launched headless Chromium browser instance.")
        return self._browser

    async def get_or_create_session(self, session_id: str) -> BrowserSession:
        """Retrieve existing active session or create an isolated new browser session."""
        async with self._lock:
            # 1. Cleanup expired sessions
            await self._cleanup_stale_unlocked()

            # 2. Return existing active session
            if session_id in self._sessions:
                sess = self._sessions[session_id]
                if sess.status == "active":
                    sess.touch()
                    return sess
                else:
                    self._sessions.pop(session_id, None)

            # 3. Enforce maximum session concurrency
            if len(self._sessions) >= self.max_sessions:
                # Evict oldest session
                oldest_id = min(self._sessions.keys(), key=lambda k: self._sessions[k].last_used_at)
                logger.info(
                    "Max browser sessions (%d) reached. Evicting oldest session '%s'.",
                    self.max_sessions,
                    oldest_id,
                )
                await self._close_session_unlocked(oldest_id)

            # 4. Launch browser and create isolated context
            browser = await self._ensure_browser_running()
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 KairoBot/1.0",
                viewport={"width": 1280, "height": 800},
                accept_downloads=True,
            )
            page = await context.new_page()

            session = BrowserSession(
                session_id=session_id,
                playwright=self._playwright,
                browser=browser,
                context=context,
                page=page,
            )
            self._sessions[session_id] = session
            logger.info("Created new isolated browser session '%s'", session_id)
            return session

    def get_session(self, session_id: str) -> BrowserSession | None:
        """Lookup active session by ID without creating one."""
        return self._sessions.get(session_id)

    async def close_session(self, session_id: str) -> bool:
        """Explicitly close a browser session and its pages."""
        async with self._lock:
            return await self._close_session_unlocked(session_id)

    async def _close_session_unlocked(self, session_id: str) -> bool:
        sess = self._sessions.pop(session_id, None)
        if sess is not None:
            await sess.close()
            logger.info("Closed browser session '%s'", session_id)
            return True
        return False

    async def cleanup_stale_sessions(self) -> int:
        """Remove and close all sessions exceeding idle timeout."""
        async with self._lock:
            return await self._cleanup_stale_unlocked()

    async def _cleanup_stale_unlocked(self) -> int:
        stale_ids = [
            sid
            for sid, sess in self._sessions.items()
            if sess.is_expired(self.session_timeout) or sess.status != "active"
        ]
        for sid in stale_ids:
            await self._close_session_unlocked(sid)
        if stale_ids:
            logger.info("Cleaned up %d stale browser sessions: %s", len(stale_ids), stale_ids)
        return len(stale_ids)

    async def close_all(self) -> None:
        """Close all active sessions, browser, and Playwright driver."""
        async with self._lock:
            for sid, sess in list(self._sessions.items()):
                await sess.close()
            self._sessions.clear()

            if self._browser is not None:
                try:
                    await self._browser.close()
                except Exception:
                    pass
                self._browser = None

            if self._playwright is not None:
                try:
                    await self._playwright.stop()
                except Exception:
                    pass
                self._playwright = None

            logger.info("BrowserManager completely shut down.")


_GLOBAL_BROWSER_MANAGER: BrowserManager | None = None


def get_browser_manager() -> BrowserManager:
    """Singleton accessor for BrowserManager."""
    global _GLOBAL_BROWSER_MANAGER
    if _GLOBAL_BROWSER_MANAGER is None:
        _GLOBAL_BROWSER_MANAGER = BrowserManager()
    return _GLOBAL_BROWSER_MANAGER
