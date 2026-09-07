"""Chat routes for Kairo AI assistant."""

import json
from typing import AsyncIterator
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agents.core import KairoAgent, get_default_agent
from app.models.provider import AuthenticationError, ProviderAPIError, ProviderError

router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    """Schema for chat input message."""

    message: str = Field(
        ...,
        min_length=1,
        description="User message for Kairo",
        examples=["Hello Kairo"],
    )


class ChatResponse(BaseModel):
    """Schema for chat response message."""

    message: str = Field(
        ...,
        description="Kairo AI response",
        examples=["Hello! How can I help?"],
    )


@router.post(
    "",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Send message to Kairo",
    description="Processes a user message through Kairo core agent and returns AI response.",
)
async def chat(
    request: ChatRequest,
    agent: KairoAgent = Depends(get_default_agent),
) -> ChatResponse:
    """Synchronous chat completion endpoint."""
    try:
        response_text = await agent.process_message(request.message)
        return ChatResponse(message=response_text)
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
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing message.",
        )


@router.post(
    "/stream",
    status_code=status.HTTP_200_OK,
    summary="Stream message from Kairo",
    description="Streams Kairo response tokens via Server-Sent Events (SSE).",
)
async def chat_stream(
    request: ChatRequest,
    agent: KairoAgent = Depends(get_default_agent),
) -> StreamingResponse:
    """Server-Sent Events streaming chat endpoint."""

    async def sse_event_generator() -> AsyncIterator[str]:
        try:
            async for chunk in agent.stream_message(request.message):
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
