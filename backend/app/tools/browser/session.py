"""BrowserSession managing Playwright browser context, page lifecycle, and safe actions."""

import base64
import logging
from datetime import UTC, datetime
from typing import Any

from playwright.async_api import Browser, BrowserContext, Page, Playwright

from app.tools.browser.policies import DownloadPolicy, SensitiveFieldPolicy, SubmissionPolicy
from app.tools.browser.safety import BrowserSafetyValidator
from app.tools.browser.schemas import PageInspectionResult
from app.tools.web.citations import CitationManager
from app.tools.web.extraction import extract_content_from_html

logger = logging.getLogger("kairo.tools.browser.session")


class BrowserSession:
    """Isolated browser session binding Playwright context, page, and security policies."""

    def __init__(
        self,
        session_id: str,
        playwright: Playwright,
        browser: Browser,
        context: BrowserContext,
        page: Page,
    ) -> None:
        self.session_id = session_id
        self.playwright = playwright
        self.browser = browser
        self.context = context
        self.page = page
        self.created_at = datetime.now(UTC)
        self.last_used_at = datetime.now(UTC)
        self.status = "active"
        self.downloaded_files: list[str] = []

        # Hook download events to enforce download policy
        self.page.on("download", self._handle_download)

    async def _handle_download(self, download: Any) -> None:
        """Handle and cancel automated downloads to protect filesystem."""
        suggested_filename = getattr(download, "suggested_filename", "unnamed")
        logger.warning(
            "Browser session '%s' triggered download for '%s'. Applying download policy.",
            self.session_id,
            suggested_filename,
        )
        allowed, reason = DownloadPolicy.evaluate_download(suggested_filename)
        if not allowed:
            try:
                await download.cancel()
                logger.info("Download of '%s' cancelled: %s", suggested_filename, reason)
            except Exception as exc:
                logger.debug("Failed to cancel download: %s", exc)

    def touch(self) -> None:
        """Update last used timestamp."""
        self.last_used_at = datetime.now(UTC)

    def is_expired(self, timeout_seconds: int = 900) -> bool:
        """Check whether the session has been idle longer than timeout_seconds."""
        elapsed = (datetime.now(UTC) - self.last_used_at).total_seconds()
        return elapsed > timeout_seconds

    async def navigate(self, url: str, timeout_ms: int = 15000) -> dict[str, Any]:
        """Navigate to a URL with SSRF protection and redirect destination validation."""
        self.touch()

        # 1. Validate target URL before navigation
        validated_url = BrowserSafetyValidator.validate_url(url)

        try:
            resp = await self.page.goto(
                validated_url,
                timeout=timeout_ms,
                wait_until="domcontentloaded",
            )
        except Exception as exc:
            logger.warning("Navigation to '%s' failed: %s", validated_url, exc)
            return {
                "success": False,
                "url": validated_url,
                "error": f"Failed to navigate: {type(exc).__name__}: {exc}",
            }

        # 2. Re-validate final URL after potential HTTP / JS redirects!
        current_url = self.page.url
        try:
            BrowserSafetyValidator.validate_url(current_url)
        except Exception as exc:
            logger.warning("Redirected URL '%s' blocked by safety policy: %s", current_url, exc)
            # Immediately close or navigate away from unsafe URL
            await self.page.goto("about:blank")
            return {
                "success": False,
                "url": current_url,
                "error": f"Navigation redirected to prohibited address: {exc}",
            }

        title = await self.page.title()
        status_code = resp.status if resp else 200

        return {
            "success": True,
            "url": current_url,
            "title": title,
            "status_code": status_code,
        }

    async def inspect(
        self,
        max_text_chars: int = 20000,
        max_links: int = 100,
        max_elements: int = 200,
    ) -> PageInspectionResult:
        """Extract structured visible text, headings, links, and buttons without exposing secrets."""
        self.touch()

        current_url = self.page.url
        title = await self.page.title()

        # 1. Extract clean visible text via HTMLTextExtractor to strip scripts/styles
        raw_html = await self.page.content()
        _, clean_text = extract_content_from_html(raw_html, max_chars=max_text_chars)

        # Wrap in untrusted boundary tags for prompt injection protection
        domain = current_url.split("/")[2] if "/" in current_url else "unknown"
        wrapped_text = CitationManager.wrap_untrusted_content(
            source_id=1,
            url=current_url,
            title=title,
            domain=domain,
            content=clean_text,
        )

        # 2. Extract Headings safely
        headings: list[str] = []
        try:
            heading_locators = await self.page.locator("h1, h2, h3, h4").all()
            for h in heading_locators[:30]:
                text = (await h.inner_text()).strip()
                if text and text not in headings:
                    headings.append(text)
        except Exception as exc:
            logger.debug("Error extracting headings: %s", exc)

        # 3. Extract visible Links
        links: list[dict[str, str]] = []
        try:
            link_locators = await self.page.locator("a[href]").all()
            for a in link_locators[:max_links]:
                is_visible = await a.is_visible()
                if not is_visible:
                    continue
                href = (await a.get_attribute("href") or "").strip()
                text = (await a.inner_text()).strip()
                if href and not href.startswith(("javascript:", "data:")):
                    links.append({"text": text[:80] or "link", "href": href})
        except Exception as exc:
            logger.debug("Error extracting links: %s", exc)

        # 4. Extract visible Buttons
        buttons: list[str] = []
        try:
            btn_locators = await self.page.locator("button, input[type='button'], input[type='submit']").all()
            for b in btn_locators[:max_elements]:
                is_visible = await b.is_visible()
                if not is_visible:
                    continue
                btn_text = (await b.inner_text() or await b.get_attribute("value") or "").strip()
                if btn_text and btn_text not in buttons:
                    buttons.append(btn_text[:50])
        except Exception as exc:
            logger.debug("Error extracting buttons: %s", exc)

        # 5. Extract Form inputs (excluding passwords & secrets)
        forms: list[dict[str, Any]] = []
        try:
            form_locators = await self.page.locator("form").all()
            for f in form_locators[:10]:
                inputs: list[dict[str, str]] = []
                input_elems = await f.locator(
                    "input:not([type='password']):not([type='hidden']), select, textarea"
                ).all()
                for inp in input_elems[:20]:
                    name = await inp.get_attribute("name") or await inp.get_attribute("id") or ""
                    placeholder = await inp.get_attribute("placeholder") or ""
                    input_type = await inp.get_attribute("type") or "text"
                    inputs.append({"name": name, "type": input_type, "placeholder": placeholder})
                if inputs:
                    action = await f.get_attribute("action") or ""
                    forms.append({"action": action, "inputs": inputs})
        except Exception as exc:
            logger.debug("Error extracting forms: %s", exc)

        total_elements = len(headings) + len(links) + len(buttons)

        return PageInspectionResult(
            url=current_url,
            title=title,
            visible_text=wrapped_text,
            headings=headings,
            links=links[:max_links],
            buttons=buttons[:max_elements],
            forms=forms,
            total_elements_found=total_elements,
        )

    def _get_safe_locator(
        self,
        selector: str | None = None,
        role: str | None = None,
        name: str | None = None,
        text: str | None = None,
    ):
        """Construct a safe Playwright locator from accessible properties or selector."""
        if role:
            if name:
                return self.page.get_by_role(role, name=name)
            return self.page.get_by_role(role)
        if text:
            return self.page.get_by_text(text, exact=False)
        if selector:
            # Enforce clean selector without javascript: or script injection
            clean_sel = selector.strip()
            if clean_sel.startswith(("javascript:", "eval(")):
                raise ValueError("Arbitrary JavaScript selectors are prohibited.")
            return self.page.locator(clean_sel)
        raise ValueError("Must specify at least one locator strategy: role, name, text, or selector.")

    async def click(
        self,
        selector: str | None = None,
        role: str | None = None,
        name: str | None = None,
        text: str | None = None,
        timeout_ms: int = 10000,
        approved: bool = False,
    ) -> dict[str, Any]:
        """Click an element safely with submission policy checks and timeout bounds."""
        self.touch()
        locator = self._get_safe_locator(selector=selector, role=role, name=name, text=text)

        # 1. Verify existence and visibility
        count = await locator.count()
        if count == 0:
            return {"success": False, "error": "Target element not found on page."}

        target = locator.first
        if not await target.is_visible():
            return {"success": False, "error": "Target element exists but is not visible/interactable."}

        # 2. Inspect element attributes for submission policy
        elem_text = (await target.inner_text() or "").strip()
        elem_type = (await target.get_attribute("type") or "").lower().strip()
        aria_label = (await target.get_attribute("aria-label") or "").strip()
        attrs = {"type": elem_type, "aria-label": aria_label}

        is_sub, sub_reason = SubmissionPolicy.is_submission_action(
            tag="", text=elem_text, element_attrs=attrs
        )

        if is_sub and not approved:
            logger.info("Submission action detected on '%s'. Approval required.", elem_text)
            return {
                "success": False,
                "approval_required": True,
                "error": f"Form submission or critical action detected ('{sub_reason}'). Explicit user approval required.",
                "action": "click",
            }

        # 3. Perform click
        try:
            await target.click(timeout=timeout_ms)
            try:
                await self.page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
            except Exception:
                pass
        except Exception as exc:
            return {"success": False, "error": f"Click failed: {type(exc).__name__}: {exc}"}

        # 4. Check resulting URL safety
        current_url = self.page.url
        if current_url and current_url != "about:blank":
            try:
                BrowserSafetyValidator.validate_url(current_url)
            except Exception as exc:
                await self.page.goto("about:blank")
                return {
                    "success": False,
                    "url": current_url,
                    "error": f"Click redirected to prohibited address: {exc}",
                }

        return {
            "success": True,
            "url": current_url,
            "title": await self.page.title(),
        }

    async def fill(
        self,
        field: str,
        value: str,
        timeout_ms: int = 10000,
        approved: bool = False,
    ) -> dict[str, Any]:
        """Fill an input field safely with sensitive credential rejection."""
        self.touch()

        # 1. Evaluate field identifier against sensitive field policy
        is_sens, sens_reason = SensitiveFieldPolicy.is_sensitive(field, value)
        if is_sens:
            logger.warning("Rejected sensitive field fill attempt for '%s': %s", field, sens_reason)
            return {
                "success": False,
                "approval_required": True,
                "error": f"Security policy blocked sensitive field entry: {sens_reason}",
            }

        # 2. Locate target input field
        target = None
        # Try placeholder
        loc = self.page.get_by_placeholder(field, exact=False)
        if await loc.count() > 0:
            target = loc.first
        else:
            # Try label
            loc = self.page.get_by_label(field, exact=False)
            if await loc.count() > 0:
                target = loc.first
            else:
                # Try selector or name
                loc = self.page.locator(f"input[name='{field}'], textarea[name='{field}'], #{field}, {field}")
                if await loc.count() > 0:
                    target = loc.first

        if target is None or not await target.is_visible():
            return {"success": False, "error": f"Target form field '{field}' not found or not visible."}

        # 3. Inspect target element attributes in DOM to verify not password or sensitive
        elem_type = (await target.get_attribute("type") or "text").lower().strip()
        autocomplete = (await target.get_attribute("autocomplete") or "").lower().strip()
        name_attr = (await target.get_attribute("name") or "").lower().strip()
        attrs = {"type": elem_type, "autocomplete": autocomplete, "name": name_attr}

        is_sens_dom, dom_reason = SensitiveFieldPolicy.is_sensitive(field, value, attrs)
        if is_sens_dom:
            return {
                "success": False,
                "approval_required": True,
                "error": f"Security policy blocked sensitive form field: {dom_reason}",
            }

        # 4. Fill field
        try:
            await target.fill(value, timeout=timeout_ms)
        except Exception as exc:
            return {"success": False, "error": f"Failed to fill field: {type(exc).__name__}: {exc}"}

        return {"success": True, "field": field, "value_length": len(value)}

    async def screenshot(self, full_page: bool = False) -> str:
        """Capture screenshot and return base64-encoded PNG string."""
        self.touch()
        png_bytes = await self.page.screenshot(full_page=full_page, type="png")
        return base64.b64encode(png_bytes).decode("ascii")

    async def close(self) -> None:
        """Close browser page, context, and mark session closed."""
        self.status = "closed"
        try:
            await self.context.close()
        except Exception:
            pass
