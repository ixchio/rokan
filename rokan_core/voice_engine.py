"""
Rokan Voice Engine — Full duplex voice loop.

Wake word detection → Speech-to-Text → Agent → Text-to-Speech → Listen again.
This is what makes FRIDAY feel real. Hands-free, always listening.

Dependencies (optional, gracefully degrades):
  pip install sounddevice numpy openwakeword faster-whisper edge-tts
"""

from __future__ import annotations

import asyncio
import io
import os
import queue
import re
import struct
import subprocess
import tempfile
import threading
import time
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

# Lazy imports — all optional
_HAS_SOUNDDEVICE = False
_HAS_NUMPY = False
_HAS_WHISPER = False
_HAS_WAKEWORD = False
_HAS_EDGE_TTS = False
_HAS_WEBRTCVAD = False


def _check_deps():
    global _HAS_SOUNDDEVICE, _HAS_NUMPY, _HAS_WHISPER, _HAS_WAKEWORD, _HAS_EDGE_TTS, _HAS_WEBRTCVAD
    try:
        import sounddevice
        _HAS_SOUNDDEVICE = True
    except ImportError:
        pass
    try:
        import numpy
        _HAS_NUMPY = True
    except ImportError:
        pass
    try:
        from faster_whisper import WhisperModel
        _HAS_WHISPER = True
    except ImportError:
        pass
    try:
        from openwakeword.model import Model as OWWModel
        _HAS_WAKEWORD = True
    except ImportError:
        pass
    try:
        import edge_tts
        _HAS_EDGE_TTS = True
    except ImportError:
        pass
    try:
        import webrtcvad
        _HAS_WEBRTCVAD = True
    except ImportError:
        pass


_check_deps()


@dataclass
class VoiceConfig:
    """Voice engine configuration."""
    wake_word: str = "hey rokan"
    stt_model: str = "base.en"  # faster-whisper model size
    tts_voice: str = "en-US-ChristopherNeural"
    tts_rate: str = "-8%"
    tts_pitch: str = "-8Hz"
    sample_rate: int = 16000
    silence_timeout: float = 1.5  # seconds of silence to stop recording
    max_record_seconds: float = 30.0
    vad_aggressiveness: int = 2  # 0-3, higher = more aggressive filtering


