"""
Reflexion Agent Implementation

Self-correcting agent that learns from failures using the Reflexion pattern.
Based on the architecture from Shinn et al. and OpenHands implementation.

Usage:
    agent = ReflexionAgent(
        llm=my_llm,
        executor=execute_fn,
        evaluator=evaluate_fn
    )
    result = await agent.execute_with_reflexion("my task")
"""

from dataclasses import dataclass, field
from typing import Optional, Any, Callable, Union
from enum import Enum
import asyncio
import json
import time
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    """Result status of execution"""
    SUCCESS = "success"
    FAILURE = "failure"
    RETRYABLE = "retryable"
    UNKNOWN = "unknown"


@dataclass
class Lesson:
    """
    A learned lesson from failed execution
    """
    id: str
    task_pattern: str
    failure_mode: str
    correction: str
    avoid_patterns: list[str] = field(default_factory=list)
    success_count: int = 0
    failure_count: int = 0
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=lambda: time.time())
    
    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "task_pattern": self.task_pattern,
            "failure_mode": self.failure_mode,
            "correction": self.correction,
            "avoid_patterns": self.avoid_patterns,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Lesson":
        return cls(**data)


@dataclass
class ExecutionResult:
    """Result of an execution attempt"""
    output: Any
    status: ExecutionStatus
    feedback: Optional[str] = None
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class ReflexionConfig:
    """Configuration for reflexion agent"""
    max_retries: int = 3
    max_depth: int = 5
    lesson_storage_path: str = ".hermes/reflexion_lessons"
    similarity_threshold: float = 0.7
    enable_lesson_lookup: bool = True
    store_failures: bool = True


