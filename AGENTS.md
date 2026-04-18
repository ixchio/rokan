# Rokan — Repository Knowledge

## Architecture (v3.0)

Rokan is a F.R.I.D.A.Y.-class desktop AI assistant. 15 real system-control skills.
Electron desktop app with monochrome UI + Makima avatar.

### Layer 1: rokan_core/ (the brain)
- `agent.py` — Central orchestrator. ALL input → `RokanAgent.process()`.
  Pipeline: skill check (FIRST) → memory recall → search (only if needed) → system info → LLM stream → fact extraction.
  40-message sliding window prevents context overflow.
- `config.py` — Pydantic config from YAML + `~/.rokan/.env` auto-loading.
  `get_api_key()` reads env file on first call (no python-dotenv dep needed).
- `llm_router.py` — Multi-provider, 4 slots (primary/reasoning/fast/code). All NVIDIA NIM.
  System prompt lists all 15 capabilities so LLM knows what it can DO.
- `memory_store.py` — SQLite + FTS5. Three tiers. Full conversation persistence.
- `skills.py` — Base skill protocol. Built-in: search, system, memory, code.
- `skills_desktop.py` — FRIDAY skills: shell, launch, files, screenshot, clipboard,
  reminder, network, media, power, datetime, notify. All work without LLM.
- `proactive.py` — Background alerts for CPU/RAM/disk/long processes.

### Layer 2: rokan_gui/ (desktop app backend)
- `server.py` — Flask backend. SSE streaming for chat. REST for status/memory/avatar/history.
  `/api/history` returns past conversation for UI reload on restart.
  `/api/voice/speak` runs TTS in background thread (non-blocking).
- `static/` — Monochrome UI. No emojis, no gradients, no glow. #111/#999/#222.
  `avatar-default.png` — Makima avatar (119KB). Pulses when AI is streaming.

### Layer 3: electron/ (native app)
- `main.js` — Spawns Python backend, loads `.env`, creates venv, BrowserWindow.
  backgroundColor #111 to match theme. Tray icon support.

### Layer 4: rokan_cli/ + rokan_tui/ (alternative interfaces)
- CLI via Click, TUI via Textual. Both use RokanAgent.

## Skill Routing Logic (IMPORTANT)
1. Slash commands (`/run`, `/open`, etc.) → `_handle_slash()` → exact name lookup, then `find_handler()`
2. Natural language → `find_handler(threshold=0.5)` → skills with smart `can_handle()` checked FIRST
3. Only if no skill handled it → `_needs_search()` (conservative: won't trigger on "what is linux")
4. Only if query mentions system words → system stats injected
5. If skill returns `inject_as_context` but LLM is down → falls back to `display_raw`
6. Memory context always injected regardless

## Known Patterns & Gotchas
- `can_handle()` base implementation divides by total triggers — scores are low. Every important skill
  needs a custom `can_handle()` with phrase-level matching returning 0.7-0.9.
- `display_raw=True` → shown directly to user. `inject_as_context=True` → sent to LLM.
  Shell/launch/remind/notify use display_raw. Files/network/datetime use inject_as_context.
- `_needs_search()` was rewritten to be conservative. Only triggers on explicit "search for",
  "latest news", "weather", "stock price" etc. Old version triggered on "what is" and "today".
- `.env` loading: config.py reads `~/.rokan/.env` once, doesn't override existing env vars.
  Electron also loads the same file and passes as subprocess env. Both paths work.
- History: 40-msg sliding window in memory, full history persisted in SQLite. UI loads
  last 20 messages on boot via `/api/history`.

## Build & Run
```bash
pip install -e .
# Set key in ~/.rokan/.env OR export directly:
echo "NVIDIA_API_KEY=nvapi-..." > ~/.rokan/.env
rokan                    # TUI
python -m rokan_gui.server  # GUI backend (http://127.0.0.1:18991)
```

## API Keys
- **NVIDIA_API_KEY** — Required. Powers all 4 LLM slots via NVIDIA NIM.
- **TAVILY_API_KEY** — Optional. Only if switching search from DuckDuckGo to Tavily.
- No other keys needed. All 15 skills work locally with zero API keys.

## Testing
```bash
python -c "
from rokan_core.agent import RokanAgent
a = RokanAgent()
print(len(a.skills.list_skills()), 'skills')
r = list(a.process('/run echo test'))
print(r[0])
"
```
