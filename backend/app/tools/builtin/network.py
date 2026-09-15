"""Native network execution and connection fabric tools executing within Kairo's secure Rust substrate."""

import ipaddress
import socket
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.tools.base import (
    BaseTool,
    ToolExecutionClass,
    ToolExecutionPreference,
)
from app.tools.permissions import PermissionLevel


# =============================================================================
# 1. Native DNS Resolve Tool
# =============================================================================

class NativeDnsResolveArgs(BaseModel):
    """Input arguments for DNS resolution."""
    hostname: str = Field(..., description="Hostname or FQDN to resolve (e.g. 'api.github.com')")
    timeout_ms: int = Field(default=5000, ge=100, le=30000, description="Resolution timeout in milliseconds")


class NativeDnsResolveOutput(BaseModel):
    """Structured output for DNS resolution."""
    hostname: str = Field(..., description="Resolved hostname")
    canonical_name: Optional[str] = Field(default=None, description="Canonical name (CNAME) if available")
    addresses: List[str] = Field(default_factory=list, description="List of validated, non-SSRF IP addresses")
    resolved_ips: List[str] = Field(default_factory=list, description="List of validated, non-SSRF IP addresses")
    ttl_seconds: int = Field(default=60, description="Time to live in seconds")
    cached: bool = Field(default=False, description="Whether result was served from cache")
    error: Optional[str] = Field(default=None, description="Error message if resolution failed")


class NativeDnsResolveTool(BaseTool):
    """Resolve hostname to safe, pre-validated IP addresses using native Rust connection fabric with SSRF protection."""

    name = "native_dns_resolve"
    description = (
        "Resolve hostname to safe, pre-validated IP addresses using the native Rust connection fabric. "
        "Enforces strict SSRF defense, filtering out loopback, link-local, RFC 1918 private ranges, "
        "and cloud metadata endpoints (169.254.169.254) before connection."
    )
    version = "1.0.0"
    permission_level = PermissionLevel.READ
    execution_class = ToolExecutionClass.NATIVE_RUST
    preference = ToolExecutionPreference.NATIVE_PREFERRED
    capability_id = "native.net.resolve"
    sandbox_profile = "NETWORK_EGRESS"
    args_model = NativeDnsResolveArgs
    output_model = NativeDnsResolveOutput
    timeout_seconds = 10.0
    idempotent = True

    async def execute(self, hostname: str, timeout_ms: int = 5000, **kwargs: Any) -> Dict[str, Any]:
        """Safe Python fallback if native runtime is offline."""
        try:
            # Check for SSRF in fallback
            addr_info = socket.getaddrinfo(hostname, None)
            safe_ips = []
            for item in addr_info:
                ip_str = item[4][0]
                ip_obj = ipaddress.ip_address(ip_str)
                if (
                    ip_obj.is_loopback
                    or ip_obj.is_private
                    or ip_obj.is_link_local
                    or ip_obj.is_multicast
                    or ip_str in ("169.254.169.254", "0.0.0.0")
                ):
                    continue
                if ip_str not in safe_ips:
                    safe_ips.append(ip_str)

            if not safe_ips:
                return {
                    "hostname": hostname,
                    "addresses": [],
                    "ttl_seconds": 0,
                    "cached": False,
                    "error": f"Resolution blocked: hostname '{hostname}' resolves only to restricted/private IP addresses",
                }

            return {
                "hostname": hostname,
                "canonical_name": hostname,
                "addresses": safe_ips,
                "resolved_ips": safe_ips,
                "ttl_seconds": 60,
                "cached": False,
            }
        except Exception as exc:
            return {
                "hostname": hostname,
                "addresses": [],
                "resolved_ips": [],
                "ttl_seconds": 0,
                "cached": False,
                "error": f"DNS resolution failed: {exc}",
            }

    def verify(self, result: Any) -> bool:
        return isinstance(result, dict) and ("addresses" in result or "resolved_ips" in result or "error" in result)


# =============================================================================
# 2. Native HTTP Fetch Tool
# =============================================================================

class NativeHttpFetchArgs(BaseModel):
    """Input arguments for HTTP fetch."""
    url: str = Field(..., description="Target URL (HTTP or HTTPS)")
    method: str = Field(default="GET", description="HTTP method (GET, HEAD, OPTIONS)")
    headers: Optional[Dict[str, str]] = Field(default=None, description="Optional request headers")
    timeout_ms: int = Field(default=30000, ge=500, le=120000, description="Request timeout in milliseconds")


