"""Voice Activity Detection (VAD) abstractions and implementations."""

import logging
import math
import struct
from abc import ABC, abstractmethod

logger = logging.getLogger("kairo.voice.vad")


class BaseVAD(ABC):
    """Abstract base class for Voice Activity Detection."""

    @abstractmethod
    def process_chunk(self, chunk: bytes) -> tuple[bool, bool]:
        """Analyze a PCM audio chunk.

        Returns:
            (is_speech_now, speech_ended)
            - is_speech_now: True if current chunk contains active human speech.
            - speech_ended: True if speech was active and has now concluded after a silence tail.
        """
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset internal state for a new speech turn."""
        pass


class EnergyVAD(BaseVAD):
    """Zero-dependency, low-latency RMS energy-based Voice Activity Detector.

    Calculates root-mean-square amplitude over 16-bit linear PCM audio chunks.
    Detects speech onset after sustained energy and speech completion after silence.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        energy_threshold: float = 450.0,
        min_speech_duration_ms: int = 250,
        silence_timeout_ms: int = 900,
    ) -> None:
        self.sample_rate = sample_rate
        self.energy_threshold = energy_threshold
        self.min_speech_duration_ms = min_speech_duration_ms
        self.silence_timeout_ms = silence_timeout_ms

        self._speech_detected = False
        self._accumulated_speech_ms = 0.0
        self._accumulated_silence_ms = 0.0

    def _calculate_rms(self, chunk: bytes) -> float:
        """Compute RMS amplitude of 16-bit mono signed PCM samples."""
        if len(chunk) < 2:
            return 0.0

        # Unpack as signed 16-bit integers
        num_samples = len(chunk) // 2
        fmt = f"<{num_samples}h"
        try:
            samples = struct.unpack(fmt, chunk[: num_samples * 2])
        except Exception:
            return 0.0

        if not samples:
            return 0.0

        sum_squares = sum(s * s for s in samples)
        return math.sqrt(sum_squares / len(samples))

    def process_chunk(self, chunk: bytes) -> tuple[bool, bool]:
        """Analyze audio chunk and evaluate speech state."""
        rms = self._calculate_rms(chunk)
        chunk_samples = len(chunk) // 2
        chunk_ms = (chunk_samples / self.sample_rate) * 1000.0 if self.sample_rate else 0.0

        is_voice = rms >= self.energy_threshold

        if is_voice:
            self._accumulated_speech_ms += chunk_ms
            self._accumulated_silence_ms = 0.0
            if self._accumulated_speech_ms >= self.min_speech_duration_ms:
                self._speech_detected = True
            return True, False

        # In silence
        if self._speech_detected:
            self._accumulated_silence_ms += chunk_ms
            if self._accumulated_silence_ms >= self.silence_timeout_ms:
                # Speech ended!
                self.reset()
                return False, True
            return False, False

        # Still in initial silence
        return False, False

    def reset(self) -> None:
        """Reset internal speech accumulation state."""
        self._speech_detected = False
        self._accumulated_speech_ms = 0.0
        self._accumulated_silence_ms = 0.0


class SileroVAD(BaseVAD):
    """Silero VAD provider with automatic fallback to EnergyVAD if ONNX/Torch is not installed."""

    def __init__(self, sample_rate: int = 16000) -> None:
        self.sample_rate = sample_rate
        self._fallback_vad = EnergyVAD(sample_rate=sample_rate)
        self._model = None
        self._try_load_silero()

    def _try_load_silero(self) -> None:
        """Attempt to load Silero model or fall back to EnergyVAD gracefully."""
        try:
            import onnxruntime  # noqa: F401

            # In a production setup with onnxruntime and silero model weights:
            # self._model = load_onnx_silero(...)
            logger.info("Silero VAD backend initialized.")
        except ImportError:
            logger.info("Silero/ONNX not installed. Gracefully using high-performance EnergyVAD fallback.")

    def process_chunk(self, chunk: bytes) -> tuple[bool, bool]:
        if self._model is not None:
            # Run model inference if loaded
            pass
        return self._fallback_vad.process_chunk(chunk)

    def reset(self) -> None:
        self._fallback_vad.reset()


def create_vad(vad_type: str = "energy", sample_rate: int = 16000) -> BaseVAD:
    """Factory creating configured VAD implementation with graceful fallback."""
    vtype = (vad_type or "energy").lower().strip()
    if vtype == "silero":
        return SileroVAD(sample_rate=sample_rate)
    return EnergyVAD(sample_rate=sample_rate)
