"""Unit and integration tests for BrowserInspectTool."""

import pytest

from app.core.config import Settings
from app.tools.browser.actions import BrowserInspectTool
from app.tools.browser.manager import BrowserManager

HTML_SAMPLE = """
<!DOCTYPE html>
<html>
<head>
    <title>Kairo Test Portal</title>
    <style>.hidden { display: none; }</style>
</head>
<body>
    <h1>Welcome to Kairo</h1>
    <h2>Section 1: Architecture</h2>
    <p>Kairo provides secure, controlled browser automation capabilities.</p>
    <div class="hidden">Secret internal text that should not appear</div>
    <script>const superSecretKey = "sk-12345";</script>

    <a href="https://example.com/docs">Documentation</a>
    <a href="javascript:alert(1)">Malicious Link</a>
    <a href="https://example.com/hidden" style="display: none;">Hidden Link</a>

    <button id="btn-search">Search Now</button>
    <button style="display: none;">Invisible Button</button>

    <form action="/login" method="post">
        <label for="username">Username</label>
        <input id="username" name="username" type="text" placeholder="Enter username" />
        <label for="password">Password</label>
        <input id="password" name="password" type="password" />
        <input type="hidden" name="csrf_token" value="csrf12345" />
    </form>
</body>
</html>
"""


@pytest.mark.asyncio
async def test_inspect_extracts_structured_content():
    """Verify BrowserInspectTool extracts headings, visible links, buttons, and safe form inputs."""
    settings = Settings(KAIRO_BROWSER_ENABLED=True, KAIRO_BROWSER_HEADLESS=True)
    manager = BrowserManager(settings=settings)
    try:
        session = await manager.get_or_create_session("inspect_test")
        await session.page.set_content(HTML_SAMPLE)

        tool = BrowserInspectTool(manager=manager)
        res = await tool.execute(session_id="inspect_test")

        assert res["success"] is True
        assert res["title"] == "Kairo Test Portal"
        assert "Welcome to Kairo" in res["headings"]
        assert "Section 1: Architecture" in res["headings"]

        # Visible text contains safe paragraphs
        assert "Kairo provides secure, controlled browser automation capabilities." in res["visible_text"]
        # Script content and hidden content are excluded from clean text
        assert "superSecretKey" not in res["visible_text"]

        # Check links (javascript: links and hidden links filtered out)
        link_hrefs = [item["href"] for item in res["links"]]
        assert "https://example.com/docs" in link_hrefs
        assert not any("javascript:" in href for href in link_hrefs)

        assert "https://example.com/hidden" not in link_hrefs

        # Buttons (hidden button excluded)
        assert "Search Now" in res["buttons"]
        assert "Invisible Button" not in res["buttons"]

        # Forms (password and hidden inputs excluded from inspect output)
        assert len(res["forms"]) == 1
        form_inputs = res["forms"][0]["inputs"]
        input_names = [i["name"] for i in form_inputs]
        assert "username" in input_names
        assert "password" not in input_names
        assert "csrf_token" not in input_names

        # Verification of no sensitive browser data in output schema
        assert "cookies" not in res
        assert "localStorage" not in res
        assert "sessionStorage" not in res
    finally:
        await manager.close_all()


@pytest.mark.asyncio
async def test_inspect_bounded_output():
    """Verify BrowserInspectTool honors character and element limits."""
    settings = Settings(
        KAIRO_BROWSER_ENABLED=True,
        KAIRO_BROWSER_HEADLESS=True,
        KAIRO_BROWSER_MAX_TEXT_CHARS=100,
        KAIRO_BROWSER_MAX_LINKS=2,
        KAIRO_BROWSER_MAX_ELEMENTS=2,
    )
    manager = BrowserManager(settings=settings)
    try:
        session = await manager.get_or_create_session("inspect_bounds")
        long_html = """
        <html><body>
            <p>""" + ("Word " * 200) + """</p>
            <a href="https://example.com/1">L1</a>
            <a href="https://example.com/2">L2</a>
            <a href="https://example.com/3">L3</a>
            <button>B1</button><button>B2</button><button>B3</button>
        </body></html>
        """
        await session.page.set_content(long_html)

        tool = BrowserInspectTool(manager=manager)
        res = await tool.execute(session_id="inspect_bounds")

        assert res["success"] is True
        assert len(res["links"]) <= 2
        assert len(res["buttons"]) <= 2
    finally:
        await manager.close_all()
