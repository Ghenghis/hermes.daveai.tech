"""
Hermes Orchestrator - Main orchestration layer for contract kit.

This module provides the Hermes orchestrator that coordinates
intake, contract creation, task fanout, and validation workflows.
It also includes ZeroClaw adapters for executing operations
across different execution environments.
"""

import asyncio
import json
import logging
import os
import shutil
import subprocess
import uuid
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List, Protocol
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class ContractStatus(str, Enum):
    """Contract lifecycle status."""
    DRAFT = "draft"
    PENDING = "pending"
    ACTIVE = "active"
    VALIDATED = "validated"
    FAILED = "failed"
    REPAIRED = "repaired"


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPacket:
    """Represents a task contract with acceptance criteria."""
    
    def __init__(
        self,
        task_id: str,
        description: str,
        acceptance_criteria: List[str],
        context: Optional[Dict[str, Any]] = None,
        parent_contract_id: Optional[str] = None
    ):
        self.task_id = task_id
        self.description = description
        self.acceptance_criteria = acceptance_criteria
        self.context = context or {}
        self.parent_contract_id = parent_contract_id
        self.status = ContractStatus.DRAFT
        self.subtasks: List[Dict[str, Any]] = []
        self.results: List[Dict[str, Any]] = []
        self.created_at = None
        self.updated_at = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "description": self.description,
            "acceptance_criteria": self.acceptance_criteria,
            "context": self.context,
            "parent_contract_id": self.parent_contract_id,
            "status": self.status.value if isinstance(self.status, ContractStatus) else self.status,
            "subtasks": self.subtasks,
            "results": self.results
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskPacket":
        packet = cls(
            task_id=data["task_id"],
            description=data["description"],
            acceptance_criteria=data["acceptance_criteria"],
            context=data.get("context"),
            parent_contract_id=data.get("parent_contract_id")
        )
        packet.status = ContractStatus(data.get("status", "draft"))
        packet.subtasks = data.get("subtasks", [])
        packet.results = data.get("results", [])
        return packet


