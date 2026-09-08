"""Browser URL safety and SSRF validation layer."""

import logging

from app.tools.web.safety import SSRFViolationError, UnsafeURLError, URLSafetyValidator

logger = logging.getLogger("kairo.tools.browser.safety")


class BrowserSafetyValidator:
    """Enforces network safety and SSRF protection for browser navigation."""

    @classmethod
    def validate_url(cls, url: str) -> str:
        """Validate target URL against SSRF, private networks, and invalid schemes.

        Reuses Kairo's centralized URLSafetyValidator.
        """
        try:
            return URLSafetyValidator.validate_url(url)
        except (SSRFViolationError, UnsafeURLError) as exc:
            logger.warning("Browser navigation SSRF violation blocked for '%s': %s", url, exc)
            raise


__all__ = [
    "BrowserSafetyValidator",
    "SSRFViolationError",
    "UnsafeURLError",
]
