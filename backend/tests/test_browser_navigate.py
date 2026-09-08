"""Unit and integration tests for BrowserNavigateTool and SSRF/URL validation."""

import pytest

from app.core.config import Settings
from app.tools.browser.actions import BrowserNavigateTool
from app.tools.browser.manager import BrowserManager
from app.tools.browser.safety import BrowserSafetyValidator


def test_safety_validator_schemes():
    """Verify non-HTTP schemes are rejected."""
    with pytest.raises(ValueError):
        BrowserSafetyValidator.validate_url("ftp://example.com/file.txt")

    with pytest.raises(ValueError):
        BrowserSafetyValidator.validate_url("file:///etc/passwd")

    with pytest.raises(ValueError):
        BrowserSafetyValidator.validate_url("javascript:alert(1)")


def test_safety_validator_localhost_and_private_ips():
    """Verify localhost, private IPs, and cloud metadata addresses are blocked."""
    prohibited_urls = [
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.2",
        "http://[::1]",
        "http://192.168.1.1/admin",
        "http://10.0.0.5",
        "http://172.16.0.100",
        "http://169.254.169.254/latest/meta-data",
    ]
    for url in prohibited_urls:
        with pytest.raises(ValueError):
            BrowserSafetyValidator.validate_url(url)


@pytest.mark.asyncio
async def test_navigate_blocks_private_ip():
    """Verify BrowserNavigateTool safely returns failure when navigating to private IP."""
    settings = Settings(KAIRO_BROWSER_ENABLED=True, KAIRO_BROWSER_HEADLESS=True)
    manager = BrowserManager(settings=settings)
    tool = BrowserNavigateTool(manager=manager)
    try:
        res = await tool.execute(url="http://127.0.0.1:8000/internal", session_id="nav_test_1")
        assert res["success"] is False
        assert "error" in res
    finally:
        await manager.close_all()


@pytest.mark.asyncio
async def test_navigate_blocks_localhost():
    """Verify BrowserNavigateTool blocks localhost URL."""
    settings = Settings(KAIRO_BROWSER_ENABLED=True, KAIRO_BROWSER_HEADLESS=True)
    manager = BrowserManager(settings=settings)
    tool = BrowserNavigateTool(manager=manager)
    try:
        res = await tool.execute(url="http://localhost:9000", session_id="nav_test_2")
        assert res["success"] is False
    finally:
        await manager.close_all()


@pytest.mark.asyncio
async def test_navigate_valid_mocked_page():
    """Verify BrowserNavigateTool succeeds when navigating to a mocked safe page."""
    settings = Settings(KAIRO_BROWSER_ENABLED=True, KAIRO_BROWSER_HEADLESS=True)
    manager = BrowserManager(settings=settings)
    try:
        session = await manager.get_or_create_session("nav_valid")

        # Mock public URL using Playwright page route
        async def handle_route(route):
            await route.fulfill(
                status=200,
                content_type="text/html",
                body="<html><head><title>Mocked Public Page</title></head><body><h1>Welcome</h1></body></html>",
            )

        await session.page.route("https://example.com/mock", handle_route)

        tool = BrowserNavigateTool(manager=manager)
        res = await tool.execute(url="https://example.com/mock", session_id="nav_valid")

        assert res["success"] is True
        assert res["title"] == "Mocked Public Page"
        assert res["status_code"] == 200
    finally:
        await manager.close_all()


@pytest.mark.asyncio
async def test_navigate_redirect_to_private_ip_blocked():
    """Verify that if a public URL redirects to a private IP, post-navigation check catches it."""
    settings = Settings(KAIRO_BROWSER_ENABLED=True, KAIRO_BROWSER_HEADLESS=True)
    manager = BrowserManager(settings=settings)
    try:
        session = await manager.get_or_create_session("nav_redirect")

        # Mock redirect to localhost
        async def handle_redirect(route):
            await route.fulfill(
                status=302,
                headers={"Location": "http://127.0.0.1:9999/secret"},
            )

        await session.page.route("https://example.com/unsafe-redirect", handle_redirect)

        tool = BrowserNavigateTool(manager=manager)
        res = await tool.execute(url="https://example.com/unsafe-redirect", session_id="nav_redirect")

        assert res["success"] is False
        assert "Navigation redirected to prohibited address" in res.get(
            "error", ""
        ) or "Failed to navigate" in res.get("error", "")
    finally:
        await manager.close_all()
