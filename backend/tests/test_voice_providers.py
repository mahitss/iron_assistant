"""Unit tests for Speech-to-Text and Text-to-Speech providers and factories."""

import pytest

from app.voice.providers.mock import MockSTTProvider, MockTTSProvider
from app.voice.stt import STTProviderError, STTUnavailableError, get_stt_provider
from app.voice.tts import TTSProviderError, TTSUnavailableError, get_tts_provider


@pytest.mark.asyncio
async def test_mock_stt_provider_success():
    """Verify MockSTTProvider transcribes audio bytes without fabricating confidence."""
    stt = MockSTTProvider(default_text="Open GitHub repository", confidence=0.97, language="en")
    transcript = await stt.transcribe(b"\x00\x01\x02\x03", content_type="audio/wav")

    assert transcript.text == "Open GitHub repository"
    assert transcript.confidence == 0.97
    assert transcript.language == "en"
    assert stt.call_count == 1


@pytest.mark.asyncio
async def test_mock_stt_provider_failure():
    """Verify MockSTTProvider raises STTProviderError when failure is simulated."""
    stt = MockSTTProvider(should_fail=True)
    with pytest.raises(STTProviderError, match="simulated failure"):
        await stt.transcribe(b"\x00\x01\x02\x03")


@pytest.mark.asyncio
async def test_mock_tts_provider_success_and_streaming():
    """Verify MockTTSProvider generates audio bytes and supports streaming chunks."""
    tts = MockTTSProvider()

    # Complete synthesis
    audio = await tts.synthesize("Hello, I am Kairo.")
    assert len(audio) > 0
    assert audio.startswith(b"RIFF")
    assert "Hello, I am Kairo." in tts.synthesized_texts

    # Stream synthesis
    chunks = []
    async for chunk in tts.stream_synthesize("Short text", chunk_size=20):
        chunks.append(chunk)

    assert len(chunks) > 1
    assert b"".join(chunks) == await tts.synthesize("Short text")


@pytest.mark.asyncio
async def test_mock_tts_provider_failure():
    """Verify MockTTSProvider raises TTSProviderError when simulated."""
    tts = MockTTSProvider(should_fail=True)
    with pytest.raises(TTSProviderError, match="simulated failure"):
        await tts.synthesize("This will fail")


def test_provider_factories_and_unconfigured_error():
    """Verify get_stt_provider and get_tts_provider handle supported and unsupported types."""
    # STT factory
    stt = get_stt_provider("mock")
    assert isinstance(stt, MockSTTProvider)

    with pytest.raises(STTUnavailableError):
        get_stt_provider("unsupported_provider_xyz")

    # TTS factory
    tts = get_tts_provider("mock")
    assert isinstance(tts, MockTTSProvider)

    with pytest.raises(TTSUnavailableError):
        get_tts_provider("unsupported_provider_xyz")
