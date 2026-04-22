"""
Hierarchical Multi-Agent Coordination

Inspired by CrewAI's hierarchical process with manager delegation.
This module provides the infrastructure for multi-agent crews with
hierarchical task decomposition and delegation.

Usage:
    crew = HierarchicalCrewManager(
        agents=[planner, coder, reviewer],
        tasks=[...],
        manager=planner
    )
    results = await crew.execute()
"""

from dataclasses import dataclass, field
from typing import Optional, Any, Callable, Union
from enum import Enum
import asyncio
import json
import logging

logger = logging.getLogger(__name__)


class ProcessType(Enum):
    """Crew execution process types"""
    SEQUENTIAL = "sequential"
    HIERARCHICAL = "hierarchical"
    CONSENSUS = "consensus"
    PARALLEL = "parallel"


class AgentRole(Enum):
    """Agent role types"""
    MANAGER = "manager"
    WORKER = "worker"
    SPECIALIST = "specialist"


@dataclass
class CrewAgent:
    """Agent within a crew with role definition"""
    id: str
    role: str
    goal: str
    backstory: str = ""
    capabilities: list[str] = field(default_factory=list)
    role_type: AgentRole = AgentRole.WORKER
    tools: list[Any] = field(default_factory=list)
    allow_delegation: bool = False
    max_concurrent_tasks: int = 3
    
    async def execute(self, task: "CrewTask") -> "TaskResult":
        """Execute assigned task - to be implemented by subclasses"""
        raise NotImplementedError
        
    def can_handle(self, task: "CrewTask") -> bool:
        """Check if agent can handle this task"""
        for capability in self.capabilities:
            if capability.lower() in task.description.lower():
                return True
        return False


@dataclass
class CrewTask:
    """Task definition for crew execution"""
    id: str
    description: str
    expected_output: Optional[str] = None
    context: Optional[str] = None
    assigned_agent: Optional[str] = None
    priority: int = 1
    dependencies: list[str] = field(default_factory=list)
    status: str = "pending"
    max_retries: int = 3


@dataclass
class TaskResult:
    """Result from task execution"""
    task_id: str
    agent_id: str
    output: Any
    success: bool = True
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class CrewConfig:
    """Configuration for crew execution"""
    process: ProcessType = ProcessType.SEQUENTIAL
    max_hierarchy_depth: int = 3
    manager_llm: Optional[Any] = None
    enable_consensus: bool = False
    consensus_threshold: float = 0.7
    parallel_execution: bool = False
    max_concurrent_tasks: int = 5


