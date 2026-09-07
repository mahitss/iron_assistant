"""Tests for /api/v1/chat and /api/v1/chat/stream endpoints with model routing, tools, and mocked providers."""

import json
from typing import Any, AsyncIterator, Dict, List, Optional
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
    ProviderResponse,
)
from app.models.registry import ModelCapability, ModelDefinition, ModelRegistry
from app.models.router import ModelRouter
from app.tools.builtin.calculator import CalculatorTool
from app.tools.executor import ToolExecutor
from app.tools.registry import ToolRegistry
from app.tools.schemas import ToolCall


class MockSuccessProvider(ModelProvider):
    """Mock provider returning controlled responses and recording called model."""

    def __init__(self) -> None:
        self.last_model_used: Optional[str] = None

    async def generate_response(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> ProviderResponse:
        self.last_model_used = model
        return ProviderResponse(content="Hello! How can I help?", model=model)

    async def stream_response(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
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
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> ProviderResponse:
        raise AuthenticationError("OpenRouter authentication failed: invalid or unauthorized API key")

    async def stream_response(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
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
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> ProviderResponse:
        raise ProviderAPIError("OpenRouter upstream overloaded", status_code=502)

    async def stream_response(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        raise ProviderAPIError("OpenRouter upstream overloaded", status_code=502)
        yield ""  # pragma: no cover


class ScriptedToolCallingProvider(ModelProvider):
    """Mock provider simulating assistant tool request followed by final response."""

    def __init__(self, responses: List[ProviderResponse]):
        self.responses = list(responses)
        self.step = 0

    async def generate_response(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> ProviderResponse:
        if self.step < len(self.responses):
            r = self.responses[self.step]
            self.step += 1
            return r
        return ProviderResponse(content="Final answer", model=model)

    async def stream_response(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        yield "Final answer"


def create_test_agent(provider: ModelProvider, with_tools: bool = False) -> KairoAgent:
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

    tool_reg = None
    tool_exec = None
    if with_tools:
        tool_reg = ToolRegistry()
        tool_reg.register(CalculatorTool())
        tool_exec = ToolExecutor(registry=tool_reg)

    return KairoAgent(
        provider=provider,
        router=router,
        tool_registry=tool_reg,
        tool_executor=tool_exec,
        model="openrouter/free",
    )


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
        assert data["tools_used"] is None
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


def test_chat_endpoint_with_tool_execution(client: TestClient) -> None:
    """Ensure POST /api/v1/chat returns executed tool metadata in response."""
    provider = ScriptedToolCallingProvider(
        responses=[
            ProviderResponse(
                tool_calls=[ToolCall(id="c1", name="calculator", arguments={"expression": "50 * 2"})]
            ),
            ProviderResponse(content="50 * 2 is 100."),
        ]
    )
    mock_agent = create_test_agent(provider, with_tools=True)
    app.dependency_overrides[get_default_agent] = lambda: mock_agent

    try:
        response = client.post("/api/v1/chat", json={"message": "Calculate 50 * 2"})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "50 * 2 is 100."
        assert data["tools_used"] is not None
        assert len(data["tools_used"]) == 1
        assert data["tools_used"][0]["tool"] == "calculator"
        assert data["tools_used"][0]["status"] == "success"
        assert data["tools_used"][0]["verification_status"] == "verified"
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
            "/api/v1/chat",
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