class LessonMemory:
    """
    Persistent storage for learned lessons
    """
    
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.lessons: dict[str, Lesson] = {}
        self._load_lessons()
        
    def _lesson_file_path(self) -> Path:
        return self.storage_path / "lessons.json"
    
    def _load_lessons(self):
        """Load lessons from persistent storage"""
        lesson_file = self._lesson_file_path()
        if lesson_file.exists():
            try:
                with open(lesson_file, 'r') as f:
                    data = json.load(f)
                    for lesson_data in data:
                        lesson = Lesson.from_dict(lesson_data)
                        self.lessons[lesson.id] = lesson
                logger.info(f"Loaded {len(self.lessons)} lessons from storage")
            except Exception as e:
                logger.warning(f"Failed to load lessons: {e}")
                
    def _save_lessons(self):
        """Persist lessons to storage"""
        try:
            lesson_file = self._lesson_file_path()
            data = [lesson.to_dict() for lesson in self.lessons.values()]
            with open(lesson_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save lessons: {e}")
            
    def store_lesson(self, lesson: Lesson):
        """Store a new or updated lesson"""
        self.lessons[lesson.id] = lesson
        self._save_lessons()
        
    def get_lesson(self, lesson_id: str) -> Optional[Lesson]:
        """Retrieve a specific lesson"""
        if lesson_id in self.lessons:
            self.lessons[lesson_id].last_accessed = time.time()
        return self.lessons.get(lesson_id)
        
    def find_relevant_lessons(
        self,
        task_description: str,
        max_results: int = 5
    ) -> list[Lesson]:
        """Find lessons relevant to the task using keyword matching"""
        relevant = []
        task_lower = task_description.lower()
        task_words = set(task_lower.split())
        
        for lesson in self.lessons.values():
            # Skip lessons with low success rates
            if lesson.success_rate < 0.3:
                continue
                
            # Check avoid patterns
            matched_avoid = False
            for pattern in lesson.avoid_patterns:
                if pattern.lower() in task_lower:
                    matched_avoid = True
                    break
                    
            if matched_avoid:
                continue
                
            # Check task pattern match
            pattern_words = set(lesson.task_pattern.lower().split())
            overlap = len(task_words & pattern_words)
            
            if overlap > 0:
                relevant.append((lesson, overlap))
                
        # Sort by overlap and success rate
        relevant.sort(key=lambda x: (x[1], x[0].success_rate), reverse=True)
        return [lesson for lesson, _ in relevant[:max_results]]
    
    def increment_success(self, lesson_id: str):
        """Increment success counter for a lesson"""
        if lesson_id in self.lessons:
            self.lessons[lesson_id].success_count += 1
            self._save_lessons()
            
    def increment_failure(self, lesson_id: str):
        """Increment failure counter for a lesson"""
        if lesson_id in self.lessons:
            self.lessons[lesson_id].failure_count += 1
            self._save_lessons()
    
    def clear_old_lessons(self, days: int = 30):
        """Remove lessons not accessed in specified days"""
        cutoff = time.time() - (days * 86400)
        to_remove = [
            lid for lid, lesson in self.lessons.items()
            if lesson.last_accessed < cutoff and lesson.success_count == 0
        ]
        for lid in to_remove:
            del self.lessons[lid]
        if to_remove:
            self._save_lessons()
            logger.info(f"Cleared {len(to_remove)} old lessons")


class ReflexionAgent:
    """
    Agent with self-correction via reflection
    
    Implements the Reflexion pattern where the agent:
    1. Executes a task
    2. Evaluates the result
    3. Reflects on failures and stores lessons
    4. Plans modifications for future attempts
    
    Args:
        llm: Language model for reasoning
        executor: Async function(task, context) -> ExecutionResult
        evaluator: Async function(task, result) -> ExecutionResult
        config: Optional configuration
    """
    
    def __init__(
        self,
        llm: Any,
        executor: Callable,
        evaluator: Callable,
        config: Optional[ReflexionConfig] = None
    ):
        self.llm = llm
        self.executor = executor
        self.evaluator = evaluator
        self.config = config or ReflexionConfig()
        self.lesson_memory = LessonMemory(self.config.lesson_storage_path)
        self.execution_history: list[dict] = []
        
    async def execute_with_reflexion(
        self,
        task: str,
        context: Optional[dict] = None
    ) -> ExecutionResult:
        """
        Execute task with self-correction loop
        
        Args:
            task: Task description
            context: Additional context for execution
            
        Returns:
            ExecutionResult with final output
        """
        attempt = 0
        current_task = task
        current_context = context.copy() if context else {}
        applied_lessons: list[str] = []
        last_result: Optional[ExecutionResult] = None
        
        while attempt < self.config.max_retries:
            # Apply relevant lessons if not first attempt
            if attempt > 0 and self.config.enable_lesson_lookup:
                relevant = self.lesson_memory.find_relevant_lessons(task)
                if relevant and attempt <= len(relevant):
                    lesson = relevant[attempt - 1]
                    current_context["applied_lesson"] = lesson
                    applied_lessons.append(lesson.id)
                    logger.info(f"Applying lesson {lesson.id} for attempt {attempt}")
                    
            # Execute the task
            try:
                result = await self.executor(current_task, current_context)
            except Exception as e:
                logger.error(f"Execution error on attempt {attempt}: {e}")
                result = ExecutionResult(
                    output=None,
                    status=ExecutionStatus.FAILURE,
                    error=str(e)
                )
                
            last_result = result
            
            # Evaluate the result
            evaluation = await self.evaluator(task, result)
            
            if evaluation.status == ExecutionStatus.SUCCESS:
                # Record success
                for lesson_id in applied_lessons:
                    self.lesson_memory.increment_success(lesson_id)
                    
                self.execution_history.append({
                    "task": task,
                    "attempt": attempt + 1,
                    "status": "success",
                    "lessons_applied": applied_lessons
                })
                
                return result
                
            # Reflection on failure
            logger.info(f"Attempt {attempt} failed, generating reflection")
            reflection = await self._reflect(task, result, evaluation)
            
            # Store lesson if critical failure
            if reflection.is_critical and self.config.store_failures:
                lesson = Lesson(
                    id=f"lesson_{int(time.time())}_{attempt}",
                    task_pattern=task,
                    failure_mode=reflection.failure_analysis,
                    correction=reflection.correction,
                    avoid_patterns=reflection.avoid_patterns
                )
                self.lesson_memory.store_lesson(lesson)
                logger.info(f"Stored new lesson: {lesson.id}")
                
            # Generate new approach for retry
            if attempt < self.config.max_retries - 1:
                current_task, current_context = await self._plan_modification(
                    task, result, reflection, current_context
                )
                
            attempt += 1
            
        # Max retries exceeded
        self.execution_history.append({
            "task": task,
            "attempt": attempt,
            "status": "failure",
            "lessons_applied": applied_lessons
        })
        
        return ExecutionResult(
            output=last_result.output if last_result else None,
            status=ExecutionStatus.FAILURE,
            feedback=f"Failed after {self.config.max_retries} attempts"
        )
        
    async def _reflect(
        self,
        task: str,
        result: ExecutionResult,
        evaluation: ExecutionResult
    ) -> "Reflection":
        """
        Generate reflection on the execution
        
        Returns Reflection object with analysis
        """
        prompt = f"""
You are analyzing a failed task execution to generate insights.

Task: {task}
Output: {str(result.output)[:500]}
Error: {result.error or 'None'}
Feedback: {result.feedback or 'None'}
Evaluation: {evaluation.feedback or 'None'}

Based on this information, provide:
1. What specifically went wrong (be precise)
2. What patterns to avoid in retry (list 2-3 specific things)
3. What correction strategy to use
4. Is this a critical failure that should be stored as a lesson? (yes/no)

Format your response as:
WRONG: <specific failure>
AVOID: <pattern1>; <pattern2>; <pattern3>
CORRECTION: <strategy>
CRITICAL: <yes/no>
"""
        
        try:
            response = await self._call_llm(prompt)
            return self._parse_reflection(response)
        except Exception as e:
            logger.error(f"Reflection generation failed: {e}")
            return Reflection(
                failure_analysis="Unknown failure",
                avoid_patterns=[],
                correction="Try a different approach",
                is_critical=False
            )
    
    async def _call_llm(self, prompt: str) -> str:
        """Call LLM with prompt"""
        if hasattr(self.llm, 'agenerate'):
            response = await self.llm.agenerate([prompt])
            return response if isinstance(response, str) else str(response)
        else:
            # Fallback for different LLM interfaces
            return await self.llm.generate(prompt)
    
    def _parse_reflection(self, response: str) -> "Reflection":
        """Parse LLM response into Reflection object"""
        lines = response.strip().split('\n')
        
        failure_analysis = ""
        avoid_patterns = []
        correction = ""
        is_critical = False
        
        for line in lines:
            line = line.strip()
            if line.startswith("WRONG:"):
                failure_analysis = line[6:].strip()
            elif line.startswith("AVOID:"):
                patterns = line[6:].strip().split(';')
                avoid_patterns = [p.strip() for p in patterns if p.strip()]
            elif line.startswith("CORRECTION:"):
                correction = line[11:].strip()
            elif line.startswith("CRITICAL:"):
                is_critical = 'yes' in line[9:].lower()
                
        return Reflection(
            failure_analysis=failure_analysis or "Unknown failure",
            avoid_patterns=avoid_patterns,
            correction=correction or "Try a different approach",
            is_critical=is_critical
        )
        
    async def _plan_modification(
        self,
        task: str,
        result: ExecutionResult,
        reflection: Reflection,
        context: dict
    ) -> tuple[str, dict]:
        """
        Plan modifications for next attempt based on reflection
        """
        # Build modified task prompt with guidance
        modified_task = f"""Task: {task}

Previous attempt failed because: {reflection.failure_analysis}

Correction to apply: {reflection.correction}

Retry the task, applying this correction."""

        # Update context with correction
        new_context = context.copy()
        new_context["correction"] = reflection.correction
        new_context["avoid"] = reflection.avoid_patterns
        new_context["retry_count"] = context.get("retry_count", 0) + 1
        
        return modified_task, new_context


@dataclass
class Reflection:
    """Result of reflection analysis"""
    failure_analysis: str
    avoid_patterns: list[str]
    correction: str
    is_critical: bool


class HermesReflexionMixin:
    """
    Mixin to add Reflexion capabilities to Hermes agent
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._reflexion_config = ReflexionConfig()
        self._reflexion_agent: Optional[ReflexionAgent] = None
        
    def setup_reflexion(
        self,
        llm: Any,
        config: Optional[ReflexionConfig] = None
    ):
        """Initialize reflexion agent"""
        if config:
            self._reflexion_config = config
            
        self._reflexion_agent = ReflexionAgent(
            llm=llm,
            executor=self._reflexion_executor,
            evaluator=self._reflexion_evaluator,
            config=self._reflexion_config
        )
        
    async def _reflexion_executor(
        self,
        task: str,
        context: dict
    ) -> ExecutionResult:
        """Execute task using Hermes capabilities"""
        try:
            result = await self.execute_task(task, context)
            return ExecutionResult(
                output=result,
                status=ExecutionStatus.SUCCESS if result else ExecutionStatus.UNKNOWN
            )
        except Exception as e:
            return ExecutionResult(
                output=None,
                status=ExecutionStatus.FAILURE,
                error=str(e)
            )
            
    async def _reflexion_evaluator(
        self,
        task: str,
        result: ExecutionResult
    ) -> ExecutionResult:
        """Evaluate if result meets success criteria"""
        # Simple evaluation - could be enhanced with LLM
        if result.status == ExecutionStatus.FAILURE:
            return ExecutionResult(
                output=result.output,
                status=ExecutionStatus.FAILURE,
                feedback="Task execution failed"
            )
            
        # Check if output is meaningful
        if result.output is None:
            return ExecutionResult(
                output=None,
                status=ExecutionStatus.FAILURE,
                feedback="No output produced"
            )
            
        return ExecutionResult(
            output=result.output,
            status=ExecutionStatus.SUCCESS,
            feedback="Task completed successfully"
        )
        
    async def execute_with_reflexion(
        self,
        task: str,
        context: Optional[dict] = None
    ) -> Any:
        """Execute task with reflexion-based self-correction"""
        if not self._reflexion_agent:
            raise RuntimeError("Reflexion not initialized. Call setup_reflexion() first.")
            
        result = await self._reflexion_agent.execute_with_reflexion(task, context)
        return result.output