class VoiceEngine:
    """
    Full voice loop: wake word → listen → transcribe → callback → speak.
    Runs entirely in background threads. Non-blocking.
    """

    def __init__(
        self,
        on_transcript: Optional[Callable[[str], None]] = None,
        on_state_change: Optional[Callable[[str], None]] = None,
        config: Optional[VoiceConfig] = None,
    ):
        self.cfg = config or VoiceConfig()
        self._on_transcript = on_transcript  # called with transcribed text
        self._on_state_change = on_state_change  # "idle", "listening", "processing", "speaking"
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._speaking = False
        self._speak_lock = threading.Lock()

        # Lazy-loaded models
        self._whisper_model = None
        self._wakeword_model = None
        self._vad = None

    @property
    def available(self) -> bool:
        """Check if minimum deps are present."""
        return _HAS_SOUNDDEVICE and _HAS_NUMPY

    @property
    def has_stt(self) -> bool:
        return _HAS_WHISPER

    @property
    def has_wake_word(self) -> bool:
        return _HAS_WAKEWORD

    @property
    def has_tts(self) -> bool:
        return _HAS_EDGE_TTS

    def get_status(self) -> dict:
        """Return capability status."""
        return {
            "available": self.available,
            "microphone": _HAS_SOUNDDEVICE,
            "stt": _HAS_WHISPER,
            "tts": _HAS_EDGE_TTS,
            "wake_word": _HAS_WAKEWORD,
            "vad": _HAS_WEBRTCVAD,
            "running": self._running,
        }

    # ── Lifecycle ────────────────────────────────────────────────

    def start(self):
        """Start the voice loop in a background thread."""
        if self._running or not self.available:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="rokan-voice")
        self._thread.start()

    def stop(self):
        """Stop the voice loop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)

    # ── TTS (can be used standalone) ─────────────────────────────

    def speak(self, text: str):
        """Speak text. Blocks until done. Thread-safe."""
        if not _HAS_EDGE_TTS:
            return
        cleaned = self._clean_for_speech(text)
        if not cleaned.strip():
            return
        self._set_state("speaking")
        self._speaking = True
        try:
            self._synthesize_and_play(cleaned)
        finally:
            self._speaking = False
            self._set_state("idle" if not self._running else "listening")

    def speak_async(self, text: str):
        """Speak in background thread."""
        threading.Thread(target=self.speak, args=(text,), daemon=True).start()

    # ── Main Loop ────────────────────────────────────────────────

    def _loop(self):
        """Main voice loop: listen → detect wake/speech → transcribe → callback."""
        import sounddevice as sd
        import numpy as np

        self._set_state("listening")

        # If we have wake word detection, use it
        if _HAS_WAKEWORD:
            self._loop_with_wakeword(sd, np)
        else:
            # Fallback: push-to-talk style via API trigger
            # The loop just waits for external trigger via record_and_transcribe()
            while self._running:
                time.sleep(0.5)

    def _loop_with_wakeword(self, sd, np):
        """Wake word detection loop using openwakeword."""
        from openwakeword.model import Model as OWWModel

        if self._wakeword_model is None:
            self._wakeword_model = OWWModel(
                wakeword_models=["hey_jarvis"],  # closest to "hey rokan"
                inference_framework="onnx",
            )

        chunk_size = 1280  # 80ms at 16kHz
        self._set_state("listening")

        def _audio_callback(indata, frames, time_info, status):
            if self._speaking:
                return
            audio = (indata[:, 0] * 32768).astype(np.int16)
            prediction = self._wakeword_model.predict(audio)

            # Check if any wake word score exceeds threshold
            for mdl_name in self._wakeword_model.prediction_buffer:
                scores = list(self._wakeword_model.prediction_buffer[mdl_name])
                if scores and scores[-1] > 0.5:
                    self._wakeword_model.reset()
                    # Wake word detected — record and transcribe
                    threading.Thread(
                        target=self._handle_voice_input, args=(sd, np),
                        daemon=True
                    ).start()

        try:
            with sd.InputStream(
                samplerate=self.cfg.sample_rate,
                channels=1,
                dtype="float32",
                blocksize=chunk_size,
                callback=_audio_callback,
            ):
                while self._running:
                    time.sleep(0.1)
        except Exception:
            pass

    def _handle_voice_input(self, sd, np):
        """Record speech after wake word, transcribe, and fire callback."""
        self._set_state("listening")

        # Record until silence
        audio_chunks = []
        silence_count = 0
        max_chunks = int(self.cfg.max_record_seconds * self.cfg.sample_rate / 1024)
        silence_threshold = int(self.cfg.silence_timeout * self.cfg.sample_rate / 1024)

        try:
            with sd.InputStream(
                samplerate=self.cfg.sample_rate,
                channels=1,
                dtype="float32",
                blocksize=1024,
            ) as stream:
                for _ in range(max_chunks):
                    if not self._running:
                        break
                    data, _ = stream.read(1024)
                    audio_chunks.append(data.copy())

                    # Simple energy-based VAD
                    energy = np.abs(data).mean()
                    if energy < 0.01:
                        silence_count += 1
                        if silence_count > silence_threshold:
                            break
                    else:
                        silence_count = 0

        except Exception:
            self._set_state("listening")
            return

        if not audio_chunks:
            self._set_state("listening")
            return

        # Concatenate and transcribe
        audio = np.concatenate(audio_chunks, axis=0).flatten()
        self._set_state("processing")
        text = self._transcribe(audio)

        if text and text.strip():
            if self._on_transcript:
                self._on_transcript(text.strip())

        self._set_state("listening")

    # ── API-triggered recording (for button press in UI) ─────────

    def record_and_transcribe(self, duration: float = 5.0) -> str:
        """Record for duration seconds and return transcript. Blocking."""
        if not self.available or not _HAS_WHISPER:
            return ""

        import sounddevice as sd
        import numpy as np

        self._set_state("listening")
        try:
            audio = sd.rec(
                int(duration * self.cfg.sample_rate),
                samplerate=self.cfg.sample_rate,
                channels=1,
                dtype="float32",
            )
            sd.wait()
            self._set_state("processing")
            text = self._transcribe(audio.flatten())
            return text or ""
        except Exception:
            return ""
        finally:
            self._set_state("idle")

    # ── STT ──────────────────────────────────────────────────────

    def _transcribe(self, audio_np) -> str:
        """Transcribe numpy audio array to text using faster-whisper."""
        if not _HAS_WHISPER:
            return ""

        try:
            from faster_whisper import WhisperModel

            if self._whisper_model is None:
                self._whisper_model = WhisperModel(
                    self.cfg.stt_model,
                    device="cpu",
                    compute_type="int8",
                )

            segments, _ = self._whisper_model.transcribe(
                audio_np,
                language="en",
                beam_size=3,
                vad_filter=True,
            )

            text = " ".join(seg.text for seg in segments)
            return text.strip()
        except Exception:
            return ""

    # ── TTS internals ────────────────────────────────────────────

    def _synthesize_and_play(self, text: str):
        """Synthesize and play audio using edge-tts."""
        with self._speak_lock:
            try:
                import edge_tts

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                out = "/tmp/rokan_speech.mp3"
                comm = edge_tts.Communicate(
                    text,
                    self.cfg.tts_voice,
                    rate=self.cfg.tts_rate,
                    pitch=self.cfg.tts_pitch,
                )
                loop.run_until_complete(comm.save(out))
                loop.close()
                self._play_audio(out)
            except Exception:
                pass

    @staticmethod
    def _play_audio(path: str):
        """Play audio file. Tries multiple players."""
        null = subprocess.DEVNULL
        for cmd in [
            ["mpv", "--no-terminal", "--no-video", "--volume=90", path],
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path],
            ["mpg123", "-q", path],
            ["aplay", path],
        ]:
            try:
                subprocess.run(cmd, stdout=null, stderr=null, check=True, timeout=30)
                return
            except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
                continue

    @staticmethod
    def _clean_for_speech(text: str) -> str:
        """Strip markdown/code for natural speech."""
        text = re.sub(r"```[\s\S]*?```", " code block omitted ", text)
        text = re.sub(r"`[^`]+`", "", text)
        text = re.sub(r"[*#_~>]", "", text)
        text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
        text = re.sub(r"https?://\S+", "", text)
        text = re.sub(r"^\s*[-•\d+\.]\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"\s+", " ", text)
        if len(text) > 500:
            cutoff = text[:500].rfind(".")
            text = text[:cutoff + 1] if cutoff > 300 else text[:500] + "..."
        return text.strip()

    def _set_state(self, state: str):
        if self._on_state_change:
            try:
                self._on_state_change(state)
            except Exception:
                pass
