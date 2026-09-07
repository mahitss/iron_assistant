"""Tests for /api/v1/chat and /api/v1/chat/stream endpoints with model routing and mocked providers."""

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
from app.models.registry import ModelCapability, ModelDefinition, ModelRegistry
from app.models.router import ModelRouter


class MockSuccessProvider(ModelProvider):
    """Mock provider returning controlled responses and recording called model."""

    def __init__(self) -> None:
        self.last_model_used: Optional[str] = None

    async def generate_response(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        **kwargs,
    ) -> str:
        self.last_model_used = model
        return "Hello! How can I help?"

    async def stream_response(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        self.last_model_used = model
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


def create_test_agent(provider: ModelProvider) -> KairoAgent:
    """Helper to build a KairoAgent with a test router and registry."""
    registry = ModelRegistry()
    registry.register_model(
        ModelDefinition(
            id="openrouter/free",
            capabilities={ModelCapability.GENERAL, ModelCapability.FAST},
            priority=10,
        )
    )
    registry.register_model(
        ModelDefinition(
            id="qwen/qwen-2.5-coder-32b-instruct",
            capabilities={ModelCapability.CODING},
            priority=50,
        )
    )
    router = ModelRouter(registry=registry, default_model_id="openrouter/free")
    return KairoAgent(provider=provider, router=router, model="openrouter/free")


def test_chat_endpoint_success_default_general(client: TestClient) -> None:
    """Ensure POST /api/v1/chat returns 200 OK and defaults to general capability model."""
    provider = MockSuccessProvider()
    mock_agent = create_test_agent(provider)
    app.dependency_overrides[get_default_agent] = lambda: mock_agent

    try:
        response = client.post("/api/v1/chat", json={"message": "Hello Kairo"})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Hello! How can I help?"
        assert data["model"] == "openrouter/free"
        assert provider.last_model_used == "openrouter/free"
    finally:
        app.dependency_overrides.clear()


def test_chat_endpoint_with_explicit_capability(client: TestClient) -> None:
    """Ensure POST /api/v1/chat routes to appropriate model when capability is specified."""
    provider = MockSuccessProvider()
    mock_agent = create_test_agent(provider)
    app.dependency_overrides[get_default_agent] = lambda: mock_agent

    try:
        response = client.post(
            "/api/v1/chat",
            json={"message": "Fix this bug", "capability": "coding"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Hello! How can I help?"
        assert data["model"] == "qwen/qwen-2.5-coder-32b-instruct"
        assert provider.last_model_used == "qwen/qwen-2.5-coder-32b-instruct"
    finally:
        app.dependency_overrides.clear()


def test_chat_endpoint_unknown_capability(client: TestClient) -> None:
    """Ensure POST /api/v1/chat with invalid capability returns HTTP 400."""
    provider = MockSuccessProvider()
    mock_agent = create_test_agent(provider)
    app.dependency_overrides[get_default_agent] = lambda: mock_agent

    try:
        response = client.post(
            "/api/v1/chat",
            json={"message": "Hello", "capability": "nonexistent_cap"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Unknown capability" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_chat_endpoint_validation_error(client: TestClient) -> None:
    """Ensure POST /api/v1/chat with missing or empty message returns 422."""
    response = client.post("/api/v1/chat", json={})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    response_empty = client.post("/api/v1/chat", json={"message": ""})
    assert response_empty.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_chat_stream_endpoint_success_with_model_metadata(client: TestClient) -> None:
    """Ensure POST /api/v1/chat/stream returns initial model event followed by tokens and [DONE]."""
    provider = MockSuccessProvider()
    mock_agent = create_test_agent(provider)
    app.dependency_overrides[get_default_agent] = lambda: mock_agent

    try:
        response = client.post(
            "/api/v1/chat/stream",
            json={"message": "Write a python function", "capability": "coding"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert "text/event-stream" in response.headers["Content-Type"]

        lines = response.text.strip().split("\n\n")
        received_model = None
        tokens = []
        has_done = False

        for block in lines:
            if block.strip() == "data: [DONE]":
                has_done = True
                continue
            if block.startswith("data: "):
                payload = json.loads(block[len("data: ") :])
                if "model" in payload:
                    received_model = payload["model"]
                elif "content" in payload:
                    tokens.append(payload["content"])

        assert received_model == "qwen/qwen-2.5-coder-32b-instruct"
        assert "".join(tokens) == "Hello! How can I help?"
        assert has_done is True
    finally:
        app.dependency_overrides.clear()


def test_chat_stream_endpoint_unknown_capability(client: TestClient) -> None:
    """Ensure POST /api/v1/chat/stream with invalid capability returns HTTP 400."""
    provider = MockSuccessProvider()
    mock_agent = create_test_agent(provider)
    app.dependency_overrides[get_default_agent] = lambda: mock_agent

    try:
        response = client.post(
            "/api/v1/chat/stream",
            json={"message": "Hello", "capability": "teleportation"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    finally:
        app.dependency_overrides.clear()


def test_chat_endpoint_authentication_error(client: TestClient) -> None:
    """Ensure POST /api/v1/chat returns 401 on authentication failure."""
    provider = MockAuthFailProvider()
    mock_agent = create_test_agent(provider)
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
    provider = MockUpstreamFailProvider()
    mock_agent = create_test_agent(provider)
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
    provider = MockAuthFailProvider()
    mock_agent = create_test_agent(provider)
    app.dependency_overrides[get_default_agent] = lambda: mock_agent

    try:
        response = client.post("/api/v1/chat/stream", json={"message": "Hello"})
        assert response.status_code == status.HTTP_200_OK
        assert "authentication failed" in response.text.lower()
        assert "data: [DONE]" in response.text
    finally:
        app.dependency_overrides.clear()
