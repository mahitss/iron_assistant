"""Model provider abstraction, structured message definitions, and provider response models."""

from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional, Protocol, Union, runtime_checkable
from pydantic import BaseModel, Field

from app.tools.schemas import ToolCall


class MessageRole(str, Enum):
    """Supported roles for chat messages."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ChatMessage(BaseModel):
    """Structured chat message exchanged with model providers."""

    role: MessageRole
    content: Optional[str] = Field(default=None, description="Message content")
    name: Optional[str] = Field(default=None, description="Tool name for tool messages")
    tool_call_id: Optional[str] = Field(default=None, description="Associated tool call identifier")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(default=None, description="Raw tool call requests from assistant")

    model_config = {"frozen": True}

    def to_dict(self) -> Dict[str, Any]:
        """Convert ChatMessage to OpenAI/OpenRouter wire format."""
        data: Dict[str, Any] = {"role": self.role.value}
        if self.content is not None:
            data["content"] = self.content
        if self.tool_call_id is not None:
            data["tool_call_id"] = self.tool_call_id
        if self.name is not None:
            data["name"] = self.name
        if self.tool_calls is not None:
            data["tool_calls"] = self.tool_calls
        return data


class ProviderResponse(BaseModel):
    """Structured response from a model provider containing message text and/or tool calls."""

    content: Optional[str] = Field(default=None, description="Assistant text response")
    tool_calls: Optional[List[ToolCall]] = Field(default=None, description="Requested tool invocations")
    model: Optional[str] = Field(default=None, description="Model identifier that produced the response")

    @property
    def has_tool_calls(self) -> bool:
        """True if the provider response contains tool calls."""
        return bool(self.tool_calls)

    def __eq__(self, other: object) -> bool:
        """Allow string comparison for backwards compatibility with tests expecting plain str."""
        if isinstance(other, str):
            return self.content == other
        return super().__eq__(other)

    def __str__(self) -> str:
        return self.content or ""


class ProviderError(Exception):
    """Base exception for model provider errors."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class AuthenticationError(ProviderError):
    """Raised when provider authentication fails (e.g. missing or invalid API key)."""

    def __init__(self, message: str = "Provider authentication failed: missing or invalid API key"):
        super().__init__(message, status_code=401)


class ProviderAPIError(ProviderError):
    """Raised when the upstream provider returns an error."""

    def __init__(self, message: str, status_code: Optional[int] = 502):
        super().__init__(message, status_code=status_code)


@runtime_checkable
class ModelProvider(Protocol):
    """Interface/protocol for model providers (OpenRouter, OpenAI, Anthropic, local)."""

    async def generate_response(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Union[str, ProviderResponse]:
        """Generate a single complete response (or tool call) from the model provider."""
        ...

    async def stream_response(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream response tokens/chunks from the model provider."""
        ...
