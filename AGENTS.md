# Rokan — Repository Knowledge

## Architecture (v2.0)

Rokan is a F.R.I.D.A.Y.-class desktop AI assistant with 3 layers:

### Layer 1: rokan_core/ (the brain)
- `agent.py` — Central orchestrator. ALL user input flows through `RokanAgent.process()`.
  Pipeline: memory recall → intent detection → skill routing → context assembly → LLM stream → fact extraction.
- `config.py` — Pydantic config. Loads from `config.yaml`, normalizes old YAML format.
  All sub-models use `extra="ignore"` for backward compatibility.
- `llm_router.py` — Multi-provider LLM abstraction. NVIDIA NIM primary. Uses OpenAI-compatible API.
  API keys from environment only — NEVER hardcoded.
- `memory_store.py` — SQLite + FTS5 persistent memory. Three tiers: episodic, semantic, procedural.
  Also stores full conversation history.
- `skills.py` — Pluggable skill protocol. Built-in: search, system, memory, code.
  Skills declare `triggers` and `can_handle()` returns 0.0-1.0 confidence.
- `proactive.py` — Background monitoring thread. Fires alerts for CPU/RAM/disk/long processes.

### Layer 2: rokan_tui/ (interface)
- `app.py` — Textual TUI. Uses `RokanAgent` exclusively. Dynamic boot sequence.
- `voice.py` — edge-tts synthesis (Microsoft neural voices). Cross-platform.
- `search.py` — DuckDuckGo web/news search. Used by SearchSkill.
- `system_monitor.py` — psutil background thread for sidebar stats.
- `styles.tcss` — Dark void theme (Solo Leveling aesthetic).
- `nvidia_client.py` — Legacy wrapper, kept for CLI backward compat.

### Layer 3: rokan_cli/ (commands)
- `main.py` — Click CLI. Commands: tui, ask, status, remember, recall, memory, skills, models, system, setup.

### Expansion Modules (standalone, not wired into core yet)
- `rokan-research/` — Tavily + Reddit + Twitter research agent
- `rokan-jobs/` — Job monitoring with skill matching
- `rokan-voice/` — Full Whisper.cpp + Piper voice pipeline
- `rokan-vcr/` — Execution recording and replay
- `rokan-system/` — Advanced Linux system agent
- `rokan-code/` — Docker-sandboxed code execution
- `rokan-memory/` — Qdrant vector memory

## Key Design Decisions
- SQLite for memory (zero setup, cross-platform) — Qdrant is optional upgrade
- FTS5 for search instead of vector embeddings (faster, no model needed)
- Skills are Python classes with a simple protocol, not a framework dependency
- Config uses Pydantic with `extra="ignore"` to handle old YAML formats
- API keys from env vars only — security-first
- Cross-platform: pathlib throughout, platform.system() for OS detection

## Build & Run
```bash
pip install -e .
export NVIDIA_API_KEY="nvapi-..."
rokan                    # TUI
rokan ask "question"     # CLI
rokan status             # Status report
```

## Testing
```bash
python -c "from rokan_core.agent import RokanAgent; a = RokanAgent(); print('OK')"
rokan setup              # Check dependencies
rokan status             # Full system report
```
