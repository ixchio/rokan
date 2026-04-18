"""
Rokan VCR - Time-Travel Debugger
Record, replay, and debug agent executions
"""

import os
import json
import hashlib
import sqlite3
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class StepRecord:
    """Single step recording"""
    step_number: int
    timestamp: datetime
    agent: str
    input_data: str
    output_data: str
    state_hash: str
    tool_calls: List[Dict]
    metadata: Dict[str, Any]


@dataclass
class Recording:
    """Complete execution recording"""
    id: str
    session_id: str
    query: str
    started_at: datetime
    completed_at: Optional[datetime]
    steps: List[StepRecord]
    final_response: Optional[str]
    total_tokens: int
    metadata: Dict[str, Any]


class VCREngine:
    """
    Time-travel debugger for agent executions
    Records, replays, and caches agent runs
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # Storage settings
        self.record_dir = Path(os.path.expanduser(
            self.config.get("storage", {}).get("directory", "~/.rokan/vcr_recordings")
        ))
        self.record_dir.mkdir(parents=True, exist_ok=True)
        
        self.format = self.config.get("storage", {}).get("format", "jsonl")
        self.max_recordings = self.config.get("storage", {}).get("max_recordings", 100)
        self.auto_cleanup_days = self.config.get("storage", {}).get("auto_cleanup_days", 30)
        
        # Cache settings
        self.cache_enabled = self.config.get("cache", {}).get("golden_runs", True)
        self.cache_threshold = self.config.get("cache", {}).get("cache_similarity_threshold", 0.95)
        
        # Git integration
        self.git_enabled = self.config.get("git", {}).get("enabled", False)
        
        # Current recording
        self.current_recording: Optional[Recording] = None
        self.is_recording = False
        
        # Cache
        self.query_cache: Dict[str, str] = {}  # query_hash -> recording_id
        
        # Initialize storage
        self._init_storage()
    
    def _init_storage(self):
        """Initialize storage backend"""
        if self.format == "sqlite":
            self.db_path = self.record_dir / "recordings.db"
            self._init_sqlite()
        
        # Load existing cache
        self._load_cache()
    
    def _init_sqlite(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recordings (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                query TEXT,
                started_at TEXT,
                completed_at TEXT,
                steps TEXT,
                final_response TEXT,
                total_tokens INTEGER,
                metadata TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache (
                query_hash TEXT PRIMARY KEY,
                recording_id TEXT,
                created_at TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_cache(self):
        """Load query cache from storage"""
        cache_file = self.record_dir / "cache.json"
        if cache_file.exists():
            try:
                with open(cache_file) as f:
                    self.query_cache = json.load(f)
            except:
                pass
    
    def _save_cache(self):
        """Save query cache to storage"""
        cache_file = self.record_dir / "cache.json"
        with open(cache_file, 'w') as f:
            json.dump(self.query_cache, f)
    
    def _query_hash(self, query: str) -> str:
        """Generate hash for query"""
        # Normalize query
        normalized = query.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()[:16]
    
    def start_recording(self, session_id: str, query: str) -> str:
        """
        Start recording a new execution
        
        Returns:
            Recording ID
        """
        recording_id = f"rec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hashlib.md5(query.encode()).hexdigest()[:6]}"
        
        self.current_recording = Recording(
            id=recording_id,
            session_id=session_id,
            query=query,
            started_at=datetime.now(),
            completed_at=None,
            steps=[],
            final_response=None,
            total_tokens=0,
            metadata={}
        )
        
        self.is_recording = True
        
        return recording_id
    
    def record_step(self, 
                    agent: str,
                    input_data: str,
                    output_data: str,
                    tool_calls: List[Dict] = None,
                    metadata: Dict = None):
        """Record a step in the current execution"""
        if not self.is_recording or not self.current_recording:
            return
        
        step = StepRecord(
            step_number=len(self.current_recording.steps) + 1,
            timestamp=datetime.now(),
            agent=agent,
            input_data=input_data,
            output_data=output_data,
            state_hash=hashlib.md5(f"{input_data}{output_data}".encode()).hexdigest()[:16],
            tool_calls=tool_calls or [],
            metadata=metadata or {}
        )
        
        self.current_recording.steps.append(step)
    
    def stop_recording(self, final_response: str = None, total_tokens: int = 0):
        """Stop and save the current recording"""
        if not self.is_recording or not self.current_recording:
            return None
        
        self.current_recording.completed_at = datetime.now()
        self.current_recording.final_response = final_response
        self.current_recording.total_tokens = total_tokens
        
        # Save recording
        self._save_recording(self.current_recording)
        
        # Cache if successful
        if final_response and self.cache_enabled:
            query_hash = self._query_hash(self.current_recording.query)
            self.query_cache[query_hash] = self.current_recording.id
            self._save_cache()
        
        recording_id = self.current_recording.id
        
        # Reset
        self.current_recording = None
        self.is_recording = False
        
        return recording_id
    
    def _save_recording(self, recording: Recording):
        """Save recording to storage"""
        if self.format == "sqlite":
            self._save_sqlite(recording)
        else:
            self._save_jsonl(recording)
    
    def _save_sqlite(self, recording: Recording):
        """Save to SQLite"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO recordings 
            (id, session_id, query, started_at, completed_at, steps, 
             final_response, total_tokens, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            recording.id,
            recording.session_id,
            recording.query,
            recording.started_at.isoformat(),
            recording.completed_at.isoformat() if recording.completed_at else None,
            json.dumps([{
                "step_number": s.step_number,
                "timestamp": s.timestamp.isoformat(),
                "agent": s.agent,
                "input_data": s.input_data,
                "output_data": s.output_data,
                "state_hash": s.state_hash,
                "tool_calls": s.tool_calls,
                "metadata": s.metadata
            } for s in recording.steps]),
            recording.final_response,
            recording.total_tokens,
            json.dumps(recording.metadata)
        ))
        
        conn.commit()
        conn.close()
    
    def _save_jsonl(self, recording: Recording):
        """Save to JSONL file"""
        filepath = self.record_dir / f"{recording.id}.jsonl"
        
        with open(filepath, 'w') as f:
            # Header
            f.write(json.dumps({
                "type": "recording_start",
                "id": recording.id,
                "session_id": recording.session_id,
                "query": recording.query,
                "started_at": recording.started_at.isoformat()
            }) + '\n')
            
            # Steps
            for step in recording.steps:
                f.write(json.dumps({
                    "type": "step",
                    "step_number": step.step_number,
                    "timestamp": step.timestamp.isoformat(),
                    "agent": step.agent,
                    "input_data": step.input_data,
                    "output_data": step.output_data,
                    "state_hash": step.state_hash,
                    "tool_calls": step.tool_calls,
                    "metadata": step.metadata
                }) + '\n')
            
            # Footer
            f.write(json.dumps({
                "type": "recording_end",
                "completed_at": recording.completed_at.isoformat() if recording.completed_at else None,
                "final_response": recording.final_response,
                "total_tokens": recording.total_tokens,
                "step_count": len(recording.steps)
            }) + '\n')
    
    def load_recording(self, recording_id: str) -> Optional[Recording]:
        """Load a recording by ID"""
        if self.format == "sqlite":
            return self._load_sqlite(recording_id)
        else:
            return self._load_jsonl(recording_id)
    
    def _load_jsonl(self, recording_id: str) -> Optional[Recording]:
        """Load from JSONL file"""
        filepath = self.record_dir / f"{recording_id}.jsonl"
        
        if not filepath.exists():
            return None
        
        recording = None
        steps = []
        
        with open(filepath) as f:
            for line in f:
                data = json.loads(line)
                
                if data["type"] == "recording_start":
                    recording = Recording(
                        id=data["id"],
                        session_id=data["session_id"],
                        query=data["query"],
                        started_at=datetime.fromisoformat(data["started_at"]),
                        completed_at=None,
                        steps=[],
                        final_response=None,
                        total_tokens=0,
                        metadata={}
                    )
                
                elif data["type"] == "step":
                    steps.append(StepRecord(
                        step_number=data["step_number"],
                        timestamp=datetime.fromisoformat(data["timestamp"]),
                        agent=data["agent"],
                        input_data=data["input_data"],
                        output_data=data["output_data"],
                        state_hash=data["state_hash"],
                        tool_calls=data.get("tool_calls", []),
                        metadata=data.get("metadata", {})
                    ))
                
                elif data["type"] == "recording_end":
                    if recording:
                        recording.completed_at = datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None
                        recording.final_response = data.get("final_response")
                        recording.total_tokens = data.get("total_tokens", 0)
                        recording.steps = steps
        
        return recording
    
    def check_cache(self, query: str) -> Optional[str]:
        """
        Check if query has cached recording
        
        Returns:
            Recording ID if cache hit, None otherwise
        """
        if not self.cache_enabled:
            return None
        
        query_hash = self._query_hash(query)
        return self.query_cache.get(query_hash)
    
    def list_recordings(self, limit: int = 50) -> List[Dict]:
        """List all recordings"""
        recordings = []
        
        if self.format == "jsonl":
            for filepath in sorted(self.record_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True):
                recording = self._load_jsonl(filepath.stem)
                if recording:
                    recordings.append({
                        "id": recording.id,
                        "query": recording.query[:100] + "..." if len(recording.query) > 100 else recording.query,
                        "started_at": recording.started_at.isoformat(),
                        "steps": len(recording.steps),
                        "cached": self._query_hash(recording.query) in self.query_cache
                    })
        
        return recordings[:limit]
    
    def replay(self, recording_id: str, from_step: int = 0, to_step: int = None) -> Dict:
        """
        Replay a recording
        
        Returns:
            Replay result with steps and final response
        """
        recording = self.load_recording(recording_id)
        
        if not recording:
            return {"error": "Recording not found"}
        
        steps = recording.steps[from_step:to_step]
        
        return {
            "recording_id": recording_id,
            "query": recording.query,
            "replayed_steps": len(steps),
            "total_steps": len(recording.steps),
            "steps": [{
                "step_number": s.step_number,
                "agent": s.agent,
                "input": s.input_data,
                "output": s.output_data
            } for s in steps],
            "final_response": recording.final_response,
            "replay_mode": True,
            "tokens_used": 0  # Replays use no tokens
        }
    
    def diff(self, recording_id_a: str, recording_id_b: str) -> Dict:
        """Compare two recordings"""
        rec_a = self.load_recording(recording_id_a)
        rec_b = self.load_recording(recording_id_b)
        
        if not rec_a or not rec_b:
            return {"error": "One or both recordings not found"}
        
        # Compare queries
        query_similarity = self._text_similarity(rec_a.query, rec_b.query)
        
        # Compare step counts
        step_diff = len(rec_a.steps) - len(rec_b.steps)
        
        # Find differing steps
        differing_steps = []
        for i, (step_a, step_b) in enumerate(zip(rec_a.steps, rec_b.steps)):
            if step_a.state_hash != step_b.state_hash:
                differing_steps.append(i + 1)
        
        return {
            "recording_a": recording_id_a,
            "recording_b": recording_id_b,
            "query_similarity": query_similarity,
            "steps_a": len(rec_a.steps),
            "steps_b": len(rec_b.steps),
            "step_difference": step_diff,
            "differing_steps": differing_steps,
            "final_response_similarity": self._text_similarity(
                rec_a.final_response or "",
                rec_b.final_response or ""
            )
        }
    
    def _text_similarity(self, a: str, b: str) -> float:
        """Calculate simple text similarity"""
        if not a or not b:
            return 0.0
        
        # Simple word overlap
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        
        if not words_a or not words_b:
            return 0.0
        
        intersection = words_a & words_b
        union = words_a | words_b
        
        return len(intersection) / len(union)


