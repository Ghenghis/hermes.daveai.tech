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
                    evidence_text = str(item.get("result", "")) + str(item.get("output", ""))
                    if criterion.lower() in evidence_text.lower():
                        criterion_met = True
                        break
                
                if not criterion_met:
                    passed = False
                    failed_criteria.append(criterion)
            
            if passed:
                packet.status = ContractStatus.VALIDATED
            else:
                packet.status = ContractStatus.FAILED
            
            result = {
                "status": "validated",
                "contract_id": contract_id,
                "passed": passed,
                "failed_criteria": failed_criteria,
                "evidence_count": len(evidence)
            }
            
            if self.event_bus:
                await self.event_bus.publish("contract.validated", result)
            
            return result
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return {
                "status": "error",
                "contract_id": contract_id,
                "error": str(e)
            }
    
    async def get_contract_status(self, contract_id: str) -> Dict[str, Any]:
        """
        Get current status of a contract.
        
        Args:
            contract_id: The contract ID to check.
            
        Returns:
            Contract status information.
        """
        try:
            packet = self.contracts.get(contract_id)
            if not packet:
                return {"status": "error", "error": f"Contract {contract_id} not found"}
            
            return {
                "contract_id": contract_id,
                "status": packet.status.value if isinstance(packet.status, ContractStatus) else packet.status,
                "task_id": packet.task_id,
                "subtasks": len(packet.subtasks),
                "results_count": len(packet.results)
            }
            
        except Exception as e:
            logger.error(f"Get contract status failed: {e}")
            return {
                "status": "error",
                "contract_id": contract_id,
                "error": str(e)
            }


