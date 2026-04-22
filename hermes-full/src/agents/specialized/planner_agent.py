"""
Strategic Planner Agent

Task decomposition and strategic planning agent for Hermes.
Provides hierarchical task breakdown and execution planning.

Usage:
    planner = PlannerAgent(llm)
    plan = await planner.create_plan("complex task")
"""

from dataclasses import dataclass, field
from typing import Optional, Any, Callable, Union
from enum import Enum
import asyncio
import json
import logging

logger = logging.getLogger(__name__)


class PlanComplexity(Enum):
    """Task complexity levels"""
    TRIVIAL = "trivial"      # Single action
    SIMPLE = "simple"       # 2-3 sequential steps
    MODERATE = "moderate"   # 4-7 steps with branching
    COMPLEX = "complex"     # 8+ steps, multiple dependencies
    EPIC = "epic"           # Multi-phase project


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class SubTask:
    """A subtask within a plan"""
    id: str
    description: str
    action_type: str
    parameters: dict = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    estimated_duration: int = 0  # minutes
    priority: int = 1
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class ExecutionPlan:
    """Complete execution plan"""
    id: str
    original_task: str
    complexity: PlanComplexity
    subtasks: list[SubTask]
    estimated_total_time: int
    parallel_execution_possible: bool = False
    execution_order: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class PlannerConfig:
    """Configuration for planner agent"""
    max_subtasks: int = 20
    enable_parallel_planning: bool = True
    include_dependencies: bool = True
    estimate_durations: bool = True
    prioritize_tasks: bool = True


