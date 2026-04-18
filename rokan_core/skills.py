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
    """System monitoring — CPU, RAM, disk, processes."""
    name = "system"
    description = "System monitoring and control"
    triggers = [
        "system status", "system", "cpu", "ram", "memory usage",
        "disk", "processes", "top", "what's running", "resource",
        "my computer", "my machine", "slow",
    ]
    priority = 70

    def execute(self, query: str, context: dict) -> SkillResult:
        try:
            import psutil

            cpu = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            load = psutil.getloadavg()

            # Get top processes
            procs = []
            for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
                try:
                    info = p.info
                    if info["cpu_percent"] and info["cpu_percent"] > 1:
                        procs.append(info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            procs.sort(key=lambda x: x.get("cpu_percent", 0), reverse=True)
            top_5 = procs[:5]

            status = (
                f"[SYSTEM STATUS]\n"
                f"CPU: {cpu}% ({psutil.cpu_count()} cores) | "
                f"Load: {load[0]:.2f}, {load[1]:.2f}, {load[2]:.2f}\n"
                f"RAM: {mem.percent}% used ({mem.used // (1024**3)}GB / {mem.total // (1024**3)}GB) | "
                f"Available: {mem.available // (1024**3)}GB\n"
                f"Disk: {disk.percent}% used ({disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB)\n"
            )

            if top_5:
                status += "\nTop processes by CPU:\n"
                for p in top_5:
                    status += f"  - {p['name']} (PID {p['pid']}): CPU {p['cpu_percent']:.1f}%, RAM {p['memory_percent']:.1f}%\n"

            return SkillResult(content=status, inject_as_context=True)

        except ImportError:
            return SkillResult(content="[SYSTEM] psutil not available", inject_as_context=True)


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
