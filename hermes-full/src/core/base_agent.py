# src/core/base_agent.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set
from enum import Enum
import asyncio
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)


class AgentState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class Message:
    id: str
    sender: str
    content: Any
    msg_type: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentConfig:
    name: str
    description: str = ""
    max_iterations: int = 10
    timeout: float = 300.0
    tools: List[str] = field(default_factory=list)
    capabilities: Set[str] = field(default_factory=set)


class BaseAgent(ABC):
    name: str
    description: str
    config: AgentConfig
    
    _state: AgentState = AgentState.IDLE
    _current_task: Optional[str] = None
    _message_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    _tools: Dict[str, Any] = field(default_factory=dict)
    _memory: Dict[str, Any] = field(default_factory=lambda: {"working": {}, "episodic": [], "semantic": {}})
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.name = config.name
        self.description = config.description
        self._setup_logging()
    
    def _setup_logging(self):
        self.logger = logging.getLogger(f"agent.{self.name}")
    
    @abstractmethod
    async def think(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def act(self, thought_result: Dict[str, Any]) -> Any:
        pass
    
    async def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> Any:
        self._state = AgentState.RUNNING
        self._current_task = task
        context = context or {}
        
        self.logger.info(f"Executing task: {task}")
        
        for iteration in range(self.config.max_iterations):
            try:
                thought_result = await self.think(task, context)
                
                if thought_result.get("done", False):
                    self._state = AgentState.COMPLETED
                    return thought_result.get("result")
                
                act_result = await self.act(thought_result)
                
                context["last_result"] = act_result
                
            except Exception as e:
                self.logger.error(f"Error in iteration {iteration}: {e}")
                self._state = AgentState.ERROR
                raise
        
        self._state = AgentState.COMPLETED
        return context.get("final_result")
    
    def register_tool(self, name: str, tool: Any):
        self._tools[name] = tool
        self.logger.info(f"Registered tool: {name}")
    
    async def use_tool(self, tool_name: str, **kwargs) -> Any:
        if tool_name not in self._tools:
            raise ValueError(f"Tool not found: {tool_name}")
        
        tool = self._tools[tool_name]
        
        if asyncio.iscoroutinefunction(tool):
            return await tool(**kwargs)
        else:
            return tool(**kwargs)
    
    async def receive_message(self, message: Message):
        await self._message_queue.put(message)
    
    async def send_message(self, recipient: str, content: Any, msg_type: str = "info"):
        message = Message(
            id=str(uuid.uuid4()),
            sender=self.name,
            content=content,
            msg_type=msg_type
        )
        return message
    
    def get_state(self) -> AgentState:
        return self._state
    
    def get_memory(self) -> Dict[str, Any]:
        return self._memory
    
    def update_working_memory(self, key: str, value: Any):
        self._memory["working"][key] = value
    
    def add_episode(self, episode: Dict[str, Any]):
        self._memory["episodic"].append({
            **episode,
            "timestamp": datetime.now().isoformat()
        })
    
    def store_semantic(self, key: str, value: Any):
        self._memory["semantic"][key] = value
    
    def retrieve_semantic(self, key: str) -> Optional[Any]:
        return self._memory["semantic"].get(key)


class Tool:
    name: str
    description: str
    func: Any
    
    def __init__(self, name: str, description: str, func: Any):
        self.name = name
        self.description = description
        self.func = func
    
    async def execute(self, **kwargs) -> Any:
        if asyncio.iscoroutinefunction(self.func):
            return await self.func(**kwargs)
        return self.func(**kwargs)


class BaseAgentDemo(BaseAgent):
    async def think(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        await asyncio.sleep(0.1)
        return {
            "thought": f"Analyzing task: {task}",
            "action": "process",
            "params": {"task": task}
        }
    
    async def act(self, thought_result: Dict[str, Any]) -> Any:
        await asyncio.sleep(0.1)
        return f"Completed: {thought_result['params']['task']}"


async def example_base_agent():
    config = AgentConfig(
        name="DemoAgent",
        description="A demonstration agent",
        max_iterations=5
    )
    
    agent = BaseAgentDemo(config)
    
    result = await agent.execute("Sample task")
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(example_base_agent())
