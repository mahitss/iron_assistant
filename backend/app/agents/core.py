"""Core Kairo agent implementation."""

from typing import AsyncIterator, List, Optional
from app.core.config import get_settings
from app.models.openrouter import OpenRouterProvider
from app.models.provider import ChatMessage, MessageRole, ModelProvider

KAIRO_SYSTEM_PROMPT = (
    "You are Kairo, an autonomous personal AI assistant. "
    "Be helpful, precise, honest, and concise. "
    "Do not claim to have performed actions you did not perform."
)


class KairoAgent:
    """Core Kairo AI agent managing context, system prompt, and provider invocation."""

    def __init__(
        self,
        provider: ModelProvider,
        system_prompt: str = KAIRO_SYSTEM_PROMPT,
        model: Optional[str] = None,
    ):
        self.provider = provider
        self.system_prompt = system_prompt
        self.model = model

    def build_prompt_messages(self, user_message: str) -> List[ChatMessage]:
        """Construct prompt messages incorporating Kairo's system persona."""
        return [
            ChatMessage(role=MessageRole.SYSTEM, content=self.system_prompt),
            ChatMessage(role=MessageRole.USER, content=user_message),
        ]

    async def process_message(self, message: str, model: Optional[str] = None) -> str:
        """Process user message and return complete assistant response."""
        messages = self.build_prompt_messages(message)
        selected_model = model or self.model
        return await self.provider.generate_response(messages, model=selected_model)

    async def stream_message(
        self,
        message: str,
        model: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Process user message and stream assistant response tokens."""
        messages = self.build_prompt_messages(message)
        selected_model = model or self.model
        async for chunk in self.provider.stream_response(messages, model=selected_model):
            yield chunk


def get_default_agent() -> KairoAgent:
    """Factory creating KairoAgent configured with OpenRouter settings."""
    settings = get_settings()
    provider = OpenRouterProvider(
        api_key=settings.openrouter_api_key_str,
        base_url=settings.OPENROUTER_BASE_URL,
        default_model=settings.KAIRO_MODEL,
        site_url=settings.OPENROUTER_SITE_URL,
        app_name=settings.OPENROUTER_APP_NAME,
    )
    return KairoAgent(provider=provider, model=settings.KAIRO_MODEL)
