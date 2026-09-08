"""Mock Speech-to-Text and Text-to-Speech providers for offline testing and development."""

from collections.abc import AsyncIterator

from app.voice.schemas import Transcript
from app.voice.stt import SpeechToTextProvider, STTProviderError
from app.voice.tts import TextToSpeechProvider, TTSProviderError

# Minimal valid WAV header for a brief 16kHz mono audio chunk
MOCK_WAV_HEADER = b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"


class MockSTTProvider(SpeechToTextProvider):
    """Deterministic STT provider for offline unit and integration tests."""

    def __init__(
        self,
        default_text: str = "Hello Kairo, how are you?",
        confidence: float | None = 0.95,
        language: str = "en",
        should_fail: bool = False,
    ) -> None:
        self.default_text = default_text
        self.confidence = confidence
        self.language = language
        self.should_fail = should_fail
        self.call_count = 0

    async def transcribe(
        self,
        audio_bytes: bytes,
        content_type: str = "audio/wav",
        language: str | None = None,
    ) -> Transcript:
        self.call_count += 1
        if self.should_fail:
            raise STTProviderError("Mock STT transcription service simulated failure.")

        return Transcript(
            text=self.default_text,
            confidence=self.confidence,
            language=language or self.language,
        )

    async def stream_transcribe(
        self,
        audio_stream: AsyncIterator[bytes],
        content_type: str = "audio/wav",
    ) -> AsyncIterator[Transcript]:
        if self.should_fail:
            raise STTProviderError("Mock STT streaming failure.")

        yield Transcript(text=self.default_text, confidence=self.confidence, language=self.language)


class MockTTSProvider(TextToSpeechProvider):
    """Deterministic TTS provider generating bounded mock audio frames."""

    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.synthesized_texts: list[str] = []

    async def synthesize(
        self,
        text: str,
        voice: str | None = None,
        output_format: str = "mp3",
    ) -> bytes:
        if self.should_fail:
            raise TTSProviderError("Mock TTS synthesis service simulated failure.")

        self.synthesized_texts.append(text)
        # Return mock audio payload matching length of text
        mock_payload = MOCK_WAV_HEADER + (b"\x00\x01" * max(1, len(text) * 10))
        return mock_payload

    async def stream_synthesize(
        self,
        text: str,
        voice: str | None = None,
        chunk_size: int = 512,
    ) -> AsyncIterator[bytes]:
        full_audio = await self.synthesize(text, voice=voice)
        for i in range(0, len(full_audio), chunk_size):
            yield full_audio[i : i + chunk_size]
