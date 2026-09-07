"""Model provider abstraction and structured message definitions."""

from enum import Enum
from typing import AsyncIterator, List, Optional, Protocol, runtime_checkable
from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Supported roles for chat messages."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    """Structured chat message exchanged with model providers."""

    role: MessageRole
    content: str = Field(..., min_length=1, description="Message content")

    model_config = {"frozen": True}


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
        **kwargs,
    ) -> str:
        """Generate a single complete response from the model provider."""
        ...

    async def stream_response(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream response tokens/chunks from the model provider."""
        ...
