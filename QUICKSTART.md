# Rokan Quick Start Guide

Get Rokan running in 5 minutes.

## Prerequisites

- Linux (Ubuntu 22.04+ recommended)
- Node.js 22+
- Python 3.10+
- Docker (optional, for Qdrant)

## Step 1: Install OpenClaw

```bash
npm install -g openclaw@latest
openclaw onboard --install-daemon
```

## Step 2: Install Rokan Skills

```bash
cd rokan-skills
chmod +x install.sh
./install.sh
```

This will:
- Install Python dependencies
- Pull Ollama models (deepseek-r2:7b, mxbai-embed-large)
- Start Qdrant in Docker
- Download voice models
- Configure OpenClaw with Rokan persona

## Step 3: Start Rokan

```bash
openclaw start
```

## Step 4: Test

```bash
# Chat with Rokan
openclaw chat "What's my system status?"

# Search
openclaw skill rokan-research search "latest AI breakthroughs"

# Job monitoring
openclaw skill rokan-jobs start_monitoring

# Check recordings
openclaw skill rokan-vcr list
```

## Common Commands

| Command | Description |
|---------|-------------|
| `openclaw start` | Start Rokan |
| `openclaw stop` | Stop Rokan |
| `openclaw chat "..."` | Send message |
| `openclaw status` | Show status |
| `rokan system` | System status |
| `rokan jobs` | Job matches |

## Directory Structure

```
~/.openclaw/
├── config.yaml          # Rokan configuration
└── skills/
    └── rokan/           # Rokan skills
        ├── rokan-memory/
        ├── rokan-voice/
        ├── rokan-research/
        ├── rokan-jobs/
        ├── rokan-system/
        ├── rokan-code/
        └── rokan-vcr/

~/.rokan/
├── logs/                # Log files
├── models/              # Voice models
├── sandbox/             # Code sandbox
├── vcr_recordings/      # Execution recordings
└── qdrant/              # Vector database
```

## Configuration

Edit `~/.openclaw/config.yaml`:

```yaml
persona:
  name: "Rokan"
  
llm:
  primary:
    model: "deepseek-r2:7b"

jobs:
  profile:
    skills:
      - python
      - machine learning
```

## Troubleshooting

### Ollama not found
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull deepseek-r2:7b
```

### Qdrant not running
```bash
docker run -d -p 6333:6333 qdrant/qdrant
```

### Permission denied
```bash
sudo usermod -aG docker $USER
# Log out and back in
```

## Next Steps

- Read [README.md](README.md) for full documentation
- Explore skills in `~/.openclaw/skills/rokan/`
- Customize your config in `~/.openclaw/config.yaml`

---

**Rokan is ready. Execute.**
