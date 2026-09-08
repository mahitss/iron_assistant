"""BaseTool implementations for Kairo's Browser Control System."""

import logging
from typing import Any

from app.core.config import get_settings
from app.tools.base import BaseTool
from app.tools.browser.manager import BrowserManager, get_browser_manager
from app.tools.browser.policies import SensitiveFieldPolicy
from app.tools.browser.schemas import (
    BrowserClickArgs,
    BrowserFillArgs,
    BrowserInspectArgs,
    BrowserNavigateArgs,
    BrowserScreenshotArgs,
)
from app.tools.permissions import PermissionLevel

logger = logging.getLogger("kairo.tools.browser.actions")

DEFAULT_BROWSER_SESSION = "default_session"


class BrowserNavigateTool(BaseTool):
    """Tool allowing Kairo to navigate a controlled browser to a public webpage."""

    name = "browser_navigate"
    description = (
        "Navigate the controlled browser to a public webpage URL. "
        "Validates URL against SSRF and private networks. Returns title and HTTP status."
    )
    permission_level = PermissionLevel.READ
    args_model = BrowserNavigateArgs

    def __init__(self, manager: BrowserManager | None = None) -> None:
        self.manager = manager or get_browser_manager()
        self.timeout_ms = int(get_settings().KAIRO_BROWSER_NAVIGATION_TIMEOUT_SECONDS * 1000)

    async def execute(self, url: str, session_id: str | None = None) -> dict[str, Any]:
        sid = (session_id or DEFAULT_BROWSER_SESSION).strip()
        try:
            session = await self.manager.get_or_create_session(sid)
            result = await session.navigate(url=url, timeout_ms=self.timeout_ms)
            result["session_id"] = sid
            return result
        except Exception as exc:
            logger.warning("browser_navigate failed for '%s': %s", url, exc)
            return {"success": False, "session_id": sid, "error": str(exc)}

    def verify(self, result: Any) -> bool:
        return isinstance(result, dict) and "success" in result


class BrowserInspectTool(BaseTool):
    """Tool allowing Kairo to inspect visible text, headings, links, and forms on the current page."""

    name = "browser_inspect"
    description = (
        "Inspect visible content, headings, links, buttons, and forms on the current page. "
        "Returns sanitized, bounded text without sensitive cookies or tokens."
    )
    permission_level = PermissionLevel.READ
    args_model = BrowserInspectArgs

    def __init__(self, manager: BrowserManager | None = None) -> None:
        self.manager = manager or get_browser_manager()
        cfg = getattr(self.manager, "settings", get_settings())
        self.max_text_chars = cfg.KAIRO_BROWSER_MAX_TEXT_CHARS
        self.max_links = cfg.KAIRO_BROWSER_MAX_LINKS
        self.max_elements = cfg.KAIRO_BROWSER_MAX_ELEMENTS

    async def execute(self, session_id: str | None = None) -> dict[str, Any]:
        sid = (session_id or DEFAULT_BROWSER_SESSION).strip()
        session = self.manager.get_session(sid)
        if session is None or session.status != "active":
            return {
                "success": False,
                "session_id": sid,
                "error": f"No active browser session '{sid}'. Please call browser_navigate first.",
            }

        try:
            inspection = await session.inspect(
                max_text_chars=self.max_text_chars,
                max_links=self.max_links,
                max_elements=self.max_elements,
            )
            return {
                "success": True,
                "session_id": sid,
                **inspection.model_dump(),
            }
        except Exception as exc:
            logger.warning("browser_inspect failed for '%s': %s", sid, exc)
            return {"success": False, "session_id": sid, "error": str(exc)}

    def verify(self, result: Any) -> bool:
        return isinstance(result, dict) and "success" in result


class BrowserScreenshotTool(BaseTool):
    """Tool allowing Kairo to capture a screenshot of the current browser page."""

    name = "browser_screenshot"
    description = (
        "Capture a screenshot of the current page as a base64-encoded PNG image. "
        "Does not expose sensitive browser cookies or authentication state."
    )
    permission_level = PermissionLevel.READ
    args_model = BrowserScreenshotArgs

    def __init__(self, manager: BrowserManager | None = None) -> None:
        self.manager = manager or get_browser_manager()

    async def execute(self, session_id: str | None = None, full_page: bool = False) -> dict[str, Any]:
        sid = (session_id or DEFAULT_BROWSER_SESSION).strip()
        session = self.manager.get_session(sid)
        if session is None or session.status != "active":
            return {
                "success": False,
                "session_id": sid,
                "error": f"No active browser session '{sid}'. Please call browser_navigate first.",
            }

        try:
            b64_img = await session.screenshot(full_page=full_page)
            return {
                "success": True,
                "session_id": sid,
                "url": session.page.url,
                "image_format": "png",
                "image_base64_length": len(b64_img),
                "image_base64": b64_img,
            }
        except Exception as exc:
            logger.warning("browser_screenshot failed for '%s': %s", sid, exc)
            return {"success": False, "session_id": sid, "error": str(exc)}

    def verify(self, result: Any) -> bool:
        return isinstance(result, dict) and "success" in result


