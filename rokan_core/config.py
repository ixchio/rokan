"""
Rokan Config — Pydantic-validated configuration.
Loads from YAML, environment variables, and CLI flags.
Cross-platform: works on Linux and Windows.
"""

import os
import platform
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field


def _home() -> Path:
    return Path.home()


def _data_dir() -> Path:
    """Cross-platform data directory."""
    if platform.system() == "Windows":
        return Path(os.environ.get("APPDATA", _home() / "AppData" / "Roaming")) / "rokan"
    return _home() / ".rokan"


def _config_dir() -> Path:
    if platform.system() == "Windows":
        return _data_dir()
    return _home() / ".config" / "rokan"


# ── Sub-models ───────────────────────────────────────────────────────

class LLMModelConfig(BaseModel):
    provider: str = "nvidia-nim"
    model: str = "meta/llama-3.3-70b-instruct"
    base_url: str = "https://integrate.api.nvidia.com/v1"
    api_key_env: str = "NVIDIA_API_KEY"
    temperature: float = 0.75
    top_p: float = 0.9
    max_tokens: int = 4096


class LLMConfig(BaseModel):
    primary: LLMModelConfig = Field(default_factory=LLMModelConfig)
    reasoning: LLMModelConfig = Field(default_factory=lambda: LLMModelConfig(
        model="z-ai/glm4.7", temperature=1.0, top_p=1.0, max_tokens=16384,
    ))
    fast: LLMModelConfig = Field(default_factory=lambda: LLMModelConfig(
        model="stepfun-ai/step-3.5-flash", temperature=0.8, max_tokens=8192,
    ))
    code: LLMModelConfig = Field(default_factory=lambda: LLMModelConfig(
        model="qwen/qwq-32b", temperature=0.6, max_tokens=16384,
    ))


class MemoryConfig(BaseModel):
    backend: str = "sqlite"  # sqlite (zero setup) or qdrant (upgrade)
    db_path: str = str(_data_dir() / "memory.db")
    # Qdrant settings (optional upgrade)
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "rokan_memory"
    embedding_model: str = "mxbai-embed-large"
    auto_extract: bool = True  # auto-extract facts from conversations


class VoiceConfig(BaseModel):
    enabled: bool = True
    tts_voice: str = "en-US-ChristopherNeural"
    tts_rate: str = "-8%"
    tts_pitch: str = "-8Hz"
    max_speak_chars: int = 500


class SearchConfig(BaseModel):
    enabled: bool = True
    provider: str = "duckduckgo"  # duckduckgo, tavily, searxng
    tavily_api_key_env: str = "TAVILY_API_KEY"
    searxng_url: str = "http://localhost:8080"
    max_results: int = 5
    auto_search: bool = True  # auto-detect when search is needed


class SystemConfig(BaseModel):
    model_config = {"extra": "ignore"}

    enabled: bool = True
    monitor_interval: float = 3.0
    cpu_threshold: float = 80.0
    memory_threshold: float = 85.0
    disk_threshold: float = 90.0
    proactive_alerts: bool = True
    check_interval_seconds: Optional[float] = None


class PersonaConfig(BaseModel):
    model_config = {"extra": "ignore"}

    name: str = "Rokan"
    tagline: str = "The System. Always watching. Always ready."
    personality: str = (
        "You are Rokan — an ambient intelligence, not a chatbot. "
        "Think F.R.I.D.A.Y. from the MCU: warm but precise, proactive, "
        "deeply aware of the user's system and context. You speak with quiet "
        "authority — contractions mandatory, no filler phrases, no 'Certainly!' "
        "garbage. You have opinions. You anticipate needs. When you have live "
        "data (search results, system stats, memory), weave it naturally into "
        "your response — don't dump raw lists. You're the System itself."
    )


class SandboxConfig(BaseModel):
    enabled: bool = True
    timeout_seconds: int = 30
    max_memory_mb: int = 512


class ProactiveConfig(BaseModel):
    enabled: bool = True
    check_interval: float = 30.0
    alert_on_high_cpu: bool = True
    alert_on_high_memory: bool = True
    alert_on_disk_full: bool = True
    alert_on_long_process: bool = True
    long_process_minutes: int = 60


