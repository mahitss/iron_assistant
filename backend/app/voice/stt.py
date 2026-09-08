"""Speech-to-Text (STT) provider interface and registry."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.voice.schemas import Transcript


class STTProviderError(Exception):
    """Raised when speech transcription fails."""


class STTUnavailableError(STTProviderError):
    """Raised when no STT provider is configured or service is unreachable."""


class SpeechToTextProvider(ABC):
    """Abstract interface for Speech-to-Text providers."""

    @abstractmethod
    async def transcribe(
        self,
        audio_bytes: bytes,
        content_type: str = "audio/wav",
        language: str | None = None,
    ) -> Transcript:
        """Transcribe audio bytes to structured text.

        Returns Transcript with text, confidence (if supported), and language.
        Does not fabricate confidence values.
        """
        pass

    @abstractmethod
    async def stream_transcribe(
        self,
        audio_stream: AsyncIterator[bytes],
        content_type: str = "audio/wav",
    ) -> AsyncIterator[Transcript]:
        """Stream transcription chunks if supported by provider."""
        pass


def get_stt_provider(provider_type: str | None = None) -> SpeechToTextProvider:
    """Factory creating configured Speech-to-Text provider."""
    from app.core.config import get_settings
    from app.voice.providers.mock import MockSTTProvider
    from app.voice.providers.openai_compatible import OpenAICompatibleSTTProvider

    cfg = get_settings()
    ptype = (provider_type or cfg.KAIRO_STT_PROVIDER or "mock").lower().strip()

    if ptype == "mock":
        return MockSTTProvider()
    elif ptype in {"openai", "whisper"}:
        return OpenAICompatibleSTTProvider(
            api_key=cfg.stt_api_key_str,
            base_url=cfg.KAIRO_STT_BASE_URL,
            model=cfg.KAIRO_STT_MODEL,
        )
    raise STTUnavailableError(f"Unsupported or unconfigured STT provider: '{ptype}'.")