class BrowserClickTool(BaseTool):
    """Tool allowing Kairo to click an interactive element. Requires approval for submission actions."""

    name = "browser_click"
    description = (
        "Click an interactive element on the page using role, accessible name, text, or selector. "
        "Critical submission actions require explicit user approval."
    )
    permission_level = PermissionLevel.EXTERNAL
    args_model = BrowserClickArgs

    def __init__(self, manager: BrowserManager | None = None) -> None:
        self.manager = manager or get_browser_manager()
        self.timeout_ms = int(get_settings().KAIRO_BROWSER_ACTION_TIMEOUT_SECONDS * 1000)

    async def execute(
        self,
        selector: str | None = None,
        role: str | None = None,
        name: str | None = None,
        text: str | None = None,
        session_id: str | None = None,
        approved: bool = False,
    ) -> dict[str, Any]:
        sid = (session_id or DEFAULT_BROWSER_SESSION).strip()
        session = self.manager.get_session(sid)
        if session is None or session.status != "active":
            return {
                "success": False,
                "session_id": sid,
                "error": f"No active browser session '{sid}'. Please call browser_navigate first.",
            }

        if not approved:
            # External actions require approval before execution
            return {
                "success": False,
                "session_id": sid,
                "approval_required": True,
                "action": "browser_click",
                "target": {"selector": selector, "role": role, "name": name, "text": text},
                "message": (
                    "Action 'browser_click' is classified as EXTERNAL and requires explicit user approval "
                    "before execution."
                ),
            }

        try:
            res = await session.click(
                selector=selector,
                role=role,
                name=name,
                text=text,
                timeout_ms=self.timeout_ms,
                approved=approved,
            )
            res["session_id"] = sid
            return res
        except Exception as exc:
            return {"success": False, "session_id": sid, "error": str(exc)}

    def verify(self, result: Any) -> bool:
        return isinstance(result, dict) and ("success" in result or "approval_required" in result)


class BrowserFillTool(BaseTool):
    """Tool allowing Kairo to fill form fields. Sensitive credentials and passwords are strictly rejected."""

    name = "browser_fill"
    description = (
        "Fill a form input field identified by label, name, placeholder, or selector. "
        "Sensitive credential fields (passwords, credit cards, CVVs, API keys) are strictly rejected."
    )
    permission_level = PermissionLevel.EXTERNAL
    args_model = BrowserFillArgs

    def __init__(self, manager: BrowserManager | None = None) -> None:
        self.manager = manager or get_browser_manager()
        self.timeout_ms = int(get_settings().KAIRO_BROWSER_ACTION_TIMEOUT_SECONDS * 1000)

    async def execute(
        self,
        field: str,
        value: str,
        session_id: str | None = None,
        approved: bool = False,
    ) -> dict[str, Any]:
        sid = (session_id or DEFAULT_BROWSER_SESSION).strip()

        # 1. Deterministic sensitive field check
        is_sens, sens_reason = SensitiveFieldPolicy.is_sensitive(field, value)
        if is_sens:
            logger.warning("Rejected sensitive field fill attempt for '%s': %s", field, sens_reason)
            return {
                "success": False,
                "session_id": sid,
                "approval_required": True,
                "error": f"Security policy blocked sensitive field entry: {sens_reason}",
            }

        session = self.manager.get_session(sid)
        if session is None or session.status != "active":
            return {
                "success": False,
                "session_id": sid,
                "error": f"No active browser session '{sid}'. Please call browser_navigate first.",
            }

        if not approved:
            # External actions require approval before execution
            return {
                "success": False,
                "session_id": sid,
                "approval_required": True,
                "action": "browser_fill",
                "field": field,
                "message": (
                    f"Action 'browser_fill' on field '{field}' is classified as EXTERNAL and requires "
                    "explicit user approval before execution."
                ),
            }

        try:
            res = await session.fill(
                field=field,
                value=value,
                timeout_ms=self.timeout_ms,
                approved=approved,
            )
            res["session_id"] = sid
            return res
        except Exception as exc:
            return {"success": False, "session_id": sid, "error": str(exc)}

    def verify(self, result: Any) -> bool:
        return isinstance(result, dict) and ("success" in result or "approval_required" in result)
