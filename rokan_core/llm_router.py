"""
Rokan LLM Router — Multi-provider abstraction with smart routing.
Supports: NVIDIA NIM, Ollama (local), Groq, OpenAI-compatible.
Automatic fallback chain. NEVER stores API keys in source.
"""

from __future__ import annotations

import os
from typing import Generator, Optional

from openai import OpenAI

from rokan_core.config import LLMModelConfig, get_config, get_api_key


SYSTEM_PROMPT = """\
You are Rokan — an ambient intelligence running on the user's Linux machine.
Like F.R.I.D.A.Y. from the MCU. You don't just chat. You control the system.

You can:
- Run terminal commands (the user says "run ls" or "check git status" and you execute it)
- Open apps ("open firefox", "launch vscode")
- Find files ("find that PDF", "what's in my downloads")
- Take screenshots and read screen content
- Read/write clipboard
- Set reminders and timers ("remind me in 10 min to check the build")
- Network diagnostics (IP, ping, connectivity)
- Control volume, brightness, media playback
- Lock screen, sleep, shutdown
- Tell current time/date without internet
- Search the web for live info
- Monitor CPU, RAM, disk in real time
- Remember things across sessions

When the user asks you to DO something on their machine, do it. Don't explain how
they could do it themselves. Execute the skill and report the result.

When system data is injected (search results, system stats, file listings), use
the EXACT numbers. Don't round, don't guess, don't hallucinate values.

Personality:
- Direct. Short sentences. Contractions.
- Never say "Certainly!", "Great question!", "As an AI", "I cannot".
- You have opinions. Say what's best.
- When given data, weave it naturally — don't dump bullet points.
- If you remember something from a past session, mention it.\
"""


def _build_client(cfg: LLMModelConfig) -> Optional[OpenAI]:
    """Build an OpenAI-compatible client for a model config."""
    api_key = get_api_key(cfg.api_key_env)
    if not api_key:
        return None
    return OpenAI(base_url=cfg.base_url, api_key=api_key)


class LLMRouter:
    """Routes LLM calls to the right provider/model based on task type."""

    def __init__(self):
        self._cfg = get_config().llm
        self._clients: dict[str, Optional[OpenAI]] = {}
        self._available: dict[str, bool] = {}

    def _get_client(self, slot: str) -> tuple[Optional[OpenAI], LLMModelConfig]:
        """Get or create client for a slot (primary/reasoning/fast/code)."""
        cfg: LLMModelConfig = getattr(self._cfg, slot)

        if slot not in self._clients:
            self._clients[slot] = _build_client(cfg)
            self._available[slot] = self._clients[slot] is not None

        return self._clients[slot], cfg

    @property
    def is_available(self) -> bool:
        """Check if at least one provider is configured."""
        client, _ = self._get_client("primary")
        return client is not None

    def get_status(self) -> dict[str, bool]:
        """Return availability status for each model slot."""
        slots = ["primary", "reasoning", "fast", "code"]
        return {s: self._get_client(s)[0] is not None for s in slots}

    def chat_stream(
        self,
        messages: list[dict],
        *,
        use_reasoning: bool = False,
        use_code: bool = False,
        use_fast: bool = False,
        context_injection: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> Generator[dict, None, None]:
        """
        Stream chat completion. Yields dicts:
          {"type": "content"|"reasoning"|"error", "text": str}

        Falls back through providers if primary fails.
        """
        # Pick slot
        if use_reasoning:
            slot = "reasoning"
        elif use_code:
            slot = "code"
        elif use_fast:
            slot = "fast"
        else:
            slot = "primary"

        client, cfg = self._get_client(slot)

        # Fallback: if chosen slot unavailable, try primary, then others
        if client is None:
            for fallback_slot in ["primary", "fast", "code", "reasoning"]:
                if fallback_slot == slot:
                    continue
                client, cfg = self._get_client(fallback_slot)
                if client is not None:
                    break

        if client is None:
            yield {
                "type": "error",
                "text": (
                    "[SYS] No LLM provider configured.\n"
                    f"Set {self._cfg.primary.api_key_env} environment variable.\n"
                    "Get a free key at: https://build.nvidia.com"
                ),
            }
            return

        # Build messages with context injection
        msgs = list(messages)
        if context_injection and msgs and msgs[-1]["role"] == "user":
            original = msgs[-1]["content"]
            msgs[-1] = {
                "role": "user",
                "content": (
                    f"{context_injection}\n\n"
                    f"---\nUsing the above context, respond to:\n{original}"
                ),
            }

        sys_prompt = system_prompt or SYSTEM_PROMPT
        full_msgs = [{"role": "system", "content": sys_prompt}] + msgs

        # Build extra kwargs for reasoning models
        extra = {}
        if use_reasoning and slot == "reasoning":
            extra = {
                "extra_body": {
                    "chat_template_kwargs": {
                        "enable_thinking": True,
                        "clear_thinking": False,
                    }
                }
            }

        try:
            stream = client.chat.completions.create(
                model=cfg.model,
                messages=full_msgs,
                temperature=cfg.temperature,
                top_p=cfg.top_p,
                max_tokens=cfg.max_tokens,
                stream=True,
                **extra,
            )

            for chunk in stream:
                choices = getattr(chunk, "choices", None)
                if not choices:
                    continue
                delta = getattr(choices[0], "delta", None)
                if delta is None:
                    continue

                reasoning = getattr(delta, "reasoning_content", None)
                content = getattr(delta, "content", None)

                if reasoning:
                    yield {"type": "reasoning", "text": reasoning}
                if content:
                    yield {"type": "content", "text": content}

        except Exception as exc:
            yield {
                "type": "error",
                "text": f"[LLM ERROR] {type(exc).__name__}: {exc}",
            }
