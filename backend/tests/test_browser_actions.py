"""Unit and integration tests for BrowserClickTool, BrowserFillTool, Screenshot, and Policies."""

import pytest

from app.core.config import Settings
from app.tools.browser.actions import BrowserClickTool, BrowserFillTool, BrowserScreenshotTool
from app.tools.browser.manager import BrowserManager
from app.tools.browser.policies import DownloadPolicy, SensitiveFieldPolicy, SubmissionPolicy

HTML_INTERACTIVE = """
<!DOCTYPE html>
<html>
<head><title>Actions Test</title></head>
<body>
    <button id="btn-normal">Click Me</button>
    <button id="btn-submit" type="submit">Submit Form</button>
    <button id="btn-hidden" style="display:none;">Hidden</button>

    <form>

        <input id="search-box" name="search" type="text" placeholder="Search articles" />
        <input id="user-password" name="password" type="password" />
        <input id="api-key" name="api_key" type="text" />
        <input id="card-num" name="credit_card" type="text" />
    </form>
</body>
</html>
"""


def test_sensitive_field_policy():
    """Verify SensitiveFieldPolicy detects passwords, keys, tokens, and credit cards."""
    # Password field
    is_sens, _ = SensitiveFieldPolicy.is_sensitive("password", "mypassword", {"type": "password"})
    assert is_sens is True

    # Credit card field
    is_sens, _ = SensitiveFieldPolicy.is_sensitive("card_number", "4111222233334444")
    assert is_sens is True

    # API key field
    is_sens, _ = SensitiveFieldPolicy.is_sensitive("api_key", "sk-live-1234567890abcdef")
    assert is_sens is True

    # Sensitive token in value
    is_sens, _ = SensitiveFieldPolicy.is_sensitive("query", "Bearer eyJhbGciOi...")
    assert is_sens is True

    # Normal field
    is_sens, _ = SensitiveFieldPolicy.is_sensitive("search_term", "climate change")
    assert is_sens is False


def test_submission_policy():
    """Verify SubmissionPolicy identifies submit buttons and checkout actions."""
    is_sub, _ = SubmissionPolicy.is_submission_action("button", "Submit", {"type": "submit"})
    assert is_sub is True

    is_sub, _ = SubmissionPolicy.is_submission_action("button", "Checkout Now")
    assert is_sub is True

    is_sub, _ = SubmissionPolicy.is_submission_action("button", "View Details")
    assert is_sub is False


def test_download_policy():
    """Verify DownloadPolicy rejects automated downloads and dangerous extensions."""
    allowed, reason = DownloadPolicy.evaluate_download("setup.exe")
    assert allowed is False
    assert "strictly prohibited" in reason

    allowed, _ = DownloadPolicy.evaluate_download("script.sh")
    assert allowed is False

    allowed, _ = DownloadPolicy.evaluate_download("document.pdf")
    assert allowed is False


@pytest.mark.asyncio
async def test_click_unapproved_requires_approval():
    """Verify BrowserClickTool requires explicit approval before executing."""
    settings = Settings(KAIRO_BROWSER_ENABLED=True, KAIRO_BROWSER_HEADLESS=True)
    manager = BrowserManager(settings=settings)
    try:
        session = await manager.get_or_create_session("click_test_1")
        await session.page.set_content(HTML_INTERACTIVE)

        tool = BrowserClickTool(manager=manager)
        res = await tool.execute(selector="#btn-normal", session_id="click_test_1", approved=False)

        assert res["success"] is False
        assert res.get("approval_required") is True
    finally:
        await manager.close_all()


@pytest.mark.asyncio
async def test_click_approved_normal_button():
    """Verify BrowserClickTool executes click when approved=True."""
    settings = Settings(KAIRO_BROWSER_ENABLED=True, KAIRO_BROWSER_HEADLESS=True)
    manager = BrowserManager(settings=settings)
    try:
        session = await manager.get_or_create_session("click_test_2")
        await session.page.set_content(HTML_INTERACTIVE)

        tool = BrowserClickTool(manager=manager)
        res = await tool.execute(selector="#btn-normal", session_id="click_test_2", approved=True)

        assert res["success"] is True
    finally:
        await manager.close_all()


