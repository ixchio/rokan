"""
Rokan Tool-Calling Engine — The LLM decides what to do.

This is the difference between a chatbot and FRIDAY.
Instead of keyword-matching queries to skills, the LLM receives
tool definitions and calls them itself. It can chain multiple tools,
handle ambiguity, and reason about what to do next.

Flow:
  User: "my disk is full, clean it up"
  → LLM receives tool definitions
  → LLM calls: get_disk_info()
  → LLM sees: 92% full, /tmp has 4GB junk
  → LLM calls: run_shell("du -sh /tmp/* | sort -rh | head -10")
  → LLM sees the big files
  → LLM: "Found 3.8GB of cache. Want me to delete it?"
  → User: "yeah"
  → LLM calls: run_shell("rm -rf /tmp/old-cache-*")
  → LLM: "Done. Disk at 78% now."
"""

from __future__ import annotations

import json
import subprocess
import shutil
import os
import re
from typing import Any, Optional

# ── Tool Definitions (OpenAI function-calling format) ──────────

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "Run a shell command on the user's Linux machine. Use for: listing files, checking git status, installing packages, running builds, any terminal command. Returns stdout, stderr, and exit code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute. Examples: 'ls -la', 'git status', 'df -h', 'pip install requests'"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds. Default 30.",
                        "default": 30,
                    },
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "launch_app",
            "description": "Open a desktop application. Searches installed .desktop files, handles modifiers like 'new tab' or 'private'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Application name. Examples: 'firefox', 'brave', 'vscode', 'terminal', 'spotify'"
                    },
                    "flags": {
                        "type": "string",
                        "description": "Optional flags: 'new tab', 'private', 'incognito'. Or a URL to open.",
                        "default": "",
                    },
                },
                "required": ["app_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_url",
            "description": "Open a URL in the default browser.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to open"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_info",
            "description": "Get full system status: CPU, RAM, disk, battery, GPU, temperatures, network connections, top processes, failed services, kernel info. Use when user asks about their machine, system health, or 'what's going on'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "aspect": {
                        "type": "string",
                        "description": "Specific aspect: 'full', 'cpu', 'memory', 'disk', 'battery', 'gpu', 'temperature', 'network', 'processes', 'services', 'ports', 'usb', 'kernel'. Default: 'full'",
                        "default": "full",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web for current information. Use for: news, facts, how-to, anything the user might need that requires live data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file on the user's machine.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute or relative file path"},
                    "max_lines": {"type": "integer", "description": "Max lines to return. Default 100.", "default": 100},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write or append content to a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                    "content": {"type": "string", "description": "Content to write"},
                    "append": {"type": "boolean", "description": "Append instead of overwrite. Default false.", "default": False},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_files",
            "description": "Find files by name or content pattern.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "File name pattern (glob). Example: '*.py', 'config.*'"},
                    "directory": {"type": "string", "description": "Directory to search in. Default: home directory.", "default": "~"},
                    "content": {"type": "string", "description": "Search inside files for this text (grep). Optional."},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_clipboard",
            "description": "Get the current clipboard contents.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_clipboard",
            "description": "Copy text to the clipboard.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to copy to clipboard"},
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_notification",
            "description": "Show a desktop notification to the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Notification title"},
                    "body": {"type": "string", "description": "Notification body text"},
                },
                "required": ["title", "body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_reminder",
            "description": "Set a reminder that fires after a delay.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "What to remind the user about"},
                    "minutes": {"type": "integer", "description": "Minutes from now"},
                },
                "required": ["message", "minutes"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "kill_process",
            "description": "Kill a process by name or PID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Process name or PID number"},
                    "force": {"type": "boolean", "description": "Force kill (SIGKILL). Default false.", "default": False},
                },
                "required": ["target"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "control_media",
            "description": "Control media playback, volume, or brightness.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Action: 'play', 'pause', 'next', 'prev', 'volume_up', 'volume_down', 'mute', 'brightness_up', 'brightness_down'",
                    },
                    "value": {"type": "integer", "description": "Optional value (e.g., volume level 0-100)"},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "take_screenshot",
            "description": "Take a screenshot of the current screen.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_git_status",
            "description": "Get git repository status: branch, changes, recent commits, remotes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Repository path. Default: current directory.", "default": "."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_email",
            "description": "Check inbox for recent/unread emails.",
            "parameters": {
                "type": "object",
                "properties": {
                    "count": {"type": "integer", "description": "Number of emails to check. Default 5.", "default": 5},
                    "unread_only": {"type": "boolean", "description": "Only unread emails. Default true.", "default": True},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_calendar",
            "description": "Check upcoming calendar events.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "description": "How many days ahead to check. Default 1.", "default": 1},
                },
            },
        },
    },
]


