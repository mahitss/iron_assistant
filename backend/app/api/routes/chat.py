"""Chat routes for Kairo AI assistant with model routing and tool execution support."""

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agents.core import KairoAgent, get_default_agent
from app.models.provider import AuthenticationError, ProviderAPIError, ProviderError
from app.models.registry import ModelCapability
from app.models.router import InvalidCapabilityError, NoUsableModelError

router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    """Schema for chat input message with optional session identifier and capability routing."""

    message: str = Field(
        ...,
        min_length=1,
        description="User message for Kairo",
        examples=["Hello Kairo"],
    )
    session_id: str | None = Field(
        default=None,
        description="Optional persistent conversation session ID. If omitted, a new session is created.",
        examples=["sess_1234567890ab"],
    )
    capability: str | None = Field(
        default=None,
        description="Optional model capability request (e.g., general, coding, reasoning, fast, vision)",
        examples=["coding"],
    )


class ToolActivitySchema(BaseModel):
    """Safe metadata describing tool execution without exposing internal reasoning."""

    tool: str = Field(..., description="Name of the executed tool")
    status: str = Field(..., description="Execution status ('success' or 'failed')")
    verification_status: str = Field(
        ..., description="Verification result ('verified', 'failed', or 'denied')"
    )


class ChatResponse(BaseModel):
    """Schema for chat response message, session tracking, and routing/tool metadata."""

    message: str = Field(
        ...,
        description="Kairo AI response text",
        examples=["Hello! How can I help?"],
    )
    session_id: str | None = Field(
        default=None,
        description="Session identifier associated with this conversation turn",
        examples=["sess_1234567890ab"],
    )
    model: str = Field(
        ...,
        description="ID of the model that served this request",
        examples=["openrouter/free"],
    )
    tools_used: list[ToolActivitySchema] | None = Field(
        default=None,
        description="List of tools invoked during response generation",
    )


def resolve_requested_capability(raw_capability: str | None) -> ModelCapability:
    """Validate and convert raw capability input to ModelCapability."""
    if not raw_capability:
        return ModelCapability.GENERAL
    try:
        return ModelCapability.from_str(raw_capability)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.post(
    "",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Send message to Kairo",
    description="Processes a user message through Kairo core agent, loads conversation/memory, and returns AI response.",
)
async def chat(
    request: ChatRequest,
    agent: KairoAgent = Depends(get_default_agent),
) -> ChatResponse:
    """Synchronous chat completion endpoint supporting internal tool execution and memory context."""
    capability = resolve_requested_capability(request.capability)

    try:
        # Emit chat.message.created event
        try:
            from app.events import event_bus
            await event_bus.publish(
                event_bus.publisher.create_event(
                    event_type="chat.message.created",
                    source="chat_router",
                    payload={"message": request.message, "role": "user", "session_id": request.session_id},
                    user_id=None,
                )
            )
        except Exception:
            pass

        response = await agent.process_message(
            request.message,
            session_id=request.session_id,
            capability=capability,
        )

        # Emit chat.response.completed event
        try:
            from app.events import event_bus
            await event_bus.publish(
                event_bus.publisher.create_event(
                    event_type="chat.response.completed",
                    source="chat_router",
                    payload={
                        "response_length": len(response.message),
                        "model": response.model,
                        "session_id": response.session_id,
                    },
                    user_id=None,
                )
            )
        except Exception:
            pass

        tools_meta = (
            [
                ToolActivitySchema(
                    tool=t.tool,
                    status=t.status,
                    verification_status=t.verification_status,
                )
                for t in response.tools_used
            ]
            if response.tools_used
            else None
        )

        return ChatResponse(
            message=response.message,
            session_id=response.session_id,
            model=response.model,
            tools_used=tools_meta,
        )
    except InvalidCapabilityError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except NoUsableModelError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.message,
        )
    except ProviderAPIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=exc.message,
        )
    except ProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exc.message,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing message.",
        )


@router.post(
    "/stream",
    status_code=status.HTTP_200_OK,
    summary="Stream message from Kairo",
    description="Streams Kairo response tokens via Server-Sent Events (SSE) with session and model metadata.",
)
async def chat_stream(
    request: ChatRequest,
    agent: KairoAgent = Depends(get_default_agent),
) -> StreamingResponse:
    """Server-Sent Events streaming chat endpoint with memory integration."""
    capability = resolve_requested_capability(request.capability)

    try:
        selected_model = agent.resolve_model(capability=capability)
    except InvalidCapabilityError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except NoUsableModelError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))

    async def sse_event_generator() -> AsyncIterator[str]:
        try:
            # Emit initial metadata event with selected model ID and session ID
            model_event = json.dumps({"model": selected_model, "session_id": request.session_id})
            yield f"data: {model_event}\n\n"

            # Stream content tokens
            async for chunk in agent.stream_message(
                request.message,
                session_id=request.session_id,
                capability=capability,
                model=selected_model,
            ):
                data = json.dumps({"content": chunk})
                yield f"data: {data}\n\n"

            yield "data: [DONE]\n\n"
        except AuthenticationError as exc:
            data = json.dumps({"error": exc.message})
            yield f"data: {data}\n\n"
            yield "data: [DONE]\n\n"
        except ProviderAPIError as exc:
            data = json.dumps({"error": exc.message})
            yield f"data: {data}\n\n"
            yield "data: [DONE]\n\n"
        except Exception:
            data = json.dumps({"error": "An unexpected error occurred during stream."})
            yield f"data: {data}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        sse_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
