"""OpenRouter model provider implementation supporting structured completions and tool calling."""

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.models.provider import (
    AuthenticationError,
    ChatMessage,
    ModelProvider,
    ProviderAPIError,
    ProviderResponse,
)
from app.tools.schemas import ToolCall


class OpenRouterProvider(ModelProvider):
    """OpenRouter OpenAI-compatible chat completion provider."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://openrouter.ai/api/v1",
        default_model: str = "openrouter/free",
        site_url: str | None = None,
        app_name: str | None = "Kairo",
        client: httpx.AsyncClient | None = None,
        timeout: float = 60.0,
    ):
        self._api_key = (api_key or "").strip()
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.site_url = site_url
        self.app_name = app_name
        self._client = client
        self.timeout = timeout

    def _ensure_authenticated(self) -> None:
        """Verify an API key is configured before making requests."""
        if not self._api_key:
            raise AuthenticationError(
                "OpenRouter API key is not configured. Please set the OPENROUTER_API_KEY environment variable."
            )

    def _get_headers(self) -> dict[str, str]:
        """Construct secure headers without exposing sensitive data in representations."""
        self._ensure_authenticated()
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        if self.site_url:
            headers["HTTP-Referer"] = self.site_url
        if self.app_name:
            headers["X-Title"] = self.app_name
        return headers

    def _get_client(self) -> httpx.AsyncClient:
        """Return the injected HTTP client or create a default instance."""
        if self._client is not None:
            return self._client
        return httpx.AsyncClient(timeout=self.timeout)

    async def generate_response(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs,
    ) -> ProviderResponse:
        """Generate a complete chat completion or tool calls from OpenRouter."""
        headers = self._get_headers()
        selected_model = model or self.default_model

        payload: dict[str, Any] = {
            "model": selected_model,
            "messages": [m.to_dict() for m in messages],
            "stream": False,
            **kwargs,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        endpoint = f"{self.base_url}/chat/completions"
        client = self._get_client()
        should_close = self._client is None

        try:
            response = await client.post(endpoint, json=payload, headers=headers)
            return self._handle_completion_response(response, selected_model)
        except httpx.HTTPStatusError as exc:
            self._handle_http_error(exc.response)
        except httpx.RequestError as exc:
            raise ProviderAPIError(f"Network error communicating with OpenRouter: {exc.__class__.__name__}")
        finally:
            if should_close:
                await client.aclose()

    def _handle_completion_response(self, response: httpx.Response, selected_model: str) -> ProviderResponse:
        """Parse non-streaming OpenRouter completion response including tool calls."""
        if response.status_code in (401, 403):
            raise AuthenticationError("OpenRouter authentication failed: invalid or unauthorized API key")
        elif response.status_code >= 400:
            self._handle_http_error(response)

        try:
            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                raise ProviderAPIError("OpenRouter returned an empty choices list")

            message_obj = choices[0].get("message", {})
            content = message_obj.get("content")
            raw_tool_calls = message_obj.get("tool_calls")

            parsed_tool_calls: list[ToolCall] | None = None
            if raw_tool_calls:
                parsed_tool_calls = []
                for tc in raw_tool_calls:
                    fn = tc.get("function", {})
                    fn_name = fn.get("name", "")
                    raw_args = fn.get("arguments", "{}")
                    if isinstance(raw_args, str):
                        try:
                            args_dict = json.loads(raw_args)
                        except Exception:
                            args_dict = {"raw": raw_args}
                    elif isinstance(raw_args, dict):
                        args_dict = raw_args
                    else:
                        args_dict = {}

                    parsed_tool_calls.append(
                        ToolCall(
                            id=tc.get("id", f"call_{len(parsed_tool_calls)}"),
                            name=fn_name,
                            arguments=args_dict,
                        )
                    )

            if content is None and not parsed_tool_calls:
                raise ProviderAPIError("OpenRouter returned neither content nor tool calls")

            return ProviderResponse(
                content=content,
                tool_calls=parsed_tool_calls,
                model=data.get("model", selected_model),
            )
        except (ValueError, KeyError) as exc:
            raise ProviderAPIError(f"Failed to parse OpenRouter response: {exc}")

    def _handle_http_error(self, response: httpx.Response) -> None:
        """Extract clean error messages from HTTP error responses without leaking keys."""
        if response.status_code in (401, 403):
            raise AuthenticationError("OpenRouter authentication failed: invalid or unauthorized API key")

        error_detail = "Unknown upstream error"
        try:
            err_data = response.json()
            if isinstance(err_data, dict):
                error_obj = err_data.get("error")
                if isinstance(error_obj, dict):
                    error_detail = error_obj.get("message", error_detail)
                elif isinstance(error_obj, str):
                    error_detail = error_obj
        except Exception:
            error_detail = response.text[:200]

        raise ProviderAPIError(
            f"OpenRouter API error (status {response.status_code}): {error_detail}",
            status_code=response.status_code,
        )

    async def stream_response(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream chat completion tokens from OpenRouter using SSE."""
        headers = self._get_headers()
        selected_model = model or self.default_model

        payload: dict[str, Any] = {
            "model": selected_model,
            "messages": [m.to_dict() for m in messages],
            "stream": True,
            **kwargs,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        endpoint = f"{self.base_url}/chat/completions"
        client = self._get_client()
        should_close = self._client is None

        try:
            async with client.stream("POST", endpoint, json=payload, headers=headers) as response:
                if response.status_code in (401, 403):
                    raise AuthenticationError("OpenRouter authentication failed: invalid or unauthorized API key")
                elif response.status_code >= 400:
                    await response.aread()
                    self._handle_http_error(response)

                async for line in response.aiter_lines():
                    trimmed = line.strip()
                    if not trimmed or not trimmed.startswith("data:"):
                        continue

                    data_payload = trimmed[len("data:") :].strip()
                    if data_payload == "[DONE]":
                        break

                    try:
                        chunk = json.loads(data_payload)
                        choices = chunk.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            content = delta.get("content")
                            if content:
                                yield content
                    except json.JSONDecodeError:
                        continue
        except httpx.RequestError as exc:
            raise ProviderAPIError(f"Network error during OpenRouter stream: {exc.__class__.__name__}")
        finally:
            if should_close:
                await client.aclose()
