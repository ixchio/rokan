"""
Rokan Agent Core — The F.R.I.D.A.Y. Brain.

This is THE missing piece that turns 7 disconnected modules
into one intelligent system. Every user input flows through here:

  Input → Memory Recall → Skill Routing → Search Augmentation →
  Context Assembly → LLM Stream → Memory Extraction → Output

It's not a chatbot. It's an ambient intelligence.
"""

from __future__ import annotations

import re
import time
import uuid
from typing import Generator, Optional

from rokan_core.config import get_config, load_config
from rokan_core.llm_router import LLMRouter
from rokan_core.memory_store import MemoryStore
from rokan_core.proactive import ProactiveEngine, Alert
from rokan_core.skills import (
    Skill,
    SkillRegistry,
    SkillResult,
    create_default_skills,
)


# ── Search Need Detection ────────────────────────────────────────────

_SEARCH_TRIGGERS = {
    "what is", "who is", "where is", "when is", "how to",
    "latest", "today", "current", "news", "recent",
    "weather", "stock", "price", "score",
    "search for", "look up", "find out", "google",
    "what happened", "tell me about",
}

_TIME_WORDS = {"today", "now", "latest", "current", "recent", "this week", "this month"}


def _needs_search(query: str) -> bool:
    """Detect if a query needs live web data."""
    q = query.lower()
    # Explicit search request
    if q.startswith("/search ") or q.startswith("search "):
        return True
    # Time-sensitive
    if any(w in q for w in _TIME_WORDS):
        return True
    # Question about factual/current info
    if any(q.startswith(t) or f" {t} " in f" {q} " for t in _SEARCH_TRIGGERS):
        return True
    return False


def _needs_system(query: str) -> bool:
    """Detect if query is about the local system."""
    q = query.lower()
    sys_words = {
        "system", "cpu", "ram", "memory", "disk", "process",
        "status", "resource", "slow", "running", "my computer",
        "my machine", "performance",
    }
    return any(w in q for w in sys_words)


# ── Agent Core ───────────────────────────────────────────────────────

