"""Tests for SSRF Protection and URL Safety Validation Layer."""

from unittest.mock import patch

import pytest

from app.tools.web.safety import (
    SSRFViolationError,
    UnsafeURLError,
    URLSafetyValidator,
)


def test_valid_public_https_url():
    """Valid public HTTPS and HTTP URLs pass validation."""
    with patch("socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [
            (2, 1, 6, "", ("93.184.216.34", 443)),  # example.com public IP
        ]
        assert (
            URLSafetyValidator.validate_url("https://example.com/docs")
            == "https://example.com/docs"
        )
        assert (
            URLSafetyValidator.validate_url("http://example.com:8080/path?q=1")
            == "http://example.com:8080/path?q=1"
        )


def test_invalid_schemes_rejected():
    """Non-HTTP(S) schemes must be rejected."""
    prohibited_urls = [
        "ftp://ftp.example.com/files",
        "file:///etc/passwd",
        "file://c:/windows/win.ini",
        "gopher://gopher.example.com",
        "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==",
        "javascript:alert(1)",
        "ws://example.com/socket",
        "ssh://git@github.com",
    ]
    for bad_url in prohibited_urls:
        with pytest.raises(UnsafeURLError) as exc_info:
            URLSafetyValidator.validate_url(bad_url)
        assert "Only HTTP and HTTPS are permitted" in str(exc_info.value) or "scheme" in str(
            exc_info.value
        ).lower()


def test_localhost_and_loopback_blocked():
    """Loopback addresses and localhost must be strictly blocked by SSRF check."""
    loopback_targets = [
        "http://localhost:8000/api",
        "http://127.0.0.1:5432",
        "http://127.0.0.2:80",
        "http://[::1]:8080",
    ]
    for target in loopback_targets:
        with pytest.raises(SSRFViolationError) as exc_info:
            URLSafetyValidator.validate_url(target)
        assert "loopback" in str(exc_info.value).lower() or "prohibited" in str(
            exc_info.value
        ).lower()


def test_private_ipv4_blocked():
    """RFC 1918 private IPv4 ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16) must be blocked."""
    private_targets = [
        "http://10.0.0.1/admin",
        "http://10.255.255.255/status",
        "http://172.16.0.5:8000",
        "http://172.31.255.254/secret",
        "http://192.168.1.1/router",
        "http://192.168.0.100/debug",
    ]
    for target in private_targets:
        with pytest.raises(SSRFViolationError) as exc_info:
            URLSafetyValidator.validate_url(target)
        assert "private" in str(exc_info.value).lower()


def test_cloud_metadata_blocked():
    """Link-local cloud instance metadata services (169.254.169.254, metadata.google.internal) must be blocked."""
    metadata_targets = [
        "http://169.254.169.254/latest/meta-data/",
        "http://169.254.169.254/computeMetadata/v1/",
        "http://metadata.google.internal/computeMetadata/v1/",
        "http://instance-data/latest/meta-data/",
    ]
    for target in metadata_targets:
        with pytest.raises(SSRFViolationError) as exc_info:
            URLSafetyValidator.validate_url(target)
        assert "metadata" in str(exc_info.value).lower() or "link-local" in str(
            exc_info.value
        ).lower()


def test_link_local_ipv6_blocked():
    """IPv6 link-local addresses (fe80::) must be blocked."""
    target = "http://[fe80::1ff:fe23:4567:890a]/"
    with pytest.raises(SSRFViolationError) as exc_info:
        URLSafetyValidator.validate_url(target)
    assert "link-local" in str(exc_info.value).lower()


def test_dns_resolves_to_private_ip():
    """A public-looking hostname that resolves via DNS to a private IP must be blocked."""
    with patch("socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [
            (2, 1, 6, "", ("192.168.1.50", 443)),  # DNS rebinding / internal host
        ]
        with pytest.raises(SSRFViolationError) as exc_info:
            URLSafetyValidator.validate_url("https://internal.mycompany.corp/dashboard")
        assert "private" in str(exc_info.value).lower()


def test_credentials_in_url_rejected():
    """URLs embedding username/password credentials must be rejected."""
    with pytest.raises(UnsafeURLError) as exc_info:
        URLSafetyValidator.validate_url("https://admin:secret123@example.com/data")
    assert "credentials are prohibited" in str(exc_info.value).lower()


def test_dns_resolution_failure():
    """Failure to resolve DNS for a hostname must raise UnsafeURLError."""
    with patch("socket.getaddrinfo", side_effect=OSError("getaddrinfo failed")):
        with pytest.raises(UnsafeURLError) as exc_info:
            URLSafetyValidator.validate_url("https://nonexistent-domain-xyz-987654321.org")
        assert "dns resolution failed" in str(exc_info.value).lower()
