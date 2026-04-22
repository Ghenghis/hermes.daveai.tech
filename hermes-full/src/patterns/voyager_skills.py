"""
Voyager-Style Skill Acquisition System

Continuous learning agent that acquires, refines, and transfers skills.
Based on the Voyager architecture from Wang et al.

Usage:
    library = SkillLibrary(".hermes/skills")
    generator = SkillGenerator(llm, executor)
    voyager = VoyagerSkillAgent(library, generator, executor, llm)
    result = await voyager.execute_task("novel task")
"""

from dataclasses import dataclass, field
from typing import Optional, Any, Callable, Union
from enum import Enum
import asyncio
import json
import time
import hashlib
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class SkillStatus(Enum):
    """Skill lifecycle status"""
    GENERATING = "generating"
    TESTING = "testing"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    IMPROVING = "improving"


@dataclass
class Skill:
    """
    A learnable skill that can be acquired and improved
    """
    id: str
    name: str
    description: str
    version: str = "1.0.0"
    status: SkillStatus = SkillStatus.GENERATING
    
    code: Optional[str] = None
    trigger_patterns: list[str] = field(default_factory=list)
    parameters: dict = field(default_factory=dict)
    
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    use_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    
    parent_skill_id: Optional[str] = None
    related_skill_ids: list[str] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "status": self.status.value,
            "code": self.code,
            "trigger_patterns": self.trigger_patterns,
            "parameters": self.parameters,
            "created_at": self.created_at,
            "last_used": self.last_used,
            "use_count": self.use_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "parent_skill_id": self.parent_skill_id,
            "related_skill_ids": self.related_skill_ids
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Skill":
        data["status"] = SkillStatus(data.get("status", "active"))
        return cls(**data)
    
    def increment_success(self):
        """Record successful execution"""
        self.success_count += 1
        self.last_used = time.time()
        self.use_count += 1
        
    def increment_failure(self):
        """Record failed execution"""
        self.failure_count += 1
        self.last_used = time.time()
        self.use_count += 1


@dataclass
class SkillGenerationRequest:
    """Request to generate a new skill"""
    task_description: str
    context: dict
    existing_skills: list[Skill] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)


@dataclass
class SkillGenerationResult:
    """Result of skill generation"""
    skill: Optional[Skill]
    success: bool
    message: str
    code: Optional[str] = None
    tests_passed: bool = False


