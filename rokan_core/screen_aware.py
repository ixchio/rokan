"""
Rokan Screen Awareness — Knows what you're doing RIGHT NOW.

Tracks active window, detects user state (coding/browsing/idle/gaming),
periodic screen capture + OCR. This context gets injected into every
LLM call so Rokan can see what you see.

Zero dependencies beyond subprocess — uses xdotool, xprop, xprintidle.
"""

from __future__ import annotations

import subprocess
import shutil
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class ScreenState:
    """Current state of the user's screen/activity."""
    active_window: str = ""
    window_class: str = ""
    user_state: str = "unknown"  # coding, browsing, terminal, media, gaming, idle, desktop
    idle_seconds: int = 0
    last_updated: str = ""
    recent_windows: list[str] = field(default_factory=list)
    screen_text: str = ""  # OCR of last screenshot


# State detection rules
_STATE_RULES = {
    "coding": [
        "code", "vscode", "visual studio", "sublime", "atom", "vim", "nvim",
        "neovim", "emacs", "jetbrains", "intellij", "pycharm", "webstorm",
        "android studio", "eclipse", "gedit", "kate", "nano",
    ],
    "terminal": [
        "terminal", "konsole", "gnome-terminal", "alacritty", "kitty",
        "tilix", "terminator", "xterm", "urxvt", "wezterm", "foot",
    ],
    "browsing": [
        "firefox", "chrome", "chromium", "brave", "edge", "opera",
        "vivaldi", "librewolf", "qutebrowser", "epiphany",
    ],
    "media": [
        "spotify", "vlc", "mpv", "totem", "rhythmbox", "audacious",
        "youtube", "netflix", "twitch", "celluloid",
    ],
    "gaming": [
        "steam", "lutris", "wine", "proton", "gamemode", "mangohud",
    ],
    "files": [
        "nautilus", "thunar", "dolphin", "nemo", "caja", "pcmanfm",
    ],
    "chat": [
        "discord", "slack", "telegram", "element", "signal",
    ],
}


