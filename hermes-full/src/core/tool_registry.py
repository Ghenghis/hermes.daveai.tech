# src/core/tool_registry.py
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Set
from enum import Enum
import asyncio
import inspect
import json
import logging

logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    SEARCH = "search"
    EXECUTION = "execution"
    IO = "io"
    API = "api"
    DATA = "data"
    CUSTOM = "custom"


@dataclass
class ToolSchema:
    name: str
    description: str
    parameters: Dict[str, Any]
    returns: Dict[str, Any]
    examples: List[Dict[str, Any]] = field(default_factory=list)
    
    def validate_parameters(self, params: Dict[str, Any]) -> bool:
        required = self.parameters.get('required', [])
        for req in required:
            if req not in params:
                raise ValueError(f"Missing required parameter: {req}")
        return True


@dataclass
class Tool:
    name: str
    description: str
    category: ToolCategory
    schema: ToolSchema
    func: Callable
    is_async: bool = False
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        self.is_async = asyncio.iscoroutinefunction(self.func)
    
    async def execute(self, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Any:
        self.schema.validate_parameters(parameters)
        context = context or {}
        
        if self.is_async:
            if inspect.iscoroutinefunction(self.func):
                return await self.func(**parameters, context=context)
            else:
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, lambda: self.func(**parameters, context=context))
        else:
            return self.func(**parameters, context=context)
    
    def execute_sync(self, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Any:
        self.schema.validate_parameters(parameters)
        context = context or {}
        return self.func(**parameters, context=context)


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._categories: Dict[ToolCategory, List[str]] = {}
        self._tags: Dict[str, Set[str]] = {}
        self._aliases: Dict[str, str] = {}
        self._lock = asyncio.Lock()
        
    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            logger.warning(f"Tool {tool.name} already registered, replacing")
            
        self._tools[tool.name] = tool
        
        if tool.category not in self._categories:
            self._categories[tool.category] = []
        if tool.name not in self._categories[tool.category]:
            self._categories[tool.category].append(tool.name)
            
        for tag in tool.tags:
            if tag not in self._tags:
                self._tags[tag] = set()
            self._tags[tag].add(tool.name)
            
        logger.info(f"Registered tool: {tool.name} in category {tool.category.value}")
        
    def register_alias(self, alias: str, tool_name: str) -> None:
        if tool_name not in self._tools:
            raise ValueError(f"Cannot create alias: tool {tool_name} not found")
        self._aliases[alias] = tool_name
        
    def get(self, name: str) -> Optional[Tool]:
        tool_name = self._aliases.get(name, name)
        return self._tools.get(tool_name)
    
    def get_by_category(self, category: ToolCategory) -> List[Tool]:
        tool_names = self._categories.get(category, [])
        return [self._tools[name] for name in tool_names if name in self._tools]
    
    def get_by_tags(self, tags: Set[str]) -> List[Tool]:
        tool_names = set()
        for tag in tags:
            tool_names.update(self._tags.get(tag, set()))
        return [self._tools[name] for name in tool_names if name in self._tools]
    
    def search(self, query: str) -> List[Tool]:
        query_lower = query.lower()
        results = []
        
        for tool in self._tools.values():
            if query_lower in tool.name.lower():
                results.append((tool, 1.0))
            elif query_lower in tool.description.lower():
                results.append((tool, 0.7))
            elif any(query_lower in tag.lower() for tag in tool.tags):
                results.append((tool, 0.5))
                
        return [tool for tool, _ in sorted(results, key=lambda x: x[1], reverse=True)]
    
    def list_all(self) -> List[Tool]:
        return list(self._tools.values())
    
    def unregister(self, name: str) -> bool:
        if name not in self._tools:
            return False
            
        tool = self._tools[name]
        del self._tools[name]
        
        if tool.category in self._categories:
            self._categories[tool.category].remove(name)
            
        for tag in tool.tags:
            if tag in self._tags:
                self._tags[tag].discard(name)
                
        logger.info(f"Unregistered tool: {name}")
        return True


def tool(
    name: str,
    description: str,
    category: ToolCategory = ToolCategory.CUSTOM,
    tags: Optional[Set[str]] = None
):
    def decorator(func: Callable) -> Tool:
        sig = inspect.signature(func)
        
        parameters = {
            'type': 'object',
            'properties': {},
            'required': []
        }
        
        for param_name, param in sig.parameters.items():
            if param_name == 'context':
                continue
                
            param_type = 'string'
            if param.annotation == int:
                param_type = 'integer'
            elif param.annotation == float:
                param_type = 'number'
            elif param.annotation == bool:
                param_type = 'boolean'
            elif param.annotation == list:
                param_type = 'array'
            elif param.annotation == dict:
                param_type = 'object'
                
            parameters['properties'][param_name] = {
                'type': param_type,
                'description': f'Parameter {param_name}'
            }
            
            if param.default == inspect.Parameter.empty:
                parameters['required'].append(param_name)
                
        schema = ToolSchema(
            name=name,
            description=description,
            parameters=parameters,
            returns={'type': 'any', 'description': 'Tool result'}
        )
        
        return Tool(
            name=name,
            description=description,
            category=category,
            schema=schema,
            func=func,
            tags=tags or set()
        )
    
    return decorator


@tool(name="web_search", description="Search the web for information", category=ToolCategory.SEARCH, tags={"search", "web"})
async def web_search(query: str, num_results: int = 5, context: dict = None) -> List[Dict[str, str]]:
    return [
        {"title": f"Result for '{query}'", "url": "https://example.com/result", "snippet": f"Information about {query}"}
    ]


@tool(name="calculator", description="Perform mathematical calculations", category=ToolCategory.EXECUTION, tags={"math", "calculate"})
def calculator(expression: str, context: dict = None) -> float:
    import ast
    import operator
    
    operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }
    
    def eval_expr(node):
        if isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type in operators:
                return operators[op_type](eval_expr(node.left), eval_expr(node.right))
        elif isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.USub):
                return -eval_expr(node.operand)
        raise ValueError(f"Unsupported expression: {expression}")
    
    tree = ast.parse(expression, mode='eval')
    return eval_expr(tree.body)