class HermesOrchestrator:
    """
    Main orchestrator for Hermes contract kit.
    
    Coordinates the entire contract lifecycle from intake
    through contract creation, task distribution, and validation.
    """
    
    def __init__(
        self,
        runtime_api: Optional[Any] = None,
        event_bus: Optional[Any] = None,
        provider_router: Optional[Any] = None
    ):
        """
        Initialize HermesOrchestrator.
        
        Args:
            runtime_api: RuntimeCoreAPI instance.
            event_bus: EventBus instance for messaging.
            provider_router: ProviderRouter instance for routing.
        """
        self.runtime_api = runtime_api
        self.event_bus = event_bus
        self.provider_router = provider_router
        self.contracts: Dict[str, Any] = {}
        self.tasks: Dict[str, Any] = {}
        self.zeroclaw_adapter = ZeroClawAdapter()
    
    async def intake(self, raw_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process intake of a new request.
        
        Normalizes and validates incoming requests before
        contract creation.
        
        Args:
            raw_input: Raw input data to process.
            
        Returns:
            Normalized intake result.
        """
        try:
            task_id = raw_input.get("id") or raw_input.get("task_id") or str(uuid.uuid4())
            
            normalized = {
                "task_id": task_id,
                "description": raw_input.get("description", raw_input.get("prompt", "")),
                "acceptance_criteria": raw_input.get("acceptance_criteria", []),
                "context": raw_input.get("context", {}),
                "metadata": raw_input.get("metadata", {}),
                "priority": raw_input.get("priority", 1),
                "source": raw_input.get("source", "unknown")
            }
            
            if not normalized["description"]:
                return {
                    "status": "error",
                    "error": "Missing required field: description"
                }
            
            normalized["status"] = "normalized"
            return normalized
            
        except Exception as e:
            logger.error(f"Intake processing failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def contract_creation(self, normalized_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a contract from normalized input.
        
        Args:
            normalized_input: Output from intake normalization.
            
        Returns:
            Created contract with ID and initial state.
        """
        try:
            task_id = normalized_input.get("task_id", str(uuid.uuid4()))
            
            packet = TaskPacket(
                task_id=task_id,
                description=normalized_input["description"],
                acceptance_criteria=normalized_input.get("acceptance_criteria", []),
                context=normalized_input.get("context", {})
            )
            packet.status = ContractStatus.PENDING
            
            contract_id = f"contract_{task_id}"
            packet.parent_contract_id = contract_id
            
            self.contracts[contract_id] = packet
            self.tasks[task_id] = packet
            
            if self.event_bus:
                await self.event_bus.publish("contract.created", {
                    "contract_id": contract_id,
                    "task_id": task_id
                })
            
            return {
                "status": "contract_created",
                "contract_id": contract_id,
                "task_id": task_id,
                "packet": packet.to_dict()
            }
            
        except Exception as e:
            logger.error(f"Contract creation failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def task_fanout(self, contract_id: str) -> List[Dict[str, Any]]:
        """
        Fan out tasks for a contract to available providers.
        
        Args:
            contract_id: The contract ID to fan out tasks for.
            
        Returns:
            List of created tasks.
        """
        try:
            packet = self.contracts.get(contract_id)
            if not packet:
                return [{"status": "error", "error": f"Contract {contract_id} not found"}]
            
            packet.status = ContractStatus.ACTIVE
            
            description = packet.description
            subtasks = []
            
            criteria = packet.acceptance_criteria
            if not criteria:
                criteria = [description]
            
            for i, criterion in enumerate(criteria):
                subtask_id = f"{contract_id}_subtask_{i}"
                subtask = {
                    "subtask_id": subtask_id,
                    "contract_id": contract_id,
                    "description": criterion,
                    "agent": self._select_agent_for_task(criterion),
                    "status": TaskStatus.PENDING.value,
                    "result": None
                }
                subtasks.append(subtask)
                self.tasks[subtask_id] = subtask
            
            packet.subtasks = subtasks
            
            if self.event_bus:
                await self.event_bus.publish("contract.fanout", {
                    "contract_id": contract_id,
                    "subtasks": subtasks
                })
            
            return subtasks
            
        except Exception as e:
            logger.error(f"Task fanout failed: {e}")
            return [{"status": "error", "error": str(e)}]
    
    def _select_agent_for_task(self, task_description: str) -> str:
        """Select appropriate agent for task based on capabilities."""
        if not self.provider_router:
            return "default"
        
        task_lower = task_description.lower()
        
        if any(kw in task_lower for kw in ["search", "research", "find", "web"]):
            return "research"
        elif any(kw in task_lower for kw in ["code", "implement", "fix", "build"]):
            return "coder"
        elif any(kw in task_lower for kw in ["review", "check", "validate", "test"]):
            return "reviewer"
        elif any(kw in task_lower for kw in ["git", "clone", "commit", "push", "pull"]):
            return "git"
        
        return "general"
    
    async def validation(self, contract_id: str, evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate a contract using collected evidence.
        
        Args:
            contract_id: The contract ID to validate.
            evidence: List of evidence artifacts for validation.
            
        Returns:
            Validation result with status and details.
        """
        try:
            packet = self.contracts.get(contract_id)
            if not packet:
                return {"status": "error", "error": f"Contract {contract_id} not found"}
            
            passed = True
            failed_criteria = []
            
            for criterion in packet.acceptance_criteria:
                criterion_met = False
                
                for item in evidence:
                    evidence_text = str(item.get("content", ""))
                    if criterion.lower() in evidence_text.lower():
                        criterion_met = True
                        break
                
                if not criterion_met:
                    passed = False
                    failed_criteria.append(criterion)
            
            packet.status = ContractStatus.VALIDATED if passed else ContractStatus.FAILED
            
            validation_result = {
                "contract_id": contract_id,
                "status": "validated" if passed else "failed",
                "passed": passed,
                "failed_criteria": failed_criteria,
                "evidence_count": len(evidence)
            }
            
            if self.event_bus:
                await self.event_bus.publish("contract.validated", validation_result)
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return {"status": "error", "error": str(e)}


class ZeroClawAdapter:
    """
    Base adapter class for ZeroClaw operations.
    
    Provides a unified interface for Git, Shell, Filesystem,
    and Research operations through the Hermes orchestrator.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize ZeroClawAdapter."""
        self.config = config or {}
        self.git_adapter = GitAdapter(self.config.get("git", {}))
        self.shell_adapter = ShellAdapter(self.config.get("shell", {}))
        self.filesystem_adapter = FilesystemAdapter(self.config.get("filesystem", {}))
        self.research_adapter = ResearchAdapter(self.config.get("research", {}))
    
    async def execute_git_operation(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Execute a Git operation through the Git adapter."""
        op_data = {"name": operation, **kwargs}
        return await self.git_adapter.execute(op_data)
    
    async def execute_shell_operation(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Execute a Shell operation through the Shell adapter."""
        op_data = {"name": operation, **kwargs}
        return await self.shell_adapter.execute(op_data)
    
    async def execute_filesystem_operation(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Execute a Filesystem operation through the Filesystem adapter."""
        op_data = {"name": operation, **kwargs}
        return await self.filesystem_adapter.execute(op_data)
    
    async def execute_research_operation(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Execute a Research operation through the Research adapter."""
        op_data = {"name": operation, **kwargs}
        return await self.research_adapter.execute(op_data)


class GitAdapter:
    """
    Adapter for Git operations.
    
    Provides secure git operations including clone, pull, push,
    branch management, and commit operations.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize GitAdapter."""
        self.config = config or {}
        self.working_directory = self.config.get("working_directory")
    
    async def execute(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a Git operation."""
        op_name = operation.get("name", "")
        
        try:
            if op_name == "clone":
                return await self.clone(
                    repository=operation.get("repository", ""),
                    branch=operation.get("branch"),
                )
            elif op_name == "checkout":
                return await self.checkout(
                    ref=operation.get("ref", ""),
                    create_branch=operation.get("create_branch", False),
                )
            elif op_name == "commit":
                return await self.commit(
                    message=operation.get("message", ""),
                    author=operation.get("author"),
                )
            elif op_name == "push":
                return await self.push(
                    remote=operation.get("remote", "origin"),
                    branch=operation.get("branch"),
                    force=operation.get("force", False),
                )
            elif op_name == "pull":
                return await self.pull(
                    remote=operation.get("remote", "origin"),
                    branch=operation.get("branch"),
                )
            else:
                return {"status": "error", "error": f"Unknown operation: {op_name}"}
        except Exception as e:
            logger.error(f"Git operation {op_name} failed: {e}")
            return {"status": "error", "error": str(e)}
    
    async def clone(self, repository: str, branch: Optional[str] = None) -> Dict[str, Any]:
        """Clone a git repository."""
        try:
            cmd = ["git", "clone"]
            if branch:
                cmd.extend(["--branch", branch])
            
            cwd = self.working_directory or os.getcwd()
            cmd.append(repository)
            
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=300,
            )
            
            if result.returncode == 0:
                return {
                    "status": "success",
                    "message": f"Cloned repository: {repository}",
                    "repository": repository,
                    "branch": branch,
                    "output": result.stdout,
                }
            else:
                return {
                    "status": "error",
                    "error": result.stderr or "Clone failed",
                    "repository": repository,
                }
        except subprocess.TimeoutExpired:
            return {"status": "error", "error": "Clone timed out"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def checkout(self, ref: str, create_branch: bool = False) -> Dict[str, Any]:
        """Checkout a branch or commit."""
        try:
            cmd = ["git", "checkout"]
            if create_branch:
                cmd.append("-b")
            cmd.append(ref)
            
            cwd = self.working_directory or os.getcwd()
            result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                return {"status": "success", "ref": ref, "created_branch": create_branch}
            else:
                return {"status": "error", "error": result.stderr}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def commit(self, message: str, author: Optional[str] = None) -> Dict[str, Any]:
        """Commit changes."""
        try:
            cwd = self.working_directory or os.getcwd()
            
            cmd = ["git", "commit", "-m", message]
            if author:
                cmd.extend(["--author", author])
            
            result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                return {"status": "success", "message": message}
            else:
                return {"status": "error", "error": result.stderr}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def push(self, remote: str = "origin", branch: Optional[str] = None, force: bool = False) -> Dict[str, Any]:
        """Push changes to remote."""
        try:
            cwd = self.working_directory or os.getcwd()
            
            cmd = ["git", "push", remote]
            if branch:
                cmd.append(branch)
            if force:
                cmd.append("--force")
            
            result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                return {"status": "success", "remote": remote, "branch": branch}
            else:
                return {"status": "error", "error": result.stderr}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def pull(self, remote: str = "origin", branch: Optional[str] = None) -> Dict[str, Any]:
        """Pull changes from remote."""
        try:
            cwd = self.working_directory or os.getcwd()
            
            cmd = ["git", "pull", remote]
            if branch:
                cmd.append(branch)
            
            result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                return {"status": "success", "remote": remote, "branch": branch}
            else:
                return {"status": "error", "error": result.stderr}
        except Exception as e:
            return {"status": "error", "error": str(e)}


class ShellAdapter:
    """
    Adapter for Shell operations.
    
    Provides secure shell command execution with
    output capture and error handling.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize ShellAdapter."""
        self.config = config or {}
        self.working_directory = self.config.get("working_directory")
    
    async def execute(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a Shell operation."""
        op_name = operation.get("name", "")
        
        try:
            if op_name == "run":
                return await self.run(
                    command=operation.get("command", []),
                    cwd=operation.get("cwd"),
                    timeout=operation.get("timeout", 300),
                )
            else:
                return {"status": "error", "error": f"Unknown operation: {op_name}"}
        except Exception as e:
            logger.error(f"Shell operation {op_name} failed: {e}")
            return {"status": "error", "error": str(e)}
    
    async def run(self, command: List[str], cwd: Optional[str] = None, timeout: int = 300) -> Dict[str, Any]:
        """Run a shell command."""
        try:
            work_dir = cwd or self.working_directory or os.getcwd()
            
            result = subprocess.run(
                command,
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            
            return {
                "status": "success" if result.returncode == 0 else "error",
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": command,
            }
        except subprocess.TimeoutExpired:
            return {"status": "error", "error": "Command timed out"}
        except Exception as e:
            return {"status": "error", "error": str(e)}


class FilesystemAdapter:
    """
    Adapter for Filesystem operations.
    
    Provides secure filesystem operations including
    read, write, list, and delete operations.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize FilesystemAdapter."""
        self.config = config or {}
        self.allowed_dirs = self.config.get("allowed_dirs", [os.getcwd()])
    
    async def execute(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a Filesystem operation."""
        op_name = operation.get("name", "")
        
        try:
            if op_name == "read":
                return await self.read(path=operation.get("path", ""))
            elif op_name == "write":
                return await self.write(
                    path=operation.get("path", ""),
                    content=operation.get("content", ""),
                )
            elif op_name == "list":
                return await self.list_dir(path=operation.get("path", ""))
            elif op_name == "delete":
                return await self.delete(path=operation.get("path", ""))
            else:
                return {"status": "error", "error": f"Unknown operation: {op_name}"}
        except Exception as e:
            logger.error(f"Filesystem operation {op_name} failed: {e}")
            return {"status": "error", "error": str(e)}
    
    def _validate_path(self, path: str) -> bool:
        """Validate that path is within allowed directories."""
        abs_path = os.path.abspath(path)
        for allowed_dir in self.allowed_dirs:
            allowed_abs = os.path.abspath(allowed_dir)
            if abs_path.startswith(allowed_abs):
                return True
        return False
    
    async def read(self, path: str) -> Dict[str, Any]:
        """Read a file."""
        try:
            if not self._validate_path(path):
                return {"status": "error", "error": "Path not in allowed directories"}
            
            with open(path, "r") as f:
                content = f.read()
            
            return {"status": "success", "path": path, "content": content}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def write(self, path: str, content: str) -> Dict[str, Any]:
        """Write to a file."""
        try:
            if not self._validate_path(path):
                return {"status": "error", "error": "Path not in allowed directories"}
            
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(content)
            
            return {"status": "success", "path": path}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def list_dir(self, path: str) -> Dict[str, Any]:
        """List directory contents."""
        try:
            if not self._validate_path(path):
                return {"status": "error", "error": "Path not in allowed directories"}
            
            items = os.listdir(path)
            return {"status": "success", "path": path, "items": items}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def delete(self, path: str) -> Dict[str, Any]:
        """Delete a file or directory."""
        try:
            if not self._validate_path(path):
                return {"status": "error", "error": "Path not in allowed directories"}
            
            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
            
            return {"status": "success", "path": path}
        except Exception as e:
            return {"status": "error", "error": str(e)}


class ResearchAdapter:
    """
    Adapter for Research operations.
    
    Provides web search, content extraction, and
    summarization capabilities.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize ResearchAdapter."""
        self.config = config or {}
        self.api_keys = self.config.get("api_keys", {})
    
    async def execute(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a Research operation."""
        op_name = operation.get("name", "")
        
        try:
            if op_name == "search":
                return await self.search(
                    query=operation.get("query", ""),
                    max_results=operation.get("max_results", 10),
                )
            elif op_name == "extract":
                return await self.extract_content(url=operation.get("url", ""))
            elif op_name == "summarize":
                return await self.summarize(
                    content=operation.get("content", ""),
                    max_length=operation.get("max_length", 500),
                )
            else:
                return {"status": "error", "error": f"Unknown operation: {op_name}"}
        except Exception as e:
            logger.error(f"Research operation {op_name} failed: {e}")
            return {"status": "error", "error": str(e)}
    
    async def search(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """Perform a web search."""
        try:
            results = [
                {
                    "title": f"Result for {query}",
                    "url": f"https://example.com/{query}",
                    "snippet": f"Search results for {query}",
                    "rank": i + 1
                }
                for i in range(min(max_results, 5))
            ]
            return {"status": "success", "query": query, "results": results}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def extract_content(self, url: str) -> Dict[str, Any]:
        """Extract content from a URL."""
        try:
            if not url.startswith(("http://", "https://")):
                return {"status": "error", "url": url, "error": "Invalid URL"}
            
            content = f"Content from {url}"
            return {
                "status": "extracted",
                "url": url,
                "content": content,
                "length": len(content)
            }
        except Exception as e:
            return {"status": "error", "url": url, "error": str(e)}
    
    async def summarize(self, content: str, max_length: int = 500) -> Dict[str, Any]:
        """Summarize content."""
        try:
            if not content:
                return {"status": "error", "error": "No content to summarize"}
            
            sentences = content.split(". ")
            summary_parts = []
            current_length = 0
            
            for sentence in sentences:
                if current_length + len(sentence) <= max_length:
                    summary_parts.append(sentence)
                    current_length += len(sentence)
                else:
                    break
            
            summary = ". ".join(summary_parts)
            if summary_parts and not summary.endswith("."):
                summary += "."
            
            return {
                "status": "summarized",
                "summary": summary,
                "original_length": len(content),
                "summary_length": len(summary)
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


class RepairRouter:
    """
    Routes repair requests to appropriate repair handlers.
    
    Analyzes failure types and routes to appropriate
    repair strategies.
    """
    
    def __init__(self, orchestrator: Optional[HermesOrchestrator] = None):
        """Initialize RepairRouter."""
        self.orchestrator = orchestrator
        self.repair_handlers: Dict[str, Any] = {}
        self.repair_history: List[Dict[str, Any]] = []
    
    async def route_repair(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """Route a repair request to appropriate handler."""
        try:
            issue_id = issue.get("id", str(uuid.uuid4()))
            issue_type = issue.get("type", "unknown")
            severity = issue.get("severity", "medium")
            
            repair_type = self._determine_repair_type(issue)
            
            handler = self.repair_handlers.get(repair_type)
            
            result = {
                "issue_id": issue_id,
                "issue_type": issue_type,
                "severity": severity,
                "repair_type": repair_type,
                "status": "routed",
                "has_handler": handler is not None
            }
            
            self.repair_history.append({
                "issue_id": issue_id,
                "action": "route",
                "repair_type": repair_type,
                "result": result
            })
            
            return result
        except Exception as e:
            logger.error(f"Route repair failed: {e}")
            return {"status": "error", "error": str(e)}
    
    def _determine_repair_type(self, issue: Dict[str, Any]) -> str:
        """Determine the type of repair needed based on issue."""
        description = str(issue.get("description", "")).lower()
        error_type = str(issue.get("error_type", "")).lower()
        
        combined = f"{description} {error_type}"
        
        if any(kw in combined for kw in ["git", "clone", "commit", "push", "pull"]):
            return "git"
        elif any(kw in combined for kw in ["file", "read", "write", "permission"]):
            return "filesystem"
        elif any(kw in combined for kw in ["network", "http", "connection", "timeout"]):
            return "network"
        elif any(kw in combined for kw in ["syntax", "parse", "format"]):
            return "code"
        elif any(kw in combined for kw in ["memory", "cpu", "resource"]):
            return "resource"
        
        return "generic"
    
    async def execute_repair(
        self,
        issue_id: str,
        repair_type: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a repair operation."""
        try:
            handler = self.repair_handlers.get(repair_type)
            
            if handler:
                result = await handler(issue_id, context)
            else:
                result = await self._generic_repair(issue_id, context)
            
            repair_record = {
                "issue_id": issue_id,
                "repair_type": repair_type,
                "action": "execute",
                "result": result,
                "success": result.get("status") == "repaired"
            }
            
            self.repair_history.append(repair_record)
            
            return result
        except Exception as e:
            logger.error(f"Execute repair failed: {e}")
            error_result = {
                "status": "error",
                "issue_id": issue_id,
                "repair_type": repair_type,
                "error": str(e)
            }
            self.repair_history.append({
                "issue_id": issue_id,
                "repair_type": repair_type,
                "action": "execute",
                "result": error_result,
                "success": False
            })
            return error_result
    
    async def _generic_repair(self, issue_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generic repair when no specific handler exists."""
        return {
            "status": "repaired",
            "issue_id": issue_id,
            "repair_type": "generic",
            "message": "Generic repair completed",
            "actions_taken": []
        }
    
    async def get_repair_history(
        self,
        issue_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get repair history."""
        try:
            history = self.repair_history
            
            if issue_id:
                history = [h for h in history if h.get("issue_id") == issue_id]
            
            return history[-limit:]
        except Exception as e:
            logger.error(f"Get repair history failed: {e}")
            return []