class NativeHttpFetchOutput(BaseModel):
    """Structured output for HTTP fetch."""
    status_code: int = Field(..., description="HTTP response status code")
    headers: Dict[str, str] = Field(default_factory=dict, description="Response headers")
    body: str = Field(default="", description="Response body content (truncated to limit)")
    bytes_received: int = Field(default=0, description="Total bytes received")
    truncated: bool = Field(default=False, description="Whether response body exceeded size limit and was truncated")
    content_type: Optional[str] = Field(default=None, description="Response Content-Type header value")
    remote_ip: Optional[str] = Field(default=None, description="Pre-validated remote IP address connected to")
    duration_ms: Optional[int] = Field(default=None, description="Total request duration in milliseconds")
    error: Optional[str] = Field(default=None, description="Error details if fetch failed")


class NativeHttpFetchTool(BaseTool):
    """Fetch remote resource via native connection fabric with SSRF protection, streaming byte limits, and typed circuit breaking."""

    name = "native_http_fetch"
    description = (
        "Fetch remote web resources using the native Rust connection fabric. "
        "Enforces pre-validated DNS socket binding (anti-DNS rebinding), SSRF prevention, "
        "streaming body truncation (10 MB default), connection pooling, and circuit breaking."
    )
    version = "1.0.0"
    permission_level = PermissionLevel.READ
    execution_class = ToolExecutionClass.NATIVE_RUST
    preference = ToolExecutionPreference.NATIVE_PREFERRED
    capability_id = "native.net.fetch"
    sandbox_profile = "NETWORK_EGRESS"
    args_model = NativeHttpFetchArgs
    output_model = NativeHttpFetchOutput
    timeout_seconds = 35.0
    idempotent = True

    async def execute(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        timeout_ms: int = 30000,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Safe Python fallback if native runtime is offline."""
        import urllib.request
        import urllib.error
        from urllib.parse import urlparse

        parsed = urlparse(url)
        if parsed.scheme.lower() not in ("http", "https"):
            return {
                "status_code": 400,
                "error": f"Protocol scheme '{parsed.scheme}' not supported; only HTTP/HTTPS are allowed",
            }

        # Validate host SSRF in fallback
        host = parsed.hostname or ""
        try:
            addr_info = socket.getaddrinfo(host, None)
            for item in addr_info:
                ip_str = item[4][0]
                ip_obj = ipaddress.ip_address(ip_str)
                if ip_obj.is_loopback or ip_obj.is_private or ip_obj.is_link_local:
                    return {
                        "status_code": 403,
                        "error": f"SSRF blocked: target host '{host}' resolves to restricted IP '{ip_str}'",
                    }
        except Exception as exc:
            return {"status_code": 502, "error": f"DNS resolution failed: {exc}"}

        try:
            req = urllib.request.Request(url, headers=headers or {}, method=method.upper())
            with urllib.request.urlopen(req, timeout=timeout_ms / 1000.0) as resp:
                resp_headers = dict(resp.headers)
                raw_bytes = resp.read(10 * 1024 * 1024)
                body_text = raw_bytes.decode("utf-8", errors="replace")
                return {
                    "status_code": resp.status,
                    "headers": resp_headers,
                    "body": body_text,
                    "bytes_received": len(raw_bytes),
                    "truncated": False,
                    "content_type": resp_headers.get("Content-Type"),
                }
        except urllib.error.HTTPError as he:
            raw_bytes = he.read(1024 * 1024)
            return {
                "status_code": he.code,
                "headers": dict(he.headers),
                "body": raw_bytes.decode("utf-8", errors="replace"),
                "bytes_received": len(raw_bytes),
                "truncated": False,
                "content_type": dict(he.headers).get("Content-Type"),
                "error": str(he),
            }
        except Exception as exc:
            return {
                "status_code": 500,
                "headers": {},
                "body": "",
                "bytes_received": 0,
                "truncated": False,
                "error": f"Fetch request failed: {exc}",
            }

    def verify(self, result: Any) -> bool:
        return isinstance(result, dict) and ("status_code" in result or "error" in result)


# =============================================================================
# 3. Native HTTP Request Tool
# =============================================================================

class NativeHttpRequestArgs(BaseModel):
    """Input arguments for full HTTP request execution."""
    url: str = Field(..., description="Target URL (HTTP or HTTPS)")
    method: str = Field(default="GET", description="HTTP method (GET, POST, PUT, DELETE, PATCH, etc.)")
    headers: Optional[Dict[str, str]] = Field(default=None, description="Request headers")
    body: Optional[str] = Field(default=None, description="Request body payload")
    timeout_ms: int = Field(default=30000, ge=500, le=120000, description="Request timeout in milliseconds")
    idempotency_key: Optional[str] = Field(default=None, description="Idempotency key for safe automatic retries")


class NativeHttpRequestOutput(BaseModel):
    """Structured output for full HTTP request execution."""
    status_code: int = Field(..., description="HTTP response status code")
    headers: Dict[str, str] = Field(default_factory=dict, description="Response headers")
    body: str = Field(default="", description="Response body content")
    bytes_received: int = Field(default=0, description="Total bytes received")
    bytes_sent: int = Field(default=0, description="Total bytes transmitted")
    truncated: bool = Field(default=False, description="Whether response body exceeded size limit and was truncated")
    content_type: Optional[str] = Field(default=None, description="Response Content-Type header value")
    remote_ip: Optional[str] = Field(default=None, description="Pre-validated remote IP address connected to")
    duration_ms: Optional[int] = Field(default=None, description="Total request duration in milliseconds")
    retries_attempted: int = Field(default=0, description="Number of retries attempted")
    error: Optional[str] = Field(default=None, description="Error details if request failed")


class NativeHttpRequestTool(BaseTool):
    """Execute full HTTP request descriptor via native connection fabric with governance approval and SSRF defense."""

    name = "native_http_request"
    description = (
        "Execute full HTTP request descriptors (GET, POST, PUT, DELETE, PATCH) via the native Rust connection fabric. "
        "Enforces pre-validated DNS socket binding, SSRF protection, strict payload limits, "
        "and Kairo governance approval for external mutation."
    )
    version = "1.0.0"
    permission_level = PermissionLevel.EXTERNAL
    execution_class = ToolExecutionClass.NATIVE_RUST
    preference = ToolExecutionPreference.NATIVE_PREFERRED
    capability_id = "native.net.request"
    sandbox_profile = "NETWORK_EGRESS"
    args_model = NativeHttpRequestArgs
    output_model = NativeHttpRequestOutput
    timeout_seconds = 35.0
    idempotent = False

    async def execute(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        body: Optional[str] = None,
        timeout_ms: int = 30000,
        idempotency_key: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Safe Python fallback if native runtime is offline."""
        import urllib.request
        import urllib.error
        from urllib.parse import urlparse

        parsed = urlparse(url)
        if parsed.scheme.lower() not in ("http", "https"):
            return {
                "status_code": 400,
                "error": f"Protocol scheme '{parsed.scheme}' not supported; only HTTP/HTTPS are allowed",
            }

        host = parsed.hostname or ""
        try:
            addr_info = socket.getaddrinfo(host, None)
            for item in addr_info:
                ip_str = item[4][0]
                ip_obj = ipaddress.ip_address(ip_str)
                if ip_obj.is_loopback or ip_obj.is_private or ip_obj.is_link_local:
                    return {
                        "status_code": 403,
                        "error": f"SSRF blocked: target host '{host}' resolves to restricted IP '{ip_str}'",
                    }
        except Exception as exc:
            return {"status_code": 502, "error": f"DNS resolution failed: {exc}"}

        try:
            data_bytes = body.encode("utf-8") if body is not None else None
            req = urllib.request.Request(url, data=data_bytes, headers=headers or {}, method=method.upper())
            with urllib.request.urlopen(req, timeout=timeout_ms / 1000.0) as resp:
                resp_headers = dict(resp.headers)
                raw_bytes = resp.read(10 * 1024 * 1024)
                body_text = raw_bytes.decode("utf-8", errors="replace")
                return {
                    "status_code": resp.status,
                    "headers": resp_headers,
                    "body": body_text,
                    "bytes_received": len(raw_bytes),
                    "bytes_sent": len(data_bytes) if data_bytes else 0,
                    "truncated": False,
                    "content_type": resp_headers.get("Content-Type"),
                    "retries_attempted": 0,
                }
        except urllib.error.HTTPError as he:
            raw_bytes = he.read(1024 * 1024)
            return {
                "status_code": he.code,
                "headers": dict(he.headers),
                "body": raw_bytes.decode("utf-8", errors="replace"),
                "bytes_received": len(raw_bytes),
                "bytes_sent": len(body.encode("utf-8")) if body else 0,
                "truncated": False,
                "content_type": dict(he.headers).get("Content-Type"),
                "retries_attempted": 0,
                "error": str(he),
            }
        except Exception as exc:
            return {
                "status_code": 500,
                "headers": {},
                "body": "",
                "bytes_received": 0,
                "bytes_sent": len(body.encode("utf-8")) if body else 0,
                "truncated": False,
                "retries_attempted": 0,
                "error": f"HTTP request failed: {exc}",
            }

    def verify(self, result: Any) -> bool:
        return isinstance(result, dict) and ("status_code" in result or "error" in result)
