"""
Rokan Desktop Skills — The stuff that makes it FRIDAY, not a chatbot.

Shell execution, app launching, file ops, screenshots, clipboard,
reminders, network tools, notifications. All real. All Linux-native.
"""

from __future__ import annotations

import datetime
import os
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from rokan_core.skills import Skill, SkillResult


# ── Shell Execution ────────────────────────────────────────────────

class ShellSkill(Skill):
    """Execute terminal commands. The core of system control."""
    name = "shell"
    description = "Run terminal commands and return output"
    triggers = [
        "run", "execute", "terminal", "command", "shell", "bash",
        "sudo", "apt", "pip", "git", "ls", "cat", "grep",
        "mkdir", "rm", "mv", "cp", "chmod", "chown",
        "install", "update", "upgrade",
    ]
    priority = 80

    # commands that need explicit confirmation
    DANGEROUS = {"rm -rf", "mkfs", "dd if=", "> /dev/", ":(){ :|:& };:"}

    def can_handle(self, query: str) -> float:
        q = query.lower().strip()
        if q.startswith("/run ") or q.startswith("/shell ") or q.startswith("/exec "):
            return 1.0
        # "run <something>" is almost certainly a shell request
        if q.startswith("run ") or q.startswith("execute "):
            return 0.9
        return super().can_handle(q)

    def execute(self, query: str, context: dict) -> SkillResult:
        cmd = query.strip()

        # Strip prefixes (slash and natural language)
        for prefix in ("/run ", "/shell ", "/exec ", "run ", "execute "):
            if cmd.lower().startswith(prefix):
                cmd = cmd[len(prefix):]
                break

        if not cmd:
            return SkillResult(content="no command given", display_raw=True)

        # Safety check
        for d in self.DANGEROUS:
            if d in cmd.lower():
                return SkillResult(
                    content=f"blocked: '{cmd}' looks dangerous. use /run --force <cmd> to override.",
                    display_raw=True,
                )

        # Force override
        if cmd.startswith("--force "):
            cmd = cmd[8:]

        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                timeout=30, cwd=str(Path.home()),
            )
            output = result.stdout.strip()
            err = result.stderr.strip()
            code = result.returncode

            parts = []
            if output:
                parts.append(output)
            if err:
                parts.append(f"stderr: {err}")
            if code != 0:
                parts.append(f"exit code: {code}")

            text = "\n".join(parts) if parts else "(no output)"
            return SkillResult(
                content=f"$ {cmd}\n{text}",
                display_raw=True,
            )
        except subprocess.TimeoutExpired:
            return SkillResult(content=f"$ {cmd}\ntimed out after 30s", display_raw=True)
        except Exception as e:
            return SkillResult(content=f"$ {cmd}\nerror: {e}", display_raw=True)


# ── App Launcher ───────────────────────────────────────────────────

