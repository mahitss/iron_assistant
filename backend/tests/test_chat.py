"""Tests for /api/v1/chat and /api/v1/chat/stream endpoints with mocked providers."""

import json
from typing import AsyncIterator, List, Optional
from fastapi import status
from fastapi.testclient import TestClient
import pytest

from app.agents.core import KairoAgent, get_default_agent
from app.main import app
from app.models.provider import (
    AuthenticationError,
    ChatMessage,
    ModelProvider,
    ProviderAPIError,
)


class MockSuccessProvider(ModelProvider):
    """Mock provider returning controlled responses."""

    async def generate_response(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        **kwargs,
    ) -> str:
        return "Hello! How can I help?"

    async def stream_response(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        for token in ["Hello", "! ", "How", " can", " I", " help?"]:
            yield token


class MockAuthFailProvider(ModelProvider):
    """Mock provider simulating authentication failure."""

    async def generate_response(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        **kwargs,
    ) -> str:
        raise AuthenticationError("OpenRouter authentication failed: invalid or unauthorized API key")

    async def stream_response(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        raise AuthenticationError("OpenRouter authentication failed: invalid or unauthorized API key")
        yield ""  # pragma: no cover


class MockUpstreamFailProvider(ModelProvider):
    """Mock provider simulating upstream provider error."""

    async def generate_response(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        **kwargs,
    ) -> str:
        raise ProviderAPIError("OpenRouter upstream overloaded", status_code=502)

    async def stream_response(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        raise ProviderAPIError("OpenRouter upstream overloaded", status_code=502)
        yield ""  # pragma: no cover


def test_chat_endpoint_success(client: TestClient) -> None:
    """Ensure POST /api/v1/chat returns 200 OK and expected AI response."""
    mock_agent = KairoAgent(provider=MockSuccessProvider())
    app.dependency_overrides[get_default_agent] = lambda: mock_agent

    try:
        response = client.post("/api/v1/chat", json={"message": "Hello Kairo"})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Hello! How can I help?"
    finally:
        app.dependency_overrides.clear()


def test_chat_endpoint_validation_error(client: TestClient) -> None:
    """Ensure POST /api/v1/chat with missing or empty message returns 422."""
    response = client.post("/api/v1/chat", json={})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    response_empty = client.post("/api/v1/chat", json={"message": ""})
    assert response_empty.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_chat_stream_endpoint_success(client: TestClient) -> None:
    """Ensure POST /api/v1/chat/stream returns SSE stream with data chunks and [DONE]."""
    mock_agent = KairoAgent(provider=MockSuccessProvider())
    app.dependency_overrides[get_default_agent] = lambda: mock_agent

    try:
        response = client.post("/api/v1/chat/stream", json={"message": "Hello Kairo"})
        assert response.status_code == status.HTTP_200_OK
        assert "text/event-stream" in response.headers["Content-Type"]

        lines = response.text.strip().split("\n\n")
        tokens = []
        has_done = False

        for block in lines:
            if block.strip() == "data: [DONE]":
                has_done = True
                continue
            if block.startswith("data: "):
                payload = json.loads(block[len("data: ") :])
                if "content" in payload:
                    tokens.append(payload["content"])

        assert "".join(tokens) == "Hello! How can I help?"
        assert has_done is True
    finally:
        app.dependency_overrides.clear()


def test_chat_endpoint_authentication_error(client: TestClient) -> None:
    """Ensure POST /api/v1/chat returns 401 on authentication failure."""
    mock_agent = KairoAgent(provider=MockAuthFailProvider())
    app.dependency_overrides[get_default_agent] = lambda: mock_agent

    try:
        response = client.post("/api/v1/chat", json={"message": "Hello Kairo"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "authentication failed" in data["detail"].lower()
    finally:
        app.dependency_overrides.clear()


def test_chat_endpoint_upstream_error(client: TestClient) -> None:
    """Ensure POST /api/v1/chat returns 502 on upstream provider failure."""
    mock_agent = KairoAgent(provider=MockUpstreamFailProvider())
    app.dependency_overrides[get_default_agent] = lambda: mock_agent

    try:
        response = client.post("/api/v1/chat", json={"message": "Hello Kairo"})
        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        data = response.json()
        assert "overloaded" in data["detail"].lower()
    finally:
        app.dependency_overrides.clear()


def test_chat_stream_auth_error_event(client: TestClient) -> None:
    """Ensure POST /api/v1/chat/stream outputs error payload on auth failure."""
    mock_agent = KairoAgent(provider=MockAuthFailProvider())
    app.dependency_overrides[get_default_agent] = lambda: mock_agent

    try:
        response = client.post("/api/v1/chat/stream", json={"message": "Hello"})
        assert response.status_code == status.HTTP_200_OK
        assert "authentication failed" in response.text.lower()
        assert "data: [DONE]" in response.text
    finally:
        app.dependency_overrides.clear()
