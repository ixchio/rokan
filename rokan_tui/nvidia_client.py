"""
NVIDIA NIM Client — Legacy wrapper. Now delegates to rokan_core.llm_router.
Kept for backward compatibility with CLI commands that import MODELS.
"""

import os
from openai import OpenAI


MODELS = {
    "primary":   "meta/llama-3.3-70b-instruct",
    "reasoning": "z-ai/glm4.7",
    "fast":      "stepfun-ai/step-3.5-flash",
    "code":      "qwen/qwq-32b",
}


class NvidiaNIMClient:
    """
    Streaming chat client backed by NVIDIA NIM free-tier endpoints.
    API key is read from NVIDIA_API_KEY environment variable — NEVER hardcoded.
    """

    def __init__(self, api_key: str | None = None):
        key = api_key or os.getenv("NVIDIA_API_KEY", "")
        self._available = bool(key)

        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=key or "placeholder",
        )

    def chat_stream(
        self,
        messages: list[dict],
        *,
        use_reasoning: bool = False,
        use_code: bool = False,
        use_fast: bool = False,
        context_injection: str | None = None,
    ):
        """Yield dicts: {"type": "content"|"reasoning"|"error", "text": str}"""
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

        if use_reasoning:
            model, extra = MODELS["reasoning"], {
                "extra_body": {"chat_template_kwargs": {"enable_thinking": True, "clear_thinking": False}}
            }
            temperature, top_p, max_tokens = 1.0, 1.0, 16384
        elif use_code:
            model, extra = MODELS["code"], {}
            temperature, top_p, max_tokens = 0.6, 0.9, 16384
        elif use_fast:
            model, extra = MODELS["fast"], {}
            temperature, top_p, max_tokens = 0.8, 0.9, 8192
        else:
            model, extra = MODELS["primary"], {}
            temperature, top_p, max_tokens = 0.75, 0.9, 4096

        msgs = list(messages)
        if context_injection and msgs and msgs[-1]["role"] == "user":
            original = msgs[-1]["content"]
            msgs[-1] = {
                "role": "user",
                "content": f"{context_injection}\n\n---\nUsing the above context, respond to:\n{original}",
            }

        system_prompt = (
            "You are Rokan — an ambient intelligence, not a chatbot. "
            "Warm but precise, proactive, direct. Contractions mandatory. "
            "No filler phrases. You have opinions. You are the System."
        )
        full_msgs = [{"role": "system", "content": system_prompt}] + msgs

        try:
            stream = self.client.chat.completions.create(
                model=model, messages=full_msgs,
                temperature=temperature, top_p=top_p, max_tokens=max_tokens,
                stream=True, **extra,
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
            yield {"type": "error", "text": f"[NIM ERROR] {type(exc).__name__}: {exc}"}
