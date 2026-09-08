"""Tests verifying Nginx reverse proxy production configuration rules."""

from pathlib import Path


def test_nginx_configuration_rules():
    """Validate deploy/nginx/nginx.conf adheres to production streaming and security rules."""
    nginx_path = Path(__file__).parent.parent.parent / "deploy" / "nginx" / "nginx.conf"
    assert nginx_path.exists(), f"nginx.conf not found at {nginx_path}"

    content = nginx_path.read_text(encoding="utf-8")

    # 1. Payload size limit
    assert "client_max_body_size 10M;" in content, "Must configure 10M body size limit"

    # 2. HTTP to HTTPS redirect
    assert "return 301 https://$host$request_uri;" in content, "Must redirect HTTP to HTTPS"

    # 3. Modern TLS protocols
    assert "TLSv1.2 TLSv1.3;" in content, "Must enforce TLS 1.2 and 1.3"

    # 4. OWASP defensive headers
    assert "Strict-Transport-Security" in content, "Must configure HSTS"
    assert 'X-Content-Type-Options "nosniff"' in content
    assert 'X-Frame-Options "DENY"' in content

    # 5. AI Streaming buffer bypass
    assert "proxy_buffering off;" in content, "Must disable proxy buffering for streaming endpoints"
    assert "/api/v1/chat/stream" in content, "Must specifically target streaming chat route"

    # 6. WebSocket upgrade headers
    assert "Upgrade $http_upgrade;" in content, "Must support WebSocket Upgrade"
    assert "Connection $connection_upgrade;" in content, "Must support Connection upgrade map"

    # 7. Extended timeout for streaming
    assert "proxy_read_timeout 300s;" in content, "Must extend read timeout for long LLM generations"