class HierarchicalCrewManager:
    """
    Manager-based crew execution with hierarchical task decomposition
    Based on CrewAI's hierarchical process pattern
    """
    
    def __init__(
        self,
        agents: list[CrewAgent],
        tasks: list[CrewTask],
        manager: CrewAgent,
        config: Optional[CrewConfig] = None
    ):
        self.agents = {a.id: a for a in agents}
        self.tasks = {t.id: t for t in tasks}
        self.manager = manager
        self.config = config or CrewConfig()
        self.results: dict[str, TaskResult] = {}
        
    async def execute(self) -> list[TaskResult]:
        """Execute crew based on configured process type"""
        if self.config.process == ProcessType.HIERARCHICAL:
            return await self._hierarchical_execute()
        elif self.config.process == ProcessType.SEQUENTIAL:
            return await self._sequential_execute()
        elif self.config.process == ProcessType.PARALLEL:
            return await self._parallel_execute()
        elif self.config.process == ProcessType.CONSENSUS:
            return await self._consensus_execute()
        else:
            raise ValueError(f"Unsupported process: {self.config.process}")
            
    async def _hierarchical_execute(self) -> list[TaskResult]:
        """
        Manager breaks down work and delegates to workers
        Manager creates task breakdown, assigns to agents, reviews results
        """
        results = []
        
        # Manager creates task breakdown
        task_breakdown = await self._create_task_breakdown()
        
        # Assign and execute subtasks
        for subtask in task_breakdown:
            agent = self._select_agent(subtask)
            if not agent:
                results.append(TaskResult(
                    task_id=subtask["id"],
                    agent_id="none",
                    output=None,
                    success=False,
                    error="No suitable agent found"
                ))
                continue
                
            # Execute with manager oversight
            task = CrewTask(
                id=subtask["id"],
                description=subtask["description"],
                expected_output=subtask.get("expected_output")
            )
            
            result = await self._execute_with_oversight(task, agent)
            results.append(result)
            
        return results
    
    async def _create_task_breakdown(self) -> list[dict]:
        """Manager creates detailed task breakdown using LLM"""
        prompt = f"""As the crew manager, break down these tasks into detailed subtasks:

Main Tasks:
{self._format_tasks(self.tasks.values())}

Available Agents:
{self._format_agents(self.agents.values())}

For each subtask, specify:
- Unique ID
- Description
- Expected output
- Required agent role/capability
- Dependencies on other subtasks

Return as JSON array of subtasks."""

        try:
            response = await self.manager_llm_call(prompt)
            return json.loads(response)
        except Exception as e:
            logger.error(f"Task breakdown failed: {e}")
            return self._fallback_task_breakdown()
    
    def _fallback_task_breakdown(self) -> list[dict]:
        """Fallback task breakdown when LLM fails"""
        breakdown = []
        for task in self.tasks.values():
            breakdown.append({
                "id": f"{task.id}_sub",
                "description": task.description,
                "expected_output": task.expected_output,
                "required_capability": task.description.split()[0] if task.description else "general"
            })
        return breakdown
    
    async def _execute_with_oversight(
        self,
        task: CrewTask,
        agent: CrewAgent
    ) -> TaskResult:
        """Execute task with manager oversight and retry logic"""
        for attempt in range(task.max_retries):
            try:
                result = await agent.execute(task)
                
                # Manager reviews result
                if self._manager_approves(result):
                    return result
                    
                if attempt < task.max_retries - 1:
                    # Get feedback and retry
                    feedback = await self._get_manager_feedback(result)
                    task.description = f"{task.description}\n\nFeedback: {feedback}"
                    
            except Exception as e:
                if attempt == task.max_retries - 1:
                    return TaskResult(
                        task_id=task.id,
                        agent_id=agent.id,
                        output=None,
                        success=False,
                        error=str(e)
                    )
                    
        return TaskResult(
            task_id=task.id,
            agent_id=agent.id,
            output=None,
            success=False,
            error="Max retries exceeded"
        )
    
    def _select_agent(self, subtask: dict) -> Optional[CrewAgent]:
        """Select best agent for subtask based on capabilities"""
        required_capabilities = subtask.get("required_capabilities", [])
        
        scored_agents = []
        for agent in self.agents.values():
            if agent.id == self.manager.id:
                continue
                
            score = sum(
                1 for cap in required_capabilities
                if cap in agent.capabilities
            )
            scored_agents.append((agent.id, score))
            
        if not scored_agents:
            # Return any available worker
            workers = [a for a in self.agents.values() if a.role_type == AgentRole.WORKER]
            return workers[0] if workers else None
            
        best_agent_id = max(scored_agents, key=lambda x: x[1])[0]
        return self.agents.get(best_agent_id)
    
    async def _manager_llm_call(self, prompt: str) -> str:
        """Call LLM for manager operations"""
        if self.config.manager_llm and hasattr(self.config.manager_llm, 'agenerate'):
            return await self.config.manager_llm.agenerate([prompt])
        raise RuntimeError("Manager LLM not configured")
    
    def _manager_approves(self, result: TaskResult) -> bool:
        """Check if manager approved the result"""
        # Simple approval based on success flag
        # Could be enhanced with LLM-based review
        return result.success
    
    async def _get_manager_feedback(self, result: TaskResult) -> str:
        """Get feedback from manager on failed result"""
        return f"Execution had issues. Please revise and retry the task."
    
    async def _sequential_execute(self) -> list[TaskResult]:
        """Execute tasks sequentially, passing context to next"""
        results = []
        context = ""
        
        for task in self.tasks.values():
            # Update task context
            task.context = context
            
            # Find suitable agent
            agent = self._find_agent_for_task(task)
            if not agent:
                results.append(TaskResult(
                    task_id=task.id,
                    agent_id="none",
                    output=None,
                    success=False,
                    error="No suitable agent found"
                ))
                continue
                
            # Execute
            result = await agent.execute(task)
            results.append(result)
            
            # Update context for next task
            if result.success:
                context += f"\n{result.output}"
                
        return results
    
    async def _parallel_execute(self) -> list[TaskResult]:
        """Execute independent tasks in parallel"""
        # Identify independent tasks
        independent_tasks = [
            t for t in self.tasks.values()
            if not t.dependencies
        ]
        
        # Execute in parallel with semaphore
        semaphore = asyncio.Semaphore(self.config.max_concurrent_tasks)
        
        async def execute_with_limit(task: CrewTask):
            async with semaphore:
                agent = self._find_agent_for_task(task)
                if agent:
                    return await agent.execute(task)
                return TaskResult(
                    task_id=task.id,
                    agent_id="none",
                    output=None,
                    success=False,
                    error="No agent available"
                )
        
        results = await asyncio.gather(*[
            execute_with_limit(t) for t in independent_tasks
        ])
        
        return list(results)
    
    async def _consensus_execute(self) -> list[TaskResult]:
        """Multiple agents work on same task, reach consensus"""
        if not self.config.enable_consensus:
            raise ValueError("Consensus not enabled")
            
        results = []
        
        for task in self.tasks.values():
            # Get multiple agents to work on same task
            agents = self._get_specialists_for_task(task)
            
            # Collect proposals
            proposals = await self._collect_proposals(task, agents)
            
            # Build consensus
            consensus = await self._build_consensus(task, proposals)
            results.append(consensus)
            
        return results
    
    async def _collect_proposals(
        self,
        task: CrewTask,
        agents: list[CrewAgent]
    ) -> list[dict]:
        """Collect proposals from multiple agents"""
        proposals = []
        
        for agent in agents:
            result = await agent.execute(task)
            proposals.append({
                "agent": agent.id,
                "proposal": result.output,
                "votes": []
            })
            
        return proposals
    
    async def _build_consensus(
        self,
        task: CrewTask,
        proposals: list[dict]
    ) -> TaskResult:
        """Build consensus from multiple proposals"""
        # Simple consensus: use proposal from most capable agent
        # Could be enhanced with voting mechanism
        
        best_proposal = max(proposals, key=lambda p: len(p["proposal"]) if p["proposal"] else 0)
        
        return TaskResult(
            task_id=task.id,
            agent_id=best_proposal["agent"],
            output=best_proposal["proposal"],
            success=True,
            metadata={"consensus": True, "proposals_count": len(proposals)}
        )
    
    def _find_agent_for_task(self, task: CrewTask) -> Optional[CrewAgent]:
        """Find any agent that can handle the task"""
        for agent in self.agents.values():
            if agent.can_handle(task):
                return agent
        return None
    
    def _get_specialists_for_task(self, task: CrewTask) -> list[CrewAgent]:
        """Get all specialists that can handle the task"""
        return [
            a for a in self.agents.values()
            if a.role_type == AgentRole.SPECIALIST and a.can_handle(task)
        ]
    
    def _format_tasks(self, tasks) -> str:
        """Format tasks for prompt"""
        lines = []
        for task in tasks:
            lines.append(f"- {task.id}: {task.description}")
        return "\n".join(lines)
    
    def _format_agents(self, agents) -> str:
        """Format agents for prompt"""
        lines = []
        for agent in agents:
            lines.append(f"- {agent.role} ({agent.id}): {agent.goal}")
            lines.append(f"  Capabilities: {', '.join(agent.capabilities)}")
        return "\n".join(lines)