class ScreenAwareness:
    """
    Background thread that tracks what the user is doing.
    Provides context for the agent to be genuinely aware.
    """

    def __init__(self, interval: float = 5.0, ocr_interval: float = 60.0):
        self._interval = interval
        self._ocr_interval = ocr_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._state = ScreenState()
        self._lock = threading.Lock()
        self._last_ocr = 0.0
        self._window_history: list[str] = []

    @property
    def state(self) -> ScreenState:
        with self._lock:
            return ScreenState(
                active_window=self._state.active_window,
                window_class=self._state.window_class,
                user_state=self._state.user_state,
                idle_seconds=self._state.idle_seconds,
                last_updated=self._state.last_updated,
                recent_windows=list(self._state.recent_windows),
                screen_text=self._state.screen_text,
            )

    def build_context(self) -> str:
        """Build a context string for LLM injection."""
        s = self.state
        if not s.active_window and s.user_state == "unknown":
            return ""

        parts = []
        if s.active_window:
            parts.append(f"active window: {s.active_window}")
        if s.user_state != "unknown":
            parts.append(f"user is: {s.user_state}")
        if s.idle_seconds > 60:
            mins = s.idle_seconds // 60
            parts.append(f"idle for {mins} min")
        if s.recent_windows:
            unique = list(dict.fromkeys(s.recent_windows[-5:]))
            parts.append(f"recent: {', '.join(unique)}")

        if not parts:
            return ""
        return "[SCREEN CONTEXT] " + " | ".join(parts)

    # ── Lifecycle ────────────────────────────────────────────────

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="rokan-screen")
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)

    # ── Main Loop ────────────────────────────────────────────────

    def _loop(self):
        while self._running:
            try:
                self._update()
            except Exception:
                pass
            time.sleep(self._interval)

    def _update(self):
        with self._lock:
            # Active window
            window_name = self._get_active_window()
            window_class = self._get_window_class()

            self._state.active_window = window_name
            self._state.window_class = window_class
            self._state.last_updated = datetime.now().isoformat()

            # Track window history
            if window_name and window_name not in ("Desktop", ""):
                self._window_history.append(window_name)
                if len(self._window_history) > 50:
                    self._window_history = self._window_history[-50:]
                self._state.recent_windows = self._window_history[-10:]

            # Detect user state
            self._state.user_state = self._detect_state(window_name, window_class)

            # Idle time
            self._state.idle_seconds = self._get_idle_seconds()

            # Periodic OCR (expensive, do rarely)
            now = time.time()
            if now - self._last_ocr > self._ocr_interval:
                self._last_ocr = now
                self._state.screen_text = self._do_ocr()

    def _detect_state(self, window: str, wclass: str) -> str:
        """Detect what the user is doing based on window info."""
        combined = f"{window} {wclass}".lower()

        # Check idle first
        idle = self._get_idle_seconds()
        if idle > 300:  # 5 minutes
            return "idle"

        for state, keywords in _STATE_RULES.items():
            if any(kw in combined for kw in keywords):
                return state

        if not window or window in ("Desktop", ""):
            return "desktop"

        return "other"

    # ── System Queries ───────────────────────────────────────────

    @staticmethod
    def _get_active_window() -> str:
        """Get the active window title."""
        # Try xdotool first (most common)
        if shutil.which("xdotool"):
            try:
                r = subprocess.run(
                    "xdotool getactivewindow getwindowname 2>/dev/null",
                    shell=True, capture_output=True, text=True, timeout=3,
                )
                if r.returncode == 0 and r.stdout.strip():
                    return r.stdout.strip()
            except Exception:
                pass

        # Fallback: xprop
        if shutil.which("xprop"):
            try:
                r = subprocess.run(
                    "xprop -root _NET_ACTIVE_WINDOW 2>/dev/null | grep -o '0x[0-9a-f]*' | tail -1",
                    shell=True, capture_output=True, text=True, timeout=3,
                )
                wid = r.stdout.strip()
                if wid:
                    r2 = subprocess.run(
                        f"xprop -id {wid} _NET_WM_NAME 2>/dev/null",
                        shell=True, capture_output=True, text=True, timeout=3,
                    )
                    if '"' in r2.stdout:
                        return r2.stdout.split('"')[1]
            except Exception:
                pass

        return ""

    @staticmethod
    def _get_window_class() -> str:
        """Get the WM_CLASS of active window."""
        if not shutil.which("xdotool"):
            return ""
        try:
            wid = subprocess.run(
                "xdotool getactivewindow 2>/dev/null",
                shell=True, capture_output=True, text=True, timeout=3,
            )
            if wid.returncode != 0:
                return ""
            r = subprocess.run(
                f"xprop -id {wid.stdout.strip()} WM_CLASS 2>/dev/null",
                shell=True, capture_output=True, text=True, timeout=3,
            )
            if '"' in r.stdout:
                parts = r.stdout.split('"')
                return parts[3] if len(parts) > 3 else parts[1]
        except Exception:
            pass
        return ""

    @staticmethod
    def _get_idle_seconds() -> int:
        """Get user idle time in seconds."""
        if shutil.which("xprintidle"):
            try:
                r = subprocess.run(
                    "xprintidle 2>/dev/null",
                    shell=True, capture_output=True, text=True, timeout=3,
                )
                if r.returncode == 0:
                    return int(r.stdout.strip()) // 1000  # ms → seconds
            except Exception:
                pass

        # Fallback: check /proc/stat for rough idle estimate
        return 0

    @staticmethod
    def _do_ocr() -> str:
        """Take a screenshot and OCR it. Expensive — called rarely."""
        if not shutil.which("tesseract"):
            return ""

        tmp_img = "/tmp/rokan_screen_ocr.png"

        # Take screenshot
        for cmd in [
            f"scrot -o {tmp_img}",
            f"gnome-screenshot -f {tmp_img}",
            f"maim {tmp_img}",
            f"import -window root {tmp_img}",
        ]:
            tool = cmd.split()[0]
            if shutil.which(tool):
                try:
                    subprocess.run(cmd, shell=True, capture_output=True, timeout=10)
                    if Path(tmp_img).exists():
                        break
                except Exception:
                    continue
        else:
            return ""

        if not Path(tmp_img).exists():
            return ""

        # OCR
        try:
            r = subprocess.run(
                f"tesseract {tmp_img} stdout 2>/dev/null",
                shell=True, capture_output=True, text=True, timeout=15,
            )
            text = r.stdout.strip()
            # Cleanup
            try:
                Path(tmp_img).unlink()
            except Exception:
                pass
            return text[:2000] if text else ""
        except Exception:
            return ""