# OpenClaw skill interface
class RokanVCRSkill:
    """OpenClaw skill interface for rokan-vcr"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.vcr = VCREngine(config)
    
    def list(self, limit: int = 50) -> str:
        """List recordings"""
        recordings = self.vcr.list_recordings(limit)
        
        if not recordings:
            return "No recordings found."
        
        output = ["Recordings:"]
        for r in recordings:
            cached = " [CACHED]" if r.get("cached") else ""
            output.append(f"  {r['id']}{cached}")
            output.append(f"    Query: {r['query'][:60]}...")
            output.append(f"    Steps: {r['steps']} | {r['started_at']}")
        
        return "\n".join(output)
    
    def replay(self, recording_id: str) -> str:
        """Replay a recording"""
        result = self.vcr.replay(recording_id)
        
        if "error" in result:
            return f"Error: {result['error']}"
        
        output = []
        output.append(f"Replaying: {result['query'][:80]}")
        output.append(f"Steps replayed: {result['replayed_steps']}/{result['total_steps']}")
        output.append(f"Tokens used: {result['tokens_used']}")
        output.append("\nFinal response:")
        output.append(result['final_response'])
        
        return "\n".join(output)
    
    def diff(self, recording_id_a: str, recording_id_b: str) -> str:
        """Compare two recordings"""
        result = self.vcr.diff(recording_id_a, recording_id_b)
        
        if "error" in result:
            return f"Error: {result['error']}"
        
        output = []
        output.append(f"Comparing {recording_id_a} vs {recording_id_b}")
        output.append(f"Query similarity: {result['query_similarity']:.1%}")
        output.append(f"Steps: {result['steps_a']} vs {result['steps_b']} (diff: {result['step_difference']:+d})")
        output.append(f"Differing steps: {result['differing_steps']}")
        output.append(f"Response similarity: {result['final_response_similarity']:.1%}")
        
        return "\n".join(output)
    
    def cache_status(self) -> str:
        """Get cache status"""
        return f"Cached queries: {len(self.vcr.query_cache)}"


# Export for OpenClaw
skill = RokanVCRSkill
