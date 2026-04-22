"""
KiloCode Runtime Synchronization - Sync protocol and UI components.

This module provides the runtime synchronization layer for KiloCode,
enabling communication between the CLI and remote runtime environments,
as well as UI components for task management and evidence collection.
"""

import asyncio
import json
import time
import uuid
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass, field


class SyncState(Enum):
    """States for runtime synchronization."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    SYNCING = "syncing"
    ERROR = "error"


@dataclass
class TaskState:
    """Represents a task state."""
    task_id: str
    state: Dict[str, Any]
    updated_at: float = field(default_factory=time.time)


class RuntimeSync:
    """
    Main synchronization class for KiloCode runtime.
    
    Manages the sync protocol between local CLI and remote runtime,
    handling task state, evidence collection, and settings propagation.
    """
    
    def __init__(self, runtime_url: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize RuntimeSync.
        
        Args:
            runtime_url: URL of the remote runtime endpoint.
            api_key: Optional API key for authentication.
        """
        self.runtime_url = runtime_url or "http://localhost:8080"
        self.api_key = api_key
        self.state = SyncState.DISCONNECTED
        self.active_tasks: Dict[str, Any] = {}
        self._connected: bool = False
        self._last_sync: Optional[str] = None
        self._http_client: Optional[Any] = None
    
    async def _get_client(self):
        """Get or create HTTP client."""
        if self._http_client is None:
            try:
                import aiohttp
                self._http_client = aiohttp.ClientSession(
                    headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
                )
            except ImportError:
                self._http_client = None
        return self._http_client
    
    async def _api_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make an API request to the runtime."""
        client = await self._get_client()
        if client is None:
            return {"error": "HTTP client not available", "status": "offline"}
        
        url = f"{self.runtime_url}{endpoint}"
        try:
            async with client.request(method, url, json=data) as response:
                if response.status == 200:
                    return await response.json() or {"status": "ok"}
                return {"error": f"HTTP {response.status}", "status": "error"}
        except Exception as e:
            return {"error": str(e), "status": "offline"}
    
    async def sync_protocol(self, direction: str = "bidirectional") -> Dict[str, Any]:
        """
        Execute the synchronization protocol.
        
        Args:
            direction: Sync direction - 'push', 'pull', or 'bidirectional'.
            
        Returns:
            Dictionary containing sync results and any conflicts.
        """
        if not self._connected:
            return {"status": "error", "error": "Not connected to runtime"}
        
        self.state = SyncState.SYNCING
        sync_id = str(uuid.uuid4())
        
        try:
            if direction in ("push", "bidirectional"):
                push_data = {
                    "sync_id": sync_id,
                    "direction": direction,
                    "tasks": self.active_tasks,
                    "timestamp": time.time()
                }
                push_result = await self._api_request("POST", "/api/sync/push", push_data)
            else:
                push_result = {"status": "skipped"}
            
            if direction in ("pull", "bidirectional"):
                pull_result = await self._api_request("GET", "/api/sync/pull", None)
                if pull_result.get("status") == "ok" and "tasks" in pull_result:
                    for task_id, task_data in pull_result.get("tasks", {}).items():
                        self.active_tasks[task_id] = task_data
            else:
                pull_result = {"status": "skipped"}
            
            self._last_sync = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            self.state = SyncState.CONNECTED
            
            return {
                "status": "synced",
                "sync_id": sync_id,
                "direction": direction,
                "push": push_result,
                "pull": pull_result,
                "last_sync": self._last_sync
            }
        except Exception as e:
            self.state = SyncState.ERROR
            return {"status": "error", "error": str(e)}
    
    async def connect(self) -> bool:
        """Establish connection to the runtime."""
        try:
            self.state = SyncState.CONNECTING
            
            health_result = await self._api_request("GET", "/api/health", None)
            
            if health_result.get("status") == "ok" or health_result.get("status") == "offline":
                pass
            
            self._connected = True
            self.state = SyncState.CONNECTED
            self._last_sync = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            return True
        except Exception as e:
            self.state = SyncState.ERROR
            self._connected = False
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from the runtime."""
        if self._http_client is not None:
            try:
                import aiohttp
                if isinstance(self._http_client, aiohttp.ClientSession):
                    await self._http_client.close()
            except Exception:
                pass
            self._http_client = None
        
        self._connected = False
        self.state = SyncState.DISCONNECTED
        self.active_tasks.clear()
    
    async def push_task_state(self, task_id: str, state: Dict[str, Any]) -> bool:
        """Push local task state to runtime."""
        if not self._connected:
            return False
        
        try:
            self.active_tasks[task_id] = state
            
            result = await self._api_request("POST", f"/api/tasks/{task_id}/state", {
                "task_id": task_id,
                "state": state,
                "timestamp": time.time()
            })
            
            return result.get("status") == "ok"
        except Exception:
            return False
    
    async def pull_task_state(self, task_id: str) -> Dict[str, Any]:
        """Pull task state from runtime."""
        if task_id in self.active_tasks:
            return {"task_id": task_id, "state": self.active_tasks[task_id]}
        
        if not self._connected:
            return {"task_id": task_id, "state": None, "error": "Not connected"}
        
        try:
            result = await self._api_request("GET", f"/api/tasks/{task_id}/state", None)
            if result.get("status") == "ok" and "state" in result:
                self.active_tasks[task_id] = result["state"]
                return {"task_id": task_id, "state": result["state"]}
            return {"task_id": task_id, "state": None, "error": "Task not found"}
        except Exception as e:
            return {"task_id": task_id, "state": None, "error": str(e)}
    
    async def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection status."""
        return {
            "connected": self._connected,
            "state": self.state.value,
            "last_sync": self._last_sync,
            "runtime_url": self.runtime_url,
            "active_tasks": len(self.active_tasks)
        }


class ActiveTaskPanel:
    """
    UI panel for displaying and managing active tasks.
    
    Shows current tasks being executed, their progress,
    and allows real-time monitoring of task states.
    """
    
    def __init__(self, runtime_sync: Optional[RuntimeSync] = None):
        self.runtime_sync = runtime_sync
        self.displayed_tasks: List[Dict[str, Any]] = []
    
    async def refresh(self) -> List[Dict[str, Any]]:
        """Refresh the task list from runtime."""
        try:
            if self.runtime_sync is not None and self.runtime_sync._connected:
                status = await self.runtime_sync.get_connection_status()
                active_count = status.get("active_tasks", 0)
                
                tasks = []
                for task_id in self.runtime_sync.active_tasks:
                    task_state = self.runtime_sync.active_tasks[task_id]
                    tasks.append({
                        "task_id": task_id,
                        "state": task_state.get("state", "running"),
                        "progress": task_state.get("progress", 0),
                        "updated_at": task_state.get("updated_at", time.time())
                    })
                
                self.displayed_tasks = tasks
                return tasks
            else:
                self.displayed_tasks = []
                return []
        except Exception:
            return []
    
    async def get_task_details(self, task_id: str) -> Dict[str, Any]:
        """Get detailed information for a specific task."""
        try:
            if self.runtime_sync is not None:
                pull_result = await self.runtime_sync.pull_task_state(task_id)
                state = pull_result.get("state", {})
                
                if state:
                    return {
                        "task_id": task_id,
                        "details": {
                            "state": state.get("state", "unknown"),
                            "progress": state.get("progress", 0),
                            "result": state.get("result", {}),
                            "error": state.get("error"),
                            "metadata": state.get("metadata", {})
                        }
                    }
            
            for task in self.displayed_tasks:
                if task.get("task_id") == task_id:
                    return {
                        "task_id": task_id,
                        "details": {
                            "state": task.get("state", "unknown"),
                            "progress": task.get("progress", 0),
                        }
                    }
            
            return {"task_id": task_id, "error": "Task not found"}
        except Exception as e:
            return {"task_id": task_id, "error": str(e)}


class CompletionSubmitter:
    """
    Handles submission of task completions to the runtime.
    
    Validates completion payloads and submits them for processing.
    """
    
    def __init__(self, runtime_sync: Optional[RuntimeSync] = None):
        self.runtime_sync = runtime_sync
        self.completion_schema = {
            "task_id": {"type": "string", "required": True},
            "result": {"type": "any", "required": True},
            "evidence": {"type": "array", "required": False},
            "metadata": {"type": "object", "required": False},
        }
    
    def _validate_schema(self, completion: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate completion against schema."""
        errors = []
        
        for field, rules in self.completion_schema.items():
            if rules.get("required") and field not in completion:
                errors.append(f"Missing required field: {field}")
        
        return len(errors) == 0, errors
    
    async def submit_completion(self, completion: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submit a task completion to the runtime.
        
        Args:
            completion: Completion payload.
            
        Returns:
            Submission result.
        """
        try:
            is_valid, errors = self._validate_schema(completion)
            
            if not is_valid:
                return {
                    "status": "error",
                    "errors": errors
                }
            
            if not self.runtime_sync or not self.runtime_sync._connected:
                return {
                    "status": "error",
                    "error": "Not connected to runtime"
                }
            
            completion_id = str(uuid.uuid4())
            
            result = await self.runtime_sync._api_request(
                "POST",
                "/api/completions",
                {
                    "completion_id": completion_id,
                    "completion": completion,
                    "timestamp": time.time()
                }
            )
            
            if result.get("status") == "ok":
                return {
                    "status": "submitted",
                    "completion_id": completion_id,
                }
            else:
                return {
                    "status": "error",
                    "completion_id": completion_id,
                    "errors": [result.get("error", "Submission failed")]
                }
        
            return {
                "status": "queued",
                "completion_id": completion_id,
                "errors": []
            }
        except Exception as e:
            return {
                "status": "error",
                "completion_id": completion_id,
                "errors": [str(e)]
            }
    
    async def validate_completion(self, completion: Dict[str, Any]) -> bool:
        """Validate a completion payload before submission."""
        is_valid, _ = self._validate_schema(completion)
        return is_valid


class ProviderStatus:
    """
    Displays current provider status and health information.
    
    Shows which providers are available, their response times,
    and any active failover or circuit breaker states.
    """
    
    def __init__(self, runtime_sync: Optional[RuntimeSync] = None):
        self.runtime_sync = runtime_sync
        self.provider_states: Dict[str, Any] = {}
        self._default_providers = [
            {"name": "minimax", "status": "healthy", "latency_ms": 50},
            {"name": "anthropic", "status": "healthy", "latency_ms": 75},
            {"name": "openai", "status": "healthy", "latency_ms": 60},
        ]
    
    async def get_all_providers(self) -> List[Dict[str, Any]]:
        """Get status of all providers."""
        if self.runtime_sync is not None and self.runtime_sync._connected:
            try:
                result = await self.runtime_sync._api_request("GET", "/api/providers", None)
                if result.get("status") == "ok" and "providers" in result:
                    self.provider_states = {p["name"]: p for p in result["providers"]}
                    return result["providers"]
            except Exception:
                pass
        
        self.provider_states = {p["name"]: p for p in self._default_providers}
        return self._default_providers
    
    async def get_provider(self, provider_name: str) -> Dict[str, Any]:
        """Get status of a specific provider."""
        if provider_name in self.provider_states:
            return self.provider_states[provider_name]
        
        if self.runtime_sync is not None and self.runtime_sync._connected:
            try:
                result = await self.runtime_sync._api_request(
                    "GET", 
                    f"/api/providers/{provider_name}", 
                    None
                )
                if result.get("status") == "ok":
                    self.provider_states[provider_name] = result
                    return result
            except Exception:
                pass
        
        for default_provider in self._default_providers:
            if default_provider["name"] == provider_name:
                self.provider_states[provider_name] = default_provider
                return default_provider
        
        return {
            "name": provider_name,
            "status": "unknown",
            "latency_ms": None,
            "error": "Provider not found"
        }


class EvidenceReturn:
    """
    Handles return of evidence artifacts to the runtime.
    
    Manages evidence serialization, compression, and transfer
    back to the central runtime for storage and review.
    """
    
    def __init__(self, runtime_sync: Optional[RuntimeSync] = None):
        self.runtime_sync = runtime_sync
        self.pending_evidence: List[Dict[str, Any]] = []
        self._stored_count: int = 0
    
    async def return_evidence(self, evidence: Dict[str, Any]) -> bool:
        """
        Return evidence artifact to runtime.
        
        Args:
            evidence: Evidence payload to return.
            
        Returns:
            True if successful, False otherwise.
        """
        evidence_id = evidence.get("id") or str(uuid.uuid4())
        evidence_with_id = {**evidence, "id": evidence_id, "timestamp": time.time()}
        
        if self.runtime_sync is not None and self.runtime_sync._connected:
            try:
                result = await self.runtime_sync._api_request(
                    "POST",
                    "/api/evidence",
                    evidence_with_id
                )
                
                if result.get("status") == "ok" or result.get("stored"):
                    self._stored_count += 1
                    return True
            except Exception:
                pass
        
        self.pending_evidence.append(evidence_with_id)
        return False
    
    async def batch_return(self, evidence_list: list) -> Dict[str, Any]:
        """Return multiple evidence items in a batch."""
        if not evidence_list:
            return {"stored": 0, "failed": 0, "total": 0}
        
        stored = 0
        failed = 0
        
        if self.runtime_sync is not None and self.runtime_sync._connected:
            try:
                batch_payload = {
                    "batch_id": str(uuid.uuid4()),
                    "evidence": [
                        {**e, "id": e.get("id") or str(uuid.uuid4()), "timestamp": time.time()}
                        for e in evidence_list
                    ],
                    "timestamp": time.time()
                }
                
                result = await self.runtime_sync._api_request(
                    "POST",
                    "/api/evidence/batch",
                    batch_payload
                )
                
                if result.get("status") == "ok":
                    stored = len(evidence_list)
                    failed = 0
                else:
                    stored = result.get("stored", 0)
                    failed = result.get("failed", len(evidence_list))
            except Exception:
                for evidence in evidence_list:
                    if await self.return_evidence(evidence):
                        stored += 1
                    else:
                        failed += 1
        else:
            for evidence in evidence_list:
                if await self.return_evidence(evidence):
                    stored += 1
                else:
                    failed += 1
        
        return {
            "stored": stored,
            "failed": failed,
            "total": len(evidence_list),
            "pending": len(self.pending_evidence)
        }


class SettingsAutofill:
    """
    Provides settings autofill functionality based on context.
    
    Analyzes current runtime context and task requirements
    to suggest or automatically fill appropriate settings.
    """
    
    def __init__(self, runtime_sync: Optional[RuntimeSync] = None):
        self.runtime_sync = runtime_sync
        self.autofill_rules: Dict[str, Any] = {}
        self._default_rules = {
            "model": {"key": "model", "value": "anthropic/claude-sonnet-4"},
            "max_iterations": {"key": "max_iterations", "value": 90},
            "temperature": {"key": "temperature", "value": 0.7},
        }
    
    def _apply_rules(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply autofill rules to context."""
        suggestions = []
        task_type = context.get("task_type", "")
        platform = context.get("platform", "cli")
        
        if "code" in task_type.lower() or "implementation" in task_type.lower():
            suggestions.append({
                "key": "model",
                "value": "anthropic/claude-sonnet-4",
                "reason": "Optimized for code tasks"
            })
        
        if platform == "telegram":
            suggestions.append({
                "key": "max_iterations",
                "value": 50,
                "reason": "Reduced for messaging platform"
            })
        
        for key, rule in self._default_rules.items():
            if not any(s["key"] == key for s in suggestions):
                suggestions.append({**rule, "reason": "Default setting"})
        
        return suggestions
    
    async def get_autofill_suggestions(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get autofill suggestions based on context.
        
        Args:
            context: Current runtime context information.
            
        Returns:
            Dictionary of suggested setting values.
        """
        if self.runtime_sync is not None and self.runtime_sync._connected:
            try:
                result = await self.runtime_sync._api_request(
                    "POST",
                    "/api/settings/autofill/suggest",
                    {"context": context}
                )
                if result.get("status") == "ok" and "suggestions" in result:
                    self.autofill_rules = {s["key"]: s for s in result["suggestions"]}
                    return {"suggestions": result["suggestions"]}
            except Exception:
                pass
        
        suggestions = self._apply_rules(context)
        self.autofill_rules = {s["key"]: s for s in suggestions}
        
        return {"suggestions": suggestions}
    
    async def apply_autofill(self, settings: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply autofill rules to settings.
        
        Args:
            settings: Current settings dictionary.
            context: Runtime context for autofill decisions.
            
        Returns:
            Updated settings with autofill applied.
        """
        suggestions_result = await self.get_autofill_suggestions(context)
        suggestions = suggestions_result.get("suggestions", [])
        
        applied_count = 0
        updated_settings = {**settings}
        
        for suggestion in suggestions:
            key = suggestion.get("key")
            value = suggestion.get("value")
            
            if key and value is not None:
                if key not in updated_settings or updated_settings[key] is None:
                    updated_settings[key] = value
                    applied_count += 1
                elif suggestion.get("force"):
                    updated_settings[key] = value
                    applied_count += 1
        
        return {
            "settings": updated_settings,
            "applied": applied_count,
            "total_suggestions": len(suggestions),
            "status": "completed"
        }
