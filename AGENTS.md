# Rokan — Repository Knowledge

## Architecture (v3.0)

Rokan is a F.R.I.D.A.Y.-class ambient intelligence. 20 skills. Voice loop.
Screen awareness. Automation engine. Git/calendar/email integration.
Electron desktop app with floating Makima overlay + monochrome UI.

### Layer 1: rokan_core/ (the brain)
- `agent.py` — Central orchestrator. ALL input → `RokanAgent.process()`.
  Pipeline: skill check (FIRST) → screen context → memory → search → system → LLM → fact extraction.
  40-message sliding window. Voice/screen/automation engines wired in.
- `config.py` — Pydantic config + `~/.rokan/.env` auto-loading.
- `llm_router.py` — 4 LLM slots (primary/reasoning/fast/code) via NVIDIA NIM.
- `memory_store.py` — SQLite + FTS5. Three tiers. Conversation persistence.
- `skills.py` — Base skill protocol: search, system, memory, code.
- `skills_desktop.py` — 11 skills: shell, launch, files, screenshot, clipboard,
  reminder, network, media, power, datetime, notify.
- `skills_integrations.py` — 5 skills: git, calendar, email, briefing, automate.
- `voice_engine.py` — Full voice loop: wake word → STT (faster-whisper) → agent → TTS (edge-tts).
  Push-to-talk via API. All deps optional, graceful degradation.
- `screen_aware.py` — Background thread: active window, user state detection
  (coding/browsing/terminal/media/gaming/idle), periodic OCR. Context injected into every LLM call.
- `automations.py` — Natural language cron + event triggers. SQLite-backed.
  Supports: daily, weekly, interval, idle, system metric triggers.
- `proactive.py` — Background CPU/RAM/disk/process alerts.

### Layer 2: rokan_gui/ (desktop app backend)
- `server.py` — Flask. SSE streaming. REST endpoints for everything:
  `/api/chat`, `/api/status`, `/api/avatar`, `/api/history`,
  `/api/screen`, `/api/voice/*`, `/api/automations`, `/api/remember`, `/api/recall`.
- `static/` — Monochrome UI (#111/#999/#222). Makima avatar with pulse animation.

### Layer 3: electron/ (native app)
- `main.js` — Python backend spawner + main window + floating overlay widget.
  Overlay: 64px avatar circle, always-on-top, bottom-right, transparent, draggable.
  Click opens main window. Tray icon support.

### Layer 4: rokan_cli/ + rokan_tui/
- CLI via Click, TUI via Textual. Both use RokanAgent.

## 20 Skills
| Skill | Type | What it does |
|-------|------|-------------|
| shell | display_raw | Run terminal commands |
| launch | display_raw | Open apps by name |
| git | both | Git status/log/diff/branch/commit |
| datetime | inject | Current time/date |
| briefing | inject | Morning briefing (weather+system+calendar+email+git) |
| system | inject | CPU/RAM/disk stats |
| reminder | display_raw | Timers with desktop notifications |
| calendar | inject | Google Calendar or calcurse |
| automate | display_raw | Create/list/manage automations |
| memory | display_raw | Store/recall facts |
| files | inject | Find files, disk usage |
| email | inject | IMAP inbox check |
| search | inject | DuckDuckGo web search |
| screenshot | inject | Screen capture + OCR |
| clipboard | both | Read/write clipboard |
| network | inject | IP, ping, connectivity |
| media | display_raw | Volume/brightness/playback |
| code | display_raw | Python sandbox |
| notify | display_raw | Desktop notifications |
| power | display_raw | Lock/sleep/shutdown |

## Routing Logic
1. Slash commands → `_handle_slash()` → exact name, then `find_handler(threshold=0.8)`
2. Natural language → `find_handler(threshold=0.5)` → skills checked FIRST
3. Screen context injected always (if running)
4. Search only on explicit triggers ("search for", "latest news", "weather")
5. If skill returns `inject_as_context` but LLM down → fallback to `display_raw`

## Key Patterns
- Every important skill needs custom `can_handle()` with phrase matching (base is too weak)
- `display_raw=True` → shown directly. `inject_as_context=True` → through LLM
- Voice engine doesn't auto-start mic — requires explicit user consent
- Automations stored in `~/.rokan/automations.db` — separate from memory.db
- `.env` loading: config.py reads `~/.rokan/.env` once, doesn't override existing env vars

## Setup
```bash
pip install -e .                    # Core
pip install -e ".[voice]"           # + voice (sounddevice, faster-whisper, openwakeword)
echo "NVIDIA_API_KEY=nvapi-..." > ~/.rokan/.env

# Optional email:
echo "IMAP_SERVER=imap.gmail.com" >> ~/.rokan/.env
echo "IMAP_USER=you@gmail.com" >> ~/.rokan/.env
echo "IMAP_PASSWORD=app-password" >> ~/.rokan/.env

# Optional tools (for full screen awareness):
sudo apt install xdotool xprintidle tesseract-ocr scrot
```

## API Keys
- **NVIDIA_API_KEY** — Required for LLM. All 20 skills work without it.
- **IMAP_SERVER/USER/PASSWORD** — Optional, for email skill.
- No other keys needed.
