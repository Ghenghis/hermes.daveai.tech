# src/agents/crew/crew_manager.py
import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from enum import Enum
import logging
import uuid

from src.core.base_agent import BaseAgent, AgentConfig

logger = logging.getLogger(__name__)


class CrewRole(Enum):
    COORDINATOR = "coordinator"
    SPECIALIST = "specialist"
    WORKER = "worker"


@dataclass
class CrewMember:
    agent: BaseAgent
    role: CrewRole
    specialties: Set[str] = field(default_factory=set)
    is_available: bool = True
    current_task: Optional[str] = None


@dataclass
class TaskAssignment:
    id: str
    task: str
    assigned_member: Optional[str] = None
    status: str = "pending"
    result: Any = None
    error: Optional[str] = None


class CrewManager:
    """
    Manages a crew of agents working together.
    
    Coordinates multiple agents with different roles and specialties
    to accomplish complex tasks through collaboration.
    """
    
    def __init__(self, name: str = "Crew"):
        self.name = name
        self.members: Dict[str, CrewMember] = {}
        self.tasks: Dict[str, TaskAssignment] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        logger.info(f"CrewManager '{name}' initialized")
    
    def add_member(
        self,
        agent: BaseAgent,
        role: CrewRole = CrewRole.SPECIALIST,
        specialties: Optional[Set[str]] = None
    ) -> str:
        member_id = getattr(agent, 'name', str(uuid.uuid4()))
        
        member = CrewMember(
            agent=agent,
            role=role,
            specialties=specialties or set()
        )
        
        self.members[member_id] = member
        logger.info(f"Added member: {member_id} with role {role.value}")
        
        return member_id
    
    def remove_member(self, member_id: str) -> bool:
        if member_id in self.members:
            del self.members[member_id]
            logger.info(f"Removed member: {member_id}")
            return True
        return False
    
    def get_available_member(self, task: str, required_specialties: Optional[Set[str]] = None) -> Optional[str]:
        for member_id, member in self.members.items():
            if not member.is_available:
                continue
            
            if required_specialties:
                if not required_specialties.issubset(member.specialties):
                    continue
            
            return member_id
        
        return None
    
    async def assign_task(
        self,
        task: str,
        required_specialties: Optional[Set[str]] = None,
        priority: int = 1
    ) -> str:
        task_id = str(uuid.uuid4())
        
        assignment = TaskAssignment(id=task_id, task=task)
        self.tasks[task_id] = assignment
        
        await self.task_queue.put((priority, task_id))
        
        logger.info(f"Assigned task {task_id}: {task[:50]}...")
        
        return task_id
    
    async def execute_task(self, task_id: str) -> Any:
        if task_id not in self.tasks:
            raise ValueError(f"Task not found: {task_id}")
        
        assignment = self.tasks[task_id]
        assignment.status = "running"
        
        member_id = self.get_available_member(assignment.task)
        
        if not member_id:
            assignment.status = "failed"
            assignment.error = "No available member"
            raise RuntimeError("No available crew member")
        
        member = self.members[member_id]
        member.is_available = False
        member.current_task = task_id
        assignment.assigned_member = member_id
        
        try:
            logger.info(f"Executing task {task_id} with member {member_id}")
            
            result = await member.agent.execute(assignment.task)
            
            assignment.status = "completed"
            assignment.result = result
            
            return result
            
        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")
            assignment.status = "failed"
            assignment.error = str(e)
            raise
            
        finally:
            member.is_available = True
            member.current_task = None
    
    async def execute_workflow(
        self,
        workflow: List[Dict[str, Any]]
    ) -> List[Any]:
        """
        Execute a workflow of tasks.
        
        Args:
            workflow: List of task definitions with 'task' and optional 'specialties', 'priority'
            
        Returns:
            List of results
        """
        results = []
        
        for step in workflow:
            task = step["task"]
            specialties = step.get("specialties")
            priority = step.get("priority", 1)
            
            task_id = await self.assign_task(task, specialties, priority)
            result = await self.execute_task(task_id)
            results.append(result)
        
        return results
    
    async def run_crew(
        self,
        initial_task: str,
        max_rounds: int = 10
    ) -> Dict[str, Any]:
        """
        Run the crew on an initial task.
        
        The crew will collaborate, potentially creating sub-tasks,
        until the task is complete.
        """
        logger.info(f"Running crew on task: {initial_task}")
        
        coordinator = None
        for member_id, member in self.members.items():
            if member.role == CrewRole.COORDINATOR:
                coordinator = member
                break
        
        if not coordinator:
            coordinator = list(self.members.values())[0]
        
        current_task = initial_task
        round_num = 0
        all_results = []
        
        while round_num < max_rounds:
            round_num += 1
            
            try:
                result = await coordinator.agent.execute(current_task)
                all_results.append(result)
                
                if isinstance(result, dict) and result.get("done"):
                    break
                
                if isinstance(result, dict) and result.get("next_task"):
                    current_task = result["next_task"]
                else:
                    break
                    
            except Exception as e:
                logger.error(f"Crew round {round_num} failed: {e}")
                break
        
        return {
            "task": initial_task,
            "rounds": round_num,
            "results": all_results,
            "completed": round_num < max_rounds
        }
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "crew_name": self.name,
            "total_members": len(self.members),
            "available_members": sum(1 for m in self.members.values() if m.is_available),
            "pending_tasks": sum(1 for t in self.tasks.values() if t.status == "pending"),
            "completed_tasks": sum(1 for t in self.tasks.values() if t.status == "completed"),
            "failed_tasks": sum(1 for t in self.tasks.values() if t.status == "failed"),
        }


async def example_crew():
    from src.agents.specialized.researcher import ResearcherAgent
    from src.agents.specialized.coder import CoderAgent
    from src.agents.specialized.reviewer import ReviewerAgent
    
    crew = CrewManager(name="DevCrew")
    
    researcher = ResearcherAgent()
    coder = CoderAgent()
    reviewer = ReviewerAgent()
    
    crew.add_member(researcher, CrewRole.SPECIALIST, {"research"})
    crew.add_member(coder, CrewRole.SPECIALIST, {"coding"})
    crew.add_member(reviewer, CrewRole.SPECIALIST, {"review"})
    
    workflow = [
        {"task": "Research best practices for Python async", "specialties": {"research"}, "priority": 1},
        {"task": "Write code following the best practices", "specialties": {"coding"}, "priority": 2},
        {"task": "Review the generated code", "specialties": {"review"}, "priority": 3},
    ]
    
    results = await crew.execute_workflow(workflow)
    
    print(f"Workflow completed with {len(results)} results")
    print(f"Crew status: {crew.get_status()}")


if __name__ == "__main__":
    asyncio.run(example_crew())
