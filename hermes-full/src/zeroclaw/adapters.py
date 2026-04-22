"""
ZeroClaw Adapters - Gateway and adapter implementations.

This module provides the ZeroClaw gateway that manages
adapters for Git, Shell, Filesystem, and Research operations.
Each adapter provides a secure interface for executing
operations in their respective domains.
"""

import asyncio
import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class ZeroClawGateway:
    """
    Main gateway for ZeroClaw adapter management.
    
    Manages registration and routing of adapter requests
    to appropriate adapter implementations.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize ZeroClawGateway."""
        self.config = config or {}
        self._adapters: Dict[str, Any] = {}
        self._operation_log: List[Dict[str, Any]] = []
        self._logger = logging.getLogger(__name__)
        asyncio.create_task(self._register_default_adapters())
    
    async def _register_default_adapters(self) -> None:
        """Register the four default adapters: git, shell, filesystem, research."""
        git = GitAdapter(self.config.get("git", {}))
        shell = ShellAdapter(self.config.get("shell", {}))
        filesystem = FilesystemAdapter(self.config.get("filesystem", {}))
        research = ResearchAdapter(self.config.get("research", {}))
        self._adapters["git"] = git
        self._adapters["shell"] = shell
        self._adapters["filesystem"] = filesystem
        self._adapters["research"] = research
        self._logger.info("Registered default adapters: git, shell, filesystem, research")
    
    async def register_adapter(self, name: str, adapter: BaseAdapter) -> None:
        """Register a custom adapter by name."""
        self._adapters[name] = adapter
        self._logger.info(f"Registered adapter: {name}")
    
    async def get_adapter(self, name: str) -> BaseAdapter:
        """Get an adapter by name."""
        if name not in self._adapters:
            raise ValueError(f"Adapter not found: {name}")
        return self._adapters[name]
    
    async def execute_operation(
        self,
        adapter_name: str,
        operation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute an operation through a specific adapter."""
        adapter = await self.get_adapter(adapter_name)
        result = await adapter.execute(operation)
        await self._log_operation(adapter_name, operation.get("name", "unknown"), result)
        return result
    
    async def execute_batch(
        self,
        operations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Execute multiple operations in batch."""
        results = []
        for op in operations:
            adapter_name = op.get("adapter")
            operation = op.get("operation", {})
            if not adapter_name:
                results.append({"status": "error", "error": "Missing adapter name"})
                continue
            try:
                result = await self.execute_operation(adapter_name, operation)
                results.append(result)
            except Exception as e:
                results.append({"status": "error", "error": str(e)})
        return results
    
    async def get_operation_log(self) -> List[Dict[str, Any]]:
        """Get the operation log."""
        return self._operation_log
    
    async def _log_operation(
        self,
        adapter_name: str,
        operation: str,
        result: Dict[str, Any]
    ) -> None:
        """Log an operation execution."""
        entry = {
            "adapter": adapter_name,
            "operation": operation,
            "status": result.get("status", "unknown"),
            "timestamp": asyncio.get_event_loop().time(),
        }
        self._operation_log.append(entry)


class BaseAdapter(ABC):
    """
    Base class for all ZeroClaw adapters.
    
    Provides common functionality for all adapters
    including validation, logging, and error handling.
    """
    
    def __init__(self, name: str):
        """
        Initialize BaseAdapter.
        
        Args:
            name: Adapter name.
        """
        self.name = name
        self.operations_count = 0
        self.last_operation: Optional[Dict[str, Any]] = None
        self._logger = logging.getLogger(f"{__name__}.{name}")
    
    @abstractmethod
    async def execute(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an operation.
        
        Args:
            operation: Operation specification.
            
        Returns:
            Operation result.
        """
        pass
    
    @abstractmethod
    async def validate(self, operation: Dict[str, Any]) -> bool:
        """
        Validate an operation before execution.
        
        Args:
            operation: Operation to validate.
            
        Returns:
            True if valid, False otherwise.
        """
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get adapter statistics.
        
        Returns:
            Dictionary of adapter statistics.
        """
        return {
            "name": self.name,
            "operations_count": self.operations_count,
            "last_operation": self.last_operation,
        }
    
    def _increment_operations(self) -> None:
        """Increment the operation counter."""
        self.operations_count += 1


class GitAdapter(BaseAdapter):
    """
    Adapter for Git operations.
    
    Provides secure git operations including clone, pull, push,
    branch management, and commit operations.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize GitAdapter.
        
        Args:
            config: Configuration dictionary.
        """
        super().__init__("git")
        self.config = config or {}
        self.working_directory = self.config.get("working_directory")
        self.current_branch: Optional[str] = None
        self.tracked_remote: Optional[str] = None
    
    async def execute(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a Git operation."""
        self._increment_operations()
        self.last_operation = operation
        
        op_name = operation.get("name", "")
        handlers = {
            "clone": lambda: self.clone(
                repository=operation.get("repository", ""),
                branch=operation.get("branch"),
            ),
            "checkout": lambda: self.checkout(
                ref=operation.get("ref", ""),
                create_branch=operation.get("create_branch", False),
            ),
            "commit": lambda: self.commit(
                message=operation.get("message", ""),
                author=operation.get("author"),
            ),
            "push": lambda: self.push(
                remote=operation.get("remote", "origin"),
                branch=operation.get("branch"),
                force=operation.get("force", False),
            ),
            "pull": lambda: self.pull(
                remote=operation.get("remote", "origin"),
                branch=operation.get("branch"),
            ),
        }
        
        handler = handlers.get(op_name)
        if not handler:
            return {"status": "error", "error": f"Unknown operation: {op_name}"}
        
        if not await self.validate(operation):
            return {"status": "error", "error": "Operation validation failed"}
        
        try:
            return await handler()
        except Exception as e:
            self._logger.error(f"Git operation {op_name} failed: {e}")
            return {"status": "error", "error": str(e)}
    
    async def validate(self, operation: Dict[str, Any]) -> bool:
        """Validate a Git operation."""
        op_name = operation.get("name", "")
        valid_ops = {"clone", "checkout", "commit", "push", "pull"}
        
        if op_name not in valid_ops:
            return False
        
        if op_name == "clone" and not operation.get("repository"):
            return False
        if op_name == "checkout" and not operation.get("ref"):
            return False
        if op_name == "commit" and not operation.get("message"):
            return False
        
        return True
    
    async def clone(self, repository: str, branch: Optional[str] = None) -> Dict[str, Any]:
        """
        Clone a git repository.
        
        Args:
            repository: Repository URL.
            branch: Optional branch to clone.
            
        Returns:
            Clone operation result.
        """
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
        """
        Checkout a branch or commit.
        
        Args:
            ref: Branch name or commit hash.
            create_branch: Whether to create a new branch.
            
        Returns:
            Checkout operation result.
        """
        try:
            cmd = ["git", "checkout"]
            if create_branch:
                cmd.extend(["-b", ref])
            else:
                cmd.append(ref)
            
            cwd = self.working_directory or os.getcwd()
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=60,
            )
            
            if result.returncode == 0:
                self.current_branch = ref
                return {
                    "status": "success",
                    "message": f"Checked out: {ref}",
                    "ref": ref,
                    "output": result.stdout,
                }
            else:
                return {
                    "status": "error",
                    "error": result.stderr or "Checkout failed",
                    "ref": ref,
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def commit(self, message: str, author: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Create a commit.
        
        Args:
            message: Commit message.
            author: Optional author information.
            
        Returns:
            Commit operation result.
        """
        try:
            env = os.environ.copy()
            if author:
                name = author.get("name", "")
                email = author.get("email", "")
                if name:
                    env["GIT_AUTHOR_NAME"] = name
                    env["GIT_COMMITTER_NAME"] = name
                if email:
                    env["GIT_AUTHOR_EMAIL"] = email
                    env["GIT_COMMITTER_EMAIL"] = email
            
            cmd = ["git", "commit", "-m", message]
            cwd = self.working_directory or os.getcwd()
            
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                env=env,
                timeout=60,
            )
            
            if result.returncode == 0:
                return {
                    "status": "success",
                    "message": f"Created commit: {message[:50]}...",
                    "commit_message": message,
                    "output": result.stdout,
                }
            else:
                return {
                    "status": "error",
                    "error": result.stderr or "Commit failed",
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def push(
        self,
        remote: str = "origin",
        branch: Optional[str] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Push to remote.
        
        Args:
            remote: Remote name.
            branch: Branch to push.
            force: Whether to force push.
            
        Returns:
            Push operation result.
        """
        try:
            cmd = ["git", "push"]
            if force:
                cmd.append("--force")
            cmd.extend([remote])
            if branch:
                cmd.append(branch)
            
            cwd = self.working_directory or os.getcwd()
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=120,
            )
            
            if result.returncode == 0:
                return {
                    "status": "success",
                    "message": f"Pushed to {remote}",
                    "remote": remote,
                    "branch": branch,
                    "output": result.stdout,
                }
            else:
                return {
                    "status": "error",
                    "error": result.stderr or "Push failed",
                    "remote": remote,
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def pull(self, remote: str = "origin", branch: Optional[str] = None) -> Dict[str, Any]:
        """
        Pull from remote.
        
        Args:
            remote: Remote name.
            branch: Branch to pull.
            
        Returns:
            Pull operation result.
        """
        try:
            cmd = ["git", "pull", remote]
            if branch:
                cmd.append(branch)
            
            cwd = self.working_directory or os.getcwd()
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=120,
            )
            
            if result.returncode == 0:
                return {
                    "status": "success",
                    "message": f"Pulled from {remote}",
                    "remote": remote,
                    "branch": branch,
                    "output": result.stdout,
                }
            else:
                return {
                    "status": "error",
                    "error": result.stderr or "Pull failed",
                    "remote": remote,
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}


class ShellAdapter(BaseAdapter):
    """
    Adapter for Shell command execution.
    
    Provides secure shell command execution with
    environment control, timeout management, and output capture.
    """
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize ShellAdapter.
        
        Args:
            config: Configuration dictionary.
        """
        super().__init__("shell")
        self.config = config or {}
        self.working_directory = self.config.get("working_directory")
        self.env = self.config.get("env", {})
        self.timeout = self.config.get("timeout", 300)
        self._running_processes: Dict[str, subprocess.Popen] = {}
    
    async def execute(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a shell command."""
        self._increment_operations()
        self.last_operation = operation
        
        op_name = operation.get("name", "")
        
        if op_name == "run":
            return await self.run(
                command=operation.get("command", ""),
                args=operation.get("args"),
                cwd=operation.get("cwd"),
                env=operation.get("env"),
                timeout=operation.get("timeout"),
            )
        elif op_name == "get_output":
            return await self.get_output(
                process_id=operation.get("process_id", ""),
            )
        
        if not await self.validate(operation):
            return {"status": "error", "error": "Operation validation failed"}
        
        return {"status": "error", "error": f"Unknown operation: {op_name}"}
    
    async def validate(self, operation: Dict[str, Any]) -> bool:
        """Validate a shell operation."""
        op_name = operation.get("name", "")
        
        if op_name == "run":
            return bool(operation.get("command"))
        if op_name == "get_output":
            return bool(operation.get("process_id"))
        
        return False
    
    async def run(
        self,
        command: str,
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Run a shell command.
        
        Args:
            command: Command to execute.
            args: Command arguments.
            cwd: Working directory.
            env: Environment variables.
            timeout: Execution timeout.
            
        Returns:
            Command execution result.
        """
        try:
            import uuid
            process_id = str(uuid.uuid4())[:8]
            
            cmd = [command]
            if args:
                cmd.extend(args)
            
            effective_cwd = cwd or self.working_directory or os.getcwd()
            effective_timeout = timeout or self.timeout
            
            merged_env = os.environ.copy()
            merged_env.update(self.env)
            if env:
                merged_env.update(env)
            
            process = subprocess.Popen(
                cmd,
                cwd=effective_cwd,
                env=merged_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            
            self._running_processes[process_id] = process
            
            try:
                stdout, stderr = process.communicate(timeout=effective_timeout)
                del self._running_processes[process_id]
                
                return {
                    "status": "success",
                    "process_id": process_id,
                    "command": command,
                    "exit_code": process.returncode,
                    "stdout": stdout,
                    "stderr": stderr,
                }
            except subprocess.TimeoutExpired:
                process.kill()
                del self._running_processes[process_id]
                return {
                    "status": "error",
                    "process_id": process_id,
                    "error": "Command timed out",
                    "timeout": effective_timeout,
                }
                
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def get_output(self, process_id: str) -> Dict[str, Any]:
        """
        Get output from a running process.
        
        Args:
            process_id: Process identifier.
            
        Returns:
            Process output.
        """
        process = self._running_processes.get(process_id)
        
        if not process:
            return {
                "status": "error",
                "error": f"Process not found: {process_id}",
                "process_id": process_id,
            }
        
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            return {
                "status": "completed",
                "process_id": process_id,
                "exit_code": process.returncode,
                "stdout": stdout,
                "stderr": stderr,
            }
        
        return {
            "status": "running",
            "process_id": process_id,
            "exit_code": None,
        }


class FilesystemAdapter(BaseAdapter):
    """
    Adapter for Filesystem operations.
    
    Provides secure file and directory operations with
    permission checking and path validation.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize FilesystemAdapter.
        
        Args:
            config: Configuration dictionary.
        """
        super().__init__("filesystem")
        self.config = config or {}
        self.root_path = self.config.get("root_path")
    
    async def execute(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a filesystem operation."""
        self._increment_operations()
        self.last_operation = operation
        
        op_name = operation.get("name", "")
        handlers = {
            "read": lambda: self.read(
                path=operation.get("path", ""),
                offset=operation.get("offset", 0),
                length=operation.get("length"),
            ),
            "write": lambda: self.write(
                path=operation.get("path", ""),
                content=operation.get("content", b""),
                append=operation.get("append", False),
            ),
            "copy": lambda: self.copy(
                source=operation.get("source", ""),
                destination=operation.get("destination", ""),
            ),
            "move": lambda: self.move(
                source=operation.get("source", ""),
                destination=operation.get("destination", ""),
            ),
            "delete": lambda: self.delete(
                path=operation.get("path", ""),
                recursive=operation.get("recursive", False),
            ),
            "list_directory": lambda: self.list_directory(
                path=operation.get("path", ""),
            ),
        }
        
        handler = handlers.get(op_name)
        if not handler:
            return {"status": "error", "error": f"Unknown operation: {op_name}"}
        
        if not await self.validate(operation):
            return {"status": "error", "error": "Operation validation failed"}
        
        try:
            return await handler()
        except Exception as e:
            self._logger.error(f"Filesystem operation {op_name} failed: {e}")
            return {"status": "error", "error": str(e)}
    
    async def validate(self, operation: Dict[str, Any]) -> bool:
        """Validate a filesystem operation."""
        op_name = operation.get("name", "")
        valid_ops = {"read", "write", "copy", "move", "delete", "list_directory"}
        
        if op_name not in valid_ops:
            return False
        
        if op_name in {"read", "write", "delete", "list_directory"}:
            return bool(operation.get("path"))
        if op_name in {"copy", "move"}:
            return bool(operation.get("source")) and bool(operation.get("destination"))
        
        return True
    
    def _resolve_path(self, path: str) -> Path:
        """Resolve a path relative to root_path if configured."""
        p = Path(path)
        if not p.is_absolute():
            if self.root_path:
                p = Path(self.root_path) / p
        return p.expanduser().resolve()
    
    async def read(self, path: str, offset: int = 0, length: Optional[int] = None) -> Dict[str, Any]:
        """
        Read file contents.
        
        Args:
            path: File path.
            offset: Read offset.
            length: Number of bytes to read.
            
        Returns:
            File contents as bytes.
        """
        try:
            resolved_path = self._resolve_path(path)
            
            if not resolved_path.exists():
                return {"status": "error", "error": f"File not found: {path}"}
            
            if resolved_path.is_dir():
                return {"status": "error", "error": f"Path is a directory: {path}"}
            
            with open(resolved_path, "rb") as f:
                if offset > 0:
                    f.seek(offset)
                content = f.read(length) if length else f.read()
            
            return {
                "status": "success",
                "path": path,
                "content": content,
                "size": len(content),
                "offset": offset,
            }
        except PermissionError:
            return {"status": "error", "error": f"Permission denied: {path}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def write(self, path: str, content: bytes, append: bool = False) -> Dict[str, Any]:
        """
        Write file contents.
        
        Args:
            path: File path.
            content: Content to write.
            append: Whether to append.
            
        Returns:
            True if successful.
        """
        try:
            resolved_path = self._resolve_path(path)
            
            resolved_path.parent.mkdir(parents=True, exist_ok=True)
            
            mode = "ab" if append else "wb"
            with open(resolved_path, mode) as f:
                f.write(content)
            
            return {
                "status": "success",
                "path": path,
                "bytes_written": len(content),
                "append": append,
            }
        except PermissionError:
            return {"status": "error", "error": f"Permission denied: {path}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def copy(self, source: str, destination: str) -> Dict[str, Any]:
        """
        Copy file or directory.
        
        Args:
            source: Source path.
            destination: Destination path.
            
        Returns:
            True if successful.
        """
        try:
            src = self._resolve_path(source)
            dst = self._resolve_path(destination)
            
            if not src.exists():
                return {"status": "error", "error": f"Source not found: {source}"}
            
            if src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            
            return {
                "status": "success",
                "source": source,
                "destination": destination,
            }
        except PermissionError:
            return {"status": "error", "error": f"Permission denied for copy operation"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def move(self, source: str, destination: str) -> Dict[str, Any]:
        """
        Move file or directory.
        
        Args:
            source: Source path.
            destination: Destination path.
            
        Returns:
            True if successful.
        """
        try:
            src = self._resolve_path(source)
            dst = self._resolve_path(destination)
            
            if not src.exists():
                return {"status": "error", "error": f"Source not found: {source}"}
            
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            
            return {
                "status": "success",
                "source": source,
                "destination": destination,
            }
        except PermissionError:
            return {"status": "error", "error": f"Permission denied for move operation"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def delete(self, path: str, recursive: bool = False) -> Dict[str, Any]:
        """
        Delete file or directory.
        
        Args:
            path: Path to delete.
            recursive: Whether to delete recursively.
            
        Returns:
            True if successful.
        """
        try:
            resolved_path = self._resolve_path(path)
            
            if not resolved_path.exists():
                return {"status": "error", "error": f"Path not found: {path}"}
            
            if resolved_path.is_dir():
                if recursive:
                    shutil.rmtree(resolved_path)
                else:
                    resolved_path.rmdir()
            else:
                resolved_path.unlink()
            
            return {
                "status": "success",
                "path": path,
                "recursive": recursive,
            }
        except PermissionError:
            return {"status": "error", "error": f"Permission denied: {path}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def list_directory(self, path: str) -> Dict[str, Any]:
        """
        List directory contents.
        
        Args:
            path: Directory path.
            
        Returns:
            List of directory entries.
        """
        try:
            resolved_path = self._resolve_path(path)
            
            if not resolved_path.exists():
                return {"status": "error", "error": f"Directory not found: {path}"}
            
            if not resolved_path.is_dir():
                return {"status": "error", "error": f"Path is not a directory: {path}"}
            
            entries = []
            for item in resolved_path.iterdir():
                entries.append({
                    "name": item.name,
                    "path": str(item),
                    "is_directory": item.is_dir(),
                    "is_file": item.is_file(),
                    "size": item.stat().st_size if item.is_file() else None,
                })
            
            return {
                "status": "success",
                "path": path,
                "entries": entries,
                "count": len(entries),
            }
        except PermissionError:
            return {"status": "error", "error": f"Permission denied: {path}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}


class ResearchAdapter(BaseAdapter):
    """
    Adapter for Research operations.
    
    Provides web search, content extraction, and
    summarization capabilities.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize ResearchAdapter.
        
        Args:
            config: Configuration dictionary with api_keys and other settings.
        """
        super().__init__("research")
        self.config = config or {}
        self.api_keys = self.config.get("api_keys", {})
        self._search_backend = self.config.get("search_backend", "firecrawl")
        self._extract_backend = self.config.get("extract_backend", "firecrawl")
    
    async def execute(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a research operation."""
        self._increment_operations()
        self.last_operation = operation
        
        op_name = operation.get("name", "")
        
        if not await self.validate(operation):
            return {"status": "error", "error": "Operation validation failed"}
        
        try:
            if op_name == "search":
                return await self.search(
                    query=operation.get("query", ""),
                    engine=operation.get("engine", "default"),
                    max_results=operation.get("max_results", 10),
                )
            elif op_name == "extract":
                return await self.extract(
                    url=operation.get("url", ""),
                    selectors=operation.get("selectors"),
                )
            elif op_name == "summarize":
                summary = await self.summarize(
                    content=operation.get("content", ""),
                    max_length=operation.get("max_length", 500),
                )
                return {"status": "success", "summary": summary}
            else:
                return {"status": "error", "error": f"Unknown operation: {op_name}"}
        except Exception as e:
            self._logger.error(f"Research operation {op_name} failed: {e}")
            return {"status": "error", "error": str(e)}
    
    async def validate(self, operation: Dict[str, Any]) -> bool:
        """Validate a research operation."""
        op_name = operation.get("name", "")
        
        if op_name == "search":
            return bool(operation.get("query"))
        if op_name == "extract":
            return bool(operation.get("url"))
        if op_name == "summarize":
            return bool(operation.get("content"))
        
        return False
    
    async def search(
        self,
        query: str,
        engine: str = "default",
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        Perform a web search.
        
        Args:
            query: Search query.
            engine: Search engine to use.
            max_results: Maximum results.
            
        Returns:
            List of search results.
        """
        try:
            try:
                from tools.web_tools import web_search_tool
                result = web_search_tool(query=query, limit=max_results)
                result_data = json.loads(result)
                
                if result_data.get("success", False):
                    return {
                        "status": "success",
                        "query": query,
                        "results": result_data.get("data", {}).get("web", []),
                        "count": len(result_data.get("data", {}).get("web", [])),
                    }
                else:
                    return {
                        "status": "error",
                        "error": result_data.get("error", "Search failed"),
                        "query": query,
                    }
            except ImportError:
                return await self._search_fallback(query, max_results)
                
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def _search_fallback(self, query: str, max_results: int) -> Dict[str, Any]:
        """Fallback search using httpx when web_tools is not available."""
        try:
            import httpx
            
            backend = self._search_backend
            results = []
            
            if backend == "tavily":
                api_key = self.api_keys.get("tavily") or os.getenv("TAVILY_API_KEY")
                if not api_key:
                    return {"status": "error", "error": "Tavily API key not configured"}
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://api.tavily.com/search",
                        json={
                            "query": query,
                            "max_results": max_results,
                            "api_key": api_key,
                        },
                        timeout=30.0,
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    for i, item in enumerate(data.get("results", []), 1):
                        results.append({
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "description": item.get("content", ""),
                            "position": i,
                        })
                
                return {
                    "status": "success",
                    "query": query,
                    "results": results,
                    "count": len(results),
                }
            
            return {"status": "error", "error": f"Unsupported search backend: {backend}"}
            
        except Exception as e:
            return {"status": "error", "error": f"Search failed: {str(e)}"}
    
    async def extract(
        self,
        url: str,
        selectors: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Extract content from URL.
        
        Args:
            url: URL to extract from.
            selectors: Optional CSS selectors.
            
        Returns:
            Extracted content.
        """
        try:
            try:
                from tools.web_tools import web_extract_tool
                import asyncio
                
                result = await web_extract_tool(
                    urls=[url],
                    format="markdown",
                    use_llm_processing=False,
                )
                result_data = json.loads(result)
                
                if result_data.get("success", False):
                    pages = result_data.get("data", {}).get("pages", [])
                    if pages:
                        return {
                            "status": "success",
                            "url": url,
                            "content": pages[0].get("content", ""),
                            "title": pages[0].get("title", ""),
                        }
                    return {
                        "status": "error",
                        "error": "No content extracted",
                        "url": url,
                    }
                else:
                    return {
                        "status": "error",
                        "error": result_data.get("error", "Extraction failed"),
                        "url": url,
                    }
            except ImportError:
                return await self._extract_fallback(url, selectors)
                
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def _extract_fallback(self, url: str, selectors: Optional[List[str]] = None) -> Dict[str, Any]:
        """Fallback extraction using httpx when web_tools is not available."""
        try:
            import httpx
            from bs4 import BeautifulSoup
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=30.0, follow_redirects=True)
                response.raise_for_status()
                
                content_type = response.headers.get("content-type", "")
                if "text/html" in content_type:
                    soup = BeautifulSoup(response.text, "html.parser")
                    
                    for script in soup(["script", "style"]):
                        script.decompose()
                    
                    text = soup.get_text(separator="\n", strip=True)
                    lines = [line for line in text.split("\n") if line.strip()]
                    clean_text = "\n".join(lines)
                    
                    return {
                        "status": "success",
                        "url": url,
                        "content": clean_text,
                        "title": soup.title.string if soup.title else "",
                    }
                else:
                    return {
                        "status": "success",
                        "url": url,
                        "content": response.text,
                    }
                    
        except Exception as e:
            return {"status": "error", "error": f"Extraction failed: {str(e)}"}
    
    async def summarize(self, content: str, max_length: int = 500) -> str:
        """
        Summarize content.
        
        Args:
            content: Content to summarize.
            max_length: Maximum summary length.
            
        Returns:
            Summarized content.
        """
        try:
            if len(content) <= max_length:
                return content
            
            sentences = content.split(". ")
            summary_parts = []
            current_length = 0
            
            for sentence in sentences:
                if current_length + len(sentence) > max_length:
                    break
                summary_parts.append(sentence)
                current_length += len(sentence) + 1
            
            summary = ". ".join(summary_parts)
            if summary and not summary.endswith("."):
                summary += "."
            
            return summary
            
        except Exception as e:
            self._logger.warning(f"Summarization failed: {e}")
            return content[:max_length] + "..." if len(content) > max_length else content