class AppLauncherSkill(Skill):
    """Open applications by name. Scans .desktop files — knows every app on your system."""
    name = "launch"
    description = "Open desktop applications"
    triggers = [
        "open", "launch", "start", "run app",
        "firefox", "chrome", "terminal", "files", "vscode",
        "code", "nautilus", "spotify", "discord", "steam",
    ]
    priority = 75

    # Quick aliases for common apps (checked first, before .desktop scan)
    _QUICK = {
        "terminal": "x-terminal-emulator",
        "files": "xdg-open ~",
        "file manager": "xdg-open ~",
        "vscode": "code",
        "vs code": "code",
        "settings": "gnome-control-center",
        "text editor": "xdg-open",
    }

    # App-specific flags/modifiers
    _APP_FLAGS = {
        "firefox":         {"new tab": "--new-tab", "private": "--private-window", "incognito": "--private-window"},
        "google-chrome":   {"new tab": "--new-window", "private": "--incognito", "incognito": "--incognito"},
        "chromium":        {"new tab": "--new-window", "private": "--incognito", "incognito": "--incognito"},
        "brave-browser":   {"new tab": "--new-window", "private": "--incognito", "incognito": "--incognito"},
        "brave":           {"new tab": "--new-window", "private": "--incognito", "incognito": "--incognito"},
    }

    # Words that are modifiers, not part of the app name
    _MODIFIERS = ["new tab", "new window", "private", "incognito", "private window",
                  "in private", "private mode", "fullscreen", "maximized"]

    def __init__(self):
        super().__init__()
        self._desktop_cache: list[dict] | None = None

    def can_handle(self, query: str) -> float:
        q = query.lower().strip()
        if q.startswith("/open ") or q.startswith("/launch "):
            return 1.0
        if any(w in q for w in ["open ", "launch ", "start ", "go to ", "browse "]):
            return 0.85
        # URL detection
        if re.search(r'https?://|www\.|\.\w{2,4}/', q):
            return 0.8
        return super().can_handle(q) * 0.3

    def execute(self, query: str, context: dict) -> SkillResult:
        q = query.lower().strip()
        for prefix in ("/open ", "/launch ", "open ", "launch ", "start ", "go to ", "browse "):
            if q.startswith(prefix):
                q = q[len(prefix):]
                break

        raw_input = q.strip()
        if not raw_input:
            return SkillResult(content="what do you want to open?", display_raw=True)

        # Extract URL if present
        url_match = re.search(r'(https?://\S+|www\.\S+)', raw_input)
        url = url_match.group(1) if url_match else None
        if url and not url.startswith("http"):
            url = "https://" + url

        # Separate app name from modifiers
        app_name, modifiers = self._parse_modifiers(raw_input)

        # If it's just a URL with no app specified, open with default browser
        if url and not app_name:
            return self._launch(f"xdg-open {url}", url)

        # 1) Quick alias match
        for alias, cmd in self._QUICK.items():
            if alias in app_name:
                return self._launch(cmd, alias)

        # 2) Scan .desktop files for fuzzy match
        match = self._find_desktop_app(app_name)
        if match:
            cmd = match["exec"]
            cmd = self._apply_flags(cmd, match["name"], modifiers, url)
            return self._launch(cmd, match["name"])

        # 3) Try as direct binary name
        for binary in [app_name.replace(" ", "-"), app_name.replace(" ", ""), app_name.split()[0]]:
            if shutil.which(binary):
                cmd = self._apply_flags(binary, binary, modifiers, url)
                return self._launch(cmd, app_name)

        # 4) If there's a URL, just open it with xdg-open
        if url:
            return self._launch(f"xdg-open {url}", url)

        # 5) Nothing found — suggest similar apps
        suggestions = self._suggest(app_name)
        msg = f"can't find '{app_name}'"
        if suggestions:
            msg += ". did you mean:\n" + "\n".join(f"  {s}" for s in suggestions[:5])
        return SkillResult(content=msg, display_raw=True)

    def _parse_modifiers(self, raw: str) -> tuple[str, list[str]]:
        """Separate 'firefox new tab' into ('firefox', ['new tab'])."""
        found = []
        cleaned = raw
        for mod in sorted(self._MODIFIERS, key=len, reverse=True):
            if mod in cleaned:
                found.append(mod)
                cleaned = cleaned.replace(mod, "").strip()
        # Remove stray "in", "a", "with" left over
        cleaned = re.sub(r'\b(in|a|an|the|with|and|my)\b', '', cleaned).strip()
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        # Also remove URL from app name
        cleaned = re.sub(r'https?://\S+|www\.\S+', '', cleaned).strip()
        return cleaned, found

    def _apply_flags(self, cmd: str, app_name: str, modifiers: list[str], url: str | None) -> str:
        """Apply modifiers like 'new tab', 'private' as CLI flags."""
        # Find which app family this belongs to
        app_lower = app_name.lower()
        cmd_base = cmd.split()[0] if cmd else ""

        for app_key, flags in self._APP_FLAGS.items():
            if app_key in app_lower or app_key in cmd_base:
                for mod in modifiers:
                    if mod in flags:
                        cmd += f" {flags[mod]}"
                break

        if url:
            cmd += f" {url}"

        return cmd

    def _launch(self, cmd: str, name: str) -> SkillResult:
        try:
            subprocess.Popen(
                cmd, shell=True,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return SkillResult(content=f"opened {name}", display_raw=True)
        except Exception as e:
            return SkillResult(content=f"failed to open {name}: {e}", display_raw=True)

    def _find_desktop_app(self, query: str) -> dict | None:
        """Search .desktop files for matching app. Fuzzy matching."""
        apps = self._scan_desktop_files()
        q = query.lower()
        q_words = set(q.split())

        best = None
        best_score = 0

        for app in apps:
            name_lower = app["name"].lower()
            # Exact name match
            if q == name_lower:
                return app
            # Query is substring of name
            if q in name_lower:
                score = len(q) / len(name_lower) + 0.5
                if score > best_score:
                    best_score = score
                    best = app
            # Name is substring of query
            if name_lower in q:
                score = len(name_lower) / len(q) + 0.4
                if score > best_score:
                    best_score = score
                    best = app
            # Word overlap
            name_words = set(name_lower.split())
            overlap = q_words & name_words
            if overlap:
                score = len(overlap) / max(len(q_words), len(name_words))
                if score > best_score:
                    best_score = score
                    best = app
            # Check keywords/generic name
            if q in app.get("generic", "").lower() or q in app.get("keywords", "").lower():
                if 0.4 > best_score:
                    best_score = 0.4
                    best = app

        return best if best_score > 0.3 else None

    def _suggest(self, query: str) -> list[str]:
        """Find similar app names for suggestions."""
        apps = self._scan_desktop_files()
        q = query.lower()
        scored = []
        for app in apps:
            name = app["name"].lower()
            # Simple: any word overlap or substring
            if any(w in name for w in q.split()) or any(w in q for w in name.split()):
                scored.append(app["name"])
        return scored[:5]

    def _scan_desktop_files(self) -> list[dict]:
        """Scan all .desktop files and cache results."""
        if self._desktop_cache is not None:
            return self._desktop_cache

        apps = []
        dirs = [
            Path("/usr/share/applications"),
            Path("/usr/local/share/applications"),
            Path.home() / ".local" / "share" / "applications",
            Path("/var/lib/flatpak/exports/share/applications"),
            Path.home() / ".local" / "share" / "flatpak" / "exports" / "share" / "applications",
            Path("/snap") if Path("/snap").exists() else None,
        ]

        seen = set()
        for d in dirs:
            if d is None or not d.exists():
                continue
            for f in d.glob("*.desktop"):
                if f.name in seen:
                    continue
                seen.add(f.name)
                try:
                    app = self._parse_desktop_file(f)
                    if app and not app.get("hidden"):
                        apps.append(app)
                except Exception:
                    continue

        self._desktop_cache = apps
        return apps

    @staticmethod
    def _parse_desktop_file(path: Path) -> dict | None:
        """Parse a .desktop file into {name, exec, generic, keywords, hidden}."""
        data = {"name": "", "exec": "", "generic": "", "keywords": "", "hidden": False}
        try:
            in_entry = False
            for line in path.read_text(errors="replace").splitlines():
                line = line.strip()
                if line == "[Desktop Entry]":
                    in_entry = True
                    continue
                if line.startswith("[") and in_entry:
                    break  # next section
                if not in_entry or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip()
                if key == "Name" and not data["name"]:
                    data["name"] = val
                elif key == "Exec" and not data["exec"]:
                    # Clean exec: remove %u, %f, %U, %F etc.
                    data["exec"] = _RE_DESKTOP_FIELD_CODES.sub("", val).strip()
                elif key == "GenericName":
                    data["generic"] = val
                elif key == "Keywords":
                    data["keywords"] = val
                elif key == "NoDisplay" and val.lower() == "true":
                    data["hidden"] = True
                elif key == "Hidden" and val.lower() == "true":
                    data["hidden"] = True
                elif key == "Type" and val != "Application":
                    return None
        except Exception:
            return None

        if not data["name"] or not data["exec"]:
            return None
        return data


_RE_DESKTOP_FIELD_CODES = re.compile(r'\s*%[uUfFdDnNickvm]\b')


# ── File Operations ────────────────────────────────────────────────

class FileSkill(Skill):
    """Find, search, and manage files."""
    name = "files"
    description = "Find and manage files on the system"
    triggers = [
        "find file", "search file", "where is", "locate",
        "file size", "how big", "disk usage", "largest files",
        "recent files", "downloads", "documents",
    ]
    priority = 65

    def can_handle(self, query: str) -> float:
        q = query.lower()
        if q.startswith("/find ") or q.startswith("/files "):
            return 1.0
        if any(p in q for p in ["find file", "search file", "where is", "disk usage", "largest file",
                                 "recent file", "recent download", "my downloads", "what's in"]):
            return 0.85
        return super().can_handle(q)

    def execute(self, query: str, context: dict) -> SkillResult:
        q = query.lower().strip()
        for prefix in ("/find ", "/files "):
            if q.startswith(prefix):
                q = q[len(prefix):]
                break

        home = str(Path.home())

        # Recent files
        if any(w in q for w in ["recent", "latest", "last downloaded", "newest"]):
            target = Path.home() / "Downloads"
            if not target.exists():
                target = Path.home()
            try:
                files = sorted(target.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
                files = [f for f in files[:15] if not f.name.startswith(".")]
                lines = []
                for f in files:
                    size = f.stat().st_size
                    mtime = datetime.datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                    sz = f"{size / 1024 / 1024:.1f}MB" if size > 1024*1024 else f"{size / 1024:.0f}KB"
                    lines.append(f"  {mtime}  {sz:>8}  {f.name}")
                text = f"recent files in {target}:\n" + "\n".join(lines)
                return SkillResult(content=text, inject_as_context=True)
            except Exception as e:
                return SkillResult(content=f"error listing files: {e}", display_raw=True)

        # Largest files
        if any(w in q for w in ["largest", "biggest", "heavy", "taking space"]):
            try:
                result = subprocess.run(
                    f"find {home} -maxdepth 4 -type f -size +50M 2>/dev/null | head -20 | xargs ls -lhS 2>/dev/null",
                    shell=True, capture_output=True, text=True, timeout=15,
                )
                text = result.stdout.strip() or "no files larger than 50MB found"
                return SkillResult(content=f"largest files:\n{text}", inject_as_context=True)
            except Exception as e:
                return SkillResult(content=f"error: {e}", display_raw=True)

        # Disk usage summary
        if any(w in q for w in ["disk usage", "how big", "folder size", "space"]):
            try:
                result = subprocess.run(
                    f"du -sh {home}/* 2>/dev/null | sort -rh | head -15",
                    shell=True, capture_output=True, text=True, timeout=15,
                )
                return SkillResult(
                    content=f"disk usage in {home}:\n{result.stdout.strip()}",
                    inject_as_context=True,
                )
            except Exception as e:
                return SkillResult(content=f"error: {e}", display_raw=True)

        # General file search
        search_term = q
        for prefix in ["find ", "search ", "where is ", "locate "]:
            if search_term.startswith(prefix):
                search_term = search_term[len(prefix):]
                break

        try:
            result = subprocess.run(
                f"find {home} -maxdepth 5 -iname '*{search_term}*' 2>/dev/null | head -20",
                shell=True, capture_output=True, text=True, timeout=15,
            )
            found = result.stdout.strip()
            if found:
                return SkillResult(content=f"found:\n{found}", inject_as_context=True)
            return SkillResult(content=f"no files matching '{search_term}'", inject_as_context=True)
        except Exception as e:
            return SkillResult(content=f"search error: {e}", display_raw=True)


# ── Screenshot ─────────────────────────────────────────────────────

class ScreenshotSkill(Skill):
    """Take screenshots and optionally OCR them."""
    name = "screenshot"
    description = "Take screenshots and read screen content"
    triggers = [
        "screenshot", "screen", "capture", "what's on my screen",
        "screen capture", "print screen",
    ]
    priority = 60

    def execute(self, query: str, context: dict) -> SkillResult:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        save_dir = Path.home() / ".rokan" / "screenshots"
        save_dir.mkdir(parents=True, exist_ok=True)
        path = save_dir / f"screenshot_{timestamp}.png"

        # Try multiple screenshot tools
        for cmd in [
            f"gnome-screenshot -f {path}",
            f"scrot {path}",
            f"import -window root {path}",  # ImageMagick
            f"maim {path}",
        ]:
            tool = cmd.split()[0]
            if shutil.which(tool):
                try:
                    subprocess.run(cmd, shell=True, timeout=10, capture_output=True)
                    if path.exists():
                        size_kb = path.stat().st_size / 1024

                        # Try OCR if available
                        ocr_text = ""
                        if shutil.which("tesseract"):
                            try:
                                r = subprocess.run(
                                    f"tesseract {path} stdout 2>/dev/null",
                                    shell=True, capture_output=True, text=True, timeout=15,
                                )
                                ocr_text = r.stdout.strip()
                            except Exception:
                                pass

                        content = f"screenshot saved: {path} ({size_kb:.0f}KB)"
                        if ocr_text:
                            content += f"\n\nscreen text (OCR):\n{ocr_text[:2000]}"

                        return SkillResult(content=content, inject_as_context=True)
                except Exception:
                    continue

        return SkillResult(
            content="no screenshot tool found. install one: sudo apt install scrot",
            display_raw=True,
        )


# ── Clipboard ──────────────────────────────────────────────────────

class ClipboardSkill(Skill):
    """Read and write system clipboard."""
    name = "clipboard"
    description = "Read and write clipboard contents"
    triggers = [
        "clipboard", "paste", "copy", "what did i copy",
        "clip", "copied",
    ]
    priority = 60

    def execute(self, query: str, context: dict) -> SkillResult:
        q = query.lower().strip()

        # Copy to clipboard
        if q.startswith("/copy "):
            text = query[6:].strip()
            return self._set_clipboard(text)

        # Read clipboard
        return self._get_clipboard()

    def _get_clipboard(self) -> SkillResult:
        for cmd in ["xclip -selection clipboard -o", "xsel --clipboard --output"]:
            tool = cmd.split()[0]
            if shutil.which(tool):
                try:
                    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
                    text = r.stdout.strip()
                    if text:
                        return SkillResult(
                            content=f"clipboard contents:\n{text[:3000]}",
                            inject_as_context=True,
                        )
                    return SkillResult(content="clipboard is empty", display_raw=True)
                except Exception as e:
                    return SkillResult(content=f"clipboard error: {e}", display_raw=True)

        return SkillResult(
            content="no clipboard tool found. install: sudo apt install xclip",
            display_raw=True,
        )

    def _set_clipboard(self, text: str) -> SkillResult:
        for cmd_template in [
            "echo -n '{}' | xclip -selection clipboard",
            "echo -n '{}' | xsel --clipboard --input",
        ]:
            tool = cmd_template.split()[3]  # xclip or xsel
            if shutil.which(tool):
                try:
                    # Use stdin to avoid shell escaping issues
                    proc = subprocess.Popen(
                        cmd_template.split("|")[1].strip(),
                        shell=True, stdin=subprocess.PIPE,
                    )
                    proc.communicate(input=text.encode(), timeout=5)
                    return SkillResult(content=f"copied to clipboard ({len(text)} chars)", display_raw=True)
                except Exception as e:
                    return SkillResult(content=f"copy failed: {e}", display_raw=True)

        return SkillResult(content="no clipboard tool found", display_raw=True)


# ── Reminders/Timers ───────────────────────────────────────────────

class ReminderSkill(Skill):
    """Set reminders and timers with desktop notifications."""
    name = "reminder"
    description = "Set reminders and timers"
    triggers = [
        "remind", "reminder", "timer", "alarm",
        "in 5 minutes", "in 10 minutes", "in an hour",
        "set timer", "set alarm", "notify me", "wake me",
    ]
    priority = 70

    _active_timers: list[dict] = []

    def can_handle(self, query: str) -> float:
        q = query.lower()
        if "/remind" in q or "/timer" in q:
            return 1.0
        if "remind" in q or "timer" in q or "alarm" in q:
            return 0.8
        # Detect time patterns
        import re
        if re.search(r'in \d+ (min|sec|hour|minute|second)', q):
            return 0.85
        return super().can_handle(q)

    def execute(self, query: str, context: dict) -> SkillResult:
        import re
        q = query.lower().strip()

        # Parse time
        seconds = self._parse_time(q)
        if seconds is None:
            return SkillResult(
                content="couldn't parse time. try: 'remind me in 5 minutes to check the oven'",
                display_raw=True,
            )

        # Parse message
        message = self._parse_message(query)
        if not message:
            message = "timer done"

        # Set the timer
        timer_id = len(self._active_timers) + 1
        fire_at = datetime.datetime.now() + datetime.timedelta(seconds=seconds)

        self._active_timers.append({
            "id": timer_id,
            "message": message,
            "fire_at": fire_at.isoformat(),
            "seconds": seconds,
        })

        # Background thread for the timer
        def _fire():
            time.sleep(seconds)
            _notify(f"rokan reminder", message)

        t = threading.Thread(target=_fire, daemon=True)
        t.start()

        if seconds >= 3600:
            time_str = f"{seconds // 3600}h {(seconds % 3600) // 60}m"
        elif seconds >= 60:
            time_str = f"{seconds // 60}m {seconds % 60}s"
        else:
            time_str = f"{seconds}s"

        return SkillResult(
            content=f"timer set: {time_str} — {message} (fires at {fire_at.strftime('%H:%M:%S')})",
            inject_as_context=False,
            display_raw=True,
        )

    def _parse_time(self, q: str) -> int | None:
        import re
        total = 0
        found = False

        for match in re.finditer(r'(\d+)\s*(h|hour|hr|m|min|minute|s|sec|second)s?', q):
            found = True
            val = int(match.group(1))
            unit = match.group(2)[0]
            if unit == 'h':
                total += val * 3600
            elif unit == 'm':
                total += val * 60
            elif unit == 's':
                total += val

        return total if found else None

    def _parse_message(self, q: str) -> str:
        import re
        # "remind me in 5 min to check oven" -> "check oven"
        for pattern in [r'to (.+)$', r'that (.+)$', r'about (.+)$', r':\s*(.+)$']:
            m = re.search(pattern, q, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return ""


# ── Network Tools ──────────────────────────────────────────────────

class NetworkSkill(Skill):
    """Network diagnostics — IP, ping, connectivity."""
    name = "network"
    description = "Network tools and diagnostics"
    triggers = [
        "ip", "my ip", "ip address", "ping", "network",
        "internet", "wifi", "connected", "speed", "dns",
        "connectivity", "is it down",
    ]
    priority = 60

    def can_handle(self, query: str) -> float:
        q = query.lower()
        if any(p in q for p in ["my ip", "ip address", "ping ", "am i online", "internet connection"]):
            return 0.9
        if any(p in q for p in ["network", "wifi", "connectivity", "connected to"]):
            return 0.7
        return super().can_handle(q)

    def execute(self, query: str, context: dict) -> SkillResult:
        q = query.lower().strip()

        # Ping check
        if "ping " in q:
            import re
            host = re.search(r'ping\s+(\S+)', q)
            if host:
                return self._ping(host.group(1))

        # IP address
        if any(w in q for w in ["my ip", "ip address", "what's my ip"]):
            return self._get_ip()

        # General connectivity check
        if any(w in q for w in ["internet", "connected", "connectivity", "online"]):
            return self._check_connectivity()

        # Network interfaces
        if any(w in q for w in ["network", "interface", "wifi", "ethernet"]):
            return self._interfaces()

        # Default: show everything
        return self._full_status()

    def _get_ip(self) -> SkillResult:
        parts = []

        # Local IP
        try:
            r = subprocess.run(
                "hostname -I 2>/dev/null | awk '{print $1}'",
                shell=True, capture_output=True, text=True, timeout=5,
            )
            local = r.stdout.strip()
            if local:
                parts.append(f"local: {local}")
        except Exception:
            pass

        # Public IP
        try:
            r = subprocess.run(
                "curl -s --max-time 5 ifconfig.me 2>/dev/null",
                shell=True, capture_output=True, text=True, timeout=8,
            )
            public = r.stdout.strip()
            if public:
                parts.append(f"public: {public}")
        except Exception:
            parts.append("public: couldn't reach ifconfig.me")

        return SkillResult(
            content="ip addresses:\n" + "\n".join(parts) if parts else "couldn't determine IP",
            inject_as_context=True,
        )

    def _ping(self, host: str) -> SkillResult:
        try:
            r = subprocess.run(
                f"ping -c 3 -W 3 {host}",
                shell=True, capture_output=True, text=True, timeout=15,
            )
            output = r.stdout.strip()
            # Extract just the summary
            lines = output.split("\n")
            summary = [l for l in lines if "packet" in l or "rtt" in l or "time=" in l]
            return SkillResult(
                content=f"ping {host}:\n" + "\n".join(summary[-3:]),
                inject_as_context=True,
            )
        except subprocess.TimeoutExpired:
            return SkillResult(content=f"ping {host}: timed out", display_raw=True)
        except Exception as e:
            return SkillResult(content=f"ping failed: {e}", display_raw=True)

    def _check_connectivity(self) -> SkillResult:
        targets = [("google.com", "8.8.8.8"), ("cloudflare", "1.1.1.1")]
        results = []
        for name, ip in targets:
            try:
                r = subprocess.run(
                    f"ping -c 1 -W 2 {ip}",
                    shell=True, capture_output=True, text=True, timeout=5,
                )
                if r.returncode == 0:
                    results.append(f"{name}: reachable")
                else:
                    results.append(f"{name}: unreachable")
            except Exception:
                results.append(f"{name}: error")

        return SkillResult(
            content="connectivity check:\n" + "\n".join(results),
            inject_as_context=True,
        )

    def _interfaces(self) -> SkillResult:
        try:
            r = subprocess.run(
                "ip -brief addr show 2>/dev/null || ifconfig 2>/dev/null",
                shell=True, capture_output=True, text=True, timeout=5,
            )
            return SkillResult(
                content=f"network interfaces:\n{r.stdout.strip()}",
                inject_as_context=True,
            )
        except Exception as e:
            return SkillResult(content=f"error: {e}", display_raw=True)

    def _full_status(self) -> SkillResult:
        parts = []
        ip_result = self._get_ip()
        parts.append(ip_result.content)
        conn_result = self._check_connectivity()
        parts.append(conn_result.content)
        return SkillResult(content="\n\n".join(parts), inject_as_context=True)


# ── Desktop Notifications ──────────────────────────────────────────

def _notify(title: str, body: str):
    """Send a desktop notification. Tries multiple methods."""
    for cmd in [
        f'notify-send "{title}" "{body}"',
        f'zenity --notification --text="{title}: {body}"',
        f'kdialog --passivepopup "{body}" 5 --title "{title}"',
    ]:
        tool = cmd.split()[0]
        if shutil.which(tool):
            try:
                subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except Exception:
                continue


class NotifySkill(Skill):
    """Send desktop notifications."""
    name = "notify"
    description = "Send desktop notifications"
    triggers = ["notify", "notification", "alert me", "popup"]
    priority = 55

    def execute(self, query: str, context: dict) -> SkillResult:
        q = query.strip()
        for prefix in ("/notify ", "notify "):
            if q.lower().startswith(prefix):
                q = q[len(prefix):]
                break

        _notify("rokan", q)
        return SkillResult(content=f"notification sent: {q}", display_raw=True)


# ── Volume / Brightness ───────────────────────────────────────────

class MediaControlSkill(Skill):
    """Control volume, brightness, media playback."""
    name = "media"
    description = "Control volume, brightness, and media"
    triggers = [
        "volume", "volume up", "volume down", "mute", "unmute",
        "brightness", "bright", "dim",
        "play", "pause", "next", "previous", "skip",
    ]
    priority = 60

    def execute(self, query: str, context: dict) -> SkillResult:
        q = query.lower().strip()

        # Volume
        if "volume" in q or "mute" in q:
            return self._volume(q)

        # Brightness
        if "bright" in q or "dim" in q:
            return self._brightness(q)

        # Media playback
        if any(w in q for w in ["play", "pause", "next", "previous", "skip"]):
            return self._playback(q)

        return SkillResult(content="specify: volume/brightness/playback", display_raw=True)

    def _volume(self, q: str) -> SkillResult:
        import re
        if "mute" in q and "unmute" not in q:
            cmd = "pactl set-sink-mute @DEFAULT_SINK@ toggle"
            label = "toggled mute"
        elif "unmute" in q:
            cmd = "pactl set-sink-mute @DEFAULT_SINK@ 0"
            label = "unmuted"
        elif "up" in q or "increase" in q or "raise" in q:
            amt = self._extract_number(q, default=10)
            cmd = f"pactl set-sink-volume @DEFAULT_SINK@ +{amt}%"
            label = f"volume +{amt}%"
        elif "down" in q or "decrease" in q or "lower" in q:
            amt = self._extract_number(q, default=10)
            cmd = f"pactl set-sink-volume @DEFAULT_SINK@ -{amt}%"
            label = f"volume -{amt}%"
        elif match := re.search(r'(\d+)\s*%', q):
            val = match.group(1)
            cmd = f"pactl set-sink-volume @DEFAULT_SINK@ {val}%"
            label = f"volume set to {val}%"
        else:
            # Get current volume
            try:
                r = subprocess.run(
                    "pactl get-sink-volume @DEFAULT_SINK@ 2>/dev/null",
                    shell=True, capture_output=True, text=True, timeout=5,
                )
                return SkillResult(content=f"current volume:\n{r.stdout.strip()}", inject_as_context=True)
            except Exception:
                return SkillResult(content="couldn't read volume", display_raw=True)

        try:
            subprocess.run(cmd, shell=True, timeout=5, capture_output=True)
            return SkillResult(content=label, display_raw=True)
        except Exception as e:
            return SkillResult(content=f"volume error: {e}", display_raw=True)

    def _brightness(self, q: str) -> SkillResult:
        if "up" in q or "increase" in q or "bright" in q:
            cmd = "brightnessctl set +10%"
        elif "down" in q or "decrease" in q or "dim" in q:
            cmd = "brightnessctl set 10%-"
        else:
            cmd = "brightnessctl get"

        if not shutil.which("brightnessctl"):
            return SkillResult(
                content="brightnessctl not found. install: sudo apt install brightnessctl",
                display_raw=True,
            )

        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
            return SkillResult(content=r.stdout.strip() or "brightness adjusted", display_raw=True)
        except Exception as e:
            return SkillResult(content=f"brightness error: {e}", display_raw=True)

    def _playback(self, q: str) -> SkillResult:
        if "pause" in q or "play" in q:
            cmd = "playerctl play-pause"
        elif "next" in q or "skip" in q:
            cmd = "playerctl next"
        elif "previous" in q or "prev" in q:
            cmd = "playerctl previous"
        else:
            cmd = "playerctl status"

        if not shutil.which("playerctl"):
            return SkillResult(
                content="playerctl not found. install: sudo apt install playerctl",
                display_raw=True,
            )

        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
            return SkillResult(content=r.stdout.strip() or "done", display_raw=True)
        except Exception as e:
            return SkillResult(content=f"playback error: {e}", display_raw=True)

    def _extract_number(self, q: str, default: int = 10) -> int:
        import re
        m = re.search(r'(\d+)', q)
        return int(m.group(1)) if m else default


# ── Power Management ───────────────────────────────────────────────

class PowerSkill(Skill):
    """System power controls — lock, sleep, shutdown."""
    name = "power"
    description = "Lock screen, sleep, restart, shutdown"
    triggers = [
        "lock", "lock screen", "sleep", "suspend",
        "shutdown", "shut down", "restart", "reboot",
        "hibernate", "log out", "logout",
    ]
    priority = 50

    def execute(self, query: str, context: dict) -> SkillResult:
        q = query.lower().strip()

        if "lock" in q:
            for cmd in ["loginctl lock-session", "xdg-screensaver lock", "gnome-screensaver-command -l"]:
                tool = cmd.split()[0]
                if shutil.which(tool):
                    subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return SkillResult(content="screen locked", display_raw=True)

        if "sleep" in q or "suspend" in q:
            subprocess.Popen("systemctl suspend", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return SkillResult(content="going to sleep", display_raw=True)

        if "restart" in q or "reboot" in q:
            return SkillResult(
                content="to restart: /run sudo reboot\n(won't auto-reboot for safety)",
                display_raw=True,
            )

        if "shutdown" in q or "shut down" in q:
            return SkillResult(
                content="to shutdown: /run sudo shutdown now\n(won't auto-shutdown for safety)",
                display_raw=True,
            )

        if "log out" in q or "logout" in q:
            subprocess.Popen("loginctl terminate-user $USER", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return SkillResult(content="logging out", display_raw=True)

        return SkillResult(content="specify: lock, sleep, restart, shutdown, logout", display_raw=True)


# ── Datetime/Timezone ─────────────────────────────────────────────

class DatetimeSkill(Skill):
    """Current time, date, timezone info — no internet needed."""
    name = "datetime"
    description = "Current time, date, timezone"
    triggers = [
        "time", "what time", "current time", "date", "today",
        "what day", "timezone", "clock",
    ]
    priority = 72

    def can_handle(self, query: str) -> float:
        q = query.lower()
        if any(w in q for w in ["what time", "current time", "what's the time", "what day", "today's date"]):
            return 0.9
        return super().can_handle(q) * 0.5

    def execute(self, query: str, context: dict) -> SkillResult:
        now = datetime.datetime.now()
        tz = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo

        info = (
            f"date: {now.strftime('%A, %B %d, %Y')}\n"
            f"time: {now.strftime('%H:%M:%S')}\n"
            f"timezone: {tz}\n"
            f"unix: {int(now.timestamp())}"
        )
        return SkillResult(content=info, inject_as_context=True)


# ── Registry ───────────────────────────────────────────────────────

def create_desktop_skills() -> list[Skill]:
    """Create all desktop-class skills."""
    return [
        ShellSkill(),
        AppLauncherSkill(),
        FileSkill(),
        ScreenshotSkill(),
        ClipboardSkill(),
        ReminderSkill(),
        NetworkSkill(),
        NotifySkill(),
        MediaControlSkill(),
        PowerSkill(),
        DatetimeSkill(),
    ]