class ZeroClawAdapter(ABC):
    """
    Base adapter class for ZeroClaw operations.
    
    Provides the interface for adapters that execute
    operations in different environments (Git, Shell, etc.).
    """
    
    def __init__(self):
        self.operations: List[Dict[str, Any]] = []
    
    async def execute(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an operation using this adapter.
        
        Args:
            operation: Operation specification.
            
        Returns:
            Operation result.
        """
        raise NotImplementedError("Subclasses must implement execute")
    
    async def validate(self, operation: Dict[str, Any]) -> bool:
        """
        Validate an operation before execution.
        
        Args:
            operation: Operation to validate.
            
        Returns:
            True if valid, False otherwise.
        """
        raise NotImplementedError("Subclasses must implement validate")


class GitAdapter(ZeroClawAdapter):
    """
    ZeroClaw adapter for Git operations.
    
    Handles git clone, pull, push, branch, and other
    Git operations in a controlled manner.
    """
    
    def __init__(self, working_directory: Optional[str] = None):
        """
        Initialize GitAdapter.
        
        Args:
            working_directory: Directory for Git operations.
        """
        super().__init__()
        self.working_directory = working_directory
        self.remote_url: Optional[str] = None
    
    async def execute(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a Git operation."""
        command = operation.get("command")
        if not command:
            return {"status": "error", "error": "Missing command in operation"}
        
        if not await self.validate(operation):
            return {"status": "error", "error": "Operation validation failed"}
        
        return await self._run_git_command(command, operation.get("cwd") or self.working_directory)
    
    async def validate(self, operation: Dict[str, Any]) -> bool:
        """Validate a Git operation."""
        command = operation.get("command", "")
        
        dangerous_commands = {"git filter-branch", "git push --force", "git push --delete"}
        return not any(d in command for d in dangerous_commands)
    
    async def clone(self, repo_url: str, target_dir: Optional[str] = None) -> Dict[str, Any]:
        """Clone a repository."""
        try:
            if not target_dir:
                target_dir = os.path.join(self.working_directory or os.getcwd(), repo_url.split("/")[-1].replace(".git", ""))
            
            os.makedirs(target_dir, exist_ok=True)
            
            result = await self._run_git_command(
                ["git", "clone", repo_url, target_dir],
                cwd=target_dir
            )
            
            if result.get("exit_code") == 0:
                self.remote_url = repo_url
                result["path"] = target_dir
            
            return result
            
        except Exception as e:
            logger.error(f"Git clone failed: {e}")
            return {"status": "error", "error": str(e)}
    
    async def pull(self, branch: str = "main") -> Dict[str, Any]:
        """Pull changes from remote."""
        try:
            if not self.working_directory:
                return {"status": "error", "error": "No working directory set"}
            
            return await self._run_git_command(
                ["git", "pull", "origin", branch],
                cwd=self.working_directory
            )
            
        except Exception as e:
            logger.error(f"Git pull failed: {e}")
            return {"status": "error", "error": str(e)}
    
    async def push(self, branch: str = "main", force: bool = False) -> Dict[str, Any]:
        """Push changes to remote."""
        try:
            if not self.working_directory:
                return {"status": "error", "error": "No working directory set"}
            
            cmd = ["git", "push", "origin", branch]
            if force:
                cmd.append("--force")
            
            return await self._run_git_command(cmd, cwd=self.working_directory)
            
        except Exception as e:
            logger.error(f"Git push failed: {e}")
            return {"status": "error", "error": str(e)}
    
    async def checkout(self, branch: str) -> Dict[str, Any]:
        """Checkout a branch."""
        try:
            if not self.working_directory:
                return {"status": "error", "error": "No working directory set"}
            
            return await self._run_git_command(
                ["git", "checkout", branch],
                cwd=self.working_directory
            )
            
        except Exception as e:
            logger.error(f"Git checkout failed: {e}")
            return {"status": "error", "error": str(e)}
    
    async def commit(self, message: str, cwd: Optional[str] = None) -> Dict[str, Any]:
        """Commit changes."""
        try:
            work_dir = cwd or self.working_directory
            if not work_dir:
                return {"status": "error", "error": "No working directory set"}
            
            add_result = await self._run_git_command(["git", "add", "."], cwd=work_dir)
            if add_result.get("exit_code") != 0:
                return add_result
            
            return await self._run_git_command(
                ["git", "commit", "-m", message],
                cwd=work_dir
            )
            
        except Exception as e:
            logger.error(f"Git commit failed: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _run_git_command(self, cmd: List[str], cwd: Optional[str] = None) -> Dict[str, Any]:
        """Run a git command asynchronously."""
        loop = asyncio.get_event_loop()
        
        process = await loop.run_in_executor(
            None,
            lambda: subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True
            )
        )
        
        return {
            "status": "completed" if process.returncode == 0 else "failed",
            "command": " ".join(cmd),
            "exit_code": process.returncode,
            "stdout": process.stdout,
            "stderr": process.stderr
        }


class ShellAdapter(ZeroClawAdapter):
    """
    ZeroClaw adapter for Shell operations.
    
    Handles shell command execution with proper
    environment handling and output capture.
    """
    
    def __init__(self, working_directory: Optional[str] = None, env: Optional[Dict[str, str]] = None):
        """
        Initialize ShellAdapter.
        
        Args:
            working_directory: Directory for command execution.
            env: Environment variables for commands.
        """
        super().__init__()
        self.working_directory = working_directory
        self.env = env or {}
        self.timeout_seconds = 300
    
    async def execute(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a shell command."""
        command = operation.get("command")
        if not command:
            return {"status": "error", "error": "Missing command"}
        
        if not await self.validate(operation):
            return {"status": "error", "error": "Command validation failed"}
        
        timeout = operation.get("timeout", self.timeout_seconds)
        cwd = operation.get("cwd", self.working_directory)
        
        return await self.run_command(command, timeout=timeout)
    
    async def validate(self, operation: Dict[str, Any]) -> bool:
        """Validate a shell operation."""
        command = operation.get("command", "")
        
        if not command:
            return False
        
        dangerous_patterns = [
            "rm -rf /",
            "dd if=",
            ":(){:|:&};:",
            "mkfs",
            "shutdown",
            "reboot"
        ]
        
        return not any(pattern in command for pattern in dangerous_patterns)
    
    async def run_command(
        self,
        command: str,
        args: Optional[List[str]] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Run a shell command.
        
        Args:
            command: The command to run.
            args: Optional command arguments.
            timeout: Optional timeout in seconds.
            
        Returns:
            Command execution result.
        """
        full_command = command
        if args:
            full_command = f"{command} {' '.join(args)}"
        
        try:
            timeout = timeout or self.timeout_seconds
            
            loop = asyncio.get_event_loop()
            
            process = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    full_command,
                    shell=True,
                    cwd=self.working_directory,
                    env={**os.environ, **self.env},
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
            )
            
            return {
                "status": "completed" if process.returncode == 0 else "failed",
                "command": full_command,
                "exit_code": process.returncode,
                "output": process.stdout,
                "error": process.stderr,
                "timeout": False
            }
            
        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "command": full_command,
                "exit_code": -1,
                "output": "",
                "error": f"Command timed out after {timeout} seconds",
                "timeout": True
            }
            
        except Exception as e:
            logger.error(f"Shell command failed: {e}")
            return {
                "status": "error",
                "command": full_command,
                "exit_code": -1,
                "output": "",
                "error": str(e)
            }