@pytest.mark.asyncio
async def test_click_missing_element():
    """Verify BrowserClickTool returns clear error when target does not exist."""
    settings = Settings(KAIRO_BROWSER_ENABLED=True, KAIRO_BROWSER_HEADLESS=True)
    manager = BrowserManager(settings=settings)
    try:
        session = await manager.get_or_create_session("click_test_3")
        await session.page.set_content(HTML_INTERACTIVE)

        tool = BrowserClickTool(manager=manager)
        res = await tool.execute(selector="#nonexistent", session_id="click_test_3", approved=True)

        assert res["success"] is False
        assert "not found" in res["error"]
    finally:
        await manager.close_all()


@pytest.mark.asyncio
async def test_click_submission_button_requires_approval():
    """Verify clicking a submit button triggers submission policy."""
    settings = Settings(KAIRO_BROWSER_ENABLED=True, KAIRO_BROWSER_HEADLESS=True)
    manager = BrowserManager(settings=settings)
    try:
        session = await manager.get_or_create_session("click_test_4")
        await session.page.set_content(HTML_INTERACTIVE)

        # Even with tool-level approval, session checks submission policy
        res = await session.click(selector="#btn-submit", approved=False)

        assert res["success"] is False
        assert res.get("approval_required") is True
        assert "submission" in res.get("error", "").lower()
    finally:
        await manager.close_all()


@pytest.mark.asyncio
async def test_fill_sensitive_password_rejected():
    """Verify BrowserFillTool strictly blocks password fields."""
    settings = Settings(KAIRO_BROWSER_ENABLED=True, KAIRO_BROWSER_HEADLESS=True)
    manager = BrowserManager(settings=settings)
    try:
        session = await manager.get_or_create_session("fill_test_1")
        await session.page.set_content(HTML_INTERACTIVE)

        tool = BrowserFillTool(manager=manager)
        res = await tool.execute(field="password", value="Secret123!", session_id="fill_test_1", approved=True)

        assert res["success"] is False
        assert "Security policy blocked" in res["error"]
    finally:
        await manager.close_all()


@pytest.mark.asyncio
async def test_fill_credit_card_and_api_key_rejected():
    """Verify BrowserFillTool rejects credit card and API key fields."""
    settings = Settings(KAIRO_BROWSER_ENABLED=True, KAIRO_BROWSER_HEADLESS=True)
    manager = BrowserManager(settings=settings)
    try:
        tool = BrowserFillTool(manager=manager)

        res_cc = await tool.execute(field="credit_card", value="4111222233334444", session_id="fill_test_2")
        assert res_cc["success"] is False
        assert "Security policy blocked" in res_cc["error"]

        res_key = await tool.execute(field="api_key", value="sk-test-abc", session_id="fill_test_2")
        assert res_key["success"] is False
        assert "Security policy blocked" in res_key["error"]
    finally:
        await manager.close_all()


@pytest.mark.asyncio
async def test_fill_normal_field():
    """Verify filling a normal non-sensitive field succeeds when approved."""
    settings = Settings(KAIRO_BROWSER_ENABLED=True, KAIRO_BROWSER_HEADLESS=True)
    manager = BrowserManager(settings=settings)
    try:
        session = await manager.get_or_create_session("fill_test_3")
        await session.page.set_content(HTML_INTERACTIVE)

        tool = BrowserFillTool(manager=manager)
        res = await tool.execute(field="search", value="quantum computing", session_id="fill_test_3", approved=True)

        assert res["success"] is True
        val = await session.page.locator("#search-box").input_value()
        assert val == "quantum computing"
    finally:
        await manager.close_all()


@pytest.mark.asyncio
async def test_browser_screenshot():
    """Verify BrowserScreenshotTool captures screenshot and returns base64 PNG."""
    settings = Settings(KAIRO_BROWSER_ENABLED=True, KAIRO_BROWSER_HEADLESS=True)
    manager = BrowserManager(settings=settings)
    try:
        session = await manager.get_or_create_session("screenshot_test")
        await session.page.set_content("<html><body><h1>Screenshot Page</h1></body></html>")

        tool = BrowserScreenshotTool(manager=manager)
        res = await tool.execute(session_id="screenshot_test")

        assert res["success"] is True
        assert "image_base64" in res
        assert len(res["image_base64"]) > 100
        assert res["image_format"] == "png"
    finally:

        await manager.close_all()
