"""Core Kairo agent implementation with model capability routing."""

from typing import AsyncIterator, List, Optional, Tuple, Union
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.models.openrouter import OpenRouterProvider
from app.models.provider import ChatMessage, MessageRole, ModelProvider
from app.models.registry import (
    ModelCapability,
    ModelDefinition,
    ModelRegistry,
    create_default_registry,
)
from app.models.router import ModelRouter

KAIRO_SYSTEM_PROMPT = (
    "You are Kairo, an autonomous personal AI assistant. "
    "Be helpful, precise, honest, and concise. "
    "Do not claim to have performed actions you did not perform."
)


class AgentResponse(BaseModel):
    """Structured response from Kairo agent containing content and model metadata."""

    message: str = Field(..., description="Assistant response text")
    model: str = Field(..., description="ID of the model that generated the response")

    def __eq__(self, other: object) -> bool:
        """Allow string comparison for backwards compatibility with tests."""
        if isinstance(other, str):
            return self.message == other
        return super().__eq__(other)

    def __str__(self) -> str:
        return self.message


class KairoAgent:
    """Core Kairo AI agent managing context, system prompt, and capability-based routing."""

    def __init__(
        self,
        provider: ModelProvider,
        router: Optional[ModelRouter] = None,
        system_prompt: str = KAIRO_SYSTEM_PROMPT,
        model: Optional[str] = None,
    ):
        self.provider = provider
        self.router = router
        self.system_prompt = system_prompt
        self.model = model

    @staticmethod
    def detect_capability(message: str) -> ModelCapability:
        """Deterministic heuristic capability selector based on message content."""
        lowered = message.lower()

        coding_triggers = [
            "python", "javascript", "typescript", "html", "css", "code", "bug",
            "error", "exception", "traceback", "syntax", "function", "class",
            "def ", "import ", "async ", "sql", "query", "regex", "algorithm",
        ]
        if any(trigger in lowered for trigger in coding_triggers):
            return ModelCapability.CODING

        reasoning_triggers = [
            "prove", "proof", "deduce", "step by step", "step-by-step",
            "logic puzzle", "solve this riddle", "mathematical",
        ]
        if any(trigger in lowered for trigger in reasoning_triggers):
            return ModelCapability.REASONING

        vision_triggers = ["image", "photo", "picture", "screenshot", "visualize"]
        if any(trigger in lowered for trigger in vision_triggers):
            return ModelCapability.VISION

        fast_triggers = ["quick", "ping", "fast", "tldr", "tl;dr", "one word"]
        if any(trigger in lowered for trigger in fast_triggers):
            return ModelCapability.FAST

        return ModelCapability.GENERAL

    def resolve_model(
        self,
        capability: Optional[Union[ModelCapability, str]] = None,
        model: Optional[str] = None,
    ) -> str:
        """Determine target model ID using router or explicit override."""
        if model:
            return model
        if self.router is not None:
            cap = capability if capability is not None else ModelCapability.GENERAL
            model_def: ModelDefinition = self.router.select_model(cap)
            return model_def.id
        return self.model or "openrouter/free"

    def build_prompt_messages(self, user_message: str) -> List[ChatMessage]:
        """Construct prompt messages incorporating Kairo's system persona."""
        return [
            ChatMessage(role=MessageRole.SYSTEM, content=self.system_prompt),
            ChatMessage(role=MessageRole.USER, content=user_message),
        ]

    async def process_message(
        self,
        message: str,
        capability: Optional[Union[ModelCapability, str]] = None,
        model: Optional[str] = None,
    ) -> AgentResponse:
        """Process user message and return complete assistant response with model metadata."""
        selected_model = self.resolve_model(capability=capability, model=model)
        messages = self.build_prompt_messages(message)
        response_text = await self.provider.generate_response(messages, model=selected_model)
        return AgentResponse(message=response_text, model=selected_model)

    async def stream_message(
        self,
        message: str,
        capability: Optional[Union[ModelCapability, str]] = None,
        model: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Process user message and stream assistant response tokens."""
        selected_model = self.resolve_model(capability=capability, model=model)
        messages = self.build_prompt_messages(message)
        async for chunk in self.provider.stream_response(messages, model=selected_model):
            yield chunk

    async def stream_message_with_metadata(
        self,
        message: str,
        capability: Optional[Union[ModelCapability, str]] = None,
        model: Optional[str] = None,
    ) -> Tuple[str, AsyncIterator[str]]:
        """Resolve model and return tuple of (model_id, stream_iterator)."""
        selected_model = self.resolve_model(capability=capability, model=model)
        messages = self.build_prompt_messages(message)
        stream = self.provider.stream_response(messages, model=selected_model)
        return selected_model, stream


def get_default_agent() -> KairoAgent:
    """Factory creating KairoAgent configured with ModelRouter and OpenRouter settings."""
    settings = get_settings()

    # Initialize model registry and router
    registry: ModelRegistry = create_default_registry(default_model_id=settings.KAIRO_MODEL)
    router: ModelRouter = ModelRouter(
        registry=registry,
        default_model_id=settings.KAIRO_MODEL,
        routing_enabled=settings.KAIRO_ROUTING_ENABLED,
    )

    # Initialize OpenRouter provider
    provider = OpenRouterProvider(
        api_key=settings.openrouter_api_key_str,
        base_url=settings.OPENROUTER_BASE_URL,
        default_model=settings.KAIRO_MODEL,
        site_url=settings.OPENROUTER_SITE_URL,
        app_name=settings.OPENROUTER_APP_NAME,
    )

    return KairoAgent(provider=provider, router=router, model=settings.KAIRO_MODEL)
