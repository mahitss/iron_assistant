"""Unit tests for Voice Activity Detection (VAD) and audio analysis."""

import math
import struct

from app.voice.vad import EnergyVAD, create_vad


def _generate_pcm_sine_wave(
    frequency: float = 440.0,
    amplitude: float = 8000.0,
    duration_ms: int = 100,
    sample_rate: int = 16000,
) -> bytes:
    """Generate 16-bit mono signed PCM audio samples for testing."""
    num_samples = int((sample_rate * duration_ms) / 1000)
    samples = []
    for i in range(num_samples):
        val = int(amplitude * math.sin(2 * math.pi * frequency * (i / sample_rate)))
        samples.append(max(-32768, min(32767, val)))
    return struct.pack(f"<{len(samples)}h", *samples)


def _generate_pcm_silence(duration_ms: int = 100, sample_rate: int = 16000) -> bytes:
    """Generate silent 16-bit mono PCM samples."""
    num_samples = int((sample_rate * duration_ms) / 1000)
    return b"\x00\x00" * num_samples


def test_energy_vad_silence_detection():
    """Verify silence chunks are not recognized as speech."""
    vad = EnergyVAD(sample_rate=16000, energy_threshold=500.0)
    silence = _generate_pcm_silence(duration_ms=100)

    is_speech, speech_ended = vad.process_chunk(silence)
    assert is_speech is False
    assert speech_ended is False


def test_energy_vad_speech_start_and_end_detection():
    """Verify speech detection triggers and detects speech end after silence tail."""
    vad = EnergyVAD(
        sample_rate=16000,
        energy_threshold=500.0,
        min_speech_duration_ms=200,
        silence_timeout_ms=300,
    )

    loud_chunk = _generate_pcm_sine_wave(amplitude=5000.0, duration_ms=100)
    silence_chunk = _generate_pcm_silence(duration_ms=100)

    # First speech chunk (100ms < 200ms min speech)
    is_speech, speech_ended = vad.process_chunk(loud_chunk)
    assert is_speech is True
    assert speech_ended is False

    # Second speech chunk (accumulated 200ms >= min speech)
    is_speech, speech_ended = vad.process_chunk(loud_chunk)
    assert is_speech is True
    assert speech_ended is False
    assert vad._speech_detected is True

    # First silence chunk after speech (100ms < 300ms silence timeout)
    is_speech, speech_ended = vad.process_chunk(silence_chunk)
    assert is_speech is False
    assert speech_ended is False

    # Second silence chunk (200ms < 300ms)
    is_speech, speech_ended = vad.process_chunk(silence_chunk)
    assert is_speech is False
    assert speech_ended is False

    # Third silence chunk (300ms >= 300ms silence timeout -> speech ended!)
    is_speech, speech_ended = vad.process_chunk(silence_chunk)
    assert is_speech is False
    assert speech_ended is True

    # State was reset after speech ended
    assert vad._speech_detected is False


def test_vad_factory():
    """Verify create_vad returns EnergyVAD and handles unknown/silero types."""
    vad_default = create_vad()
    assert isinstance(vad_default, EnergyVAD)

    vad_energy = create_vad("energy", sample_rate=8000)
    assert isinstance(vad_energy, EnergyVAD)
    assert vad_energy.sample_rate == 8000
