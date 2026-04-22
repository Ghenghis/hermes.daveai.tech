# src/core/orchestrator.py
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from collections import defaultdict
import uuid
import time
import logging

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    id: str
    description: str
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)


@dataclass
class AgentCapabilities:
    name: str
    description: str
    supported_task_types: List[str]
    tools: List[str]
    max_concurrent_tasks: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)


class Orchestrator:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.agents: Dict[str, Any] = {}
        self.capabilities: Dict[str, AgentCapabilities] = {}
        self.tasks: Dict[str, Task] = {}
        self.task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.active_agents: Dict[str, asyncio.Task] = {}
        self.message_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self.session_state: Dict[str, Any] = defaultdict(dict)
        self._running = False
        self._lock = asyncio.Lock()
        
    async def start(self):
        self._running = True
        logger.info("Orchestrator started")
        asyncio.create_task(self._process_tasks())
        
    async def stop(self):
        self._running = False
        for task in self.active_agents.values():
            task.cancel()
        logger.info("Orchestrator stopped")
        
    async def register_agent(self, agent: Any, capabilities: Optional[AgentCapabilities] = None):
        agent_id = getattr(agent, 'id', str(uuid.uuid4()))
        
        async with self._lock:
            self.agents[agent_id] = agent
            
            if capabilities is None:
                capabilities = AgentCapabilities(
                    name=agent_id,
                    description=getattr(agent, 'description', ''),
                    supported_task_types=getattr(agent, 'supported_tasks', []),
                    tools=getattr(agent, 'available_tools', [])
                )
            
            self.capabilities[agent_id] = capabilities
            logger.info(f"Registered agent: {agent_id}")
            
    async def unregister_agent(self, agent_id: str):
        async with self._lock:
            if agent_id in self.agents:
                del self.agents[agent_id]
            if agent_id in self.capabilities:
                del self.capabilities[agent_id]
            logger.info(f"Unregistered agent: {agent_id}")
            
    def find_agent_for_task(self, task_type: str) -> Optional[str]:
        for agent_id, caps in self.capabilities.items():
            if task_type in caps.supported_task_types:
                return agent_id
        return None
    
    async def submit_task(
        self,
        description: str,
        task_type: Optional[str] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        dependencies: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        task = Task(
            id=str(uuid.uuid4()),
            description=description,
            priority=priority,
            metadata=metadata or {},
            dependencies=dependencies or []
        )
        
        self.tasks[task.id] = task
        await self.task_queue.put((priority.value, task.id))
        logger.info(f"Submitted task: {task.id} - {description}")
        
        return task.id
    
    async def _process_tasks(self):
        while self._running:
            try:
                priority, task_id = await self.task_queue.get()
                task = self.tasks.get(task_id)
                
                if task and task.status == TaskStatus.PENDING:
                    asyncio.create_task(self.execute_task(task_id))
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing task: {e}")
            
            await asyncio.sleep(0.01)
    
    async def execute_task(self, task_id: str) -> Any:
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
            
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        
        agent_id = self.find_agent_for_task(task.metadata.get('task_type', ''))
        
        if not agent_id:
            available = list(self.agents.keys())
            if available:
                agent_id = available[0]
            else:
                task.status = TaskStatus.FAILED
                task.error = "No agents available"
                raise RuntimeError("No agents available")
                
        task.assigned_agent = agent_id
        agent = self.agents[agent_id]
        
        try:
            logger.info(f"Executing task {task_id} with agent {agent_id}")
            result = await agent.execute(task.description, context=task.metadata)
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = time.time()
            return result
            
        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")
            task.status = TaskStatus.FAILED
            task.error = str(e)
            raise
    
    async def execute_workflow(self, workflow: List[Dict[str, Any]]) -> List[Any]:
        task_ids = []
        
        for step in workflow:
            dependencies = step.get('dependencies', [])
            validated_deps = [tid for tid in dependencies if tid in task_ids]
            
            task_id = await self.submit_task(
                description=step['description'],
                task_type=step.get('task_type'),
                priority=TaskPriority[step.get('priority', 'NORMAL')],
                dependencies=validated_deps,
                metadata=step.get('metadata', {})
            )
            task_ids.append(task_id)
            
        results = []
        for task_id in task_ids:
            result = await self.execute_task(task_id)
            results.append(result)
            
        return results
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        task = self.tasks.get(task_id)
        return task.status if task else None
    
    def get_orchestrator_stats(self) -> Dict[str, Any]:
        return {
            "total_tasks": len(self.tasks),
            "pending_tasks": len([t for t in self.tasks.values() if t.status == TaskStatus.PENDING]),
            "running_tasks": len([t for t in self.tasks.values() if t.status == TaskStatus.RUNNING]),
            "completed_tasks": len([t for t in self.tasks.values() if t.status == TaskStatus.COMPLETED]),
            "failed_tasks": len([t for t in self.tasks.values() if t.status == TaskStatus.FAILED]),
            "registered_agents": len(self.agents)
        }


async def example_orchestrator():
    from src.core.base_agent import BaseAgentDemo, AgentConfig
    
    orchestrator = Orchestrator()
    await orchestrator.start()
    
    agent_config = AgentConfig(name="TestAgent", description="Test agent")
    agent = BaseAgentDemo(agent_config)
    
    await orchestrator.register_agent(agent)
    
    task_id = await orchestrator.submit_task(
        description="Test task",
        priority=TaskPriority.NORMAL
    )
    
    await asyncio.sleep(0.5)
    
    result = await orchestrator.execute_task(task_id)
    print(f"Result: {result}")
    
    stats = orchestrator.get_orchestrator_stats()
    print(f"Stats: {stats}")
    
    await orchestrator.stop()


if __name__ == "__main__":
    asyncio.run(example_orchestrator())
