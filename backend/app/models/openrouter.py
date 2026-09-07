"""OpenRouter model provider implementation."""

import json
from typing import AsyncIterator, List, Optional
import httpx

from app.models.provider import (
    AuthenticationError,
    ChatMessage,
    ModelProvider,
    ProviderAPIError,
    ProviderError,
)


class OpenRouterProvider(ModelProvider):
    """OpenRouter OpenAI-compatible chat completion provider."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://openrouter.ai/api/v1",
        default_model: str = "openrouter/free",
        site_url: Optional[str] = None,
        app_name: Optional[str] = "Kairo",
        client: Optional[httpx.AsyncClient] = None,
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
        messages: List[ChatMessage],
        model: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Generate a complete chat completion from OpenRouter."""
        headers = self._get_headers()
        selected_model = model or self.default_model

        payload = {
            "model": selected_model,
            "messages": [{"role": m.role.value, "content": m.content} for m in messages],
            "stream": False,
            **kwargs,
        }

        endpoint = f"{self.base_url}/chat/completions"
        client = self._get_client()
        should_close = self._client is None

        try:
            response = await client.post(endpoint, json=payload, headers=headers)
            return self._handle_completion_response(response)
        except httpx.HTTPStatusError as exc:
            self._handle_http_error(exc.response)
        except httpx.RequestError as exc:
            raise ProviderAPIError(f"Network error communicating with OpenRouter: {exc.__class__.__name__}")
        finally:
            if should_close:
                await client.aclose()

    def _handle_completion_response(self, response: httpx.Response) -> str:
        """Parse non-streaming OpenRouter completion response."""
        if response.status_code == 401 or response.status_code == 403:
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
            if content is None:
                raise ProviderAPIError("OpenRouter returned null message content")
            return content
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
        messages: List[ChatMessage],
        model: Optional[str] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream chat completion tokens from OpenRouter using SSE."""
        headers = self._get_headers()
        selected_model = model or self.default_model

        payload = {
            "model": selected_model,
            "messages": [{"role": m.role.value, "content": m.content} for m in messages],
            "stream": True,
            **kwargs,
        }

        endpoint = f"{self.base_url}/chat/completions"
        client = self._get_client()
        should_close = self._client is None

        try:
            async with client.stream("POST", endpoint, json=payload, headers=headers) as response:
                if response.status_code == 401 or response.status_code == 403:
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
