# Rokan for OpenClaw - Complete Package

## What You Got

A complete OpenClaw skill pack that transforms OpenClaw into **Rokan** — the Sung Jin-Woo edition AI assistant for Linux.

### Package Contents

```
rokan-skills/
├── README.md              # Full documentation
├── QUICKSTART.md          # 5-minute setup guide
├── LICENSE                # MIT License
├── config.yaml            # Rokan configuration
├── install.sh             # One-command installer
├── setup.py               # Python package setup
├── MANIFEST.in            # Package manifest
│
├── rokan-memory/          # 3-tier memory system
│   ├── SKILL.md
│   └── memory.py          # Qdrant + mxbai-embed-large
│
├── rokan-voice/           # Local voice pipeline
│   ├── SKILL.md
│   └── voice_pipeline.py  # openWakeWord + Whisper.cpp + Piper
│
├── rokan-research/        # Deep research agent
│   ├── SKILL.md
│   └── research_agent.py  # Tavily + Crawl4AI + Reddit + Twitter
│
├── rokan-jobs/            # Job monitoring
│   ├── SKILL.md
│   └── job_monitor.py     # Reddit/Twitter job scraping + matching
│
├── rokan-system/          # Linux system control
│   ├── SKILL.md
│   └── system_agent.py    # psutil + dbus monitoring
│
├── rokan-code/            # Sandboxed code execution
│   ├── SKILL.md
│   └── code_executor.py   # restrictedpython + subprocess sandbox
│
├── rokan-vcr/             # Time-travel debugger (THE MOAT)
│   ├── SKILL.md
│   └── vcr_engine.py      # agent-vcr integration
│
└── rokan_cli/             # CLI tools
    ├── __init__.py
    └── main.py
```

## Key Features

### 1. Three-Tier Memory
- **Episodic**: Conversation history (365 days)
- **Semantic**: Facts and knowledge (permanent)
- **Procedural**: Workflows and patterns (permanent)

### 2. Local Voice Pipeline
- Wake word: "Hey Rokan"
- STT: Whisper.cpp (local, fast)
- TTS: Piper (local, <50ms latency)
- **Fully offline** — no cloud

### 3. Research Agent
- Web search: Tavily + SearXNG
- Deep crawl: Crawl4AI
- Social: Reddit + Twitter APIs
- Real-time monitoring

### 4. Job Hunter
- Monitors r/forhire, r/hiring, r/remotejs, r/devopsjobs
- Twitter job searches
- Skill matching algorithm
- Desktop notifications

### 5. System Agent
- CPU/RAM/disk monitoring
- Process management
- Service control
- Proactive alerts

### 6. Code Sandbox
- Restricted Python execution
- Resource limits (30s, 512MB)
- Import whitelist/blacklist
- No network access

### 7. VCR Debugger (Your Moat)
- Record every agent step
- Replay from any checkpoint
- Golden Run Cache (zero tokens)
- Compare executions
- Git integration

## Stack (All Free)

| Component | Tool | Cost |
|-----------|------|------|
| LLM | Ollama (deepseek-r2:7b) | Free |
| Embeddings | mxbai-embed-large | Free |
| Vector DB | Qdrant (local Docker) | Free |
| Search | Tavily (free tier) | Free |
| STT | Whisper.cpp | Free |
| TTS | Piper | Free |
| Framework | OpenClaw | Free |

## Installation

```bash
# 1. Install OpenClaw
npm install -g openclaw@latest

# 2. Extract and install Rokan
tar -xzf rokan-skills.tar.gz
cd rokan-skills
chmod +x install.sh
./install.sh

# 3. Start
openclaw start
```

## Usage Examples

```bash
# System status
openclaw chat "What's my system status?"

# Research
openclaw skill rokan-research search "latest Linux kernel features"
openclaw skill rokan-research reddit r/linux "Wayland"

# Jobs
openclaw skill rokan-jobs start_monitoring
openclaw skill rokan-jobs search "remote AI engineer"

# VCR
openclaw skill rokan-vcr list
openclaw skill rokan-vcr replay rec_abc123

# Code
openclaw skill rokan-code calc "sum(range(100))"
```

## Why This Beats Building From Scratch

| Approach | Time | Effort | Features |
|----------|------|--------|----------|
| Build from scratch | 6 months | Full-time team | Basic |
| OpenClaw fork | 2 weeks | Part-time | Full |
| **Rokan skill pack** | **1 day** | **Minimal** | **Elite** |

You get:
- ✅ 310k-star runtime (OpenClaw)
- ✅ Multi-channel support (Telegram, Discord)
- ✅ Proactive task execution
- ✅ Self-extending skills
- ✅ Your VCR moat

## The Sung Jin-Woo Philosophy

> "I don't ask unnecessary questions. I execute."

Rokan is for developers who:
- Want Linux-native AI
- Refuse cloud lock-in
- Value privacy
- Need proactive monitoring
- Want jobs delivered to them

## Files Ready for Use

- `rokan-skills.tar.gz` — Complete package
- Extract and run `./install.sh`

---

**Rokan is ready. Execute.**
