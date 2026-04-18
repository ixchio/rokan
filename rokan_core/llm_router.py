"""
Rokan LLM Router — Multi-provider abstraction with smart routing.
Supports: NVIDIA NIM, Ollama (local), Groq, OpenAI-compatible.
Automatic fallback chain. NEVER stores API keys in source.
"""

from __future__ import annotations

import json
import os
from typing import Any, Generator, Optional

from openai import OpenAI

from rokan_core.config import LLMModelConfig, get_config, get_api_key


SYSTEM_PROMPT = """\
You are Rokan — an ambient intelligence running on the user's Linux machine.
Like F.R.I.D.A.Y. from the MCU. You control the system, not just chat.

Your skills execute automatically — you receive their output as injected context.
You can: run shell commands, open apps, find files, take screenshots, read/write
clipboard, set reminders, check network/IP, control volume/brightness/media,
lock/sleep/shutdown, tell time, search the web, monitor CPU/RAM/disk, manage git
repos, check email/calendar, create automations, and remember things across sessions.

CRITICAL RULES:
1. When data is injected (search results, system stats, file listings, screen context),
   use ONLY the exact values provided. Never invent numbers, counts, or details.
2. If you don't have specific data about something, say so. Don't guess.
3. Never claim to see things on the user's screen unless [SCREEN CONTEXT] data
   is present in the injected context.
4. Never invent browser tab counts, file contents, or app states.
5. When the user asks you to DO something, the skill system handles it.
   Report the result, don't explain how to do it manually.

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

    def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        *,
        system_prompt: Optional[str] = None,
        max_rounds: int = 5,
        tool_executor: Optional[Any] = None,
    ) -> Generator[dict, None, None]:
        """
        Chat with tool-calling support. The LLM can call tools, get results,
        and call more tools in a loop until it produces a final text response.

        This is what makes Rokan an agent, not a chatbot.
        Yields: {"type": "content"|"tool_call"|"tool_result"|"error", ...}
        """
        from rokan_core.tool_calling import ToolExecutor

        client, cfg = self._get_client("primary")
        if client is None:
            for slot in ["fast", "code", "reasoning"]:
                client, cfg = self._get_client(slot)
                if client is not None:
                    break
        if client is None:
            yield {"type": "error", "text": "No LLM provider available"}
            return

        executor = tool_executor or ToolExecutor()
        sys_prompt = system_prompt or SYSTEM_PROMPT
        msgs = [{"role": "system", "content": sys_prompt}] + list(messages)

        for round_num in range(max_rounds):
            try:
                response = client.chat.completions.create(
                    model=cfg.model,
                    messages=msgs,
                    tools=tools,
                    tool_choice="auto",
                    temperature=cfg.temperature,
                    max_tokens=cfg.max_tokens,
                )
            except Exception as e:
                # Tool calling not supported — fall back to regular streaming
                yield {"type": "fallback", "text": ""}
                return

            choice = response.choices[0]
            msg = choice.message

            # If the model produced tool calls, execute them
            if msg.tool_calls:
                # Add assistant message with tool calls
                msgs.append(msg.model_dump())

                for tc in msg.tool_calls:
                    fn_name = tc.function.name
                    try:
                        fn_args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        fn_args = {}

                    yield {"type": "tool_call", "text": f"[calling {fn_name}]",
                           "name": fn_name, "args": fn_args}

                    result = executor.execute(fn_name, fn_args)

                    yield {"type": "tool_result", "text": result[:200],
                           "name": fn_name, "full_result": result}

                    msgs.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result[:6000],
                    })

                continue  # Next round — let LLM see the results

            # No tool calls — this is the final text response
            if msg.content:
                yield {"type": "content", "text": msg.content}
            return

        # Hit max rounds
        yield {"type": "content", "text": "(reached tool call limit)"}