class HermesPlannerAgent:
    """
    Strategic planner agent for task decomposition
    """
    
    def __init__(
        self,
        llm: Any,
        config: Optional[PlannerConfig] = None
    ):
        self.llm = llm
        self.config = config or PlannerConfig()
        
    async def create_plan(
        self,
        task: str,
        context: Optional[dict] = None
    ) -> ExecutionPlan:
        """
        Create a detailed execution plan for a task
        
        Args:
            task: The task to plan
            context: Optional context for better planning
            
        Returns:
            ExecutionPlan with subtasks and ordering
        """
        # Assess complexity
        complexity = await self._assess_complexity(task)
        
        # Generate subtasks
        subtasks = await self._generate_subtasks(task, complexity)
        
        # Identify dependencies
        if self.config.include_dependencies:
            subtasks = await self._analyze_dependencies(subtasks)
            
        # Prioritize tasks
        if self.config.prioritize_tasks:
            subtasks = await self._prioritize_tasks(subtasks)
            
        # Calculate execution order
        execution_order = self._calculate_execution_order(subtasks)
        
        # Estimate duration
        total_time = sum(t.estimated_duration for t in subtasks)
        
        return ExecutionPlan(
            id=f"plan_{int(asyncio.get_event_loop().time())}",
            original_task=task,
            complexity=complexity,
            subtasks=subtasks,
            estimated_total_time=total_time,
            parallel_execution_possible=self._can_execute_in_parallel(subtasks),
            execution_order=execution_order
        )
    
    async def _assess_complexity(self, task: str) -> PlanComplexity:
        """Assess task complexity"""
        prompt = f"""Assess the complexity of this task:

Task: {task}

Complexity levels:
- TRIVIAL: Single action, can be done in one step
- SIMPLE: 2-3 sequential steps
- MODERATE: 4-7 steps with some branching
- COMPLEX: 8+ steps, multiple phases
- EPIC: Multi-phase project, days of work

Return only the complexity level name."""

        response = await self._call_llm(prompt)
        
        try:
            return PlanComplexity(response.strip().upper())
        except:
            # Default to moderate if uncertain
            return PlanComplexity.MODERATE
    
    async def _generate_subtasks(
        self,
        task: str,
        complexity: PlanComplexity
    ) -> list[SubTask]:
        """Generate subtasks from main task"""
        
        # Determine number of subtasks based on complexity
        num_subtasks = {
            PlanComplexity.TRIVIAL: 1,
            PlanComplexity.SIMPLE: 3,
            PlanComplexity.MODERATE: 6,
            PlanComplexity.COMPLEX: 12,
            PlanComplexity.EPIC: 20
        }.get(complexity, 5)
        
        num_subtasks = min(num_subtasks, self.config.max_subtasks)
        
        prompt = f"""Break down this task into {num_subtasks} specific subtasks:

Task: {task}

For each subtask provide:
- Unique ID
- Clear description of what to do
- Action type (e.g., "research", "code", "write", "test", "review")
- Key parameters needed

Return as JSON array:
[{{"id": "step_1", "description": "...", "action_type": "...", "parameters": {{}}}}]"""

        response = await self._call_llm(prompt)
        
        try:
            data = json.loads(response)
            subtasks = []
            
            for item in data:
                subtask = SubTask(
                    id=item.get("id", f"step_{len(subtasks)}"),
                    description=item.get("description", ""),
                    action_type=item.get("action_type", "general"),
                    parameters=item.get("parameters", {}),
                    estimated_duration=item.get("estimated_duration", 10)
                )
                subtasks.append(subtask)
                
            return subtasks
            
        except json.JSONDecodeError:
            logger.error("Failed to parse subtasks")
            return self._fallback_subtasks(task)
    
    def _fallback_subtasks(self, task: str) -> list[SubTask]:
        """Fallback when LLM fails"""
        return [
            SubTask(
                id="step_1",
                description=f"Execute: {task}",
                action_type="execute",
                estimated_duration=30
            )
        ]
    
    async def _analyze_dependencies(
        self,
        subtasks: list[SubTask]
    ) -> list[SubTask]:
        """Analyze and set dependencies between subtasks"""
        
        # Create prompt for dependency analysis
        task_list = "\n".join([
            f"- {t.id}: {t.description}"
            for t in subtasks
        ])
        
        prompt = f"""Analyze dependencies between these subtasks:

{json.dumps(task_list, indent=2)}

For each subtask, list the IDs of subtasks it depends on (must complete before it starts).
Return as JSON object:
{{"subtask_id": ["dependency_id1", "dependency_id2"]}}"""

        response = await self._call_llm(prompt)
        
        try:
            deps = json.loads(response)
            
            for subtask in subtasks:
                if subtask.id in deps:
                    subtask.dependencies = deps[subtask.id]
                    
        except json.JSONDecodeError:
            # Set simple linear dependencies if parsing fails
            for i, subtask in enumerate(subtasks):
                if i > 0:
                    subtask.dependencies = [subtasks[i-1].id]
                    
        return subtasks
    
    async def _prioritize_tasks(
        self,
        subtasks: list[SubTask]
    ) -> list[SubTask]:
        """Prioritize tasks based on dependencies and importance"""
        
        # Simple prioritization: tasks with fewer dependencies first
        # More sophisticated version would use LLM for importance scoring
        
        prioritized = []
        remaining = subtasks.copy()
        
        while remaining:
            # Find tasks with all dependencies satisfied
            ready = [
                t for t in remaining
                if all(d in [p.id for p in prioritized] for d in t.dependencies)
            ]
            
            if not ready:
                # Deadlock - just take the first one
                ready = [remaining[0]]
                
            # Sort by priority then by estimated duration (shorter first)
            ready.sort(key=lambda t: (t.priority, t.estimated_duration))
            
            prioritized.append(ready[0])
            remaining.remove(ready[0])
            
        return prioritized
    
    def _calculate_execution_order(
        self,
        subtasks: list[SubTask]
    ) -> list[str]:
        """Calculate the order of execution"""
        return [t.id for t in subtasks]
    
    def _can_execute_in_parallel(self, subtasks: list[SubTask]) -> bool:
        """Check if any tasks can execute in parallel"""
        for subtask in subtasks:
            if not subtask.dependencies:
                # Tasks with no dependencies could run in parallel
                other_no_deps = sum(
                    1 for t in subtasks
                    if t.id != subtask.id and not t.dependencies
                )
                if other_no_deps > 0:
                    return True
        return False
    
    async def execute_plan(
        self,
        plan: ExecutionPlan,
        executor: Callable
    ) -> dict:
        """
        Execute a plan with the given executor function
        
        Args:
            plan: The plan to execute
            executor: Async function(subtask) -> result
            
        Returns:
            Dictionary with results and statistics
        """
        results = {}
        start_time = asyncio.get_event_loop().time()
        
        for subtask_id in plan.execution_order:
            subtask = next(t for t in plan.subtasks if t.id == subtask_id)
            
            # Check dependencies
            deps_satisfied = all(
                results.get(d, {}).get("status") == "completed"
                for d in subtask.dependencies
            )
            
            if not deps_satisfied:
                subtask.status = TaskStatus.BLOCKED
                results[subtask_id] = {
                    "status": "blocked",
                    "error": "Dependencies not satisfied"
                }
                continue
                
            try:
                subtask.status = TaskStatus.IN_PROGRESS
                result = await executor(subtask)
                subtask.status = TaskStatus.COMPLETED
                subtask.result = result
                results[subtask_id] = {
                    "status": "completed",
                    "result": result
                }
            except Exception as e:
                subtask.status = TaskStatus.FAILED
                subtask.error = str(e)
                results[subtask_id] = {
                    "status": "failed",
                    "error": str(e)
                }
                
        end_time = asyncio.get_event_loop().time()
        
        return {
            "plan_id": plan.id,
            "results": results,
            "completed": sum(1 for r in results.values() if r.get("status") == "completed"),
            "failed": sum(1 for r in results.values() if r.get("status") == "failed"),
            "total_time": end_time - start_time
        }
    
    async def _call_llm(self, prompt: str) -> str:
        """Call LLM with prompt"""
        if hasattr(self.llm, 'agenerate'):
            response = await self.llm.agenerate([prompt])
            return response if isinstance(response, str) else str(response)
        return await self.llm.generate(prompt)


