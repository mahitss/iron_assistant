"""OpenAI-compatible HTTP STT and TTS providers."""

import logging
from collections.abc import AsyncIterator

import httpx

from app.voice.schemas import Transcript
from app.voice.stt import SpeechToTextProvider, STTProviderError, STTUnavailableError
from app.voice.tts import TextToSpeechProvider, TTSProviderError, TTSUnavailableError

logger = logging.getLogger("kairo.voice.providers.openai")


class OpenAICompatibleSTTProvider(SpeechToTextProvider):
    """STT provider targeting OpenAI-compatible /v1/audio/transcriptions endpoint."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "whisper-1",
        timeout_seconds: float = 30.0,
    ) -> None:
        self.api_key = (api_key or "").strip()
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def transcribe(
        self,
        audio_bytes: bytes,
        content_type: str = "audio/wav",
        language: str | None = None,
    ) -> Transcript:
        if not self.api_key and "api.openai.com" in self.base_url:
            raise STTUnavailableError("No STT API key configured for OpenAI Speech-to-Text provider.")

        url = f"{self.base_url}/audio/transcriptions"
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        ext = "wav" if "wav" in content_type else "mp3"
        files = {"file": (f"audio.{ext}", audio_bytes, content_type)}
        data = {"model": self.model}
        if language:
            data["language"] = language

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(url, headers=headers, files=files, data=data)
                if resp.status_code != 200:
                    raise STTProviderError(
                        f"STT service returned HTTP {resp.status_code}: {resp.text[:200]}"
                    )
                result = resp.json()
                text = result.get("text", "").strip()
                return Transcript(text=text, language=language)
        except STTProviderError:
            raise
        except Exception as exc:
            logger.warning("STT transcription network request failed: %s", exc)
            raise STTProviderError(f"Transcription failed: {exc}") from exc

    async def stream_transcribe(
        self,
        audio_stream: AsyncIterator[bytes],
        content_type: str = "audio/wav",
    ) -> AsyncIterator[Transcript]:
        # Collect stream for batch transcription when streaming STT is not supported by endpoint
        buffer = bytearray()
        async for chunk in audio_stream:
            buffer.extend(chunk)
        res = await self.transcribe(bytes(buffer), content_type=content_type)
        yield res


class OpenAICompatibleTTSProvider(TextToSpeechProvider):
    """TTS provider targeting OpenAI-compatible /v1/audio/speech endpoint."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "tts-1",
        voice: str = "alloy",
        timeout_seconds: float = 30.0,
    ) -> None:
        self.api_key = (api_key or "").strip()
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.model = model
        self.voice = voice
        self.timeout_seconds = timeout_seconds

    async def synthesize(
        self,
        text: str,
        voice: str | None = None,
        output_format: str = "mp3",
    ) -> bytes:
        if not self.api_key and "api.openai.com" in self.base_url:
            raise TTSUnavailableError("No TTS API key configured for OpenAI Text-to-Speech provider.")

        url = f"{self.base_url}/audio/speech"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "input": text,
            "voice": voice or self.voice,
            "response_format": output_format,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code != 200:
                    raise TTSProviderError(
                        f"TTS service returned HTTP {resp.status_code}: {resp.text[:200]}"
                    )
                return resp.content
        except TTSProviderError:
            raise
        except Exception as exc:
            logger.warning("TTS synthesis network request failed: %s", exc)
            raise TTSProviderError(f"Synthesis failed: {exc}") from exc

    async def stream_synthesize(
        self,
        text: str,
        voice: str | None = None,
        chunk_size: int = 4096,
    ) -> AsyncIterator[bytes]:
        full_audio = await self.synthesize(text, voice=voice)
        for i in range(0, len(full_audio), chunk_size):
            yield full_audio[i : i + chunk_size]
