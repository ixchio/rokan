# Rokan for OpenClaw

**The Player. Linux-first. No cloud leaks.**

Sung Jin-Woo edition AI assistant — built as an OpenClaw skill pack. Zero reinventing the wheel, maximum execution.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Platform](https://img.shields.io/badge/platform-Linux-black.svg)
![OpenClaw](https://img.shields.io/badge/OpenClaw-Skill%20Pack-green.svg)

## What is Rokan?

Rokan is a **personality + skill pack** for [OpenClaw](https://github.com/OpenClaw) — the 310k-star open-source AI assistant framework. Instead of building from scratch, you get:

- ✅ OpenClaw runtime (proactive, multi-channel, autonomous)
- ✅ Rokan personality (Sung Jin-Woo vibes — silent, precise, deadly)
- ✅ 7 specialized skills (memory, voice, research, jobs, system, code, vcr)
- ✅ 100% free stack (Ollama, Qdrant, Whisper.cpp, Piper)

## The Moat: rokan-vcr

**Time-travel debugging for AI agents.**

- Record every execution step
- Replay from any checkpoint (zero tokens)
- Golden Run Cache: same query = instant response
- Compare runs, debug failures, optimize workflows

No other OpenClaw fork has this.

## Skill Pack

| Skill | Description | Stack |
|-------|-------------|-------|
| `rokan-memory` | 3-tier memory (episodic, semantic, procedural) | Qdrant + mxbai-embed-large |
| `rokan-voice` | Local voice pipeline | openWakeWord + Whisper.cpp + Piper |
| `rokan-research` | Deep research + social scraping | Tavily + Crawl4AI + Reddit + Twitter |
| `rokan-jobs` | Real-time job monitoring | Reddit + Twitter + matching algo |
| `rokan-system` | Linux system control | psutil + dbus |
| `rokan-code` | Sandboxed Python execution | restrictedpython + docker |
| `rokan-vcr` | Time-travel debugger | agent-vcr integration |

## Quick Install

```bash
# 1. Install OpenClaw (needs Node 22+)
npm install -g openclaw@latest
openclaw onboard --install-daemon

# 2. Clone Rokan skills
git clone https://github.com/yourusername/rokan-skills.git
cd rokan-skills

# 3. Install
chmod +x install.sh
./install.sh

# 4. Start
openclaw start
```

## Configuration

Edit `~/.openclaw/config.yaml`:

```yaml
persona:
  name: "Rokan"
  tagline: "The Player. Linux-first. No cloud leaks."
  
llm:
  primary:
    provider: "ollama"
    model: "deepseek-r2:7b"
  fallbacks:
    - provider: "groq"
      model: "llama-3.3-70b-versatile"

skills:
  workspace: "~/.openclaw/skills/rokan"
  priority: "workspace"
```

## Usage

### Chat
```bash
openclaw chat "What's my system status?"
```

### Voice Mode
```bash
# Wake word: "Hey Rokan"
openclaw voice enable
```

### Job Monitoring
```bash
# Start background monitoring
openclaw skill rokan-jobs start_monitoring

# Instant search
openclaw skill rokan-jobs search "remote AI engineer"
```

### Research
```bash
# Deep research
openclaw skill rokan-research "Latest Linux kernel features"

# Reddit scan
openclaw skill rokan-research reddit r/linux "Wayland sentiment"

# Twitter tracking
openclaw skill rokan-research twitter "hiring AI engineer"
```

### VCR Replay
```bash
# List recordings
openclaw skill rokan-vcr list

# Replay execution
openclaw skill rokan-vcr replay rec_abc123

# Compare runs
openclaw skill rokan-vcr diff rec_abc123 rec_def456
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    OpenClaw Runtime                      │
│         (Multi-channel, Proactive, Autonomous)          │
└─────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼────┐       ┌────▼────┐       ┌────▼────┐
   │ Rokan   │       │ Skills  │       │ Memory  │
   │ Persona │       │ System  │       │ Layer   │
   └────┬────┘       └────┬────┘       └────┬────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
    ┌──────────────────────┼──────────────────────┐
    │                      │                      │
┌───▼───┐  ┌──────────┐  ┌─▼────┐  ┌────────┐  ┌▼──────┐
│rokan- │  │ rokan-   │  │rokan-│  │rokan-  │  │rokan- │
│memory │  │ voice    │  │research│ │jobs    │  │vcr    │
└───────┘  └──────────┘  └──────┘  └────────┘  └───────┘
```

## Stack (All Free)

| Component | Tool | Cost |
|-----------|------|------|
| LLM | Ollama (deepseek-r2:7b) | Free |
| Embeddings | mxbai-embed-large | Free |
| Vector DB | Qdrant (local) | Free |
| Search | Tavily (free tier) + SearXNG | Free |
| STT | Whisper.cpp | Free |
| TTS | Piper | Free |
| Wake Word | openWakeWord | Free |

## API Keys (Optional)

Local Ollama works without any API keys. For fallbacks:

```bash
# Groq (free tier: 1M tokens/day)
export GROQ_API_KEY="gsk_..."

# Tavily (free tier: 1000 searches/month)
export TAVILY_API_KEY="tvly-..."

# Reddit (free)
export REDDIT_CLIENT_ID="..."
export REDDIT_CLIENT_SECRET="..."

# Twitter (free tier: 500 posts/month)
export TWITTER_BEARER_TOKEN="..."
```

## Why OpenClaw + Rokan?

| Approach | Effort | Features | Maintenance |
|----------|--------|----------|-------------|
| Build from scratch | 6 months | Basic | Full-time |
| OpenClaw fork | 2 weeks | Full | Minimal |
| **OpenClaw + Rokan** | **1 day** | **Elite** | **Skill updates** |

## The Sung Jin-Woo Philosophy

> "I don't ask unnecessary questions. I execute."

Rokan is designed for developers who:
- Want a Linux-native AI assistant
- Refuse cloud lock-in
- Value privacy and local execution
- Need proactive system monitoring
- Want job opportunities delivered to them

## Contributing

1. Fork the repo
2. Create a skill: `mkdir rokan-yourskill && touch SKILL.md`
3. Follow the [OpenClaw skill spec](https://docs.openclaw.dev/skills)
4. Submit PR

## Roadmap

- [ ] IronClaw compatibility (hardened mode)
- [ ] GPU acceleration for voice
- [ ] More job sources (LinkedIn, AngelList)
- [ ] Screen awareness (scrot + vision model)
- [ ] Plugin marketplace

## License

MIT — Use it, fork it, make it yours.

## Credits

- OpenClaw team for the incredible runtime
- Sung Jin-Woo for the inspiration
- The Linux community for keeping it open

---

**Rokan** — *Arise.*
