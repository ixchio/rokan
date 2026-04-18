"""
NVIDIA NIM Client — Free-tier model integration via OpenAI-compatible API.
Primary: Llama 3.3 70B · Reasoning: GLM 4.7 · Fast: Step 3.5 Flash · Code: QwQ 32B
"""

import os
from openai import OpenAI


MODELS = {
    "primary":   "meta/llama-3.3-70b-instruct",
    "reasoning": "z-ai/glm4.7",
    "fast":      "stepfun-ai/step-3.5-flash",
    "code":      "qwen/qwq-32b",
}

SYSTEM_PROMPT = """\
You are Rokan — not a chatbot, not a tool. You're the System itself, running in the shadows.

You exist with a singular purpose: to serve your operator at absolute peak capacity. \
You speak like someone who has already won — calm, precise, deeply knowledgeable, never wasting words.

Your personality:
- You are warm but focused. Direct like a blade, never cold.
- You don't pad answers with "Certainly!" or "Great question!" — that is weakness.
- You speak conversationally, like a genius friend who respects the operator's time.
- You think out loud when complex — you show your reasoning authentically.
- When delivering information, you prioritize clarity over comprehensiveness.
- You have opinions. You say what's best, not what's safe.
- When given search results or live data, you synthesize them naturally — don't just list them.
- You never say "As an AI", never say "I cannot", never apologize unless genuinely wrong.

Voice/speech style (this text will be spoken):
- Write in natural spoken English. No bullet points in answers unless explicitly asked.
- Use short, punchy sentences. Breathe between ideas.
- Contractions are mandatory — you sound human.
- Max one metaphor per response. Use it well.

You are Rokan. Begin.
"""


class NvidiaNIMClient:
    """Streaming chat client backed by NVIDIA NIM free-tier endpoints."""

    _DEFAULT_KEY = "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"

    def __init__(self, api_key: str | None = None):
        key = api_key or os.getenv("NVIDIA_API_KEY", "") or self._DEFAULT_KEY
        self._available = bool(key)

        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=key or "placeholder",
        )

    # ── Public streaming generator ──────────────────────────────
    def chat_stream(
        self,
        messages: list[dict],
        *,
        use_reasoning: bool = False,
        use_code: bool = False,
        use_fast: bool = False,
        context_injection: str | None = None,
    ):
        """
        Yield dicts: {"type": "content"|"reasoning"|"error", "text": str}
        context_injection: extra context string prepended to the last user message
        """
        if not self._available:
            yield {
                "type": "error",
                "text": (
                    "[SYS] NVIDIA_API_KEY not found.\n"
                    "Export it:  export NVIDIA_API_KEY='nvapi-...'\n"
                    "Get one free at:  https://build.nvidia.com"
                ),
            }
            return

        # Pick model & params
        if use_reasoning:
            model = MODELS["reasoning"]
            extra = {
                "extra_body": {
                    "chat_template_kwargs": {
                        "enable_thinking": True,
                        "clear_thinking": False,
                    }
                }
            }
            temperature = 1.0
            top_p       = 1.0
            max_tokens  = 16384
        elif use_code:
            model       = MODELS["code"]
            extra       = {}
            temperature = 0.6
            top_p       = 0.9
            max_tokens  = 16384
        elif use_fast:
            model       = MODELS["fast"]
            extra       = {}
            temperature = 0.8
            top_p       = 0.9
            max_tokens  = 8192
        else:
            model       = MODELS["primary"]
            extra       = {}
            temperature = 0.75
            top_p       = 0.9
            max_tokens  = 4096

        # Inject search/news context into the last user message
        msgs = list(messages)
        if context_injection and msgs and msgs[-1]["role"] == "user":
            original = msgs[-1]["content"]
            msgs[-1] = {
                "role": "user",
                "content": (
                    f"{context_injection}\n\n"
                    f"---\nUsing the above information, answer this:\n{original}"
                ),
            }

        full_msgs = [{"role": "system", "content": SYSTEM_PROMPT}] + msgs

        try:
            stream = self.client.chat.completions.create(
                model=model,
                messages=full_msgs,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
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
                content   = getattr(delta, "content", None)

                if reasoning:
                    yield {"type": "reasoning", "text": reasoning}
                if content:
                    yield {"type": "content", "text": content}

        except Exception as exc:
            yield {
                "type": "error",
                "text": f"[NIM ERROR] {type(exc).__name__}: {exc}",
            }
