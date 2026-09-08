"""Tests for OpenRouter provider implementation, streaming, and tool calls."""

import json

import httpx
import pytest

from app.models.openrouter import OpenRouterProvider
from app.models.provider import (
    AuthenticationError,
    ChatMessage,
    MessageRole,
    ProviderAPIError,
    ProviderResponse,
)


def test_provider_initialization() -> None:
    """Ensure OpenRouter provider initializes with expected defaults."""
    provider = OpenRouterProvider(
        api_key="test-key",
        default_model="openrouter/free",
        app_name="KairoTest",
    )
    assert provider.default_model == "openrouter/free"
    assert provider.app_name == "KairoTest"
    assert provider.base_url == "https://openrouter.ai/api/v1"


def test_missing_api_key_raises_authentication_error() -> None:
    """Ensure initializing or calling without API key raises AuthenticationError."""
    provider = OpenRouterProvider(api_key="")
    with pytest.raises(AuthenticationError) as exc_info:
        provider._ensure_authenticated()
    assert "OPENROUTER_API_KEY" in str(exc_info.value)


@pytest.mark.asyncio
async def test_generate_response_mocked() -> None:
    """Ensure generate_response correctly sends payload and parses choices."""
    expected_content = "Hello! I am Kairo, ready to assist."

    def mock_handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://openrouter.ai/api/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer test-key"
        body = json.loads(request.content.decode("utf-8"))
        assert body["model"] == "openrouter/free"
        assert len(body["messages"]) == 1

        mock_response = {
            "id": "gen-123",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": expected_content,
                    }
                }
            ],
        }
        return httpx.Response(200, json=mock_response)

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OpenRouterProvider(api_key="test-key", client=client)
        messages = [ChatMessage(role=MessageRole.USER, content="Hello")]
        result = await provider.generate_response(messages)
        assert result == expected_content
        assert isinstance(result, ProviderResponse)
        assert result.content == expected_content
        assert not result.has_tool_calls


@pytest.mark.asyncio
async def test_generate_response_with_tool_calls_mocked() -> None:
    """Ensure OpenRouter provider correctly parses tool_calls in completion responses."""
    def mock_handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        assert "tools" in body
        assert body["tool_choice"] == "auto"

        mock_response = {
            "id": "gen-tool-1",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_calc_1",
                                "type": "function",
                                "function": {
                                    "name": "calculator",
                                    "arguments": json.dumps({"expression": "40 + 2"}),
                                },
                            }
                        ],
                    }
                }
            ],
        }
        return httpx.Response(200, json=mock_response)

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OpenRouterProvider(api_key="test-key", client=client)
        messages = [ChatMessage(role=MessageRole.USER, content="Compute 40 + 2")]
        tools = [{"type": "function", "function": {"name": "calculator"}}]
        response: ProviderResponse = await provider.generate_response(messages, tools=tools)

        assert response.has_tool_calls is True
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].id == "call_calc_1"
        assert response.tool_calls[0].name == "calculator"
        assert response.tool_calls[0].arguments == {"expression": "40 + 2"}


@pytest.mark.asyncio
async def test_tool_result_continuation_mocked() -> None:
    """Ensure passing tool results back to OpenRouter correctly serializes tool messages."""
    def mock_handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        assert len(body["messages"]) == 3
        # Third message must be tool role
        assert body["messages"][2]["role"] == "tool"
        assert body["messages"][2]["tool_call_id"] == "call_calc_1"

        mock_response = {
            "id": "gen-final",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "40 + 2 is 42.",
                    }
                }
            ],
        }
        return httpx.Response(200, json=mock_response)

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OpenRouterProvider(api_key="test-key", client=client)
        messages = [
            ChatMessage(role=MessageRole.USER, content="Compute 40 + 2"),
            ChatMessage(role=MessageRole.ASSISTANT, content=None, tool_calls=[{"id": "call_calc_1"}]),
            ChatMessage(role=MessageRole.TOOL, content='{"status": "success", "result": 42}', tool_call_id="call_calc_1", name="calculator"),
        ]
        response = await provider.generate_response(messages)
        assert response.content == "40 + 2 is 42."


@pytest.mark.asyncio
async def test_stream_response_mocked() -> None:
    """Ensure stream_response parses SSE chunks and yields tokens."""
    sse_body = (
        'data: {"choices": [{"delta": {"content": "Hello"}}]}\n\n'
        'data: {"choices": [{"delta": {"content": " world"}}]}\n\n'
        'data: [DONE]\n\n'
    )

    def mock_handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://openrouter.ai/api/v1/chat/completions"
        return httpx.Response(
            200,
            text=sse_body,
            headers={"Content-Type": "text/event-stream"},
        )

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OpenRouterProvider(api_key="test-key", client=client)
        messages = [ChatMessage(role=MessageRole.USER, content="Hi")]

        chunks = []
        async for chunk in provider.stream_response(messages):
            chunks.append(chunk)

        assert chunks == ["Hello", " world"]


@pytest.mark.asyncio
async def test_upstream_auth_error_handling() -> None:
    """Ensure HTTP 401 from OpenRouter maps to AuthenticationError."""
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "Invalid API key"}})

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OpenRouterProvider(api_key="invalid-key", client=client)
        with pytest.raises(AuthenticationError):
            await provider.generate_response([ChatMessage(role=MessageRole.USER, content="Hi")])


@pytest.mark.asyncio
async def test_upstream_server_error_handling() -> None:
    """Ensure HTTP 500 from OpenRouter maps to ProviderAPIError."""
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": {"message": "Internal upstream error"}})

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OpenRouterProvider(api_key="test-key", client=client)
        with pytest.raises(ProviderAPIError) as exc_info:
            await provider.generate_response([ChatMessage(role=MessageRole.USER, content="Hi")])
        assert "Internal upstream error" in str(exc_info.value)