class CrewBuilder:
    """Builder for constructing crews"""
    
    def __init__(self):
        self.agents: list[CrewAgent] = []
        self.tasks: list[CrewTask] = []
        self.manager: Optional[CrewAgent] = None
        self.config: CrewConfig = CrewConfig()
        
    def add_agent(
        self,
        agent_id: str,
        role: str,
        goal: str,
        capabilities: list[str],
        **kwargs
    ) -> "CrewBuilder":
        """Add an agent to the crew"""
        agent = CrewAgent(
            id=agent_id,
            role=role,
            goal=goal,
            capabilities=capabilities,
            **kwargs
        )
        self.agents.append(agent)
        return self
        
    def set_manager(self, agent_id: str) -> "CrewBuilder":
        """Set the manager agent"""
        if agent_id in [a.id for a in self.agents]:
            agent = next(a for a in self.agents if a.id == agent_id)
            agent.role_type = AgentRole.MANAGER
            agent.allow_delegation = True
            self.manager = agent
        return self
    
    def add_task(
        self,
        task_id: str,
        description: str,
        **kwargs
    ) -> "CrewBuilder":
        """Add a task to the crew"""
        task = CrewTask(id=task_id, description=description, **kwargs)
        self.tasks.append(task)
        return self
    
    def set_process(self, process: ProcessType) -> "CrewBuilder":
        """Set the process type"""
        self.config.process = process
        return self
    
    def build(self) -> HierarchicalCrewManager:
        """Build the crew manager"""
        if not self.manager:
            # Auto-assign first agent as manager
            if self.agents:
                self.agents[0].role_type = AgentRole.MANAGER
                self.agents[0].allow_delegation = True
                self.manager = self.agents[0]
                
        return HierarchicalCrewManager(
            agents=self.agents,
            tasks=self.tasks,
            manager=self.manager,
            config=self.config
        )


# Convenience function

async def create_crew(
    agents: list[dict],
    tasks: list[dict],
    process: ProcessType = ProcessType.SEQUENTIAL
) -> list[TaskResult]:
    """
    Create and execute a crew with given agents and tasks
    
    Args:
        agents: List of agent definitions
        tasks: List of task definitions
        process: Process type to use
        
    Returns:
        List of task results
    """
    builder = CrewBuilder()
    
    for agent in agents:
        builder.add_agent(**agent)
        
    for task in tasks:
        builder.add_task(**task)
        
    builder.set_process(process)
    
    crew = builder.build()
    return await crew.execute()
