"""SSRF Protection and URL Safety Validation Layer for Kairo Web Research."""

import ipaddress
import logging
import socket
from urllib.parse import urlparse

logger = logging.getLogger("kairo.tools.web.safety")

# Known cloud metadata hostnames and addresses that must never be accessed
DISALLOWED_METADATA_HOSTS = {
    "metadata.google.internal",
    "instance-data",
    "169.254.169.254",
    "fd00:ec2::254",  # AWS IPv6 IMDS
}


class SSRFViolationError(ValueError):
    """Raised when a URL targets a private, internal, loopback, or metadata destination."""

    def __init__(self, message: str, url: str, ip: str | None = None) -> None:
        super().__init__(message)
        self.url = url
        self.ip = ip


class UnsafeURLError(ValueError):
    """Raised when a URL scheme, format, or resolution is invalid or prohibited."""

    def __init__(self, message: str, url: str) -> None:
        super().__init__(message)
        self.url = url


class URLSafetyValidator:
    """Validates URLs against SSRF, private network access, and protocol violations."""

    ALLOWED_SCHEMES = frozenset({"http", "https"})

    @classmethod
    def validate_url(cls, url: str) -> str:
        """Validate that a URL is safe to fetch over the public internet.

        Performs:
        1. Scheme validation (only http/https)
        2. Hostname extraction and syntax check
        3. Exclusion of credentials in URL
        4. DNS resolution of host
        5. IP range verification (rejecting private, loopback, link-local, multicast, reserved)
        6. Metadata endpoint verification

        Returns normalized URL if safe, raises SSRFViolationError or UnsafeURLError otherwise.
        """
        if not url or not isinstance(url, str):
            raise UnsafeURLError("URL must be a non-empty string.", url=str(url))

        url = url.strip()

        try:
            parsed = urlparse(url)
        except Exception as exc:
            raise UnsafeURLError(f"Malformed URL: {exc}", url=url) from exc

        # 1. Scheme check
        scheme = (parsed.scheme or "").lower()
        if scheme not in cls.ALLOWED_SCHEMES:
            raise UnsafeURLError(
                f"Prohibited URL scheme '{scheme}'. Only HTTP and HTTPS are permitted.",
                url=url,
            )

        # 2. Hostname check
        hostname = (parsed.hostname or "").strip().lower()
        if not hostname:
            raise UnsafeURLError("URL must contain a valid hostname.", url=url)

        # Prohibit embedded credentials (user:pass@host)
        if parsed.username or parsed.password:
            raise UnsafeURLError("URLs containing user authentication credentials are prohibited.", url=url)

        # 3. Known cloud metadata hostname check
        if hostname in DISALLOWED_METADATA_HOSTS:
            logger.warning("SSRF blocked: Attempt to access cloud metadata hostname '%s'", hostname)
            raise SSRFViolationError(
                f"Access to cloud metadata service '{hostname}' is strictly prohibited.",
                url=url,
                ip=hostname,
            )

        # 4. Direct IP address or DNS resolution
        port = parsed.port or (443 if scheme == "https" else 80)
        resolved_ips = cls._resolve_host(hostname, port, url)

        # 5. Inspect every resolved IP address
        for ip_str in resolved_ips:
            try:
                ip_obj = ipaddress.ip_address(ip_str)
            except ValueError as exc:
                raise UnsafeURLError(
                    f"Resolved invalid IP address '{ip_str}' for host '{hostname}'", url=url
                ) from exc

            cls._verify_ip_safety(ip_obj, url=url, hostname=hostname)

        return url

    @classmethod
    def _resolve_host(cls, hostname: str, port: int, url: str) -> list[str]:
        """Resolve hostname to a list of IP addresses via socket.getaddrinfo."""
        # If hostname is already an IP literal
        try:
            ipaddress.ip_address(hostname)
            return [hostname]
        except ValueError:
            pass

        try:
            # Resolve both IPv4 and IPv6
            addr_info = socket.getaddrinfo(
                hostname,
                port,
                family=socket.AF_UNSPEC,
                type=socket.SOCK_STREAM,
                proto=socket.IPPROTO_TCP,
            )
        except (socket.gaierror, OSError) as exc:
            raise UnsafeURLError(
                f"DNS resolution failed for host '{hostname}': {exc}",
                url=url,
            ) from exc
        except Exception as exc:
            raise UnsafeURLError(
                f"Unexpected error resolving host '{hostname}': {exc}",
                url=url,
            ) from exc

        resolved = []
        for family, _, _, _, sockaddr in addr_info:
            ip_str = sockaddr[0]
            if ip_str not in resolved:
                resolved.append(ip_str)

        if not resolved:
            raise UnsafeURLError(f"No IP addresses resolved for host '{hostname}'", url=url)

        return resolved

    @classmethod
    def _verify_ip_safety(
        cls,
        ip: ipaddress.IPv4Address | ipaddress.IPv6Address,
        url: str,
        hostname: str,
    ) -> None:
        """Enforce strict IP network classification boundaries."""
        ip_str = str(ip)

        # Loopback: 127.0.0.0/8, ::1
        if ip.is_loopback:
            logger.warning("SSRF blocked: Host '%s' resolved to loopback IP %s", hostname, ip_str)
            raise SSRFViolationError(
                f"Access to loopback address '{ip_str}' is prohibited.",
                url=url,
                ip=ip_str,
            )

        # Link-local: 169.254.0.0/16, fe80::/10 (AWS/GCP/Azure IMDS)
        if ip.is_link_local:
            logger.warning("SSRF blocked: Host '%s' resolved to link-local IP %s", hostname, ip_str)
            raise SSRFViolationError(
                f"Access to link-local address '{ip_str}' is prohibited.",
                url=url,
                ip=ip_str,
            )

        # Private: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, fc00::/7
        if ip.is_private:
            logger.warning("SSRF blocked: Host '%s' resolved to private IP %s", hostname, ip_str)
            raise SSRFViolationError(
                f"Access to private internal network IP '{ip_str}' is prohibited.",
                url=url,
                ip=ip_str,
            )

        # Multicast: 224.0.0.0/4, ff00::/8
        if ip.is_multicast:
            raise SSRFViolationError(
                f"Access to multicast address '{ip_str}' is prohibited.",
                url=url,
                ip=ip_str,
            )

        # Reserved / Unspecified (0.0.0.0, ::)
        if ip.is_reserved or ip.is_unspecified:
            raise SSRFViolationError(
                f"Access to reserved or unspecified address '{ip_str}' is prohibited.",
                url=url,
                ip=ip_str,
            )
