"""Core Kairo agent implementation with model capability routing and tool execution loop."""

import json
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.models.openrouter import OpenRouterProvider
from app.models.provider import ChatMessage, MessageRole, ModelProvider, ProviderResponse
from app.models.registry import (
    ModelCapability,
    ModelDefinition,
    ModelRegistry,
    create_default_registry,
)
from app.models.router import ModelRouter
from app.tools.executor import ToolExecutor
from app.tools.registry import ToolRegistry, create_default_tool_registry
from app.tools.schemas import ToolCall, ToolResult

KAIRO_SYSTEM_PROMPT = (
    "You are Kairo, an autonomous personal AI assistant. "
    "Be helpful, precise, honest, and concise. "
    "Do not claim to have performed actions you did not perform."
)


class ToolActivity(BaseModel):
    """Metadata detailing a tool call executed during message processing."""

    tool: str = Field(..., description="Name of the invoked tool")
    status: str = Field(..., description="Execution status ('success' or 'failed')")
    verification_status: str = Field(..., description="Output verification result")


class AgentResponse(BaseModel):
    """Structured response from Kairo agent containing content and model/tool metadata."""

    message: str = Field(..., description="Assistant response text")
    model: str = Field(..., description="ID of the model that generated the response")
    tools_used: List[ToolActivity] = Field(
        default_factory=list,
        description="List of tools invoked while producing this response",
    )

    def __eq__(self, other: object) -> bool:
        """Allow string comparison for backwards compatibility with tests."""
        if isinstance(other, str):
            return self.message == other
        return super().__eq__(other)

    def __str__(self) -> str:
        return self.message


class KairoAgent:
    """Core Kairo AI agent managing context, system prompt, routing, and tool iteration loop."""

    def __init__(
        self,
        provider: ModelProvider,
        router: Optional[ModelRouter] = None,
        tool_registry: Optional[ToolRegistry] = None,
        tool_executor: Optional[ToolExecutor] = None,
        system_prompt: str = KAIRO_SYSTEM_PROMPT,
        model: Optional[str] = None,
        max_tool_iterations: int = 5,
    ):
        self.provider = provider
        self.router = router
        self.tool_registry = tool_registry
        self.tool_executor = tool_executor
        self.system_prompt = system_prompt
        self.model = model
        self.max_tool_iterations = max_tool_iterations

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

    def _get_tool_schemas(self) -> Optional[List[Dict[str, Any]]]:
        """Fetch model-compatible tool schemas if registry is present."""
        if self.tool_registry is not None:
            schemas = self.tool_registry.get_schemas()
            return schemas if schemas else None
        return None

    async def process_message(
        self,
        message: str,
        capability: Optional[Union[ModelCapability, str]] = None,
        model: Optional[str] = None,
    ) -> AgentResponse:
        """Process user message and execute tool loop if requested by model."""
        selected_model = self.resolve_model(capability=capability, model=model)
        messages = self.build_prompt_messages(message)
        tool_schemas = self._get_tool_schemas()
        tools_used: List[ToolActivity] = []

        iterations = 0
        while iterations < self.max_tool_iterations:
            response = await self.provider.generate_response(
                messages,
                model=selected_model,
                tools=tool_schemas,
            )

            # Check if response contains structured tool calls
            has_tool_calls = getattr(response, "has_tool_calls", False)
            tool_calls = getattr(response, "tool_calls", None) or []

            if not has_tool_calls or not tool_calls:
                # Model provided a direct final answer
                final_text = getattr(response, "content", None)
                if final_text is None:
                    final_text = str(response) if not isinstance(response, ProviderResponse) else ""
                return AgentResponse(
                    message=final_text,
                    model=selected_model,
                    tools_used=tools_used,
                )

            # Record assistant tool call message in history
            assistant_tool_call_dicts = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments),
                    },
                }
                for tc in tool_calls
            ]
            messages.append(
                ChatMessage(
                    role=MessageRole.ASSISTANT,
                    content=getattr(response, "content", None),
                    tool_calls=assistant_tool_call_dicts,
                )
            )

            # Execute each requested tool call
            for tc in tool_calls:
                if self.tool_executor:
                    result: ToolResult = await self.tool_executor.execute(tc)
                else:
                    result = ToolResult(
                        success=False,
                        tool_name=tc.name,
                        tool_call_id=tc.id,
                        error="Tool execution engine is not configured.",
                        verification_status="failed",
                    )

                tools_used.append(
                    ToolActivity(
                        tool=tc.name,
                        status="success" if result.success else "failed",
                        verification_status=result.verification_status,
                    )
                )

                # Feed structured tool result back into conversation
                messages.append(
                    ChatMessage(
                        role=MessageRole.TOOL,
                        content=result.to_model_output(),
                        tool_call_id=tc.id,
                        name=tc.name,
                    )
                )

            iterations += 1

        # Fallback if maximum tool iterations exceeded
        return AgentResponse(
            message=f"I reached the maximum number of tool iterations ({self.max_tool_iterations}) without reaching a final response.",
            model=selected_model,
            tools_used=tools_used,
        )

    async def stream_message(
        self,
        message: str,
        capability: Optional[Union[ModelCapability, str]] = None,
        model: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Stream assistant response tokens. If tools are needed, run tool loop first then stream result."""
        selected_model = self.resolve_model(capability=capability, model=model)
        tool_schemas = self._get_tool_schemas()

        # If tools are enabled, run tool resolution
        if tool_schemas and self.tool_executor:
            agent_resp = await self.process_message(message, capability=capability, model=selected_model)
            yield agent_resp.message
        else:
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
        stream = self.stream_message(message, capability=capability, model=selected_model)
        return selected_model, stream


def get_default_agent() -> KairoAgent:
    """Factory creating KairoAgent configured with ModelRouter, ToolRegistry, ToolExecutor, and OpenRouter."""
    settings = get_settings()

    # Initialize model registry and router
    registry: ModelRegistry = create_default_registry(default_model_id=settings.KAIRO_MODEL)
    router: ModelRouter = ModelRouter(
        registry=registry,
        default_model_id=settings.KAIRO_MODEL,
        routing_enabled=settings.KAIRO_ROUTING_ENABLED,
    )

    # Initialize tool registry and executor with safe starter tools
    tool_registry: ToolRegistry = create_default_tool_registry()
    tool_executor: ToolExecutor = ToolExecutor(registry=tool_registry)

    # Initialize OpenRouter provider
    provider = OpenRouterProvider(
        api_key=settings.openrouter_api_key_str,
        base_url=settings.OPENROUTER_BASE_URL,
        default_model=settings.KAIRO_MODEL,
        site_url=settings.OPENROUTER_SITE_URL,
        app_name=settings.OPENROUTER_APP_NAME,
    )

    return KairoAgent(
        provider=provider,
        router=router,
        tool_registry=tool_registry,
        tool_executor=tool_executor,
        model=settings.KAIRO_MODEL,
    )
