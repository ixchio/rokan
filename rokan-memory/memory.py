"""
Rokan Memory System - 3-Tier Architecture
Episodic, Semantic, Procedural memory with Qdrant
"""

import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import ollama


@dataclass
class MemoryEntry:
    """Single memory entry"""
    content: str
    tier: str  # episodic, semantic, procedural
    timestamp: datetime
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = None
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict:
        return {
            "content": self.content,
            "tier": self.tier,
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id,
            "metadata": self.metadata or {}
        }


class ThreeTierMemory:
    """
    Three-tier memory system:
    - Episodic: What happened (conversations, events)
    - Semantic: What you know (facts, preferences)
    - Procedural: How to do things (workflows, patterns)
    """
    
    def __init__(self, 
                 host: str = "localhost", 
                 port: int = 6333,
                 collection_name: str = "rokan_memory",
                 embedding_model: str = "mxbai-embed-large"):
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        
        # Initialize Qdrant
        self.client = QdrantClient(host=host, port=port)
        self._ensure_collection()
    
    def _ensure_collection(self):
        """Ensure memory collection exists"""
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]
        
        if self.collection_name not in collection_names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=1024, distance=Distance.COSINE)
            )
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using Ollama"""
        try:
            response = ollama.embeddings(
                model=self.embedding_model,
                prompt=text
            )
            return response["embedding"]
        except Exception as e:
            print(f"Embedding error: {e}")
            # Return zero vector as fallback
            return [0.0] * 1024
    
    def store(self, 
              content: str, 
              tier: str = "semantic",
              session_id: Optional[str] = None,
              metadata: Optional[Dict] = None) -> str:
        """
        Store a memory entry
        
        Args:
            content: The memory content
            tier: episodic, semantic, or procedural
            session_id: Optional session identifier
            metadata: Additional metadata
        
        Returns:
            Memory ID
        """
        # Generate embedding
        embedding = self._generate_embedding(content)
        
        # Create entry
        entry = MemoryEntry(
            content=content,
            tier=tier,
            timestamp=datetime.now(),
            session_id=session_id,
            metadata=metadata,
            embedding=embedding
        )
        
        # Generate ID
        memory_id = hashlib.md5(
            f"{content}{entry.timestamp}".encode()
        ).hexdigest()
        
        # Store in Qdrant
        self.client.upsert(
            collection_name=self.collection_name,
            points=[PointStruct(
                id=memory_id,
                vector=embedding,
                payload={
                    **entry.to_dict(),
                    "tier": tier  # For filtering
                }
            )]
        )
        
        return memory_id
    
    def recall(self, 
               query: str, 
               tier: Optional[str] = None,
               limit: int = 5,
               session_id: Optional[str] = None) -> List[Dict]:
        """
        Retrieve relevant memories
        
        Args:
            query: Search query
            tier: Filter by tier (optional)
            limit: Max results
            session_id: Filter by session (optional)
        
        Returns:
            List of memory entries
        """
        # Generate query embedding
        query_embedding = self._generate_embedding(query)
        
        # Build filter
        filter_conditions = []
        if tier:
            filter_conditions.append(
                {"key": "tier", "match": {"value": tier}}
            )
        if session_id:
            filter_conditions.append(
                {"key": "session_id", "match": {"value": session_id}}
            )
        
        # Search
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=limit,
            query_filter={"must": filter_conditions} if filter_conditions else None
        )
        
        # Format results
        memories = []
        for result in results:
            memories.append({
                "id": result.id,
                "content": result.payload.get("content"),
                "tier": result.payload.get("tier"),
                "timestamp": result.payload.get("timestamp"),
                "score": result.score,
                "metadata": result.payload.get("metadata", {})
            })
        
        return memories
    
    def get_episodic(self, 
                     session_id: Optional[str] = None,
                     since: Optional[datetime] = None,
                     limit: int = 20) -> List[Dict]:
        """Get episodic memories (conversation history)"""
        filter_conditions = [{"key": "tier", "match": {"value": "episodic"}}]
        
        if session_id:
            filter_conditions.append(
                {"key": "session_id", "match": {"value": session_id}}
            )
        
        # Scroll instead of search for time-based queries
        results = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter={"must": filter_conditions},
            limit=limit
        )[0]
        
        memories = []
        for point in results:
            memory_time = datetime.fromisoformat(point.payload.get("timestamp", ""))
            if since and memory_time < since:
                continue
            
            memories.append({
                "id": point.id,
                "content": point.payload.get("content"),
                "timestamp": point.payload.get("timestamp"),
                "session_id": point.payload.get("session_id")
            })
        
        return sorted(memories, key=lambda x: x["timestamp"], reverse=True)
    
    def get_semantic(self, topic: str, limit: int = 10) -> List[Dict]:
        """Get semantic memories about a topic"""
        return self.recall(query=topic, tier="semantic", limit=limit)
    
    def get_procedural(self, task_type: str) -> List[Dict]:
        """Get procedural memories for a task type"""
        return self.recall(query=task_type, tier="procedural", limit=5)
    
    def store_procedure(self, 
                        name: str, 
                        steps: List[str],
                        description: str = "") -> str:
        """Store a procedure/workflow"""
        content = f"Procedure: {name}\n"
        if description:
            content += f"Description: {description}\n"
        content += "Steps:\n" + "\n".join(f"{i+1}. {step}" for i, step in enumerate(steps))
        
        return self.store(
            content=content,
            tier="procedural",
            metadata={"name": name, "steps": steps}
        )
    
    def summarize_session(self, session_id: str) -> str:
        """Generate a summary of a session"""
        memories = self.get_episodic(session_id=session_id)
        
        if not memories:
            return "No memories found for this session."
        
        # Simple extraction - in production, use LLM
        topics = set()
        for m in memories:
            # Extract key topics (simplified)
            words = m["content"].lower().split()
            topics.update([w for w in words if len(w) > 5])
        
        return f"Session {session_id}: {len(memories)} interactions. Topics: {', '.join(list(topics)[:10])}"
    
    def cleanup_old_memories(self, days: int = 365):
        """Remove memories older than specified days"""
        cutoff = datetime.now() - timedelta(days=days)
        
        # This is a simplified version - in production, use proper date filtering
        all_points = self.client.scroll(
            collection_name=self.collection_name,
            limit=10000
        )[0]
        
        to_delete = []
        for point in all_points:
            try:
                memory_time = datetime.fromisoformat(point.payload.get("timestamp", ""))
                if memory_time < cutoff and point.payload.get("tier") == "episodic":
                    to_delete.append(point.id)
            except:
                pass
        
        if to_delete:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=to_delete
            )
        
        return len(to_delete)


# OpenClaw skill interface
class RokanMemorySkill:
    """OpenClaw skill interface for rokan-memory"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.memory = ThreeTierMemory(
            host=self.config.get("qdrant", {}).get("host", "localhost"),
            port=self.config.get("qdrant", {}).get("port", 6333),
            collection_name=self.config.get("qdrant", {}).get("collection", "rokan_memory"),
            embedding_model=self.config.get("embeddings", {}).get("model", "mxbai-embed-large")
        )
    
    def store(self, content: str, tier: str = "semantic", **kwargs) -> str:
        """Store a memory"""
        return self.memory.store(content, tier=tier, **kwargs)
    
    def recall(self, query: str, tier: str = None, limit: int = 5) -> List[Dict]:
        """Recall memories"""
        return self.memory.recall(query, tier=tier, limit=limit)
    
    def get_episodic(self, session_id: str = None, limit: int = 20) -> List[Dict]:
        """Get episodic memories"""
        return self.memory.get_episodic(session_id=session_id, limit=limit)
    
    def store_procedure(self, name: str, steps: List[str]) -> str:
        """Store a procedure"""
        return self.memory.store_procedure(name, steps)


# Export for OpenClaw
skill = RokanMemorySkill
