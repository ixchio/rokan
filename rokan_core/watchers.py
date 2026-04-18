"""
Rokan Watchers — Clipboard intelligence + file/build watching.

Clipboard: detects when you copy errors, URLs, code.
  "I see you copied a Python traceback. Want me to debug it?"
  "Want me to open that URL or summarize the page?"

File watcher: detects builds finishing, test results, config changes.
  "Your build just finished — 0 errors, 3 warnings."
  "Tests passed: 47/47."
"""

from __future__ import annotations

import os
import re
import subprocess
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional


@dataclass
class ClipboardEvent:
    """Emitted when clipboard content changes and is interesting."""
    type: str  # "error", "url", "code", "path", "json", "text"
    content: str
    suggestion: str  # what Rokan could do about it
    timestamp: datetime


@dataclass
class FileEvent:
    """Emitted when a watched file/directory changes."""
    type: str  # "modified", "created", "deleted", "build_done"
    path: str
    details: str
    timestamp: datetime


class ClipboardWatcher:
    """
    Watches clipboard for interesting content. Fires events when you copy:
    - Python/JS tracebacks → offer to debug
    - URLs → offer to open or summarize
    - File paths → offer to open or show contents
    - JSON → offer to format or analyze
    - Shell errors → offer to fix
    """

    def __init__(self, on_event: Optional[Callable[[ClipboardEvent], None]] = None):
        self._on_event = on_event
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_content: str = ""
        self._last_check: float = 0

    def start(self, interval: float = 2.0):
        if self._running:
            return
        self._running = True
        self._interval = interval
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)

    def _loop(self):
        while self._running:
            try:
                self._check()
            except Exception:
                pass
            time.sleep(self._interval)

    def _check(self):
        content = self._get_clipboard()
        if not content or content == self._last_content:
            return
        self._last_content = content

        event = self._analyze(content)
        if event and self._on_event:
            self._on_event(event)

    def _get_clipboard(self) -> str:
        try:
            r = subprocess.run(
                ["xclip", "-selection", "clipboard", "-o"],
                capture_output=True, text=True, timeout=2,
            )
            return r.stdout[:5000] if r.returncode == 0 else ""
        except Exception:
            return ""

    def _analyze(self, content: str) -> Optional[ClipboardEvent]:
        """Analyze clipboard content and classify it."""
        content = content.strip()
        if len(content) < 5:
            return None

        now = datetime.now()

        # Python traceback
        if "Traceback (most recent call last):" in content or re.search(r'File ".*", line \d+', content):
            # Extract the error type
            lines = content.strip().splitlines()
            error_line = lines[-1] if lines else ""
            return ClipboardEvent(
                type="error",
                content=content,
                suggestion=f"Looks like a Python error: {error_line[:80]}. Want me to debug it?",
                timestamp=now,
            )

        # JavaScript/Node error
        if re.search(r'(TypeError|ReferenceError|SyntaxError|Error):', content) and ("at " in content or "node_modules" in content):
            return ClipboardEvent(
                type="error",
                content=content,
                suggestion="Looks like a JS/Node error. Want me to analyze it?",
                timestamp=now,
            )

        # Shell command error
        if re.search(r'(command not found|Permission denied|No such file|segmentation fault)', content, re.IGNORECASE):
            return ClipboardEvent(
                type="error",
                content=content,
                suggestion="Looks like a shell error. Want me to help fix it?",
                timestamp=now,
            )

        # URL
        if re.match(r'https?://\S+$', content):
            return ClipboardEvent(
                type="url",
                content=content,
                suggestion=f"Want me to open {content[:60]} or summarize the page?",
                timestamp=now,
            )

        # File path
        if content.startswith("/") and len(content) < 256 and "\n" not in content:
            if os.path.exists(content):
                if os.path.isdir(content):
                    return ClipboardEvent(
                        type="path",
                        content=content,
                        suggestion=f"That's a directory. Want me to list what's in {content}?",
                        timestamp=now,
                    )
                return ClipboardEvent(
                    type="path",
                    content=content,
                    suggestion=f"Want me to open or show the contents of {os.path.basename(content)}?",
                    timestamp=now,
                )

        # JSON
        if (content.startswith("{") or content.startswith("[")) and len(content) > 20:
            try:
                import json
                json.loads(content)
                return ClipboardEvent(
                    type="json",
                    content=content,
                    suggestion="Copied JSON. Want me to format or analyze it?",
                    timestamp=now,
                )
            except (json.JSONDecodeError, ValueError):
                pass

        # Code block (has indentation + keywords)
        code_keywords = ["def ", "class ", "import ", "function ", "const ", "let ", "var ", "if ", "for ", "while "]
        if any(kw in content for kw in code_keywords) and "\n" in content:
            lines = content.count("\n")
            return ClipboardEvent(
                type="code",
                content=content,
                suggestion=f"Copied {lines} lines of code. Want me to review or explain it?",
                timestamp=now,
            )

        return None


class FileWatcher:
    """
    Watch directories for file changes. Detects:
    - Build outputs finishing
    - Test results appearing
    - Config file changes
    """

    def __init__(self, on_event: Optional[Callable[[FileEvent], None]] = None):
        self._on_event = on_event
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._watches: dict[str, float] = {}  # path -> last mtime

    def watch(self, path: str):
        """Add a path to watch."""
        p = os.path.expanduser(path)
        if os.path.exists(p):
            self._watches[p] = os.path.getmtime(p)

    def start(self, interval: float = 3.0):
        if self._running:
            return
        self._running = True
        self._interval = interval
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)

    def _loop(self):
        while self._running:
            try:
                self._check()
            except Exception:
                pass
            time.sleep(self._interval)

    def _check(self):
        for path, last_mtime in list(self._watches.items()):
            try:
                current_mtime = os.path.getmtime(path)
                if current_mtime > last_mtime:
                    self._watches[path] = current_mtime
                    self._fire_change(path)
            except FileNotFoundError:
                pass

    def _fire_change(self, path: str):
        if not self._on_event:
            return

        name = os.path.basename(path)
        now = datetime.now()

        # Detect build artifacts
        build_names = ["build.log", "compile_commands.json", ".build", "dist", "target"]
        if any(b in name for b in build_names):
            self._on_event(FileEvent(
                type="build_done", path=path,
                details=f"Build output changed: {name}",
                timestamp=now,
            ))
            return

        # Detect test results
        test_names = ["test-results", "junit", ".coverage", "pytest", "jest"]
        if any(t in name.lower() for t in test_names):
            self._on_event(FileEvent(
                type="build_done", path=path,
                details=f"Test results updated: {name}",
                timestamp=now,
            ))
            return

        self._on_event(FileEvent(
            type="modified", path=path,
            details=f"{name} was modified",
            timestamp=now,
        ))
