"""Browser control module for Kairo using Playwright."""

from app.tools.browser.actions import (
    BrowserClickTool,
    BrowserFillTool,
    BrowserInspectTool,
    BrowserNavigateTool,
    BrowserScreenshotTool,
)
from app.tools.browser.manager import BrowserManager, get_browser_manager
from app.tools.browser.session import BrowserSession

__all__ = [
    "BrowserClickTool",
    "BrowserFillTool",
    "BrowserInspectTool",
    "BrowserManager",
    "BrowserNavigateTool",
    "BrowserScreenshotTool",
    "BrowserSession",
    "get_browser_manager",
]
