# Rokan

**Ambient Intelligence for your machine. F.R.I.D.A.Y.-class desktop assistant.**

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Windows-black.svg)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)

## What is Rokan?

Rokan is a desktop AI assistant that actually *knows* your machine. Not a chatbot — an ambient intelligence that:

- 🧠 **Remembers everything** — persistent SQLite memory across sessions
- 🔍 **Searches when needed** — auto-detects when your question needs live data
- 🖥️ **Monitors your system** — proactive alerts for CPU, RAM, disk
- ⚡ **Routes to the right model** — primary, reasoning, fast, and code models
- 🗣️ **Speaks responses** — neural voice synthesis (edge-tts)
- 🔌 **Pluggable skills** — search, system, memory, code execution, and more

Built for developers who want a real assistant, not a wrapper around an API call.

## Quick Install

```bash
# Clone
git clone https://github.com/ixchio/rokan.git
cd rokan

# Install (works on Linux and Windows)
pip install -e .

# Set your API key (free at https://build.nvidia.com)
export NVIDIA_API_KEY="nvapi-..."   # Linux/Mac
# or: set NVIDIA_API_KEY=nvapi-...  # Windows

# Launch
rokan
```

That's it. No Docker. No external databases. No Node.js. Just Python.

## How It Works

```
┌─────────────────────────────────────────────────────────┐
│                     User Interface                       │
│              TUI (terminal)  ·  CLI  ·  Voice            │
└──────────────────────────┬──────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │  AGENT CORE │  ← The brain
                    │             │
                    │  • Intent detection
                    │  • Skill routing
                    │  • Memory recall
                    │  • Context assembly
                    │  • Fact extraction
                    └──────┬──────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
    ┌─────▼─────┐   ┌─────▼─────┐   ┌─────▼─────┐
    │  LLM      │   │  Skills   │   │  Memory   │
    │  Router   │   │  Registry │   │  Store    │
    │           │   │           │   │           │
    │ NVIDIA NIM│   │ /search   │   │ SQLite    │
    │ Ollama    │   │ /system   │   │ FTS5      │
    │ Groq      │   │ /memory   │   │ (zero     │
    │ OpenAI    │   │ /code     │   │  setup)   │
    └───────────┘   └───────────┘   └───────────┘
```

Every query flows through the Agent Core:
1. **Memory recall** — pull relevant memories and user facts
2. **Intent detection** — does this need web search? system info?
3. **Skill routing** — find the right skill to handle it
4. **Context assembly** — combine memory + search + system data
5. **LLM streaming** — send rich context to the model
6. **Fact extraction** — learn preferences from the conversation

## Usage

### TUI (default)
```bash
rokan           # Launch the terminal UI
```

The TUI features:
- Real-time system monitoring sidebar
- Streaming LLM responses
- Proactive alerts (CPU spikes, disk full, etc.)
- Voice output
- Slash commands for skills

### CLI
```bash
rokan ask "What's happening with AI today?"     # Auto-searches the web
rokan ask --think "Analyze this architecture"    # Uses reasoning model
rokan ask --code "Write a Python async server"   # Uses code model
rokan ask --fast "Quick: what's a mutex?"        # Uses fast model

rokan status                    # System + LLM + memory report
rokan remember "I use neovim"   # Store a fact
rokan recall "editor"           # Search memories
rokan memory                    # Memory statistics
rokan skills                    # List active skills
rokan system                    # System metrics
```

### Slash Commands (in TUI)
| Command | Effect |
|---------|--------|
| `/think <query>` | Use reasoning model (deep analysis) |
| `/fast <query>` | Use fast model (quick answers) |
| `/search <query>` | Force web search |
| `/system` | Show system status |
| `/memory` | Show memory stats |
| `/remember <fact>` | Store a fact |
| `/recall <query>` | Search memories |
| `/code <python>` | Execute code |
| `/skills` | List active skills |
| `/voice` | Toggle voice output |
| `/clear` | Clear chat |

## Model Stack (NVIDIA NIM — Free Tier)

| Slot | Model | Best For |
|------|-------|----------|
| PRIMARY | meta/llama-3.3-70b-instruct | General queries |
| REASONING | z-ai/glm4.7 | Deep analysis, complex problems |
| FAST | stepfun-ai/step-3.5-flash | Quick answers, low latency |
| CODE | qwen/qwq-32b | Code generation, debugging |

Get a free API key at [build.nvidia.com](https://build.nvidia.com).

## Configuration

Edit `config.yaml` in the repo root (or `~/.rokan/config.yaml`):

```yaml
persona:
  name: "Rokan"

llm:
  primary:
    provider: "nvidia-nim"
    model: "meta/llama-3.3-70b-instruct"

memory:
  backend: "sqlite"  # zero setup, cross-platform

system:
  enabled: true
  thresholds:
    cpu_percent: 80
    memory_percent: 85
    disk_percent: 90
```

## Skills

Rokan comes with 4 built-in skills, plus 7 expansion modules:

### Built-in (always active)
| Skill | What it does |
|-------|-------------|
| **search** | Auto-searches web when query needs live data |
| **system** | CPU/RAM/disk monitoring, process list |
| **memory** | Remember facts, recall context, track conversations |
| **code** | Sandboxed Python execution |

### Expansion Modules (in repo, wire-able)
| Module | Description |
|--------|-------------|
| `rokan-research/` | Tavily + Reddit + Twitter deep research |
| `rokan-jobs/` | Job monitoring with skill matching |
| `rokan-voice/` | Full local voice pipeline (Whisper + Piper) |
| `rokan-vcr/` | Execution recording and replay |

## Cross-Platform

| Feature | Linux | Windows |
|---------|-------|---------|
| TUI | ✓ | ✓ |
| CLI | ✓ | ✓ |
| LLM (NVIDIA NIM) | ✓ | ✓ |
| Memory (SQLite) | ✓ | ✓ |
| System monitoring | ✓ | ✓ |
| Voice (edge-tts) | ✓ | ✓ |
| Web search | ✓ | ✓ |

## API Keys

Only one is needed. Everything else is optional.

```bash
# Required — NVIDIA NIM (free tier)
export NVIDIA_API_KEY="nvapi-..."
```

## Contributing

1. Fork the repo
2. Create a skill in `rokan_core/skills.py` (subclass `Skill`)
3. Register it in `agent.py`
4. Submit PR

## Roadmap

- [ ] Ollama local model support (no internet needed)
- [ ] Groq fallback provider
- [ ] Screen awareness (screenshot + vision model)
- [ ] Calendar integration
- [ ] Custom wake word (local STT)
- [ ] Plugin system for third-party skills

## License

MIT — Use it, fork it, make it yours.

---

**Rokan** — *The System is online.*
