# src/patterns/planner_executor.py
import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
import logging
import uuid
import inspect

logger = logging.getLogger(__name__)


class StepStatus(Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ExecutionStep:
    id: str
    description: str
    tool_name: str
    parameters: Dict[str, Any]
    status: StepStatus = StepStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)


@dataclass
class ExecutionPlan:
    id: str
    goal: str
    steps: List[ExecutionStep]
    created_at: float = 0
    completed_at: Optional[float] = None
    
    def get_step(self, step_id: str) -> Optional[ExecutionStep]:
        for step in self.steps:
            if step.id == step_id:
                return step
        return None
    
    def get_ready_steps(self) -> List[ExecutionStep]:
        ready = []
        for step in self.steps:
            if step.status != StepStatus.PENDING:
                continue
            deps_met = all(
                self.get_step(dep_id).status == StepStatus.COMPLETED
                for dep_id in step.dependencies
            )
            if deps_met:
                ready.append(step)
        return ready


@dataclass
class PlannerExecutor:
    name: str
    description: str = ""
    max_plan_steps: int = 10
    tools: Dict[str, Callable] = field(default_factory=dict)
    planner_llm: Optional[Any] = field(default=None, repr=False)
    executor_llm: Optional[Any] = field(default=None, repr=False)
    
    _current_plan: Optional[ExecutionPlan] = field(default=None, init=False)
    _context: Dict[str, Any] = field(default_factory=dict, init=False)
    
    def register_tool(self, name: str, func: Callable, description: str = ""):
        self.tools[name] = func
        logger.info(f"Registered tool: {name}")
    
    async def plan(self, goal: str, context: Optional[Dict[str, Any]] = None) -> ExecutionPlan:
        logger.info(f"Planning for goal: {goal}")
        
        tools_description = "\n".join(
            f"- {name}: {func.__doc__ or 'No description'}"
            for name, func in self.tools.items()
        )
        
        prompt = f"""Create a plan to achieve this goal: {goal}

Available tools:
{tools_description}

Respond with a JSON array of steps:
[
  {{"id": "step_1", "description": "...", "tool_name": "...", "parameters": {{}}, "dependencies": []}}
]
Maximum {self.max_plan_steps} steps."""
        
        if self.planner_llm:
            response = await self.planner_llm.complete(prompt)
        else:
            response = self._mock_plan_response(goal)
        
        steps = self._parse_plan_response(response)
        
        plan = ExecutionPlan(id=str(uuid.uuid4()), goal=goal, steps=steps)
        self._current_plan = plan
        logger.info(f"Created plan with {len(steps)} steps")
        
        return plan
    
    def _mock_plan_response(self, goal: str) -> str:
        return f'''[
  {{"id": "step_1", "description": "Search for information", "tool_name": "web_search", "parameters": {{"query": "{goal}"}}, "dependencies": []}},
  {{"id": "step_2", "description": "Process results", "tool_name": "process_results", "parameters": {{"data": "{{context.last_result}}"}}, "dependencies": ["step_1"]}}
]'''
    
    def _parse_plan_response(self, response: str) -> List[ExecutionStep]:
        try:
            steps_data = json.loads(response)
        except json.JSONDecodeError:
            logger.error("Failed to parse plan response")
            return []
        
        steps = []
        for step_data in steps_data:
            step = ExecutionStep(
                id=step_data["id"],
                description=step_data["description"],
                tool_name=step_data["tool_name"],
                parameters=step_data.get("parameters", {}),
                dependencies=step_data.get("dependencies", [])
            )
            steps.append(step)
        
        return steps
    
    async def execute(self, plan: ExecutionPlan) -> Dict[str, Any]:
        logger.info(f"Executing plan {plan.id} with {len(plan.steps)} steps")
        
        pending_steps = {step.id: asyncio.create_task(self._execute_step(step))
                        for step in plan.get_ready_steps()}
        
        completed = 0
        total = len(plan.steps)
        
        while pending_steps and completed < total:
            done, pending_steps = await asyncio.wait(
                pending_steps.values(),
                return_when=asyncio.FIRST_COMPLETED
            )
            
            for task in done:
                step_id = None
                for s, t in list(pending_steps.items()):
                    if t == task:
                        step_id = s
                        break
                
                result = task.result()
                if result["status"] == StepStatus.COMPLETED:
                    completed += 1
                    logger.info(f"Step {result['step_id']} completed")
                    
                    for new_step in plan.get_ready_steps():
                        pending_steps[new_step.id] = asyncio.create_task(self._execute_step(new_step))
                elif result["status"] == StepStatus.FAILED:
                    logger.error(f"Step {result['step_id']} failed: {result['error']}")
            
            await asyncio.sleep(0.1)
        
        return {
            "plan_id": plan.id,
            "completed_steps": completed,
            "total_steps": total,
            "success": completed == total,
            "steps": [
                {"id": s.id, "description": s.description, "status": s.status.value, "result": s.result, "error": s.error}
                for s in plan.steps
            ]
        }
    
    async def _execute_step(self, step: ExecutionStep) -> Dict[str, Any]:
        step.status = StepStatus.EXECUTING
        logger.info(f"Executing step {step.id}: {step.description}")
        
        if step.tool_name not in self.tools:
            step.status = StepStatus.FAILED
            step.error = f"Unknown tool: {step.tool_name}"
            return {"step_id": step.id, "status": step.status, "error": step.error}
        
        try:
            tool = self.tools[step.tool_name]
            resolved_params = self._resolve_parameters(step.parameters)
            
            if asyncio.iscoroutinefunction(tool):
                result = await tool(**resolved_params)
            else:
                result = tool(**resolved_params)
            
            step.status = StepStatus.COMPLETED
            step.result = result
            
            return {"step_id": step.id, "status": step.status, "result": result}
            
        except Exception as e:
            logger.error(f"Step {step.id} failed: {e}")
            step.status = StepStatus.FAILED
            step.error = str(e)
            return {"step_id": step.id, "status": step.status, "error": str(e)}
    
    def _resolve_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        resolved = {}
        for key, value in parameters.items():
            if isinstance(value, str) and value.startswith("{{context."):
                context_key = value[10:-2]
                resolved[key] = self._context.get(context_key)
            else:
                resolved[key] = value
        return resolved
    
    async def run(self, goal: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self._context = context or {}
        
        plan = await self.plan(goal, self._context)
        result = await self.execute(plan)
        
        return {"goal": goal, "plan_id": plan.id, **result}


async def example_usage():
    def web_search(query: str, num_results: int = 5) -> List[Dict[str, str]]:
        return [{"title": f"Result for '{query}'", "url": "https://example.com", "snippet": f"Info about {query}"}]
    
    agent = PlannerExecutor(name="ResearchAgent")
    agent.register_tool("web_search", web_search)
    
    result = await agent.run("Research Python async programming")
    print(f"Success: {result['success']}")
    print(f"Completed: {result['completed_steps']}/{result['total_steps']}")


if __name__ == "__main__":
    import json
    asyncio.run(example_usage())
