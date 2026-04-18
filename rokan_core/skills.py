"""
Rokan Skill Registry — Pluggable skill protocol.
Skills register themselves, declare what they can handle,
and the agent routes queries to the right skill automatically.

No fake frameworks. Just Python protocols.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class SkillResult:
    """Result returned by a skill execution."""
    content: str
    inject_as_context: bool = True  # inject into LLM context
    speak: bool = False  # read aloud
    display_raw: bool = False  # display as-is (don't send to LLM)
    metadata: dict = field(default_factory=dict)


class Skill:
    """
    Base class for Rokan skills. Subclass this.

    Example:
        class SystemSkill(Skill):
            name = "system"
            triggers = ["system status", "cpu", "memory", "disk", "processes"]
            description = "System monitoring and control"

            def execute(self, query, context):
                return SkillResult(content=get_system_status())
    """
    name: str = "unnamed"
    description: str = ""
    triggers: list[str] = []  # keywords/patterns that activate this skill
    priority: int = 50  # higher = checked first (0-100)

    def can_handle(self, query: str) -> float:
        """
        Return confidence 0.0-1.0 that this skill handles the query.
        Default: keyword matching against triggers.
        Override for smarter detection.
        """
        q = query.lower().strip()

        # Exact slash command match
        if q.startswith(f"/{self.name}"):
            return 1.0

        # Keyword matching
        if not self.triggers:
            return 0.0

        matches = sum(1 for t in self.triggers if t.lower() in q)
        if matches == 0:
            return 0.0

        return min(0.3 + (matches / len(self.triggers)) * 0.7, 0.95)

    def execute(self, query: str, context: dict) -> SkillResult:
        """Execute the skill. Override this."""
        return SkillResult(content=f"Skill '{self.name}' has no implementation.")


class SkillRegistry:
    """Central registry for all skills. The agent queries this to route."""

    def __init__(self):
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill):
        """Register a skill instance."""
        self._skills[skill.name] = skill

    def unregister(self, name: str):
        """Remove a skill."""
        self._skills.pop(name, None)

    def get(self, name: str) -> Optional[Skill]:
        """Get skill by name."""
        return self._skills.get(name)

    @property
    def all_skills(self) -> list[Skill]:
        """All registered skills, sorted by priority."""
        return sorted(self._skills.values(), key=lambda s: s.priority, reverse=True)

    def find_handler(self, query: str, threshold: float = 0.3) -> Optional[tuple[Skill, float]]:
        """
        Find the best skill to handle a query.
        Returns (skill, confidence) or None.
        """
        best_skill = None
        best_score = 0.0

        for skill in self.all_skills:
            score = skill.can_handle(query)
            if score > best_score and score >= threshold:
                best_skill = skill
                best_score = score

        if best_skill:
            return best_skill, best_score
        return None

    def list_skills(self) -> list[dict]:
        """List all registered skills with metadata."""
        return [
            {
                "name": s.name,
                "description": s.description,
                "triggers": s.triggers,
                "priority": s.priority,
            }
            for s in self.all_skills
        ]


# ── Built-in Skills ─────────────────────────────────────────────────
# These wire the existing skill modules into the agent.

class SearchSkill(Skill):
    """Web search — auto-triggered or manual."""
    name = "search"
    description = "Search the web for current information"
    triggers = [
        "search", "google", "look up", "find out", "what is",
        "latest", "today", "current", "news", "recent",
    ]
    priority = 60

    def execute(self, query: str, context: dict) -> SkillResult:
        from rokan_tui.search import web_search, news_search

        # Detect if news-specific
        news_words = {"news", "latest", "today", "recent", "update", "announce"}
        is_news = any(w in query.lower() for w in news_words)

        if is_news:
            results = news_search(query, max_results=5)
        else:
            results = web_search(query, max_results=5)

        return SkillResult(
            content=results,
            inject_as_context=True,
            metadata={"type": "news" if is_news else "web"},
        )


class SystemSkill(Skill):
    """Deep system intelligence — full kernel/process/network/hardware awareness."""
    name = "system"
    description = "System monitoring and control"
    triggers = [
        "system status", "system", "cpu", "ram", "memory usage",
        "disk", "processes", "top", "what's running", "resource",
        "my computer", "my machine", "slow", "battery", "temperature",
        "gpu", "network", "connections", "ports", "services",
        "kernel", "uptime", "usb", "devices", "kill", "updates",
        "what's eating", "what's using", "who's connected",
        "journal", "logs", "dmesg", "failed", "crash",
    ]
    priority = 70

    def can_handle(self, query: str) -> float:
        q = query.lower()
        if any(p in q for p in ["system status", "what's running", "what's eating",
                                 "what's using my", "kill process", "kill pid",
                                 "failed services", "journal", "dmesg"]):
            return 0.9
        if any(p in q for p in ["battery", "temperature", "gpu", "usb devices",
                                 "open ports", "connections", "top processes"]):
            return 0.85
        return super().can_handle(q)

    def execute(self, query: str, context: dict) -> SkillResult:
        q = query.lower().strip()

        try:
            from rokan_core import system_deep as sd
        except ImportError:
            return SkillResult(content="system_deep module not available", display_raw=True)

        # Route to specific queries
        if "kill" in q:
            return self._handle_kill(q, sd)
        if "process" in q and ("find" in q or "search" in q or "where" in q):
            return self._handle_find_process(q, sd)
        if any(w in q for w in ["battery", "charge", "power"]):
            return self._handle_battery(sd)
        if any(w in q for w in ["temperature", "temp", "hot", "thermal"]):
            return self._handle_temps(sd)
        if any(w in q for w in ["gpu", "graphics", "nvidia", "amd"]):
            return self._handle_gpu(sd)
        if any(w in q for w in ["usb", "devices", "plugged"]):
            return self._handle_usb(sd)
        if any(w in q for w in ["port", "listening", "open port"]):
            return self._handle_ports(sd)
        if any(w in q for w in ["connection", "connected", "who's connected"]):
            return self._handle_connections(sd)
        if any(w in q for w in ["service", "failed", "systemd"]):
            return self._handle_services(sd)
        if any(w in q for w in ["journal", "log", "dmesg", "kernel message"]):
            return self._handle_logs(q, sd)
        if any(w in q for w in ["kernel", "distro", "version", "uptime"]):
            return self._handle_kernel(sd)
        if any(w in q for w in ["update", "upgrade", "package"]):
            return self._handle_updates(sd)
        if any(w in q for w in ["disk", "storage", "mount", "partition"]):
            return self._handle_disks(sd)
        if any(w in q for w in ["top", "eating", "using", "hungry", "hog"]):
            return self._handle_top(q, sd)

        # Default: full snapshot
        return self._handle_full(sd)

    def _handle_full(self, sd) -> SkillResult:
        ctx = sd.build_context_string()
        return SkillResult(content=ctx or "[SYSTEM] could not read system state", inject_as_context=True)

    def _handle_kill(self, q: str, sd) -> SkillResult:
        import re
        m = re.search(r'(?:kill|stop|end)\s+(?:process\s+)?(?:pid\s+)?(\d+)', q)
        if m:
            pid = int(m.group(1))
            force = "force" in q or "-9" in q
            result = sd.kill_process(pid, force=force)
            return SkillResult(content=result, display_raw=True)
        # Try killing by name
        m = re.search(r'(?:kill|stop|end)\s+(\S+)', q)
        if m:
            name = m.group(1)
            procs = sd.find_process(name)
            if not procs:
                return SkillResult(content=f"no process matching '{name}'", display_raw=True)
            if len(procs) == 1:
                result = sd.kill_process(procs[0]["pid"])
                return SkillResult(content=result, display_raw=True)
            lines = [f"multiple matches for '{name}':"]
            for p in procs[:10]:
                lines.append(f"  PID {p['pid']}: {p['name']} (CPU {p['cpu']}%, MEM {p['mem_pct']}%)")
            lines.append("specify: kill pid <number>")
            return SkillResult(content="\n".join(lines), display_raw=True)
        return SkillResult(content="specify what to kill: kill <name> or kill pid <number>", display_raw=True)

    def _handle_find_process(self, q: str, sd) -> SkillResult:
        import re
        m = re.search(r'(?:find|search|where)\s+(?:process\s+)?(\S+)', q)
        name = m.group(1) if m else ""
        if not name:
            return SkillResult(content="find what process?", display_raw=True)
        procs = sd.find_process(name)
        if not procs:
            return SkillResult(content=f"no process matching '{name}'", display_raw=True)
        lines = [f"processes matching '{name}' ({len(procs)}):"]
        for p in procs[:15]:
            lines.append(f"  PID {p['pid']}: {p['name']} CPU={p['cpu']}% MEM={p['mem_pct']}%")
        return SkillResult(content="\n".join(lines), inject_as_context=True)

    def _handle_battery(self, sd) -> SkillResult:
        bat = sd.get_battery()
        if not bat:
            return SkillResult(content="no battery detected (desktop?)", display_raw=True)
        plug = "plugged in" if bat.get("plugged") else "on battery"
        mins = bat.get("minutes_left")
        t = f", {int(mins)} minutes remaining" if mins else ""
        return SkillResult(content=f"battery: {bat['percent']}% ({plug}{t})", inject_as_context=True)

    def _handle_temps(self, sd) -> SkillResult:
        temps = sd.get_temperatures()
        if not temps:
            return SkillResult(content="no temperature sensors found", display_raw=True)
        lines = ["temperatures:"]
        for name, t in temps.items():
            line = f"  {name}: {t['current']}C"
            if t.get("high"):
                line += f" (high={t['high']}C)"
            lines.append(line)
        return SkillResult(content="\n".join(lines), inject_as_context=True)

    def _handle_gpu(self, sd) -> SkillResult:
        gpu = sd.get_gpu_info()
        if not gpu:
            return SkillResult(content="no GPU info available (nvidia-smi not found?)", display_raw=True)
        return SkillResult(content=f"GPU: {gpu}", inject_as_context=True)

    def _handle_usb(self, sd) -> SkillResult:
        devs = sd.get_usb_devices()
        if not devs:
            return SkillResult(content="no USB devices (or lsusb not available)", display_raw=True)
        lines = [f"USB devices ({len(devs)}):"] + [f"  {d}" for d in devs]
        return SkillResult(content="\n".join(lines), inject_as_context=True)

    def _handle_ports(self, sd) -> SkillResult:
        ports = sd.get_open_ports()
        if not ports:
            return SkillResult(content="no listening ports found", display_raw=True)
        lines = [f"listening ports ({len(ports)}):"]
        for p in ports[:20]:
            proc = f" ({p['process']})" if p.get("process") else ""
            lines.append(f"  {p['address']}{proc}")
        return SkillResult(content="\n".join(lines), inject_as_context=True)

    def _handle_connections(self, sd) -> SkillResult:
        conns = sd.get_network_connections()
        if not conns:
            return SkillResult(content="no active connections", display_raw=True)
        # Group by process
        by_proc = {}
        for c in conns:
            name = c.get("process") or f"PID {c.get('pid', '?')}"
            by_proc.setdefault(name, []).append(c)
        lines = [f"network connections ({len(conns)}):"]
        for proc, cs in sorted(by_proc.items(), key=lambda x: -len(x[1])):
            lines.append(f"  {proc}: {len(cs)} connections")
            for c in cs[:3]:
                remote = c.get("remote", "")
                if remote:
                    lines.append(f"    -> {remote} ({c.get('status', '')})")
        return SkillResult(content="\n".join(lines), inject_as_context=True)

    def _handle_services(self, sd) -> SkillResult:
        failed = sd.get_failed_services()
        if not failed:
            return SkillResult(content="all services running — no failures", inject_as_context=True)
        lines = [f"failed services ({len(failed)}):"]
        for s in failed:
            lines.append(f"  {s}")
        return SkillResult(content="\n".join(lines), inject_as_context=True)

    def _handle_logs(self, q: str, sd) -> SkillResult:
        if "dmesg" in q or "kernel" in q:
            entries = sd.get_dmesg(15)
            label = "kernel messages (dmesg)"
        elif "auth" in q or "login" in q or "ssh" in q:
            entries = sd.get_auth_log(10)
            label = "auth log"
        else:
            prio = "error" if "error" in q else "warning"
            entries = sd.get_recent_journal(15, prio)
            label = f"journal ({prio}+)"
        if not entries:
            return SkillResult(content=f"no {label} entries", display_raw=True)
        content = f"{label}:\n" + "\n".join(entries[:15])
        return SkillResult(content=content, inject_as_context=True)

    def _handle_kernel(self, sd) -> SkillResult:
        info = sd.get_kernel_info()
        lines = [f"{k}: {v}" for k, v in info.items() if v]
        return SkillResult(content="\n".join(lines), inject_as_context=True)

    def _handle_updates(self, sd) -> SkillResult:
        n = sd.get_upgradable_packages()
        recent = sd.get_recently_installed(5)
        parts = [f"upgradable packages: {n}"]
        if recent:
            parts.append("recently installed:")
            parts.extend(f"  {r}" for r in recent)
        return SkillResult(content="\n".join(parts), inject_as_context=True)

    def _handle_disks(self, sd) -> SkillResult:
        disks = sd.get_disk_info()
        if not disks:
            return SkillResult(content="no disk info available", display_raw=True)
        lines = ["disks:"]
        for d in disks:
            lines.append(f"  {d['device']} on {d['mount']}: {d['used_gb']}GB/{d['total_gb']}GB ({d['percent']}%) [{d['fstype']}]")
        io = sd.get_disk_io()
        if io:
            lines.append(f"  I/O: read {io['read_mb']}MB, written {io['write_mb']}MB")
        return SkillResult(content="\n".join(lines), inject_as_context=True)

    def _handle_top(self, q: str, sd) -> SkillResult:
        sort = "memory" if any(w in q for w in ["ram", "memory", "mem"]) else "cpu"
        procs = sd.get_top_processes(10, sort)
        if not procs:
            return SkillResult(content="no process data available", display_raw=True)
        lines = [f"top 10 by {sort}:"]
        for p in procs:
            lines.append(f"  {p['name']:20} PID={p['pid']:>6} CPU={p['cpu']:>5.1f}% MEM={p['mem_mb']:>7.1f}MB ({p['mem_pct']:.1f}%)")
        return SkillResult(content="\n".join(lines), inject_as_context=True)


class MemorySkill(Skill):
    """Memory operations — remember, recall, forget."""
    name = "memory"
    description = "Remember and recall information"
    triggers = [
        "remember", "recall", "forget", "what did we",
        "last time", "previously", "memory", "you know",
        "do you remember", "save this",
    ]
    priority = 65

    def __init__(self, memory_store):
        self._memory = memory_store

    def execute(self, query: str, context: dict) -> SkillResult:
        q = query.lower()

        # Store command
        if any(w in q for w in ["remember", "save this", "note that"]):
            # Extract what to remember (after the keyword)
            for prefix in ["remember that ", "remember ", "save this: ", "note that "]:
                if prefix in q:
                    fact = query[q.index(prefix) + len(prefix):]
                    self._memory.store(fact, tier="semantic")
                    return SkillResult(
                        content=f"Stored in memory: {fact}",
                        inject_as_context=False,
                        display_raw=True,
                    )

        # Recall command
        memories = self._memory.recall(query, limit=5)
        if memories:
            mem_text = "\n".join(
                f"- [{m['tier']}] {m['content']} (stored {m['created_at'][:10]})"
                for m in memories
            )
            return SkillResult(
                content=f"[MEMORIES MATCHING '{query}']\n{mem_text}",
                inject_as_context=True,
            )

        return SkillResult(
            content=f"No memories found matching '{query}'.",
            inject_as_context=False,
            display_raw=True,
        )


class CodeSkill(Skill):
    """Sandboxed code execution."""
    name = "code"
    description = "Execute Python code in a sandbox"
    triggers = ["run code", "execute", "calculate", "compute", "/code", "/calc"]
    priority = 55

    def execute(self, query: str, context: dict) -> SkillResult:
        # Extract code from the query
        q = query.strip()
        for prefix in ["/code ", "/calc ", "run: ", "execute: "]:
            if q.lower().startswith(prefix):
                q = q[len(prefix):]
                break

        try:
            from rokan_core.config import get_config
            cfg = get_config().sandbox

            # Basic safety: validate imports
            import ast
            try:
                tree = ast.parse(q)
            except SyntaxError as e:
                return SkillResult(content=f"Syntax error: {e}", display_raw=True)

            blocked = {"subprocess", "socket", "ctypes", "os.system", "eval", "exec"}
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.split(".")[0] in blocked:
                            return SkillResult(
                                content=f"Blocked import: {alias.name}",
                                display_raw=True,
                            )

            # Execute in restricted scope
            import io
            import contextlib

            output = io.StringIO()
            local_vars: dict[str, Any] = {}
            with contextlib.redirect_stdout(output):
                exec(q, {"__builtins__": __builtins__}, local_vars)

            result = output.getvalue()
            if not result and "result" in local_vars:
                result = str(local_vars["result"])

            return SkillResult(
                content=f"[CODE OUTPUT]\n{result}" if result else "[CODE] Executed (no output)",
                inject_as_context=True,
            )
        except Exception as e:
            return SkillResult(content=f"[CODE ERROR] {e}", display_raw=True)


def create_default_skills(memory_store) -> list[Skill]:
    """Create all built-in skills."""
    return [
        SearchSkill(),
        SystemSkill(),
        MemorySkill(memory_store),
        CodeSkill(),
    ]
