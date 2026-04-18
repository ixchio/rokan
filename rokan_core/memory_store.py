"""
Rokan Memory Store — Persistent memory using SQLite.
Zero setup, cross-platform, no Docker required.
Qdrant is an optional upgrade path for vector search.

Three tiers:
  - Episodic: conversation history (auto-stored, auto-recalled)
  - Semantic: facts, preferences, knowledge (extracted by LLM)
  - Procedural: workflows, patterns (user-taught or learned)
"""

from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from rokan_core.config import get_config


class MemoryStore:
    """SQLite-backed persistent memory. Just works."""

    def __init__(self, db_path: Optional[str] = None):
        cfg = get_config().memory
        self._db_path = db_path or cfg.db_path
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS memories (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    tier        TEXT NOT NULL,  -- episodic, semantic, procedural
                    content     TEXT NOT NULL,
                    session_id  TEXT,
                    metadata    TEXT DEFAULT '{}',
                    created_at  TEXT NOT NULL,
                    updated_at  TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_tier ON memories(tier);
                CREATE INDEX IF NOT EXISTS idx_session ON memories(session_id);
                CREATE INDEX IF NOT EXISTS idx_created ON memories(created_at);

                CREATE TABLE IF NOT EXISTS conversations (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id  TEXT NOT NULL,
                    role        TEXT NOT NULL,
                    content     TEXT NOT NULL,
                    created_at  TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session_id);

                CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts
                    USING fts5(content, tier, metadata);
            """)

    # ── Conversation History ─────────────────────────────────────

    def save_message(self, session_id: str, role: str, content: str):
        """Save a conversation message (auto-called by agent)."""
        now = datetime.now().isoformat()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO conversations (session_id, role, content, created_at) VALUES (?,?,?,?)",
                (session_id, role, content, now),
            )

    def get_conversation(self, session_id: str, limit: int = 50) -> list[dict]:
        """Get conversation history for a session."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT role, content, created_at FROM conversations "
                "WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def get_recent_sessions(self, limit: int = 10) -> list[dict]:
        """Get recent session summaries."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT session_id, MIN(created_at) as started, "
                "MAX(created_at) as last_msg, COUNT(*) as msg_count "
                "FROM conversations GROUP BY session_id "
                "ORDER BY last_msg DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Memory Storage ───────────────────────────────────────────

    def store(
        self,
        content: str,
        tier: str = "semantic",
        session_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> int:
        """Store a memory entry. Returns memory ID."""
        now = datetime.now().isoformat()
        meta_json = json.dumps(metadata or {})

        with self._conn() as conn:
            cursor = conn.execute(
                "INSERT INTO memories (tier, content, session_id, metadata, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?)",
                (tier, content, session_id, meta_json, now, now),
            )
            mem_id = cursor.lastrowid
            # Also index in FTS
            conn.execute(
                "INSERT INTO memory_fts (rowid, content, tier, metadata) VALUES (?,?,?,?)",
                (mem_id, content, tier, meta_json),
            )
        return mem_id

    def recall(
        self,
        query: str,
        tier: Optional[str] = None,
        limit: int = 5,
    ) -> list[dict]:
        """Search memories using full-text search. Fast, no embeddings needed."""
        # Sanitize query for FTS5
        fts_query = " OR ".join(
            f'"{w}"' for w in query.split() if len(w) > 2
        )
        if not fts_query:
            return []

        tier_filter = f"AND tier = '{tier}'" if tier else ""

        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT m.id, m.tier, m.content, m.session_id, m.metadata, "
                f"m.created_at, rank "
                f"FROM memory_fts f "
                f"JOIN memories m ON f.rowid = m.id "
                f"WHERE memory_fts MATCH ? {tier_filter} "
                f"ORDER BY rank LIMIT ?",
                (fts_query, limit),
            ).fetchall()

        return [
            {
                "id": r["id"],
                "tier": r["tier"],
                "content": r["content"],
                "session_id": r["session_id"],
                "metadata": json.loads(r["metadata"]) if r["metadata"] else {},
                "created_at": r["created_at"],
                "relevance": abs(r["rank"]),
            }
            for r in rows
        ]

    def get_by_tier(self, tier: str, limit: int = 20) -> list[dict]:
        """Get all memories of a specific tier."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, tier, content, metadata, created_at "
                "FROM memories WHERE tier = ? ORDER BY created_at DESC LIMIT ?",
                (tier, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_facts(self, limit: int = 20) -> list[dict]:
        """Get semantic memories (facts about the user)."""
        return self.get_by_tier("semantic", limit)

    def get_procedures(self, limit: int = 10) -> list[dict]:
        """Get procedural memories (workflows/patterns)."""
        return self.get_by_tier("procedural", limit)

    # ── Context Building ─────────────────────────────────────────

    def build_context(self, query: str, session_id: Optional[str] = None) -> str:
        """
        Build a context string for LLM injection.
        Combines: relevant memories + recent conversation + user facts.
        This is called automatically before every LLM call.
        """
        parts = []

        # Relevant memories
        memories = self.recall(query, limit=3)
        if memories:
            mem_text = "\n".join(
                f"- [{m['tier']}] {m['content']}" for m in memories
            )
            parts.append(f"[RELEVANT MEMORIES]\n{mem_text}")

        # User facts/preferences
        facts = self.get_facts(limit=5)
        if facts:
            fact_text = "\n".join(f"- {f['content']}" for f in facts)
            parts.append(f"[USER CONTEXT]\n{fact_text}")

        if not parts:
            return ""

        return "\n\n".join(parts)

    # ── Cleanup ──────────────────────────────────────────────────

    def cleanup_old(self, days: int = 365):
        """Remove episodic memories older than N days."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        with self._conn() as conn:
            # Get IDs to delete
            rows = conn.execute(
                "SELECT id FROM memories WHERE tier = 'episodic' AND created_at < ?",
                (cutoff,),
            ).fetchall()
            ids = [r["id"] for r in rows]
            if ids:
                placeholders = ",".join("?" * len(ids))
                conn.execute(f"DELETE FROM memories WHERE id IN ({placeholders})", ids)
                conn.execute(f"DELETE FROM memory_fts WHERE rowid IN ({placeholders})", ids)
        return len(ids) if 'ids' in dir() else 0

    def stats(self) -> dict:
        """Memory statistics."""
        with self._conn() as conn:
            tier_counts = conn.execute(
                "SELECT tier, COUNT(*) as count FROM memories GROUP BY tier"
            ).fetchall()
            conv_count = conn.execute(
                "SELECT COUNT(DISTINCT session_id) as sessions FROM conversations"
            ).fetchone()
            msg_count = conn.execute(
                "SELECT COUNT(*) as msgs FROM conversations"
            ).fetchone()

        return {
            "tiers": {r["tier"]: r["count"] for r in tier_counts},
            "total_memories": sum(r["count"] for r in tier_counts),
            "sessions": conv_count["sessions"] if conv_count else 0,
            "total_messages": msg_count["msgs"] if msg_count else 0,
        }