class RokanAgent:
    """
    The brain. Orchestrates memory, skills, search, LLM, and proactive monitoring.
    Use this from the TUI, CLI, or any other interface.
    """

    def __init__(self, config_path: Optional[str] = None):
        # Load config first — everything reads from this
        self.config = load_config(config_path)

        # Core components
        self.llm = LLMRouter()
        self.memory = MemoryStore()
        self.skills = SkillRegistry()
        self.proactive = ProactiveEngine(on_alert=self._on_proactive_alert)

        # Session
        self.session_id = f"session_{uuid.uuid4().hex[:8]}"
        self.history: list[dict] = []
        self._alert_callback: Optional[callable] = None

        # Register built-in skills
        for skill in create_default_skills(self.memory):
            self.skills.register(skill)

        # Register desktop skills (FRIDAY-class)
        try:
            from rokan_core.skills_desktop import create_desktop_skills
            for skill in create_desktop_skills():
                self.skills.register(skill)
        except ImportError:
            pass

    def start(self):
        """Start background services."""
        self.proactive.start()

    def stop(self):
        """Shutdown cleanly."""
        self.proactive.stop()

    def set_alert_callback(self, callback: callable):
        """Set callback for proactive alerts (TUI subscribes to this)."""
        self._alert_callback = callback

    def _on_proactive_alert(self, alert: Alert):
        """Handle proactive alert from background engine."""
        if self._alert_callback:
            self._alert_callback(alert)

    # ── Main Entry Point ─────────────────────────────────────────

    def process(
        self,
        user_input: str,
        *,
        use_reasoning: bool = False,
        use_code: bool = False,
        use_fast: bool = False,
    ) -> Generator[dict, None, None]:
        """
        Process user input through the full pipeline.
        Yields stream chunks: {"type": "content"|"reasoning"|"error"|"skill"|"system", "text": str}

        Pipeline:
          1. Save user message to memory
          2. Check if a skill should handle this directly
          3. Gather context (memory + search + system)
          4. Stream LLM response with full context
          5. Save assistant response to memory
          6. Extract facts for long-term storage
        """
        user_input = user_input.strip()
        if not user_input:
            return

        # ── Step 1: Save user message ────────────────────────────
        self.history.append({"role": "user", "content": user_input})
        self.memory.save_message(self.session_id, "user", user_input)

        # ── Step 2: Slash commands (direct skill invocation) ─────
        if user_input.startswith("/"):
            slash_result = self._handle_slash(user_input)
            if slash_result is not None:
                yield from slash_result
                return

        # ── Step 3: Build context ────────────────────────────────
        context_parts = []

        # Memory context
        mem_context = self.memory.build_context(user_input, self.session_id)
        if mem_context:
            context_parts.append(mem_context)

        # Auto-search if needed
        if self.config.search.auto_search and _needs_search(user_input):
            yield {"type": "system", "text": "[searching the web...]"}
            search_handler = self.skills.get("search")
            if search_handler:
                result = search_handler.execute(user_input, {})
                if result.content and "ERROR" not in result.content:
                    context_parts.append(result.content)

        # Auto system info if query is about the machine
        if _needs_system(user_input):
            sys_handler = self.skills.get("system")
            if sys_handler:
                result = sys_handler.execute(user_input, {})
                if result.content:
                    context_parts.append(result.content)

        # Check if any other skill wants to handle this
        skill_match = self.skills.find_handler(user_input, threshold=0.6)
        if skill_match:
            skill, confidence = skill_match
            # Don't double-invoke search/system (already handled above)
            if skill.name not in ("search", "system"):
                result = skill.execute(user_input, {"history": self.history})
                if result.display_raw:
                    yield {"type": "skill", "text": result.content}
                    self.memory.save_message(self.session_id, "assistant", result.content)
                    return
                if result.inject_as_context:
                    context_parts.append(result.content)

        # ── Step 4: Assemble context injection ───────────────────
        context_injection = "\n\n".join(context_parts) if context_parts else None

        # ── Step 5: Stream LLM response ──────────────────────────
        full_response = ""
        full_reasoning = ""

        for chunk in self.llm.chat_stream(
            self.history,
            use_reasoning=use_reasoning,
            use_code=use_code,
            use_fast=use_fast,
            context_injection=context_injection,
        ):
            ctype = chunk["type"]
            ctext = chunk["text"]

            if ctype == "reasoning":
                full_reasoning += ctext
            elif ctype == "content":
                full_response += ctext
            elif ctype == "error":
                yield chunk
                return

            yield chunk

        # ── Step 6: Save response ────────────────────────────────
        if full_response:
            self.history.append({"role": "assistant", "content": full_response})
            self.memory.save_message(self.session_id, "assistant", full_response)

            # ── Step 7: Extract facts (lightweight) ──────────────
            if self.config.memory.auto_extract:
                self._maybe_extract_facts(user_input, full_response)

    def _handle_slash(self, cmd: str) -> Optional[Generator]:
        """Handle slash commands. Returns None if not a known command."""
        parts = cmd.split(maxsplit=1)
        command = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if command == "/clear":
            self.history.clear()
            yield {"type": "system", "text": "Chat cleared."}
            return

        if command == "/memory":
            stats = self.memory.stats()
            text = (
                f"Memory: {stats['total_memories']} entries "
                f"({stats['tiers'].get('semantic', 0)} facts, "
                f"{stats['tiers'].get('procedural', 0)} procedures, "
                f"{stats['tiers'].get('episodic', 0)} episodes) | "
                f"{stats['sessions']} sessions, {stats['total_messages']} messages"
            )
            yield {"type": "system", "text": text}
            return

        if command == "/remember" and arg:
            self.memory.store(arg, tier="semantic")
            yield {"type": "system", "text": f"Remembered: {arg}"}
            return

        if command == "/recall" and arg:
            memories = self.memory.recall(arg, limit=5)
            if memories:
                text = "Recalled:\n" + "\n".join(
                    f"  [{m['tier']}] {m['content']}" for m in memories
                )
            else:
                text = f"No memories matching '{arg}'."
            yield {"type": "system", "text": text}
            return

        if command == "/skills":
            skills = self.skills.list_skills()
            text = "Active skills:\n" + "\n".join(
                f"  /{s['name']} — {s['description']}" for s in skills
            )
            yield {"type": "system", "text": text}
            return

        if command == "/search" and arg:
            search = self.skills.get("search")
            if search:
                result = search.execute(arg, {})
                # Inject and let LLM synthesize
                for chunk in self.llm.chat_stream(
                    [{"role": "user", "content": arg}],
                    context_injection=result.content,
                ):
                    yield chunk
            return

        if command == "/code" and arg:
            code_skill = self.skills.get("code")
            if code_skill:
                result = code_skill.execute(arg, {})
                yield {"type": "skill", "text": result.content}
            return

        if command == "/system":
            sys_skill = self.skills.get("system")
            if sys_skill:
                result = sys_skill.execute("full system status", {})
                yield {"type": "skill", "text": result.content}
            return

        # Generic slash routing — /run, /open, /find, /remind, /ping, etc.
        cmd_name = command[1:]  # strip leading /
        skill = self.skills.get(cmd_name)
        if skill:
            result = skill.execute(arg or "", {"history": self.history})
            if result.display_raw:
                yield {"type": "skill", "text": result.content}
            elif result.inject_as_context:
                for chunk in self.llm.chat_stream(
                    [{"role": "user", "content": user_input}],
                    context_injection=result.content,
                ):
                    yield chunk
            return

        # Unknown slash command — not handled, let it flow to LLM
        return None

    def _maybe_extract_facts(self, user_input: str, response: str):
        """
        Lightweight fact extraction from conversation.
        Looks for preference statements, personal info, etc.
        No LLM call needed — pattern matching is enough for basics.
        """
        q = user_input.lower()
        patterns = [
            (r"(?:i (?:prefer|like|use|love|hate|dislike|work with|am|need))\s+(.+)",
             "semantic"),
            (r"(?:my (?:name|email|job|title|stack|setup|os) is)\s+(.+)",
             "semantic"),
            (r"(?:remember (?:that|this)?)\s*:?\s*(.+)",
             "semantic"),
            (r"(?:always|never|don't ever)\s+(.+)",
             "procedural"),
        ]

        for pattern, tier in patterns:
            match = re.search(pattern, q)
            if match:
                fact = match.group(1).strip().rstrip(".")
                if len(fact) > 5:  # skip trivial matches
                    self.memory.store(
                        f"User: {fact}",
                        tier=tier,
                        session_id=self.session_id,
                    )
                break  # one extraction per message

    # ── Public Helpers ───────────────────────────────────────────

    @property
    def is_llm_available(self) -> bool:
        return self.llm.is_available

    def get_model_status(self) -> dict:
        return self.llm.get_status()

    def get_pending_alerts(self) -> list[Alert]:
        return self.proactive.pending_alerts

    def dismiss_alerts(self):
        self.proactive.dismiss_all()
