# src/agents/specialized/reviewer.py
import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import logging

from src.core.base_agent import BaseAgent, AgentConfig

logger = logging.getLogger(__name__)


@dataclass
class ReviewResult:
    item_type: str
    item_content: str
    issues: List[Dict[str, Any]]
    suggestions: List[str]
    approved: bool
    score: float


@dataclass
class ReviewerAgent(BaseAgent):
    name: str = "Reviewer"
    description: str = "Agent specialized in reviewing and critiquing work"
    
    review_strictness: float = 0.7
    auto_approve_threshold: float = 0.9
    
    _review_history: List[ReviewResult] = field(default_factory=list, init=False)
    
    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(name=self.name, description=self.description)
        super().__init__(config)
        self._setup_review_tools()
    
    def _setup_review_tools(self):
        self.register_tool("review_code", self._review_code)
        self.register_tool("review_document", self._review_document)
        self.register_tool("review_design", self._review_design)
    
    async def _review_code(
        self,
        code: str,
        language: str = "python"
    ) -> Dict[str, Any]:
        logger.info(f"Reviewing {language} code")
        await asyncio.sleep(0.1)
        
        issues = []
        suggestions = []
        
        if not code or len(code.strip()) == 0:
            issues.append({"severity": "error", "message": "Empty code submitted"})
        
        if "TODO" in code or "FIXME" in code:
            issues.append({"severity": "warning", "message": "Code contains unfinished markers"})
        
        if "#" not in code and len(code) > 200:
            suggestions.append("Add inline comments for better maintainability")
        
        if "except:" in code:
            issues.append({"severity": "error", "message": "Bare except clause found - be specific"})
        
        if "print(" in code and "debug" not in code.lower():
            suggestions.append("Consider removing debug print statements")
        
        approved = len([i for i in issues if i["severity"] == "error"]) == 0
        
        return {
            "issues": issues,
            "suggestions": suggestions,
            "approved": approved,
            "score": 1.0 - (len(issues) * 0.2) - (len(suggestions) * 0.05)
        }
    
    async def _review_document(
        self,
        content: str,
        doc_type: str = "general"
    ) -> Dict[str, Any]:
        logger.info(f"Reviewing {doc_type} document")
        await asyncio.sleep(0.1)
        
        issues = []
        suggestions = []
        
        if not content or len(content.strip()) == 0:
            issues.append({"severity": "error", "message": "Empty document submitted"})
        
        words = content.split()
        if len(words) < 10:
            suggestions.append("Document seems too short - consider expanding")
        
        if content.isupper():
            suggestions.append("Consider using proper capitalization")
        
        approved = len([i for i in issues if i["severity"] == "error"]) == 0
        
        return {
            "issues": issues,
            "suggestions": suggestions,
            "approved": approved,
            "score": 1.0 - (len(issues) * 0.2)
        }
    
    async def _review_design(
        self,
        design_spec: Dict[str, Any]
    ) -> Dict[str, Any]:
        logger.info("Reviewing design specification")
        await asyncio.sleep(0.1)
        
        issues = []
        suggestions = []
        
        required_fields = ["name", "description", "components"]
        for field in required_fields:
            if field not in design_spec:
                issues.append({"severity": "error", "message": f"Missing required field: {field}"})
        
        if "components" in design_spec:
            components = design_spec["components"]
            if not isinstance(components, list):
                issues.append({"severity": "error", "message": "Components must be a list"})
            elif len(components) == 0:
                suggestions.append("Consider adding more components")
        
        approved = len([i for i in issues if i["severity"] == "error"]) == 0
        
        return {
            "issues": issues,
            "suggestions": suggestions,
            "approved": approved,
            "score": 1.0 - (len(issues) * 0.2)
        }
    
    async def think(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        review_type = context.get("review_type", "general")
        
        self.update_working_memory("current_task", task)
        self.update_working_memory("review_type", review_type)
        
        return {
            "thought": f"Reviewing {review_type}: {task}",
            "action": "review_generic",
            "params": {"task": task, "context": context}
        }
    
    async def act(self, thought_result: Dict[str, Any]) -> Any:
        action = thought_result.get("action")
        params = thought_result.get("params", {})
        
        if action == "review_generic":
            context = params.get("context", {})
            review_type = context.get("review_type", "general")
            
            if review_type == "code":
                return await self._review_code(context.get("code", ""), context.get("language", "python"))
            elif review_type == "document":
                return await self._review_document(context.get("content", ""), context.get("doc_type", "general"))
            elif review_type == "design":
                return await self._review_design(context.get("design_spec", {}))
        
        return None
    
    async def review(
        self,
        item_type: str,
        item_content: Any,
        **kwargs
    ) -> ReviewResult:
        """
        Review an item of any supported type.
        
        Args:
            item_type: Type of item ('code', 'document', 'design')
            item_content: The content to review
            
        Returns:
            ReviewResult with review findings
        """
        context = {"item_type": item_type, item_type: item_content, **kwargs}
        
        if item_type == "code":
            result = await self._review_code(
                item_content,
                kwargs.get("language", "python")
            )
        elif item_type == "document":
            result = await self._review_document(
                item_content,
                kwargs.get("doc_type", "general")
            )
        elif item_type == "design":
            result = await self._review_design(item_content)
        else:
            result = {"issues": [], "suggestions": ["Unknown item type"], "approved": False, "score": 0.0}
        
        review_result = ReviewResult(
            item_type=item_type,
            item_content=str(item_content)[:100],
            issues=result.get("issues", []),
            suggestions=result.get("suggestions", []),
            approved=result.get("approved", False),
            score=result.get("score", 0.0)
        )
        
        self._review_history.append(review_result)
        
        return review_result


async def example_reviewer():
    config = AgentConfig(name="ReviewerAgent", description="Code review specialist")
    agent = ReviewerAgent(config)
    
    code = '''
def example():
    # TODO: implement this
    pass
'''
    
    result = await agent.review("code", code, language="python")
    
    print(f"Approved: {result.approved}")
    print(f"Score: {result.score:.2f}")
    print(f"Issues: {len(result.issues)}")
    print(f"Suggestions: {len(result.suggestions)}")


if __name__ == "__main__":
    asyncio.run(example_reviewer())
