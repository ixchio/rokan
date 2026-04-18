# rokan-vcr

**Rokan's Time-Travel Debugger** — Record, replay, and debug any agent execution. Powered by agent-vcr integration.

## Description

The moat. Rokan's secret weapon. Record full agent execution state at every step, replay from any checkpoint, and debug complex multi-step tasks without burning tokens. This is what separates Rokan from every other OpenClaw fork.

## Features

| Feature | Description | Benefit |
|---------|-------------|---------|
| **State Snapshots** | JSONL recording per step | Full execution history |
| **Checkpoint Replay** | Resume from any point | Debug without re-running |
| **Golden Run Cache** | Same query = instant replay | Zero token cost for repeats |
| **Git Integration** | ACID workspace isolation | Clean session branches |
| **Diff View** | Compare two executions | See what changed |
| **Time Travel** | Step forward/backward | Debug step by step |

## When to Use

- "Replay that last task"
- "Go back to step 3"
- "What happened at step 5?"
- "Debug why this failed"
- "Compare these two runs"
- "Cache this successful workflow"

## Setup

```bash
# 1. Install agent-vcr
pip install ai-agent-vcr

# 2. Configure storage
mkdir -p ~/.rokan/vcr_recordings

# 3. Optional: Enable git integration
git init ~/.rokan/vcr_workspace
```

## Configuration

Add to `~/.openclaw/config.yaml`:

```yaml
skills:
  rokan-vcr:
    enabled: true
    
    storage:
      directory: "~/.rokan/vcr_recordings"
      format: "jsonl"  # jsonl, sqlite, or git
      max_recordings: 100
      auto_cleanup_days: 30
    
    recording:
      record_states: true
      record_tools: true
      record_llm_calls: true
      record_memory: true
      compress: true
    
    cache:
      golden_runs: true
      cache_similarity_threshold: 0.95
      max_cache_size: 1000
    
    git:
      enabled: true
      workspace: "~/.rokan/vcr_workspace"
      auto_commit: true
      branch_per_session: true
    
    ui:
      show_timeline: true
      show_diff: true
      max_display_steps: 50
```

## Usage

### Automatic Recording
Every agent execution is automatically recorded:
```
User: "Search for Linux kernel updates"
[Rokan]: [Executing...] ✓ Done
       [Recording saved: rec_abc123.jsonl]
```

### Replay Execution
```
User: "Replay that search"
[Rokan]: Replaying from checkpoint rec_abc123...
       [Step 1/5] Intent: research
       [Step 2/5] Tool: tavily_search
       [Step 3/5] Tool: crawl4ai_extract
       [Step 4/5] LLM: synthesize_results
       [Step 5/5] Response generated
       ✓ Replay complete (0 tokens used)
```

### Step Back
```
User: "Go back to step 3"
[Rokan]: Rewinding to step 3/5...
       State restored.
       Continue from here? (y/n/edit)
```

### Debug Failed Run
```
User: "Debug why the last task failed"
[Rokan]: Analyzing recording rec_def456...
       
       Failure at Step 4: crawl4ai_extract
       Error: Timeout after 30s
       
       Options:
       1. Retry with longer timeout
       2. Skip this step
       3. Use alternative tool
       4. Edit parameters manually
```

### Golden Run Cache
```
User: "Check system status"
[Rokan]: [Cache hit! Golden run found]
       Replaying cached execution...
       ✓ Response from cache (0 tokens)
```

### Compare Runs
```
User: "Compare my last two research queries"
[Rokan]: 
┌─ Comparison: rec_abc123 vs rec_def456 ─┐
│                                        │
│ Query similarity: 78%                  │
│ Steps differ at: Step 3, Step 5        │
│                                        │
│ Step 3 diff:                           │
│   - rec_abc123: 3 sources crawled      │
│   - rec_def456: 5 sources crawled      │
│                                        │
│ Step 5 diff:                           │
│   - rec_abc123: Used GPT-4             │
│   - rec_def456: Used local model       │
│                                        │
│ Result quality: Similar (92% vs 89%)   │
│ Token cost: rec_def456 saved 45%       │
└────────────────────────────────────────┘
```

## API

### `vcr.start_recording(session_id=None)`
Start recording a new execution.

### `vcr.record_step(step_data)`
Record a step in the current execution.

### `vcr.stop_recording()`
Finalize and save recording.

### `vcr.list_recordings(limit=50)`
List all available recordings.

### `vcr.load_recording(recording_id)`
Load a recording for replay.

### `vcr.replay(recording_id, from_step=0, to_step=None)`
Replay execution from recording.

### `vcr.checkpoint()`
Create a manual checkpoint.

### `vcr.rollback(steps=1)`
Roll back N steps in current execution.

### `vcr.diff(rec_id_a, rec_id_b)`
Compare two recordings.

### `vcr.cache_query(query, recording_id)`
Cache a query-result pair.

### `vcr.check_cache(query)`
Check if query has cached result.

## Recording Format

```jsonl
# rec_abc123.jsonl
{"type": "session_start", "timestamp": "2025-04-05T20:00:00Z", "session_id": "sess_001"}
{"type": "step", "step": 1, "agent": "intent_analyzer", "input": "Search for AI news", "output": "intent: research", "state_hash": "a1b2c3"}
{"type": "tool_call", "step": 2, "tool": "tavily_search", "params": {"query": "AI news"}, "result": "...", "duration_ms": 1200}
{"type": "llm_call", "step": 3, "model": "deepseek-r2:7b", "prompt_tokens": 150, "completion_tokens": 200, "cost": 0}
{"type": "session_end", "timestamp": "2025-04-05T20:00:05Z", "total_steps": 5, "total_tokens": 350}
```

## Golden Run Workflow

1. **First Execution** → Record full trace
2. **Cache Key** → Hash of normalized query
3. **Similar Query** → Check cache first
4. **Cache Hit** → Replay recording (0 tokens)
5. **Cache Miss** → Execute normally, record

## Files

- `vcr_engine.py` — Core recording/replay engine
- `storage.py` — JSONL/SQLite storage backends
- `git_backend.py` — Git-based version control
- `cache.py` — Golden run caching
- `diff.py` — Recording comparison
- `timeline.py` — Step visualization

## License

MIT — Part of Rokan Skill Pack for OpenClaw
