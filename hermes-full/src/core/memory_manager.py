# src/core/memory_manager.py
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict
from datetime import datetime
import uuid
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class Message:
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class WorkingMemory:
    context_window: List[Message] = field(default_factory=list)
    task_description: Optional[str] = None
    task_parameters: Dict[str, Any] = field(default_factory=dict)
    available_tools: List[Any] = field(default_factory=list)
    intermediate_results: Dict[str, Any] = field(default_factory=dict)
    max_window_size: int = 50
    
    def add_message(self, role: str, content: str):
        self.context_window.append(Message(role=role, content=content))
        if len(self.context_window) > self.max_window_size:
            self.context_window.pop(0)
            
    def get_recent_messages(self, n: int = 10) -> List[Message]:
        return self.context_window[-n:]
    
    def update_result(self, key: str, value: Any):
        self.intermediate_results[key] = value
        
    def get_result(self, key: str) -> Optional[Any]:
        return self.intermediate_results.get(key)


@dataclass
class Episode:
    id: str
    timestamp: float
    task_type: str
    task_description: str
    actions_taken: List[Dict[str, Any]]
    outcome: str
    success: bool
    duration: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class EpisodicMemory:
    def __init__(self, max_episodes: int = 1000):
        self.episodes: List[Episode] = []
        self.max_episodes = max_episodes
        self._index: Dict[str, List[int]] = defaultdict(list)
        
    def add_episode(self, episode: Episode):
        self.episodes.append(episode)
        self._index['recent'].append(len(self.episodes) - 1)
        self._index[episode.task_type].append(len(self.episodes) - 1)
        
        if len(self.episodes) > self.max_episodes:
            self._evict_oldest()
            
    def _evict_oldest(self):
        if self.episodes:
            self.episodes.pop(0)
            
    def get_recent(self, n: int = 10) -> List[Episode]:
        return self.episodes[-n:]
    
    def get_by_task_type(self, task_type: str) -> List[Episode]:
        indices = self._index.get(task_type, [])
        return [self.episodes[i] for i in indices if i < len(self.episodes)]
    
    def get_similar(self, description: str, threshold: float = 0.7) -> List[Episode]:
        similar = []
        for episode in self.episodes:
            similarity = self._calculate_similarity(description, episode.task_description)
            if similarity >= threshold:
                similar.append((episode, similarity))
        return sorted(similar, key=lambda x: x[1], reverse=True)
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0.0
        intersection = words1.intersection(words2)
        return len(intersection) / len(words1.union(words2))


@dataclass
class KnowledgeEntry:
    id: str
    content: Any
    embedding: Optional[List[float]] = None
    tags: Set[str] = field(default_factory=set)
    source: str
    confidence: float = 1.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class SemanticMemory:
    def __init__(self, embedding_model: Optional[Any] = None):
        self.knowledge: Dict[str, KnowledgeEntry] = {}
        self.embedding_model = embedding_model
        self._tag_index: Dict[str, Set[str]] = defaultdict(set)
        
    async def store(
        self,
        content: Any,
        tags: Optional[Set[str]] = None,
        source: str = "user"
    ) -> str:
        entry_id = str(uuid.uuid4())
        
        embedding = None
        if self.embedding_model and isinstance(content, str):
            embedding = await self.embedding_model.encode(content)
            
        entry = KnowledgeEntry(
            id=entry_id,
            content=content,
            embedding=embedding,
            tags=tags or set(),
            source=source
        )
        
        self.knowledge[entry_id] = entry
        
        for tag in entry.tags:
            self._tag_index[tag].add(entry_id)
            
        return entry_id
    
    async def query(
        self,
        query: str,
        tags: Optional[Set[str]] = None,
        limit: int = 10
    ) -> List[KnowledgeEntry]:
        results = []
        
        if tags:
            candidate_ids = set()
            for tag in tags:
                candidate_ids.update(self._tag_index.get(tag, set()))
        else:
            candidate_ids = set(self.knowledge.keys())
            
        if self.embedding_model:
            query_embedding = await self.embedding_model.encode(query)
            
            for entry_id in candidate_ids:
                entry = self.knowledge[entry_id]
                if entry.embedding:
                    similarity = self._cosine_similarity(query_embedding, entry.embedding)
                    results.append((entry, similarity))
                    
            results.sort(key=lambda x: x[1], reverse=True)
            return [entry for entry, _ in results[:limit]]
        else:
            return [self.knowledge[eid] for eid in list(candidate_ids)[:limit]]
            
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude = lambda v: sum(x * x for x in v) ** 0.5
        return dot_product / (magnitude(vec1) * magnitude(vec2) + 1e-8)


class MemoryManager:
    def __init__(
        self,
        working_capacity: int = 50,
        episodic_capacity: int = 1000,
        embedding_model: Optional[Any] = None
    ):
        self.working = WorkingMemory(max_window_size=working_capacity)
        self.episodic = EpisodicMemory(max_episodes=episodic_capacity)
        self.semantic = SemanticMemory(embedding_model=embedding_model)
        
    async def initialize_for_task(
        self,
        task_description: str,
        task_type: str,
        context: Optional[List[Message]] = None
    ):
        self.working.task_description = task_description
        self.working.task_parameters = {'task_type': task_type}
        
        if context:
            for msg in context:
                self.working.add_message(msg.role, msg.content)
                
    async def remember_relevant(
        self,
        query: str,
        limit: int = 5
    ) -> List[Any]:
        memories = []
        
        semantic_results = await self.semantic.query(query, limit=limit)
        memories.extend([('semantic', r) for r in semantic_results])
        
        episodic_similar = self.episodic.get_similar(query, threshold=0.5)
        memories.extend([('episodic', e) for e, _ in episodic_similar[:limit]])
        
        return memories
    
    async def save_episode(
        self,
        task_type: str,
        task_description: str,
        actions: List[Dict[str, Any]],
        outcome: str,
        success: bool,
        duration: float
    ):
        episode = Episode(
            id=str(uuid.uuid4()),
            timestamp=time.time(),
            task_type=task_type,
            task_description=task_description,
            actions_taken=actions,
            outcome=outcome,
            success=success,
            duration=duration
        )
        self.episodic.add_episode(episode)
        
    def get_context_for_agent(self) -> Dict[str, Any]:
        return {
            'recent_messages': self.working.get_recent_messages(),
            'task': self.working.task_description,
            'intermediate_results': self.working.intermediate_results,
            'available_tools': self.working.available_tools
        }
