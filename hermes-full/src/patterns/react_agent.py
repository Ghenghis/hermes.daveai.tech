# src/patterns/react_agent.py
import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
import logging
import json
import uuid

logger = logging.getLogger(__name__)


class ActionResult:
    def __init__(self, success: bool, data: Any = None, error: Optional[str] = None):
        self.success = success
        self.data = data
        self.error = error


@dataclass
class ReActStep:
    thought: str
    action: str
    action_input: Dict[str, Any]
    observation: Optional[str] = None
    result: Optional[ActionResult] = None


@dataclass
class ReActAgent:
    name: str
    description: str = ""
    max_iterations: int = 10
    tools: Dict[str, Callable] = field(default_factory=dict)
    llm_provider: Optional[Any] = field(default=None, repr=False)
    
    _history: List[ReActStep] = field(default_factory=list, init=False)
    _context: Dict[str, Any] = field(default_factory=dict, init=False)
    
    def register_tool(self, name: str, func: Callable, description: str = ""):
        self.tools[name] = func
        logger.info(f"Registered tool: {name}")
        
    async def think(self, prompt: str, context: Dict[str, Any]) -> ReActStep:
        history_text = self._format_history()
        tools_description = self._format_tools()
        
        system_prompt = f"""You are a {self.name} agent following the ReAct pattern.

TASK: {prompt}

AVAILABLE TOOLS:
{tools_description}

PREVIOUS STEPS:
{history_text if history_text else "No previous steps taken."}

CONTEXT:
{self._format_context(context)}

Follow the ReAct pattern:
1. THOUGHT: Reason about the current situation
2. ACTION: Choose a tool or "finish"
3. ACTION_INPUT: Arguments for the tool

Respond exactly in this format:
THOUGHT: [your reasoning]
ACTION: [tool_name or "finish"]
ACTION_INPUT: {{"param1": "value1", ...}}
"""
        
        response = await self._call_llm(system_prompt)
        return self._parse_llm_response(response)
    
    def _format_history(self) -> str:
        if not self._history:
            return ""
        lines = []
        for i, step in enumerate(self._history, 1):
            lines.append(f"Step {i}:")
            lines.append(f"  Thought: {step.thought}")
            lines.append(f"  Action: {step.action}")
            lines.append(f"  Action Input: {step.action_input}")
            if step.observation:
                lines.append(f"  Observation: {step.observation}")
            lines.append("")
        return "\n".join(lines)
    
    def _format_tools(self) -> str:
        if not self.tools:
            return "No tools available."
        lines = []
        for name, func in self.tools.items():
            doc = func.__doc__ or "No description"
            lines.append(f"- {name}: {doc.strip().split(chr(10))[0]}")
        return "\n".join(lines)
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        if not context:
            return "No additional context."
        lines = []
        for key, value in context.items():
            if len(str(value)) > 200:
                value = str(value)[:200] + "..."
            lines.append(f"- {key}: {value}")
        return "\n".join(lines)
    
    async def _call_llm(self, prompt: str) -> str:
        if self.llm_provider:
            return await self.llm_provider.complete(prompt)
        return self._mock_llm_response(prompt)
    
    def _mock_llm_response(self, prompt: str) -> str:
        return """THOUGHT: I need to search for information about this topic.
ACTION: web_search
ACTION_INPUT: {"query": "information about topic", "num_results": 3}"""
    
    def _parse_llm_response(self, response: str) -> ReActStep:
        lines = response.strip().split("\n")
        thought = ""
        action = ""
        action_input = {}
        
        for line in lines:
            line = line.strip()
            if line.startswith("THOUGHT:"):
                thought = line[8:].strip()
            elif line.startswith("ACTION:"):
                action = line[7:].strip()
            elif line.startswith("ACTION_INPUT:"):
                input_str = line[13:].strip()
                action_input = self._parse_action_input(input_str)
        
        return ReActStep(
            thought=thought,
            action=action,
            action_input=action_input
        )
    
    def _parse_action_input(self, input_str: str) -> Dict[str, Any]:
        try:
            return json.loads(input_str)
        except json.JSONDecodeError:
            try:
                cleaned = input_str.replace("'", '"')
                return json.loads(cleaned)
            except json.JSONDecodeError:
                return {}
    
    async def execute_tool(self, action: str, action_input: Dict[str, Any]) -> ActionResult:
        if action == "finish":
            return ActionResult(success=True, data="Task completed")
        
        if action not in self.tools:
            return ActionResult(success=False, error=f"Unknown tool: {action}")
        
        try:
            tool = self.tools[action]
            if asyncio.iscoroutinefunction(tool):
                result = await tool(**action_input)
            else:
                result = tool(**action_input)
            return ActionResult(success=True, data=result)
        except Exception as e:
            logger.error(f"Tool {action} failed: {e}")
            return ActionResult(success=False, error=str(e))
    
    async def run(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self._history = []
        self._context = context or {}
        
        for iteration in range(self.max_iterations):
            logger.info(f"ReAct iteration {iteration + 1}/{self.max_iterations}")
            step = await self.think(prompt, self._context)
            self._history.append(step)
            
            if step.action == "finish":
                final_result = step.action_input.get("response", "Task completed")
                return {
                    "result": final_result,
                    "history": self._history,
                    "iterations": iteration + 1
                }
            
            result = await self.execute_tool(step.action, step.action_input)
            step.result = result
            step.observation = str(result.data) if result.success else result.error
            self._context["last_result"] = result.data
            self._context["last_observation"] = step.observation
            
            if not result.success:
                logger.warning(f"Tool failed: {result.error}")
        
        return {
            "result": "Max iterations reached",
            "history": self._history,
            "iterations": self.max_iterations
        }


async def example_usage():
    def web_search(query: str, num_results: int = 5) -> List[Dict[str, str]]:
        return [
            {"title": f"Result for '{query}'", "url": "https://example.com/1", "snippet": f"Info about {query}"}
        ]
    
    def calculator(expression: str) -> float:
        import ast
        import operator
        operators = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}
        tree = ast.parse(expression, mode='eval')
        left, right = tree.body.left, tree.body.right
        op = operators[type(tree.body.op)]
        return op(eval(ast.unparse(left)), eval(ast.unparse(right)))
    
    agent = ReActAgent(name="ResearchAssistant")
    agent.register_tool("web_search", web_search)
    agent.register_tool("calculator", calculator)
    
    result = await agent.run("Search for Python decorators and calculate 15 + 25")
    print(f"Result: {result['result']}")
    print(f"Iterations: {result['iterations']}")


if __name__ == "__main__":
    asyncio.run(example_usage())