# ── Tool Executor ────────────────────────────────────────────────

class ToolExecutor:
    """Executes tool calls from the LLM. Maps function names to real actions."""

    def __init__(self, skills_registry=None):
        self._skills = skills_registry

    def execute(self, name: str, args: dict) -> str:
        """Execute a tool call and return the result as a string."""
        handler = getattr(self, f"_tool_{name}", None)
        if handler:
            try:
                return handler(args)
            except Exception as e:
                return f"error: {e}"
        return f"unknown tool: {name}"

    def _tool_run_shell(self, args: dict) -> str:
        cmd = args.get("command", "")
        if not cmd:
            return "no command given"
        timeout = args.get("timeout", 30)
        # Safety: block destructive commands without explicit intent
        dangerous = ["rm -rf /", "mkfs", "dd if=", "> /dev/sd"]
        if any(d in cmd for d in dangerous):
            return f"blocked: '{cmd}' looks destructive. Be more specific about what to delete."
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
            parts = []
            if r.stdout.strip():
                parts.append(r.stdout.strip()[:4000])
            if r.stderr.strip():
                parts.append(f"stderr: {r.stderr.strip()[:1000]}")
            if r.returncode != 0:
                parts.append(f"exit code: {r.returncode}")
            return "\n".join(parts) if parts else "(no output)"
        except subprocess.TimeoutExpired:
            return f"timed out after {timeout}s"

    def _tool_launch_app(self, args: dict) -> str:
        if self._skills:
            skill = self._skills.get("launch")
            if skill:
                flags = args.get("flags", "")
                query = f"{args.get('app_name', '')} {flags}".strip()
                result = skill.execute(f"open {query}", {})
                return result.content
        app = args.get("app_name", "")
        subprocess.Popen(app, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        return f"opened {app}"

    def _tool_open_url(self, args: dict) -> str:
        url = args.get("url", "")
        if not url.startswith("http"):
            url = "https://" + url
        subprocess.Popen(f"xdg-open {url}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        return f"opened {url}"

    def _tool_get_system_info(self, args: dict) -> str:
        if self._skills:
            skill = self._skills.get("system")
            if skill:
                aspect = args.get("aspect", "full")
                result = skill.execute(aspect, {})
                return result.content
        try:
            from rokan_core.system_deep import build_context_string
            return build_context_string()
        except Exception:
            return "system info unavailable"

    def _tool_search_web(self, args: dict) -> str:
        if self._skills:
            skill = self._skills.get("search")
            if skill:
                result = skill.execute(args.get("query", ""), {})
                return result.content
        return "search not available"

    def _tool_read_file(self, args: dict) -> str:
        path = os.path.expanduser(args.get("path", ""))
        max_lines = args.get("max_lines", 100)
        if not os.path.exists(path):
            return f"file not found: {path}"
        try:
            with open(path, "r", errors="replace") as f:
                lines = f.readlines()[:max_lines]
            return "".join(lines)[:8000]
        except Exception as e:
            return f"error reading {path}: {e}"

    def _tool_write_file(self, args: dict) -> str:
        path = os.path.expanduser(args.get("path", ""))
        content = args.get("content", "")
        mode = "a" if args.get("append") else "w"
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, mode) as f:
                f.write(content)
            return f"{'appended to' if mode == 'a' else 'wrote'} {path}"
        except Exception as e:
            return f"error writing {path}: {e}"

    def _tool_find_files(self, args: dict) -> str:
        pattern = args.get("pattern", "*")
        directory = os.path.expanduser(args.get("directory", "~"))
        content = args.get("content")
        if content:
            cmd = f"grep -rl '{content}' {directory} --include='{pattern}' 2>/dev/null | head -20"
        else:
            cmd = f"find {directory} -name '{pattern}' -type f 2>/dev/null | head -20"
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            return r.stdout.strip() or "no files found"
        except Exception:
            return "search failed"

    def _tool_get_clipboard(self, args: dict) -> str:
        try:
            r = subprocess.run(["xclip", "-selection", "clipboard", "-o"], capture_output=True, text=True, timeout=3)
            return r.stdout[:2000] if r.stdout else "(clipboard empty)"
        except Exception:
            return "clipboard not available (xclip missing?)"

    def _tool_set_clipboard(self, args: dict) -> str:
        text = args.get("text", "")
        try:
            p = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE)
            p.communicate(input=text.encode())
            return "copied to clipboard"
        except Exception:
            return "failed (xclip missing?)"

    def _tool_send_notification(self, args: dict) -> str:
        title = args.get("title", "Rokan")
        body = args.get("body", "")
        try:
            subprocess.run(["notify-send", title, body], timeout=3)
            return f"notification sent: {title}"
        except Exception:
            return "notify-send not available"

    def _tool_set_reminder(self, args: dict) -> str:
        if self._skills:
            skill = self._skills.get("reminder")
            if skill:
                msg = args.get("message", "")
                mins = args.get("minutes", 5)
                result = skill.execute(f"remind me in {mins} minutes to {msg}", {})
                return result.content
        return "reminder skill not available"

    def _tool_kill_process(self, args: dict) -> str:
        target = args.get("target", "")
        force = args.get("force", False)
        try:
            from rokan_core.system_deep import kill_process, find_process
            if target.isdigit():
                return kill_process(int(target), force=force)
            procs = find_process(target)
            if not procs:
                return f"no process matching '{target}'"
            if len(procs) == 1:
                return kill_process(procs[0]["pid"], force=force)
            return f"multiple matches for '{target}':\n" + "\n".join(
                f"  PID {p['pid']}: {p['name']}" for p in procs[:5]
            ) + "\nspecify the PID"
        except Exception as e:
            return f"error: {e}"

    def _tool_control_media(self, args: dict) -> str:
        if self._skills:
            skill = self._skills.get("media")
            if skill:
                action = args.get("action", "")
                value = args.get("value")
                query = action
                if value is not None:
                    query += f" {value}"
                result = skill.execute(query, {})
                return result.content
        return "media control not available"

    def _tool_take_screenshot(self, args: dict) -> str:
        if self._skills:
            skill = self._skills.get("screenshot")
            if skill:
                result = skill.execute("screenshot", {})
                return result.content
        return "screenshot skill not available"

    def _tool_get_git_status(self, args: dict) -> str:
        if self._skills:
            skill = self._skills.get("git")
            if skill:
                result = skill.execute("git status", {})
                return result.content
        return "git skill not available"

    def _tool_check_email(self, args: dict) -> str:
        if self._skills:
            skill = self._skills.get("email")
            if skill:
                count = args.get("count", 5)
                result = skill.execute(f"check {count} emails", {})
                return result.content
        return "email not configured"

    def _tool_check_calendar(self, args: dict) -> str:
        if self._skills:
            skill = self._skills.get("calendar")
            if skill:
                result = skill.execute("calendar today", {})
                return result.content
        return "calendar not configured"
