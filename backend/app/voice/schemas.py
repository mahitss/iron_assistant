"""Data schemas and event models for Kairo Voice WebSocket protocol and audio pipeline."""

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class VoiceState(str, Enum):
    """Explicit states of a VoiceSession state machine."""

    IDLE = "IDLE"
    LISTENING = "LISTENING"
    TRANSCRIBING = "TRANSCRIBING"
    PROCESSING = "PROCESSING"
    SPEAKING = "SPEAKING"
    STOPPING = "STOPPING"
    CLOSED = "CLOSED"
    ERROR = "ERROR"


class Transcript(BaseModel):
    """Structured transcription result from Speech-to-Text provider."""

    text: str = Field(..., description="Transcribed spoken text")
    confidence: float | None = Field(default=None, description="Confidence score between 0.0 and 1.0 if provided")
    language: str | None = Field(default=None, description="Detected or configured language code (e.g. 'en')")
    timestamps: list[dict[str, Any]] | None = Field(default=None, description="Word/segment timestamps if supported")


# ---------------------------------------------------------------------------
# Client -> Server WebSocket Events
# ---------------------------------------------------------------------------

class StartSessionEvent(BaseModel):
    """Client initiates voice session."""

    type: Literal["start_session"] = "start_session"
    session_id: str | None = Field(default=None, description="Optional existing session ID to resume")
    sample_rate: int = Field(default=16000, description="Audio sample rate in Hz (default: 16000)")


class AudioChunkEvent(BaseModel):
    """Client sends a base64-encoded audio chunk over text WebSocket frame."""

    type: Literal["audio_chunk"] = "audio_chunk"
    data: str = Field(..., description="Base64-encoded audio payload")


class StopSpeakingEvent(BaseModel):
    """Client indicates user finished speaking."""

    type: Literal["stop_speaking"] = "stop_speaking"


class InterruptEvent(BaseModel):
    """Client signals user interruption / barge-in while assistant is speaking."""

    type: Literal["interrupt"] = "interrupt"


class EndSessionEvent(BaseModel):
    """Client terminates voice session."""

    type: Literal["end_session"] = "end_session"


# ---------------------------------------------------------------------------
# Server -> Client WebSocket Events
# ---------------------------------------------------------------------------

class SessionStartedEvent(BaseModel):
    """Server acknowledges session startup."""

    type: Literal["session_started"] = "session_started"
    session_id: str = Field(..., description="Assigned voice session identifier")
    sample_rate: int = Field(default=16000, description="Agreed sample rate")


class TranscriptPartialEvent(BaseModel):
    """Interim real-time transcription feedback."""

    type: Literal["transcript_partial"] = "transcript_partial"
    text: str = Field(..., description="Partial interim transcript")


class TranscriptFinalEvent(BaseModel):
    """Final verified speech transcription ready for Kairo Core."""

    type: Literal["transcript_final"] = "transcript_final"
    text: str = Field(..., description="Final transcribed user message")
    confidence: float | None = Field(default=None, description="Transcription confidence")
    language: str | None = Field(default=None, description="Detected language")


class ThinkingEvent(BaseModel):
    """Assistant is executing reasoning / retrieving memory."""

    type: Literal["thinking"] = "thinking"


class ToolActivityEvent(BaseModel):
    """Safe user-facing notification of an active tool execution."""

    type: Literal["tool_activity"] = "tool_activity"
    tool: str = Field(..., description="Tool name (e.g., 'web_search', 'calculator')")
    status: str = Field(..., description="Execution status ('started', 'completed')")
    message: str | None = Field(default=None, description="Friendly status description")


class ResponseTextEvent(BaseModel):
    """Streaming text chunk of assistant response."""

    type: Literal["response_text"] = "response_text"
    chunk: str = Field(..., description="Assistant text chunk")


class AudioChunkServerEvent(BaseModel):
    """Audio chunk sent as JSON text frame when binary frame is not used."""

    type: Literal["audio_chunk"] = "audio_chunk"
    data: str = Field(..., description="Base64-encoded synthesized audio chunk")


class ResponseCompleteEvent(BaseModel):
    """Assistant turn is complete."""

    type: Literal["response_complete"] = "response_complete"
    full_text: str = Field(..., description="Complete assistant response text")
    duration_ms: float | None = Field(default=None, description="Total turn duration in milliseconds")


class InterruptedEvent(BaseModel):
    """Server acknowledges interruption and halted synthesis."""

    type: Literal["interrupted"] = "interrupted"


class ErrorEvent(BaseModel):
    """Structured error notification."""

    type: Literal["error"] = "error"
    message: str = Field(..., description="Human-readable error description")
    code: str = Field(default="VOICE_ERROR", description="Error category code")


class SessionEndedEvent(BaseModel):
    """Session has been cleanly closed."""

    type: Literal["session_ended"] = "session_ended"
    session_id: str = Field(..., description="Closed session identifier")
