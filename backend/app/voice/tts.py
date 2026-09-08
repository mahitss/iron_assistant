"""Text-to-Speech (TTS) provider interface and registry."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class TTSProviderError(Exception):
    """Raised when speech synthesis fails."""


class TTSUnavailableError(TTSProviderError):
    """Raised when no TTS provider is configured or service is unreachable."""


class TextToSpeechProvider(ABC):
    """Abstract interface for Text-to-Speech providers."""

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice: str | None = None,
        output_format: str = "mp3",
    ) -> bytes:
        """Synthesize text into complete audio bytes.

        Returns raw synthesized audio bytes (e.g. mp3 or wav).
        """
        pass

    @abstractmethod
    async def stream_synthesize(
        self,
        text: str,
        voice: str | None = None,
        chunk_size: int = 4096,
    ) -> AsyncIterator[bytes]:
        """Yield synthesized audio in bounded streaming chunks."""
        pass


def get_tts_provider(provider_type: str | None = None) -> TextToSpeechProvider:
    """Factory creating configured Text-to-Speech provider."""
    from app.core.config import get_settings
    from app.voice.providers.mock import MockTTSProvider
    from app.voice.providers.openai_compatible import OpenAICompatibleTTSProvider

    cfg = get_settings()
    ptype = (provider_type or cfg.KAIRO_TTS_PROVIDER or "mock").lower().strip()

    if ptype == "mock":
        return MockTTSProvider()
    elif ptype in {"openai", "tts"}:
        return OpenAICompatibleTTSProvider(
            api_key=cfg.tts_api_key_str,
            base_url=cfg.KAIRO_TTS_BASE_URL,
            model=cfg.KAIRO_TTS_MODEL,
            voice=cfg.KAIRO_TTS_VOICE,
        )
    raise TTSUnavailableError(f"Unsupported or unconfigured TTS provider: '{ptype}'.")

