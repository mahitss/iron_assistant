"""VoiceService orchestrating VAD, STT, Kairo Core, TTS, and real-time streaming."""

import asyncio
import logging
import time
import uuid
from collections.abc import Callable, Coroutine
from typing import Any

from app.agents.core import KairoAgent
from app.core.config import Settings, get_settings
from app.voice.schemas import (
    ErrorEvent,
    InterruptedEvent,
    ResponseCompleteEvent,
    ResponseTextEvent,
    ThinkingEvent,
    ToolActivityEvent,
    TranscriptFinalEvent,
    VoiceState,
)
from app.voice.session import AudioLimitExceededError, VoiceSession
from app.voice.stt import SpeechToTextProvider, STTProviderError, STTUnavailableError, get_stt_provider
from app.voice.tts import TextToSpeechProvider, TTSProviderError, TTSUnavailableError, get_tts_provider
from app.voice.vad import BaseVAD, create_vad

logger = logging.getLogger("kairo.voice.service")

EventCallback = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]
AudioCallback = Callable[[bytes], Coroutine[Any, Any, None]]


class VoiceService:
    """Coordinates voice session state, real-time VAD, STT transcription, Kairo Core reasoning, and TTS playback."""

    def __init__(
        self,
        agent: KairoAgent,
        stt_provider: SpeechToTextProvider | None = None,
        tts_provider: TextToSpeechProvider | None = None,
        vad: BaseVAD | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.agent = agent
        self.settings = settings or get_settings()
        self.stt_provider = stt_provider or get_stt_provider()
        self.tts_provider = tts_provider or get_tts_provider()
        self.sample_rate = self.settings.KAIRO_VOICE_SAMPLE_RATE
        self.vad = vad or create_vad(sample_rate=self.sample_rate)
        self.max_concurrent_sessions = self.settings.KAIRO_VOICE_MAX_CONCURRENT_SESSIONS

        self._sessions: dict[str, VoiceSession] = {}
        self._lock = asyncio.Lock()

    async def create_session(self, session_id: str | None = None) -> VoiceSession:
        """Create and register a new VoiceSession, enforcing concurrency limits."""
        async with self._lock:
            # 1. Clean up stale or expired sessions
            self._cleanup_stale_sessions_unlocked()

            sid = (session_id or f"voice_{uuid.uuid4().hex[:12]}").strip()

            if sid in self._sessions:
                existing = self._sessions[sid]
                if existing.state != VoiceState.CLOSED:
                    return existing

            # 2. Concurrency limit check
            active_count = sum(1 for s in self._sessions.values() if s.state != VoiceState.CLOSED)
            if active_count >= self.max_concurrent_sessions:
                # Evict oldest session
                oldest_sid = min(
                    (s.session_id for s in self._sessions.values() if s.state != VoiceState.CLOSED),
                    key=lambda k: self._sessions[k].last_activity,
                    default=None,
                )
                if oldest_sid:
                    logger.info("Max voice sessions reached. Evicting oldest session '%s'", oldest_sid)
                    self._close_session_unlocked(oldest_sid)

            session = VoiceSession(
                session_id=sid,
                sample_rate=self.sample_rate,
                max_session_seconds=self.settings.KAIRO_VOICE_MAX_SESSION_SECONDS,
                max_audio_chunk_bytes=self.settings.KAIRO_VOICE_MAX_AUDIO_CHUNK_BYTES,
                max_message_seconds=self.settings.KAIRO_VOICE_MAX_MESSAGE_SECONDS,
            )
            self._sessions[sid] = session
            logger.info("Created voice session '%s'", sid)
            return session

    def get_session(self, session_id: str) -> VoiceSession | None:
        """Lookup active session by ID."""
        return self._sessions.get(session_id)

    async def close_session(self, session_id: str) -> None:
        """Close an active session and cancel running tasks."""
        async with self._lock:
            self._close_session_unlocked(session_id)

    def _close_session_unlocked(self, session_id: str) -> None:
        session = self._sessions.pop(session_id, None)
        if session:
            session.close()
            logger.info("Closed voice session '%s'", session_id)

    def _cleanup_stale_sessions_unlocked(self) -> None:
        stale_ids = [
            sid
            for sid, sess in self._sessions.items()
            if sess.is_expired() or sess.state == VoiceState.CLOSED
        ]
        for sid in stale_ids:
            self._close_session_unlocked(sid)

    async def handle_audio_chunk(
        self,
        session: VoiceSession,
        chunk: bytes,
        emit_event: EventCallback,
        emit_audio: AudioCallback,
    ) -> None:
        """Process an incoming microphone audio chunk.

        Enforces audio bounds, updates VAD, and triggers processing on speech end.
        """
        if session.state == VoiceState.CLOSED:
            return

        if session.is_expired():
            await emit_event(
                ErrorEvent(message="Voice session expired.", code="SESSION_TIMEOUT").model_dump()
            )
            session.close()
            return

        # If assistant was speaking and user starts speaking, treat as interruption
        if session.state == VoiceState.SPEAKING:
            is_voice, _ = self.vad.process_chunk(chunk)
            if is_voice:
                logger.info("User barge-in detected during playback for session '%s'", session.session_id)
                await self.handle_interrupt(session, emit_event)
                return

        if session.state == VoiceState.IDLE:
            session.transition_to(VoiceState.LISTENING)

        if session.state != VoiceState.LISTENING:
            return

        try:
            session.append_audio(chunk)
        except AudioLimitExceededError as exc:
            logger.warning("Audio limit exceeded for session '%s': %s", session.session_id, exc)
            await emit_event(ErrorEvent(message=str(exc), code="AUDIO_LIMIT_EXCEEDED").model_dump())
            session.clear_audio_buffer()
            return

        # Analyze chunk through VAD
        _, speech_ended = self.vad.process_chunk(chunk)
        if speech_ended:
            logger.debug("VAD detected end of speech for session '%s'", session.session_id)
            await self._process_speech_turn(session, emit_event, emit_audio)

    async def force_process_speech(
        self,
        session: VoiceSession,
        emit_event: EventCallback,
        emit_audio: AudioCallback,
    ) -> None:
        """Force processing of currently buffered speech (e.g. when user clicks stop speaking)."""
        if session.state == VoiceState.LISTENING and session.get_audio_bytes():
            self.vad.reset()
            await self._process_speech_turn(session, emit_event, emit_audio)

    async def _process_speech_turn(
        self,
        session: VoiceSession,
        emit_event: EventCallback,
        emit_audio: AudioCallback,
    ) -> None:
        """Execute full speech turn: STT -> Kairo Core -> TTS -> audio stream."""
        audio_bytes = session.get_audio_bytes()
        # Privacy guarantee: Clear raw audio buffer immediately
        session.clear_audio_buffer()

        if len(audio_bytes) < 1000:
            # Insufficient audio, return to listening
            return

        session.transition_to(VoiceState.TRANSCRIBING)
        session.reset_cancellation()

        # 1. Speech-to-Text Transcription
        try:
            transcript = await self.stt_provider.transcribe(audio_bytes)
        except (STTUnavailableError, STTProviderError) as exc:
            logger.warning("STT transcription error for session '%s': %s", session.session_id, exc)
            session.transition_to(VoiceState.ERROR)
            await emit_event(
                ErrorEvent(message=f"Transcription failed: {exc}", code="STT_ERROR").model_dump()
            )
            session.transition_to(VoiceState.LISTENING)
            return

        text = (transcript.text or "").strip()
        if not text:
            # Empty transcription (background noise / silence)
            session.transition_to(VoiceState.LISTENING)
            return

        session.last_transcript = text
        await emit_event(
            TranscriptFinalEvent(
                text=text,
                confidence=transcript.confidence,
                language=transcript.language,
            ).model_dump()
        )

        if session.is_cancelled:
            session.transition_to(VoiceState.LISTENING)
            return

        # 2. Reasoning with Kairo Core
        session.transition_to(VoiceState.PROCESSING)
        await emit_event(ThinkingEvent().model_dump())

        turn_start = time.perf_counter()

        # Wrap agent execution in a cancellable task
        async def run_agent():
            return await self.agent.process_message(message=text, session_id=session.session_id)

        session.active_task = asyncio.create_task(run_agent())
        try:
            agent_response = await session.active_task
        except asyncio.CancelledError:
            logger.info("Agent processing cancelled for session '%s'", session.session_id)
            session.transition_to(VoiceState.LISTENING)
            return
        except Exception as exc:
            logger.error(
                "Agent reasoning failure in voice session '%s': %s", session.session_id, exc, exc_info=True
            )
            session.transition_to(VoiceState.ERROR)
            await emit_event(
                ErrorEvent(message=f"Agent reasoning failed: {exc}", code="CORE_ERROR").model_dump()
            )
            session.transition_to(VoiceState.LISTENING)
            return
        finally:
            session.active_task = None

        if session.is_cancelled:
            session.transition_to(VoiceState.LISTENING)
            return

        # Emit safe tool activity if any tools were used
        for tool in agent_response.tools_used:
            await emit_event(
                ToolActivityEvent(
                    tool=tool.tool,
                    status=tool.status,
                    message=f"Used {tool.tool}",
                ).model_dump()
            )

        response_text = agent_response.message.strip()
        await emit_event(ResponseTextEvent(chunk=response_text).model_dump())

        # 3. Text-to-Speech Synthesis & Streaming
        session.transition_to(VoiceState.SPEAKING)

        async def run_tts():
            async for audio_chunk in self.tts_provider.stream_synthesize(response_text):
                if session.is_cancelled:
                    break
                await emit_audio(audio_chunk)

        session.active_task = asyncio.create_task(run_tts())
        try:
            await session.active_task
        except asyncio.CancelledError:
            logger.info("TTS streaming cancelled for session '%s'", session.session_id)
        except (TTSUnavailableError, TTSProviderError) as exc:
            logger.warning("TTS synthesis error for session '%s': %s", session.session_id, exc)
            # Text was already sent to client; log error and recover cleanly
            await emit_event(
                ErrorEvent(message=f"Audio synthesis failed: {exc}", code="TTS_ERROR").model_dump()
            )
        finally:
            session.active_task = None

        turn_duration_ms = (time.perf_counter() - turn_start) * 1000.0

        if not session.is_cancelled:
            await emit_event(
                ResponseCompleteEvent(
                    full_text=response_text,
                    duration_ms=turn_duration_ms,
                ).model_dump()
            )

        session.transition_to(VoiceState.LISTENING)

    async def handle_interrupt(self, session: VoiceSession, emit_event: EventCallback) -> None:
        """Halt active synthesis or generation (barge-in / cancel)."""
        session.cancel_active_turn()
        self.vad.reset()
        await emit_event(InterruptedEvent().model_dump())
        if session.state in {VoiceState.PROCESSING, VoiceState.SPEAKING, VoiceState.TRANSCRIBING}:
            session.transition_to(VoiceState.LISTENING)
