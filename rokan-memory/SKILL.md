# rokan-memory

**Rokan's 3-Tier Memory System** — Episodic, Semantic, Procedural memory powered by Qdrant and mem0.

## Description

Implements a comprehensive memory architecture that allows Rokan to remember conversations, facts, and procedures across sessions. Uses local Qdrant vector database with mxbai-embed-large embeddings.

## When to Use

- User asks "What did we discuss before?" or "Remember that..."
- Storing important facts, preferences, or context
- Recalling previous solutions or workflows
- Building procedural knowledge over time

## Tier Structure

| Tier | Purpose | Retention | Example |
|------|---------|-----------|---------|
| **Episodic** | What happened | 365 days | "Yesterday we fixed nginx config" |
| **Semantic** | What you know | Permanent | "User prefers Python over Node.js" |
| **Procedural** | How to do things | Permanent | "Deploy workflow: git pull → docker restart" |

## Setup

```bash
# 1. Start Qdrant (Docker)
docker run -d -p 6333:6333 -v ~/.rokan/qdrant:/qdrant/storage qdrant/qdrant

# 2. Pull embedding model
ollama pull mxbai-embed-large

# 3. Install mem0 (optional enhancement)
pip install mem0ai
```

## Configuration

Add to `~/.openclaw/config.yaml`:

```yaml
skills:
  rokan-memory:
    qdrant:
      host: localhost
      port: 6333
      collection: rokan_memory
    embeddings:
      provider: ollama
      model: mxbai-embed-large
    tiers:
      episodic:
        enabled: true
        retention_days: 365
      semantic:
        enabled: true
      procedural:
        enabled: true
    mem0:
      enabled: true
```

## Usage

### Store Memory
```
User: "Remember that I prefer dark mode in all my editors"
→ Stores in semantic memory
```

### Recall Memory
```
User: "What did we work on yesterday?"
→ Queries episodic memory for recent events
```

### Procedural Memory
```
User: "Save this deployment workflow: pull, build, restart"
→ Stores as procedural step sequence
```

## API

### `memory.store(content, tier="semantic", metadata={})`
Store new memory in specified tier.

### `memory.recall(query, tier=None, limit=5)`
Retrieve relevant memories by query.

### `memory.summarize_session(session_id)`
Generate session summary for episodic storage.

### `memory.get_procedures(task_type)`
Get stored procedures for a task type.

## Dependencies

- `qdrant-client>=1.12.0`
- `ollama>=0.4.0`
- `mem0ai>=0.1.0` (optional)

## Files

- `memory.py` — Core memory manager
- `embedder.py` — Ollama embedding wrapper
- `retriever.py` — Hybrid BM25 + vector search

## License

MIT — Part of Rokan Skill Pack for OpenClaw