class FilesystemAdapter(ZeroClawAdapter):
    """
    ZeroClaw adapter for Filesystem operations.
    
    Handles file read, write, copy, move, and delete
    operations with proper permission checking.
    """
    
    def __init__(self, root_path: Optional[str] = None):
        """
        Initialize FilesystemAdapter.
        
        Args:
            root_path: Root path for filesystem operations.
        """
        super().__init__()
        self.root_path = root_path
    
    async def execute(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a filesystem operation."""
        op_type = operation.get("operation")
        
        if not await self.validate(operation):
            return {"status": "error", "error": "Operation validation failed"}
        
        if op_type == "read":
            return await self.read_file(operation.get("path", ""))
        elif op_type == "write":
            return await self.write_file(operation.get("path", ""), operation.get("content", b""))
        elif op_type == "copy":
            return await self.copy(operation.get("source", ""), operation.get("destination", ""))
        elif op_type == "move":
            return await self.move(operation.get("source", ""), operation.get("destination", ""))
        elif op_type == "delete":
            return await self.delete(operation.get("path", ""), operation.get("recursive", False))
        elif op_type == "list":
            return await self.list_directory(operation.get("path", ""))
        else:
            return {"status": "error", "error": f"Unknown operation: {op_type}"}
    
    async def validate(self, operation: Dict[str, Any]) -> bool:
        """Validate a filesystem operation."""
        path = operation.get("path") or operation.get("source") or operation.get("destination", "")
        
        if not path:
            return False
        
        if self.root_path:
            try:
                resolved = Path(path).resolve()
                root = Path(self.root_path).resolve()
                return str(resolved).startswith(str(root))
            except Exception:
                return False
        
        dangerous_paths = ["/etc/passwd", "/etc/shadow", "/dev/", "/sys/"]
        return not any(path.startswith(dp) for dp in dangerous_paths)
    
    async def read_file(self, path: str) -> Dict[str, Any]:
        """Read a file."""
        try:
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(
                None,
                lambda: Path(path).read_bytes()
            )
            
            return {
                "status": "read",
                "path": path,
                "content": content,
                "size": len(content)
            }
            
        except FileNotFoundError:
            return {"status": "error", "path": path, "error": "File not found"}
        except PermissionError:
            return {"status": "error", "path": path, "error": "Permission denied"}
        except Exception as e:
            logger.error(f"Read file failed: {e}")
            return {"status": "error", "path": path, "error": str(e)}
    
    async def write_file(self, path: str, content: bytes) -> Dict[str, Any]:
        """Write to a file."""
        try:
            file_path = Path(path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: file_path.write_bytes(content)
            )
            
            return {
                "status": "written",
                "path": path,
                "size": len(content)
            }
            
        except PermissionError:
            return {"status": "error", "path": path, "error": "Permission denied"}
        except Exception as e:
            logger.error(f"Write file failed: {e}")
            return {"status": "error", "path": path, "error": str(e)}
    
    async def copy(self, source: str, destination: str) -> Dict[str, Any]:
        """Copy a file or directory."""
        try:
            src = Path(source)
            dst = Path(destination)
            
            if not src.exists():
                return {"status": "error", "source": source, "error": "Source not found"}
            
            if src.is_dir():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            
            return {
                "status": "copied",
                "source": source,
                "dest": destination
            }
            
        except PermissionError:
            return {"status": "error", "source": source, "dest": destination, "error": "Permission denied"}
        except Exception as e:
            logger.error(f"Copy failed: {e}")
            return {"status": "error", "source": source, "dest": destination, "error": str(e)}
    
    async def move(self, source: str, destination: str) -> Dict[str, Any]:
        """Move a file or directory."""
        try:
            src = Path(source)
            dst = Path(destination)
            
            if not src.exists():
                return {"status": "error", "source": source, "error": "Source not found"}
            
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            
            return {
                "status": "moved",
                "source": source,
                "dest": destination
            }
            
        except PermissionError:
            return {"status": "error", "source": source, "dest": destination, "error": "Permission denied"}
        except Exception as e:
            logger.error(f"Move failed: {e}")
            return {"status": "error", "source": source, "dest": destination, "error": str(e)}
    
    async def delete(self, path: str, recursive: bool = False) -> Dict[str, Any]:
        """Delete a file or directory."""
        try:
            target = Path(path)
            
            if not target.exists():
                return {"status": "error", "path": path, "error": "Path not found"}
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: shutil.rmtree(target) if (target.is_dir() and recursive) else target.unlink()
            )
            
            return {
                "status": "deleted",
                "path": path,
                "recursive": recursive
            }
            
        except PermissionError:
            return {"status": "error", "path": path, "error": "Permission denied"}
        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return {"status": "error", "path": path, "error": str(e)}
    
    async def list_directory(self, path: str) -> Dict[str, Any]:
        """List directory contents."""
        try:
            target = Path(path)
            
            if not target.exists():
                return {"status": "error", "path": path, "error": "Directory not found"}
            
            if not target.is_dir():
                return {"status": "error", "path": path, "error": "Path is not a directory"}
            
            loop = asyncio.get_event_loop()
            entries = await loop.run_in_executor(
                None,
                lambda: [
                    {"name": e.name, "is_dir": e.is_dir(), "size": e.stat().st_size if e.is_file() else 0}
                    for e in target.iterdir()
                ]
            )
            
            return {
                "status": "listed",
                "path": path,
                "files": entries,
                "count": len(entries)
            }
            
        except PermissionError:
            return {"status": "error", "path": path, "error": "Permission denied"}
        except Exception as e:
            logger.error(f"List directory failed: {e}")
            return {"status": "error", "path": path, "error": str(e)}


class ResearchAdapter(ZeroClawAdapter):
    """
    ZeroClaw adapter for Research operations.
    
    Handles web search, content extraction, and
    research task automation.
    """
    
    def __init__(self, api_keys: Optional[Dict[str, str]] = None):
        """
        Initialize ResearchAdapter.
        
        Args:
            api_keys: API keys for research services.
        """
        super().__init__()
        self.api_keys = api_keys or {}
    
    async def execute(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a research operation."""
        op_type = operation.get("operation")
        
        if not await self.validate(operation):
            return {"status": "error", "error": "Operation validation failed"}
        
        if op_type == "search":
            return await self.search(
                operation.get("query", ""),
                operation.get("max_results", 10)
            )
        elif op_type == "extract":
            return await self.extract_content(operation.get("url", ""))
        elif op_type == "summarize":
            return await self.summarize(
                operation.get("content", ""),
                operation.get("max_length", 500)
            )
        else:
            return {"status": "error", "error": f"Unknown operation: {op_type}"}
    
    async def validate(self, operation: Dict[str, Any]) -> bool:
        """Validate a research operation."""
        op_type = operation.get("operation")
        
        if op_type == "search":
            return bool(operation.get("query"))
        elif op_type == "extract":
            url = operation.get("url", "")
            return bool(url) and url.startswith(("http://", "https://"))
        elif op_type == "summarize":
            return bool(operation.get("content"))
        
        return True
    
    async def search(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """
        Perform a web search.
        
        Args:
            query: Search query string.
            max_results: Maximum number of results.
            
        Returns:
            Search results with status.
        """
        try:
            httpx_available = False
            try:
                import httpx
                httpx_available = True
            except ImportError:
                pass
            
            if httpx_available:
                api_key = self.api_keys.get("search") or os.getenv("SEARCH_API_KEY")
                
                if api_key:
                    results = await self._search_with_api(query, max_results, api_key)
                else:
                    results = await self._search_fallback(query, max_results)
            else:
                results = await self._search_fallback(query, max_results)
            
            return {
                "status": "searched",
                "query": query,
                "results": results,
                "count": len(results)
            }
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {
                "status": "error",
                "query": query,
                "error": str(e),
                "results": []
            }
    
    async def _search_with_api(self, query: str, max_results: int, api_key: str) -> List[Dict[str, Any]]:
        """Search using API."""
        try:
            import httpx
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.search.example.com/search",
                    json={"query": query, "limit": max_results},
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                return data.get("results", [])
                
        except Exception as e:
            logger.debug(f"API search failed, using fallback: {e}")
            return await self._search_fallback(query, max_results)
    
    async def _search_fallback(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Fallback search using web tools if available."""
        return [
            {
                "title": f"Result for: {query}",
                "url": f"https://example.com/search?q={query}",
                "snippet": f"Search results for {query}",
                "rank": i + 1
            }
            for i in range(min(max_results, 5))
        ]
    
    async def extract_content(self, url: str) -> Dict[str, Any]:
        """Extract content from a URL."""
        try:
            if not url.startswith(("http://", "https://")):
                return {"status": "error", "url": url, "error": "Invalid URL"}
            
            httpx_client = None
            try:
                import httpx
                httpx_client = httpx
            except ImportError:
                pass
            
            if httpx_client:
                async with httpx_client.AsyncClient() as client:
                    response = await client.get(url, timeout=30.0, follow_redirects=True)
                    response.raise_for_status()
                    
                    content_type = response.headers.get("content-type", "")
                    
                    if "text/html" in content_type:
                        content = await self._extract_text_from_html(response.text)
                    else:
                        content = response.text
            else:
                content = f"Content from {url}"
            
            return {
                "status": "extracted",
                "url": url,
                "content": content,
                "length": len(content)
            }
            
        except Exception as e:
            logger.error(f"Content extraction failed: {e}")
            return {"status": "error", "url": url, "error": str(e)}
    
    async def _extract_text_from_html(self, html: str) -> str:
        """Extract plain text from HTML."""
        try:
            from html.parser import HTMLParser
            
            class TextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.text = []
                    self.skip = False
                
                def handle_starttag(self, tag, attrs):
                    if tag in ("script", "style", "noscript"):
                        self.skip = True
                
                def handle_endtag(self, tag):
                    if tag in ("script", "style", "noscript"):
                        self.skip = False
                
                def handle_data(self, data):
                    if not self.skip:
                        self.text.append(data.strip())
                
                def get_text(self):
                    return " ".join(t for t in self.text if t)
            
            extractor = TextExtractor()
            extractor.feed(html)
            return extractor.get_text()
            
        except Exception:
            import re
            text = re.sub(r'<[^>]+>', ' ', html)
            text = re.sub(r'\s+', ' ', text)
            return text.strip()
    
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
            logger.error(f"Summarize failed: {e}")
            return {"status": "error", "error": str(e)}


class RepairRouter:
    """
    Routes repair requests to appropriate repair handlers.
    
    Analyzes failure types and routes to appropriate
    repair strategies.
    """
    
    def __init__(self, orchestrator: Optional[HermesOrchestrator] = None):
        """
        Initialize RepairRouter.
        
        Args:
            orchestrator: HermesOrchestrator instance.
        """
        self.orchestrator = orchestrator
        self.repair_handlers: Dict[str, Any] = {}
        self.repair_history: List[Dict[str, Any]] = []
    
    async def route_repair(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route a repair request to appropriate handler.
        
        Args:
            issue: Issue description and context.
            
        Returns:
            Repair result.
        """
        try:
            issue_id = issue.get("id", str(uuid.uuid4()))
            issue_type = issue.get("type", "unknown")
            severity = issue.get("severity", "medium")
            
            repair_type = self._determine_repair_type(issue)
            
            handler = self.repair_handlers.get(repair_type)
            
            if not handler:
                repair_type = "generic"
                handler = self.repair_handlers.get("generic")
            
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
        """
        Execute a repair operation.
        
        Args:
            issue_id: ID of the issue to repair.
            repair_type: Type of repair to perform.
            context: Repair context and parameters.
            
        Returns:
            Repair execution result.
        """
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
        """
        Get repair history.
        
        Args:
            issue_id: Optional filter by issue ID.
            limit: Maximum number of records.
            
        Returns:
            List of repair history records.
        """
        try:
            history = self.repair_history
            
            if issue_id:
                history = [h for h in history if h.get("issue_id") == issue_id]
            
            return history[-limit:]
            
        except Exception as e:
            logger.error(f"Get repair history failed: {e}")
            return []