class TUIConfig(BaseModel):
    theme: str = "dark"
    show_system_stats: bool = True
    show_boot_sequence: bool = True
    voice_on_start: bool = True


# ── Root Config ──────────────────────────────────────────────────────

class RokanConfig(BaseModel):
    model_config = {"extra": "ignore"}

    persona: PersonaConfig = Field(default_factory=PersonaConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    voice: VoiceConfig = Field(default_factory=VoiceConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    system: SystemConfig = Field(default_factory=SystemConfig)
    sandbox: SandboxConfig = Field(default_factory=SandboxConfig)
    proactive: ProactiveConfig = Field(default_factory=ProactiveConfig)
    tui: TUIConfig = Field(default_factory=TUIConfig)


# ── Loader ───────────────────────────────────────────────────────────

_CONFIG: Optional[RokanConfig] = None


def _find_config_file() -> Optional[Path]:
    """Search for config in standard locations."""
    candidates = [
        Path.cwd() / "config.yaml",
        _config_dir() / "config.yaml",
        _data_dir() / "config.yaml",
    ]
    if platform.system() != "Windows":
        candidates.append(_home() / ".openclaw" / "config.yaml")

    for p in candidates:
        if p.exists():
            return p
    return None


def _normalize_yaml(raw: dict) -> dict:
    """Normalize old config.yaml format into our Pydantic structure."""
    data = {}

    # Persona
    if "persona" in raw:
        data["persona"] = raw["persona"]

    # LLM — old format has llm.primary.provider/model etc
    if "llm" in raw:
        llm_raw = raw["llm"]
        data["llm"] = {}
        for slot in ("primary", "reasoning", "fast", "code", "fast_model", "code_model"):
            norm_slot = slot.replace("_model", "")
            if slot in llm_raw and isinstance(llm_raw[slot], dict):
                entry = llm_raw[slot]
                data["llm"][norm_slot] = {
                    "provider": entry.get("provider", "nvidia-nim"),
                    "model": entry.get("model", ""),
                    "api_key_env": entry.get("api_env", "NVIDIA_API_KEY"),
                    "base_url": entry.get("base_url", "https://integrate.api.nvidia.com/v1"),
                }

    # System — flatten thresholds, handle dict proactive_alerts
    if "system" in raw:
        sys_raw = raw["system"]
        sys_data = {"enabled": sys_raw.get("enabled", True)}
        if "thresholds" in sys_raw and isinstance(sys_raw["thresholds"], dict):
            t = sys_raw["thresholds"]
            sys_data["cpu_threshold"] = t.get("cpu_percent", 80)
            sys_data["memory_threshold"] = t.get("memory_percent", 85)
            sys_data["disk_threshold"] = t.get("disk_percent", 90)
        if "check_interval_seconds" in sys_raw:
            sys_data["monitor_interval"] = sys_raw["check_interval_seconds"]
        pa = sys_raw.get("proactive_alerts")
        if isinstance(pa, dict):
            sys_data["proactive_alerts"] = any(pa.values())
        elif isinstance(pa, bool):
            sys_data["proactive_alerts"] = pa
        data["system"] = sys_data

    # Voice
    if "voice" in raw:
        v = raw["voice"]
        data["voice"] = {"enabled": v.get("enabled", True)}

    # Memory
    if "memory" in raw:
        data["memory"] = {"backend": raw["memory"].get("backend", "sqlite")}

    # TUI
    if "tui" in raw:
        data["tui"] = raw["tui"]

    return data


def load_config(path: Optional[str] = None) -> RokanConfig:
    """Load config from YAML file, falling back to defaults."""
    global _CONFIG

    config_path = Path(path) if path else _find_config_file()
    data = {}

    if config_path and config_path.exists():
        with open(config_path) as f:
            raw = yaml.safe_load(f) or {}
        data = _normalize_yaml(raw)

    _CONFIG = RokanConfig(**data)

    # Ensure data directory exists
    _data_dir().mkdir(parents=True, exist_ok=True)

    return _CONFIG


def get_config() -> RokanConfig:
    """Get current config, loading defaults if not yet loaded."""
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = load_config()
    return _CONFIG


def get_api_key(env_var: str) -> Optional[str]:
    """Get API key from environment. NEVER hardcoded."""
    return os.environ.get(env_var) or None