class HierarchicalPlanner:
    """
    Multi-level planner for complex tasks
    Creates hierarchical plans with high-level phases and detailed steps
    """
    
    def __init__(self, llm: Any):
        self.llm = llm
        self.planner = HermesPlannerAgent(llm)
        
    async def create_hierarchical_plan(
        self,
        task: str,
        num_phases: int = 3
    ) -> list[ExecutionPlan]:
        """
        Create a hierarchical plan with multiple phases
        
        Args:
            task: The overall task
            num_phases: Number of major phases
            
        Returns:
            List of ExecutionPlans, one per phase
        """
        # First, identify major phases
        phases = await self._identify_phases(task, num_phases)
        
        # Create a plan for each phase
        plans = []
        for i, phase in enumerate(phases):
            phase_task = f"Phase {i+1}: {phase['name']}\nDescription: {phase['description']}"
            phase_context = phase.get("context", {})
            
            plan = await self.planner.create_plan(phase_task, phase_context)
            plans.append(plan)
            
        return plans
    
    async def _identify_phases(
        self,
        task: str,
        num_phases: int
    ) -> list[dict]:
        """Identify major phases of the task"""
        
        prompt = f"""Break down this task into {num_phases} major phases:

Task: {task}

For each phase provide:
- Name
- Brief description
- Key objectives
- Any context needed

Return as JSON array:
[{{"name": "...", "description": "...", "context": {{}}}}]"""

        response = await self._call_llm(prompt)
        
        try:
            return json.loads(response)
        except:
            return [{"name": "Main", "description": task, "context": {}}]
    
    async def _call_llm(self, prompt: str) -> str:
        """Call LLM with prompt"""
        if hasattr(self.llm, 'agenerate'):
            response = await self.llm.agenerate([prompt])
            return response if isinstance(response, str) else str(response)
        return await self.llm.generate(prompt)
