"""
Rokan Voice — Deep, human, non-robotic synthesis.
Uses edge-tts Microsoft Azure neural voices. No API key needed.
Voice: en-US-ChristopherNeural — smooth baritone authority.
"""

import asyncio
import os
import re
import subprocess
import threading

try:
    import edge_tts
    _HAS_EDGE_TTS = True
except ImportError:
    _HAS_EDGE_TTS = False


class RokanVoice:
    """Non-blocking TTS — fires off speech in a daemon thread."""

    # Best deep-voice options (in order of preference):
    #   en-US-ChristopherNeural  — smooth professional baritone
    #   en-US-GuyNeural          — warm conversational baritone  
    #   en-GB-RyanNeural         — calm British authority
    VOICE = "en-US-ChristopherNeural"
    RATE  = "-8%"     # Slightly slower — more gravity, less robotic rush
    PITCH = "-8Hz"    # Slightly deeper — authority without sounding artificial

    def __init__(self):
        self._lock   = threading.Lock()
        self._thread: threading.Thread | None = None

    @property
    def available(self) -> bool:
        return _HAS_EDGE_TTS

    def speak(self, text: str) -> None:
        """Speak text asynchronously — cancels previous speech if still running."""
        if not _HAS_EDGE_TTS:
            return
        cleaned = self._clean(text)
        if not cleaned.strip():
            return
        # Start new daemon thread — lock inside ensures no overlap
        t = threading.Thread(
            target=self._synthesize_and_play,
            args=(cleaned,),
            daemon=True,
        )
        t.start()
        self._thread = t

    # ── internals ────────────────────────────────────────────────

    @staticmethod
    def _clean(text: str) -> str:
        """Strip markdown/code so TTS reads natural prose, not syntax."""
        # Remove fenced code blocks entirely
        text = re.sub(r"```[\s\S]*?```", "…code block omitted…", text)
        # Remove inline code
        text = re.sub(r"`[^`]+`", "", text)
        # Remove markdown bold/italic/headers/blockquotes
        text = re.sub(r"[*#_~>]", "", text)
        # Remove markdown links but keep the link text
        text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
        # Remove URLs
        text = re.sub(r"https?://\S+", "", text)
        # Remove bullet points / numbered lists markers
        text = re.sub(r"^\s*[-•\d+\.]\s+", "", text, flags=re.MULTILINE)
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text)
        # Truncate long responses — voice reads first 500 chars
        if len(text) > 500:
            # Try to cut at a sentence boundary
            cutoff = text[:500].rfind(".")
            if cutoff > 300:
                text = text[:cutoff + 1]
            else:
                text = text[:500] + "…"
        return text.strip()

    def _synthesize_and_play(self, text: str) -> None:
        with self._lock:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                out = "/tmp/rokan_speech.mp3"
                comm = edge_tts.Communicate(
                    text,
                    self.VOICE,
                    rate=self.RATE,
                    pitch=self.PITCH,
                )
                loop.run_until_complete(comm.save(out))
                loop.close()
                self._play(out)
            except Exception:
                pass

    @staticmethod
    def _play(path: str) -> None:
        """Play audio — tries mpv, ffplay, mpg123 in order."""
        devnull = subprocess.DEVNULL
        for cmd in [
            ["mpv", "--no-terminal", "--no-video", "--volume=90", path],
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path],
            ["mpg123", "-q", path],
            ["aplay", path],
        ]:
            try:
                subprocess.run(cmd, stdout=devnull, stderr=devnull, check=True)
                return
            except (FileNotFoundError, subprocess.CalledProcessError):
                continue