class SkillLibrary:
    """
    Persistent storage and retrieval for skills
    """
    
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.skills: dict[str, Skill] = {}
        self.name_index: dict[str, str] = {}
        self.pattern_index: dict[str, list[str]] = {}
        self._load_skills()
        
    def _skills_file_path(self) -> Path:
        return self.storage_path / "skills.json"
    
    def _load_skills(self):
        """Load skills from persistent storage"""
        skills_file = self._skills_file_path()
        if skills_file.exists():
            try:
                with open(skills_file, 'r') as f:
                    data = json.load(f)
                    for skill_data in data:
                        skill = Skill.from_dict(skill_data)
                        self.skills[skill.id] = skill
                        self.name_index[skill.name] = skill.id
                        for pattern in skill.trigger_patterns:
                            if pattern not in self.pattern_index:
                                self.pattern_index[pattern] = []
                            self.pattern_index[pattern].append(skill.id)
                logger.info(f"Loaded {len(self.skills)} skills from storage")
            except Exception as e:
                logger.warning(f"Failed to load skills: {e}")
                
    def _save_skills(self):
        """Persist skills to storage"""
        try:
            skills_file = self._skills_file_path()
            data = [skill.to_dict() for skill in self.skills.values()]
            with open(skills_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save skills: {e}")
            
    def add_skill(self, skill: Skill):
        """Add a new skill to the library"""
        self.skills[skill.id] = skill
        self.name_index[skill.name] = skill.id
        for pattern in skill.trigger_patterns:
            if pattern not in self.pattern_index:
                self.pattern_index[pattern] = []
            if skill.id not in self.pattern_index[pattern]:
                self.pattern_index[pattern].append(skill.id)
        self._save_skills()
        logger.info(f"Added skill: {skill.name} (v{skill.version})")
        
    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """Get a skill by ID"""
        return self.skills.get(skill_id)
    
    def get_skill_by_name(self, name: str) -> Optional[Skill]:
        """Get a skill by name"""
        skill_id = self.name_index.get(name)
        return self.skills.get(skill_id) if skill_id else None
        
    def find_skills_by_pattern(self, pattern: str) -> list[Skill]:
        """Find skills matching a trigger pattern"""
        skill_ids = self.pattern_index.get(pattern, [])
        return [self.skills[sid] for sid in skill_ids if sid in self.skills]
        
    def find_similar_skills(self, description: str) -> list[Skill]:
        """Find skills with similar descriptions"""
        desc_words = set(description.lower().split())
        scored = []
        
        for skill in self.skills.values():
            skill_words = set(skill.description.lower().split())
            overlap = len(desc_words & skill_words)
            if overlap > 0:
                scored.append((skill, overlap))
                
        scored.sort(key=lambda x: x[1], reverse=True)
        return [s for s, _ in scored]
        
    def update_skill(self, skill: Skill):
        """Update an existing skill"""
        self.skills[skill.id] = skill
        self._save_skills()
        
    def deprecate_skill(self, skill_id: str):
        """Mark a skill as deprecated"""
        if skill_id in self.skills:
            self.skills[skill_id].status = SkillStatus.DEPRECATED
            self._save_skills()
            
    def get_active_skills(self) -> list[Skill]:
        """Get all active skills"""
        return [s for s in self.skills.values() if s.status == SkillStatus.ACTIVE]
    
    def get_skill_stats(self) -> dict:
        """Get statistics about skills"""
        active = len([s for s in self.skills.values() if s.status == SkillStatus.ACTIVE])
        deprecated = len([s for s in self.skills.values() if s.status == SkillStatus.DEPRECATED])
        total_uses = sum(s.use_count for s in self.skills.values())
        total_success = sum(s.success_count for s in self.skills.values())
        
        return {
            "total_skills": len(self.skills),
            "active_skills": active,
            "deprecated_skills": deprecated,
            "total_uses": total_uses,
            "overall_success_rate": total_success / total_uses if total_uses > 0 else 0
        }


class SkillGenerator:
    """
    Generates new skills from task descriptions
    """
    
    def __init__(self, llm: Any, code_executor: Callable):
        self.llm = llm
        self.code_executor = code_executor
        
    async def generate_skill(
        self,
        request: SkillGenerationRequest
    ) -> SkillGenerationResult:
        """
        Generate a new skill from a task description
        """
        skill_id = self._generate_skill_id(request.task_description)
        skill_name = self._generate_skill_name(request.task_description)
        
        skill = Skill(
            id=skill_id,
            name=skill_name,
            description=request.task_description,
            status=SkillStatus.GENERATING,
            trigger_patterns=self._extract_triggers(request.task_description)
        )
        
        code_result = await self._generate_code(request)
        if not code_result.success:
            return SkillGenerationResult(
                skill=None,
                success=False,
                message=code_result.message
            )
            
        skill.code = code_result.code
        
        validation = await self._validate_code(skill.code, request.context)
        
        if validation.success:
            skill.status = SkillStatus.ACTIVE
            return SkillGenerationResult(
                skill=skill,
                success=True,
                message="Skill generated and validated",
                code=skill.code,
                tests_passed=True
            )
        else:
            return SkillGenerationResult(
                skill=None,
                success=False,
                message=f"Validation failed: {validation.message}"
            )
    
    async def _generate_code(
        self,
        request: SkillGenerationRequest
    ) -> SkillGenerationResult:
        """Generate skill implementation code"""
        prompt = f"""Generate Python code for the following skill:

Task: {request.task_description}

Context:
{json.dumps(request.context, indent=2)}

Existing skills available:
{self._format_existing_skills(request.existing_skills)}

Constraints:
{chr(10).join(f"- {c}" for c in request.constraints)}

Requirements:
1. Function must be named 'execute_skill'
2. Include proper error handling
3. Return dict with 'success' and optionally 'result' or 'error' keys
4. Follow Python best practices

Return ONLY the code wrapped in a JSON object:
{{"code": "def execute_skill(...):\\n    ..."}}"""

        try:
            response = await self._call_llm(prompt)
            data = json.loads(response)
            code = data.get("code", "")
            
            compile(code, '<string>', 'exec')
            
            return SkillGenerationResult(
                skill=None,
                success=True,
                message="Code generated",
                code=code
            )
        except json.JSONDecodeError as e:
            return SkillGenerationResult(
                skill=None,
                success=False,
                message=f"Failed to parse generated code: {e}"
            )
        except SyntaxError as e:
            return SkillGenerationResult(
                skill=None,
                success=False,
                message=f"Syntax error in generated code: {e}"
            )
    
    async def _validate_code(
        self,
        code: str,
        context: dict
    ) -> SkillGenerationResult:
        """Validate skill code against context"""
        try:
            result = await self.code_executor(code, context)
            
            if result.get("success"):
                return SkillGenerationResult(
                    skill=None,
                    success=True,
                    message="Validation passed"
                )
            else:
                return SkillGenerationResult(
                    skill=None,
                    success=False,
                    message=f"Validation failed: {result.get('error')}"
                )
        except Exception as e:
            return SkillGenerationResult(
                skill=None,
                success=False,
                message=f"Validation error: {str(e)}"
            )
    
    async def _call_llm(self, prompt: str) -> str:
        """Call LLM with prompt"""
        if hasattr(self.llm, 'agenerate'):
            response = await self.llm.agenerate([prompt])
            return response if isinstance(response, str) else str(response)
        return await self.llm.generate(prompt)
    
    def _generate_skill_id(self, description: str) -> str:
        """Generate unique skill ID"""
        hash_input = f"{description}{time.time()}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:12]
    
    def _generate_skill_name(self, description: str) -> str:
        """Generate skill name from description"""
        words = description.lower().split()
        core_words = [w for w in words if len(w) > 3][:3]
        return "_".join(core_words) + "_skill"
    
    def _extract_triggers(self, description: str) -> list[str]:
        """Extract trigger patterns from description"""
        triggers = []
        words = description.lower().split()
        
        for i, word in enumerate(words):
            if word in ["when", "if", "on", "during"]:
                if i + 1 < len(words):
                    triggers.append(f"{words[i]} {words[i+1]}")
                    
        triggers.extend([w for w in words if len(w) > 5][:3])
        return triggers[:5]
    
    def _format_existing_skills(self, skills: list[Skill]) -> str:
        """Format existing skills for prompt"""
        if not skills:
            return "No existing skills available"
            
        lines = []
        for skill in skills[:5]:
            lines.append(f"- {skill.name}: {skill.description}")
            if skill.code:
                lines.append(f"  Code: {skill.code[:100]}...")
                
        return "\n".join(lines)


class VoyagerSkillAgent:
    """
    Voyager-style agent with continuous skill learning
    """
    
    def __init__(
        self,
        skill_library: SkillLibrary,
        skill_generator: SkillGenerator,
        skill_executor: Callable,
        llm: Any
    ):
        self.library = skill_library
        self.generator = skill_generator
        self.executor = skill_executor
        self.llm = llm
        
    async def execute_task(self, task: str, context: dict = None) -> dict:
        """
        Execute a task, learning new skills if needed
        """
        context = context or {}
        
        existing_skill = self._find_applicable_skill(task)
        
        if existing_skill:
            result = await self._execute_with_skill(existing_skill, task, context)
            
            if not result.get("success"):
                await self._improve_skill(existing_skill, result, context)
                
            return result
            
        return await self._learn_new_skill(task, context)
    
    def _find_applicable_skill(self, task: str) -> Optional[Skill]:
        """Find an existing skill applicable to the task"""
        for skill in self.library.skills.values():
            if skill.status != SkillStatus.ACTIVE:
                continue
                
            for pattern in skill.trigger_patterns:
                if pattern.lower() in task.lower():
                    return skill
                    
        similar = self.library.find_similar_skills(task)
        return similar[0] if similar else None
    
    async def _execute_with_skill(
        self,
        skill: Skill,
        task: str,
        context: dict
    ) -> dict:
        """Execute task using a skill"""
        try:
            result = await self.executor(skill.code, task, context)
            
            if result.get("success"):
                skill.increment_success()
            else:
                skill.increment_failure()
                
            self.library.update_skill(skill)
            return result
            
        except Exception as e:
            skill.increment_failure()
            self.library.update_skill(skill)
            return {"success": False, "error": str(e)}
    
    async def _learn_new_skill(
        self,
        task: str,
        context: dict
    ) -> dict:
        """Generate and learn a new skill for the task"""
        existing_skills = list(self.library.skills.values())
        
        request = SkillGenerationRequest(
            task_description=task,
            context=context,
            existing_skills=existing_skills
        )
        
        result = await self.generator.generate_skill(request)
        
        if result.success and result.skill:
            self.library.add_skill(result.skill)
            return await self._execute_with_skill(result.skill, task, context)
        else:
            return {
                "success": False,
                "error": f"Failed to generate skill: {result.message}"
            }
    
    async def _improve_skill(
        self,
        skill: Skill,
        failed_result: dict,
        context: dict
    ):
        """Improve a skill based on failed execution"""
        skill.status = SkillStatus.IMPROVING
        
        analysis = await self._analyze_failure(skill, failed_result, context)
        
        if analysis.can_fix:
            improved_code = await self._generate_improved_code(
                skill, analysis, context
            )
            
            test_result = await self.generator._validate_code(
                improved_code, context
            )
            
            if test_result.success:
                skill.code = improved_code
                skill.version = self._bump_version(skill.version)
                
        skill.status = SkillStatus.ACTIVE
        self.library.update_skill(skill)
    
    async def _analyze_failure(
        self,
        skill: Skill,
        result: dict,
        context: dict
    ) -> "FailureAnalysis":
        """Analyze why a skill execution failed"""
        prompt = f"""Analyze why this skill execution failed:

Skill: {skill.name}
Skill code: {skill.code}
Error: {result.get('error')}
Context: {json.dumps(context)}

Determine:
1. Root cause of failure
2. Can this be fixed with code modification? (yes/no)
3. Specific changes needed (if any)

Return JSON with root_cause, can_fix (boolean), and suggested_changes (array)."""

        try:
            response = await self.generator._call_llm(prompt)
            data = json.loads(response)
            return FailureAnalysis(
                root_cause=data.get("root_cause", "Unknown"),
                can_fix=data.get("can_fix", False),
                suggested_changes=data.get("suggested_changes", [])
            )
        except:
            return FailureAnalysis(
                root_cause="Unknown",
                can_fix=False,
                suggested_changes=[]
            )
    
    async def _generate_improved_code(
        self,
        skill: Skill,
        analysis: FailureAnalysis,
        context: dict
    ) -> str:
        """Generate improved version of skill code"""
        prompt = f"""Improve this skill code based on failure analysis:

Original code:
{skill.code}

Root cause: {analysis.root_cause}
Suggested changes: {chr(10).join(analysis.suggested_changes)}

Generate improved code that addresses the failure.
Return as JSON: {{"code": "..."}}"""

        try:
            response = await self.generator._call_llm(prompt)
            data = json.loads(response)
            return data.get("code", skill.code)
        except:
            return skill.code
    
    def _bump_version(self, version: str) -> str:
        """Bump skill version number"""
        parts = version.split(".")
        if len(parts) == 3:
            major, minor, patch = parts
            return f"{major}.{minor}.{int(patch) + 1}"
        return "1.0.1"


@dataclass
class FailureAnalysis:
    """Analysis of skill execution failure"""
    root_cause: str
    can_fix: bool
    suggested_changes: list[str]
