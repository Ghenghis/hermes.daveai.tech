# src/agents/specialized/researcher.py
import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
import logging

from src.core.base_agent import BaseAgent, AgentConfig
from src.core.memory_manager import MemoryManager

logger = logging.getLogger(__name__)


@dataclass
class ResearchResult:
    topic: str
    summary: str
    sources: List[Dict[str, str]]
    key_findings: List[str]
    confidence: float
    research_time: float


@dataclass
class ResearcherAgent(BaseAgent):
    name: str = "Researcher"
    description: str = "Agent specialized in researching and gathering information"
    
    research_depth: str = "medium"
    max_sources: int = 10
    
    _search_cache: Dict[str, Any] = field(default_factory=dict, init=False)
    
    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(name=self.name, description=self.description)
        super().__init__(config)
        self.memory_manager = MemoryManager()
        self._setup_research_tools()
    
    def _setup_research_tools(self):
        self.register_tool("web_search", self._web_search)
        self.register_tool("read_file", self._read_file)
        self.register_tool("analyze_data", self._analyze_data)
    
    async def _web_search(self, query: str, num_results: int = 10) -> List[Dict[str, str]]:
        logger.info(f"Searching web for: {query}")
        await asyncio.sleep(0.1)
        
        cache_key = f"{query}:{num_results}"
        if cache_key in self._search_cache:
            return self._search_cache[cache_key]
        
        results = [
            {
                "title": f"Result {i+1} for '{query}'",
                "url": f"https://example.com/result{i}",
                "snippet": f"This is a sample search result for {query}. Contains relevant information.",
                "relevance": 0.9 - (i * 0.1)
            }
            for i in range(num_results)
        ]
        
        self._search_cache[cache_key] = results
        return results
    
    async def _read_file(self, filepath: str) -> str:
        logger.info(f"Reading file: {filepath}")
        await asyncio.sleep(0.05)
        return f"Content of {filepath}"
    
    async def _analyze_data(self, data: List[Any], analysis_type: str = "summary") -> Dict[str, Any]:
        logger.info(f"Analyzing data with type: {analysis_type}")
        await asyncio.sleep(0.1)
        
        return {
            "analysis_type": analysis_type,
            "count": len(data),
            "summary": f"Analysis of {len(data)} items"
        }
    
    async def think(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        depth_map = {"quick": 5, "medium": 10, "deep": 20}
        num_results = depth_map.get(self.research_depth, 10)
        
        self.update_working_memory("current_task", task)
        self.update_working_memory("research_depth", self.research_depth)
        
        return {
            "thought": f"Researching: {task}",
            "action": "web_search",
            "params": {"query": task, "num_results": num_results}
        }
    
    async def act(self, thought_result: Dict[str, Any]) -> Any:
        action = thought_result.get("action")
        params = thought_result.get("params", {})
        
        if action == "web_search":
            results = await self.use_tool("web_search", **params)
            self.update_working_memory("search_results", results)
            return results
        elif action == "analyze_data":
            return await self.use_tool("analyze_data", **params)
        
        return None
    
    async def research(
        self,
        topic: str,
        depth: Optional[str] = None
    ) -> ResearchResult:
        """
        Conduct comprehensive research on a topic.
        
        Args:
            topic: The research topic
            depth: Research depth ('quick', 'medium', 'deep')
            
        Returns:
            ResearchResult with findings
        """
        if depth:
            self.research_depth = depth
        
        depth_map = {"quick": 5, "medium": 10, "deep": 20}
        num_results = depth_map.get(self.research_depth, 10)
        
        await self.memory_manager.initialize_for_task(topic, "research")
        
        start_time = datetime.now()
        
        search_results = await self._web_search(topic, num_results)
        
        sources = [{"title": r["title"], "url": r["url"]} for r in search_results]
        
        key_findings = []
        for i, result in enumerate(search_results[:5]):
            key_findings.append(f"Finding {i+1}: {result['snippet'][:100]}...")
        
        summary = f"Research on '{topic}' found {len(search_results)} sources. "
        summary += "Key insights include: " + "; ".join(key_findings[:3])
        
        research_time = (datetime.now() - start_time).total_seconds()
        
        confidence = min(1.0, len(search_results) / 20 + 0.3)
        
        self.add_episode({
            "task_type": "research",
            "task_description": topic,
            "num_sources": len(search_results),
            "confidence": confidence
        })
        
        return ResearchResult(
            topic=topic,
            summary=summary,
            sources=sources,
            key_findings=key_findings,
            confidence=confidence,
            research_time=research_time
        )


async def example_researcher():
    config = AgentConfig(name="ResearcherAgent", description="Research specialist")
    agent = ResearcherAgent(config)
    
    result = await agent.research("Python async programming", depth="medium")
    
    print(f"Topic: {result.topic}")
    print(f"Summary: {result.summary}")
    print(f"Confidence: {result.confidence:.2f}")
    print(f"Sources found: {len(result.sources)}")


if __name__ == "__main__":
    asyncio.run(example_researcher())
