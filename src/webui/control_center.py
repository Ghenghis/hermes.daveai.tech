"""
WebUI Control Center - Main application and panel components.

This module provides the web-based control center interface for monitoring
and managing contract kit operations across providers, agents, workflows,
evidence collection, repairs, and settings.
"""

import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List


class ControlCenterApp:
    """
    Main FastAPI application for the WebUI Control Center.
    
    Provides routing for all control center panels and orchestrates
    the web interface for contract kit management.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Control Center application.
        
        Args:
            config: Optional configuration dictionary for the application.
        """
        self.config = config or {}
        self._panels: Dict[str, Any] = {}
    
    async def mount_panel(self, panel_name: str, panel: Any) -> None:
        """
        Mount a panel to the control center.
        
        Args:
            panel_name: Unique name identifier for the panel.
            panel: The panel instance to mount.
        """
        self._panels[panel_name] = panel
    
    async def get_routes(self) -> list:
        """
        Get all routes for the control center.
        
        Returns:
            List of route definitions for FastAPI registration.
        """
        return [
            ("/control-center/health", self.health_check),
            ("/control-center/providers", self.list_providers),
            ("/control-center/providers/status", self.get_providers_status),
            ("/control-center/providers/metrics", self.get_providers_metrics),
            ("/control-center/agents", self.list_agents),
            ("/control-center/agents/{agent_id}", self.get_agent),
            ("/control-center/workflows", self.list_workflows),
            ("/control-center/workflows/{workflow_id}", self.get_workflow),
            ("/control-center/evidence", self.list_evidence),
            ("/control-center/evidence/{evidence_id}", self.get_evidence_item),
            ("/control-center/evidence/{evidence_id}/export", self.export_evidence_item),
            ("/control-center/repairs", self.list_repairs),
            ("/control-center/repairs/{repair_id}", self.get_repair),
            ("/control-center/repairs/trigger", self.trigger_repair),
            ("/control-center/repairs/{repair_id}/cancel", self.cancel_repair),
            ("/control-center/settings", self.get_settings),
            ("/control-center/settings/update", self.update_setting),
            ("/control-center/settings/reset", self.reset_settings),
        ]
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check endpoint for the control center."""
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "panels": list(self._panels.keys()),
        }
    
    async def list_providers(self) -> Dict[str, Any]:
        """List all registered providers."""
        panel = self._panels.get("providers")
        if panel:
            return await panel.get_status()
        return {"providers": [], "healthy_count": 0}
    
    async def get_providers_status(self) -> Dict[str, Any]:
        """Get detailed provider status."""
        panel = self._panels.get("providers")
        if panel:
            return await panel.get_status()
        return {"providers": [], "healthy_count": 0}
    
    async def get_providers_metrics(self) -> Dict[str, Any]:
        """Get provider metrics."""
        panel = self._panels.get("providers")
        if panel:
            return await panel.get_metrics()
        return {"latency_ms": 0, "error_rate": 0.0}
    
    async def list_agents(self) -> Dict[str, Any]:
        """List all active agents."""
        panel = self._panels.get("agents")
        if panel:
            agents = await panel.get_active_agents()
            return {"agents": agents, "count": len(agents)}
        return {"agents": [], "count": 0}
    
    async def get_agent(self, agent_id: str) -> Dict[str, Any]:
        """Get specific agent details."""
        panel = self._panels.get("agents")
        if panel:
            return await panel.get_agent_state(agent_id)
        return {"error": "Agent not found", "agent_id": agent_id}
    
    async def list_workflows(self) -> Dict[str, Any]:
        """List all active workflows."""
        panel = self._panels.get("workflows")
        if panel:
            workflows = await panel.get_active_workflows()
            return {"workflows": workflows, "count": len(workflows)}
        return {"workflows": [], "count": 0}
    
    async def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Get specific workflow details."""
        panel = self._panels.get("workflows")
        if panel:
            return await panel.get_workflow_status(workflow_id)
        return {"error": "Workflow not found", "workflow_id": workflow_id}
    
    async def list_evidence(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """List evidence items with optional filtering."""
        panel = self._panels.get("evidence")
        if panel:
            items = await panel.list_evidence(filters)
            return {"evidence": items, "count": len(items)}
        return {"evidence": [], "count": 0}
    
    async def get_evidence_item(self, evidence_id: str) -> Dict[str, Any]:
        """Get specific evidence item details."""
        panel = self._panels.get("evidence")
        if panel:
            return await panel.get_evidence(evidence_id)
        return {"error": "Evidence not found", "evidence_id": evidence_id}
    
    async def export_evidence_item(self, evidence_id: str, format: str = "json") -> Dict[str, Any]:
        """Export evidence item in specified format."""
        panel = self._panels.get("evidence")
        if panel:
            return await panel.export_evidence(evidence_id, format)
        return {"error": "Evidence not found", "evidence_id": evidence_id}
    
    async def list_repairs(self) -> Dict[str, Any]:
        """List all repair operations."""
        panel = self._panels.get("repairs")
        if panel:
            return {"repairs": panel.repair_history, "count": len(panel.repair_history)}
        return {"repairs": [], "count": 0}
    
    async def get_repair(self, repair_id: str) -> Dict[str, Any]:
        """Get specific repair operation status."""
        panel = self._panels.get("repairs")
        if panel:
            return await panel.get_repair_status(repair_id)
        return {"error": "Repair not found", "repair_id": repair_id}
    
    async def trigger_repair(self, issue_id: str, repair_type: str) -> Dict[str, Any]:
        """Trigger a new repair operation."""
        panel = self._panels.get("repairs")
        if panel:
            return await panel.trigger_repair(issue_id, repair_type)
        return {"error": "Repair panel not available"}
    
    async def cancel_repair(self, repair_id: str) -> Dict[str, Any]:
        """Cancel an in-progress repair operation."""
        panel = self._panels.get("repairs")
        if panel:
            success = await panel.cancel_repair(repair_id)
            return {"repair_id": repair_id, "cancelled": success}
        return {"error": "Repair not found", "repair_id": repair_id}
    
    async def get_settings(self, category: Optional[str] = None) -> Dict[str, Any]:
        """Get settings, optionally filtered by category."""
        panel = self._panels.get("settings")
        if panel:
            return await panel.get_settings(category)
        return {"settings": {}}
    
    async def update_setting(self, key: str, value: Any) -> Dict[str, Any]:
        """Update a single setting."""
        panel = self._panels.get("settings")
        if panel:
            return await panel.update_setting(key, value)
        return {"error": "Settings panel not available", "key": key}
    
    async def reset_settings(self, category: Optional[str] = None) -> Dict[str, Any]:
        """Reset settings to defaults."""
        panel = self._panels.get("settings")
        if panel:
            return await panel.reset_to_defaults(category)
        return {"error": "Settings panel not available"}


class ProviderPanel:
    """
    Panel for monitoring and managing provider status and health.
    
    Displays provider metrics, connection status, and allows
    configuration of provider priorities and fallbacks.
    """
    
    def __init__(self, provider_router: Optional[Any] = None):
        self.provider_router = provider_router
        self._providers: Dict[str, Dict[str, Any]] = {}
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get current provider status information.
        
        Returns:
            Dictionary containing provider statuses and health counts.
        """
        try:
            providers = []
            healthy_count = 0
            
            if self.provider_router:
                if hasattr(self.provider_router, 'get_all_providers'):
                    providers = await self.provider_router.get_all_providers()
                elif hasattr(self.provider_router, 'providers'):
                    providers = getattr(self.provider_router, 'providers', [])
            
            for provider in providers:
                if isinstance(provider, dict):
                    self._providers[provider.get('id', str(uuid.uuid4()))] = provider
                    if provider.get('status') == 'healthy' or provider.get('state') == 'connected':
                        healthy_count += 1
                elif hasattr(provider, 'id'):
                    provider_id = provider.id
                    status = getattr(provider, 'status', 'unknown')
                    self._providers[provider_id] = {
                        'id': provider_id,
                        'status': status,
                        'name': getattr(provider, 'name', provider_id),
                    }
                    if status in ('healthy', 'connected'):
                        healthy_count += 1
            
            return {
                "providers": list(self._providers.values()),
                "healthy_count": healthy_count,
                "total_count": len(self._providers),
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            return {
                "providers": [],
                "healthy_count": 0,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
    
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get provider performance metrics.
        
        Returns:
            Dictionary containing latency, error rates, and other metrics.
        """
        try:
            total_latency = 0.0
            total_requests = 0
            error_count = 0
            
            for provider in self._providers.values():
                if 'latency_ms' in provider:
                    total_latency += float(provider['latency_ms'])
                if 'request_count' in provider:
                    total_requests += int(provider['request_count'])
                if 'error_count' in provider:
                    error_count += int(provider['error_count'])
            
            avg_latency = total_latency / len(self._providers) if self._providers else 0
            error_rate = error_count / total_requests if total_requests > 0 else 0.0
            
            return {
                "latency_ms": round(avg_latency, 2),
                "error_rate": round(error_rate, 4),
                "total_requests": total_requests,
                "error_count": error_count,
                "provider_count": len(self._providers),
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            return {
                "latency_ms": 0,
                "error_rate": 0.0,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }


class AgentPanel:
    """
    Panel for monitoring active agents and their current tasks.
    
    Displays agent state, active conversations, and task assignments.
    """
    
    def __init__(self):
        self.agents: Dict[str, Any] = {}
    
    async def get_active_agents(self) -> List[Dict[str, Any]]:
        """
        Get list of currently active agents.
        
        Returns:
            List of active agent information dictionaries.
        """
        try:
            active_agents = []
            for agent_id, agent_data in self.agents.items():
                if isinstance(agent_data, dict):
                    status = agent_data.get('status', 'unknown')
                else:
                    status = getattr(agent_data, 'status', 'unknown')
                
                if status in ('running', 'active', 'busy'):
                    active_agents.append({
                        "agent_id": agent_id,
                        "status": status,
                        "data": agent_data if isinstance(agent_data, dict) else {"status": status},
                    })
            
            return active_agents
        except Exception as e:
            return [{"error": str(e)}]
    
    async def get_agent_state(self, agent_id: str) -> Dict[str, Any]:
        """
        Get state information for a specific agent.
        
        Args:
            agent_id: The unique identifier of the agent.
            
        Returns:
            Dictionary containing agent state information.
        """
        try:
            if agent_id in self.agents:
                agent_data = self.agents[agent_id]
                if isinstance(agent_data, dict):
                    return {
                        "agent_id": agent_id,
                        "state": agent_data.get('state', 'unknown'),
                        "status": agent_data.get('status', 'unknown'),
                        "data": agent_data,
                    }
                else:
                    return {
                        "agent_id": agent_id,
                        "state": getattr(agent_data, 'state', 'unknown'),
                        "status": getattr(agent_data, 'status', 'unknown'),
                    }
            
            return {
                "agent_id": agent_id,
                "state": "not_found",
                "status": "unknown",
                "error": "Agent not found in registry",
            }
        except Exception as e:
            return {
                "agent_id": agent_id,
                "state": "error",
                "error": str(e),
            }


class WorkflowPanel:
    """
    Panel for monitoring and managing contract workflows.
    
    Displays active workflows, their current stages, and allows
    intervention in stalled or failed workflows.
    """
    
    def __init__(self):
        self.workflows: Dict[str, Any] = {}
    
    async def get_active_workflows(self) -> List[Dict[str, Any]]:
        """
        Get list of currently active workflows.
        
        Returns:
            List of active workflow information dictionaries.
        """
        try:
            active_workflows = []
            for workflow_id, workflow_data in self.workflows.items():
                if isinstance(workflow_data, dict):
                    status = workflow_data.get('status', 'unknown')
                    phase = workflow_data.get('phase', 'unknown')
                else:
                    status = getattr(workflow_data, 'status', 'unknown')
                    phase = getattr(workflow_data, 'phase', 'unknown')
                
                if status in ('running', 'active', 'pending', 'in_progress'):
                    active_workflows.append({
                        "workflow_id": workflow_id,
                        "status": status,
                        "phase": phase,
                        "data": workflow_data if isinstance(workflow_data, dict) else {"status": status, "phase": phase},
                    })
            
            return active_workflows
        except Exception as e:
            return [{"error": str(e)}]
    
    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get status of a specific workflow.
        
        Args:
            workflow_id: The unique identifier of the workflow.
            
        Returns:
            Dictionary containing workflow status information.
        """
        try:
            if workflow_id in self.workflows:
                workflow_data = self.workflows[workflow_id]
                if isinstance(workflow_data, dict):
                    return {
                        "workflow_id": workflow_id,
                        "phase": workflow_data.get('phase', 'unknown'),
                        "status": workflow_data.get('status', 'unknown'),
                        "data": workflow_data,
                    }
                else:
                    return {
                        "workflow_id": workflow_id,
                        "phase": getattr(workflow_data, 'phase', 'unknown'),
                        "status": getattr(workflow_data, 'status', 'unknown'),
                    }
            
            return {
                "workflow_id": workflow_id,
                "phase": "not_found",
                "status": "unknown",
                "error": "Workflow not found",
            }
        except Exception as e:
            return {
                "workflow_id": workflow_id,
                "phase": "error",
                "error": str(e),
            }


class EvidencePanel:
    """
    Panel for reviewing and managing collected evidence.
    
    Displays evidence artifacts, their validation status, and
    allows export or deletion of evidence items.
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path
        self.evidence_items: Dict[str, Any] = {}
    
    async def list_evidence(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        List evidence items with optional filtering.
        
        Args:
            filters: Optional dictionary of filter criteria.
            
        Returns:
            List of evidence item dictionaries matching the filters.
        """
        try:
            filters = filters or {}
            filtered_items = []
            
            for evidence_id, evidence_data in self.evidence_items.items():
                match = True
                
                if 'type' in filters:
                    item_type = evidence_data.get('type') if isinstance(evidence_data, dict) else getattr(evidence_data, 'type', None)
                    if item_type != filters['type']:
                        match = False
                
                if 'status' in filters:
                    item_status = evidence_data.get('status') if isinstance(evidence_data, dict) else getattr(evidence_data, 'status', None)
                    if item_status != filters['status']:
                        match = False
                
                if 'source' in filters:
                    item_source = evidence_data.get('source') if isinstance(evidence_data, dict) else getattr(evidence_data, 'source', None)
                    if item_source != filters['source']:
                        match = False
                
                if match:
                    if isinstance(evidence_data, dict):
                        filtered_items.append({
                            "evidence_id": evidence_id,
                            "type": evidence_data.get('type', 'unknown'),
                            "status": evidence_data.get('status', 'unknown'),
                            "source": evidence_data.get('source', 'unknown'),
                            "created_at": evidence_data.get('created_at', datetime.utcnow().isoformat()),
                        })
                    else:
                        filtered_items.append({
                            "evidence_id": evidence_id,
                            "type": getattr(evidence_data, 'type', 'unknown'),
                            "status": getattr(evidence_data, 'status', 'unknown'),
                            "source": getattr(evidence_data, 'source', 'unknown'),
                            "created_at": getattr(evidence_data, 'created_at', datetime.utcnow().isoformat()),
                        })
            
            return filtered_items
        except Exception as e:
            return [{"error": str(e)}]
    
    async def get_evidence(self, evidence_id: str) -> Dict[str, Any]:
        """
        Get detailed information for a specific evidence item.
        
        Args:
            evidence_id: The unique identifier of the evidence item.
            
        Returns:
            Dictionary containing evidence details.
        """
        try:
            if evidence_id in self.evidence_items:
                evidence_data = self.evidence_items[evidence_id]
                if isinstance(evidence_data, dict):
                    return {
                        "evidence_id": evidence_id,
                        "content": evidence_data.get('content', {}),
                        "type": evidence_data.get('type', 'unknown'),
                        "status": evidence_data.get('status', 'unknown'),
                        "metadata": evidence_data.get('metadata', {}),
                    }
                else:
                    return {
                        "evidence_id": evidence_id,
                        "content": getattr(evidence_data, 'content', {}),
                        "type": getattr(evidence_data, 'type', 'unknown'),
                        "status": getattr(evidence_data, 'status', 'unknown'),
                        "metadata": getattr(evidence_data, 'metadata', {}),
                    }
            
            return {
                "evidence_id": evidence_id,
                "error": "Evidence not found",
            }
        except Exception as e:
            return {
                "evidence_id": evidence_id,
                "error": str(e),
            }
    
    async def export_evidence(self, evidence_id: str, format: str = "json") -> Dict[str, Any]:
        """
        Export evidence in the specified format.
        
        Args:
            evidence_id: The unique identifier of the evidence item.
            format: The export format (json, csv, pdf).
            
        Returns:
            Dictionary containing export status and path.
        """
        try:
            if evidence_id not in self.evidence_items:
                return {
                    "evidence_id": evidence_id,
                    "error": "Evidence not found",
                }
            
            evidence_data = self.evidence_items[evidence_id]
            content = evidence_data.get('content', {}) if isinstance(evidence_data, dict) else getattr(evidence_data, 'content', {})
            
            export_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().isoformat().replace(':', '-')
            
            if format == "json":
                export_filename = f"evidence_{evidence_id}_{timestamp}.json"
                export_path = f"{self.storage_path or '/tmp'}/{export_filename}"
                try:
                    with open(export_path, 'w', encoding='utf-8') as f:
                        json.dump({"evidence_id": evidence_id, "content": content, "exported_at": timestamp}, f, indent=2)
                except Exception:
                    pass
                return {
                    "export_path": export_path,
                    "format": format,
                    "evidence_id": evidence_id,
                    "export_id": export_id,
                }
            
            elif format == "csv":
                export_filename = f"evidence_{evidence_id}_{timestamp}.csv"
                export_path = f"{self.storage_path or '/tmp'}/{export_filename}"
                try:
                    with open(export_path, 'w', encoding='utf-8') as f:
                        if isinstance(content, dict):
                            for key, value in content.items():
                                f.write(f"{key},{value}\n")
                        elif isinstance(content, list):
                            for item in content:
                                f.write(f"{item}\n")
                except Exception:
                    pass
                return {
                    "export_path": export_path,
                    "format": format,
                    "evidence_id": evidence_id,
                    "export_id": export_id,
                }
            
            elif format == "pdf":
                export_filename = f"evidence_{evidence_id}_{timestamp}.pdf"
                export_path = f"{self.storage_path or '/tmp'}/{export_filename}"
                return {
                    "export_path": export_path,
                    "format": format,
                    "evidence_id": evidence_id,
                    "export_id": export_id,
                    "note": "PDF export requires additional library",
                }
            
            return {
                "evidence_id": evidence_id,
                "error": f"Unsupported format: {format}",
            }
        except Exception as e:
            return {
                "evidence_id": evidence_id,
                "error": str(e),
            }


class RepairPanel:
    """
    Panel for managing automated repair workflows.
    
    Displays repair history, success rates, and allows triggering
    or cancelling repair operations.
    """
    
    def __init__(self, repair_router: Optional[Any] = None):
        self.repair_router = repair_router
        self.repair_history: List[Dict[str, Any]] = []
        self._active_repairs: Dict[str, Dict[str, Any]] = {}
    
    async def get_repair_status(self, repair_id: str) -> Dict[str, Any]:
        """
        Get status of a specific repair operation.
        
        Args:
            repair_id: The unique identifier of the repair operation.
            
        Returns:
            Dictionary containing repair status information.
        """
        try:
            for repair in self.repair_history:
                if repair.get('repair_id') == repair_id:
                    return {
                        "repair_id": repair_id,
                        "status": repair.get('status', 'unknown'),
                        "repair_type": repair.get('repair_type', 'unknown'),
                        "issue_id": repair.get('issue_id', 'unknown'),
                        "started_at": repair.get('started_at'),
                        "completed_at": repair.get('completed_at'),
                    }
            
            if repair_id in self._active_repairs:
                return {
                    "repair_id": repair_id,
                    "status": self._active_repairs[repair_id].get('status', 'running'),
                    "progress": self._active_repairs[repair_id].get('progress', 0),
                }
            
            return {
                "repair_id": repair_id,
                "status": "not_found",
                "error": "Repair operation not found",
            }
        except Exception as e:
            return {
                "repair_id": repair_id,
                "status": "error",
                "error": str(e),
            }
    
    async def trigger_repair(self, issue_id: str, repair_type: str) -> Dict[str, Any]:
        """
        Trigger a repair operation for a given issue.
        
        Args:
            issue_id: The identifier of the issue to repair.
            repair_type: The type of repair to perform.
            
        Returns:
            Dictionary containing the new repair information.
        """
        try:
            repair_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().isoformat()
            
            new_repair = {
                "repair_id": repair_id,
                "issue_id": issue_id,
                "repair_type": repair_type,
                "status": "pending",
                "started_at": timestamp,
                "completed_at": None,
            }
            
            self.repair_history.insert(0, new_repair)
            self._active_repairs[repair_id] = {
                "status": "running",
                "progress": 0,
                "repair": new_repair,
            }
            
            if self.repair_router and hasattr(self.repair_router, 'trigger_repair'):
                try:
                    result = await self.repair_router.trigger_repair(issue_id, repair_type)
                    if isinstance(result, dict):
                        new_repair.update(result)
                except Exception:
                    pass
            
            return {
                "repair_id": repair_id,
                "issue_id": issue_id,
                "repair_type": repair_type,
                "status": "triggered",
            }
        except Exception as e:
            return {
                "error": str(e),
                "issue_id": issue_id,
                "repair_type": repair_type,
            }
    
    async def cancel_repair(self, repair_id: str) -> bool:
        """
        Cancel an in-progress repair operation.
        
        Args:
            repair_id: The unique identifier of the repair operation.
            
        Returns:
            True if the repair was cancelled, False otherwise.
        """
        try:
            for repair in self.repair_history:
                if repair.get('repair_id') == repair_id and repair.get('status') in ('pending', 'running'):
                    repair['status'] = 'cancelled'
                    repair['completed_at'] = datetime.utcnow().isoformat()
                    
                    if repair_id in self._active_repairs:
                        self._active_repairs[repair_id]['status'] = 'cancelled'
                    
                    if self.repair_router and hasattr(self.repair_router, 'cancel_repair'):
                        try:
                            await self.repair_router.cancel_repair(repair_id)
                        except Exception:
                            pass
                    
                    return True
            
            if repair_id in self._active_repairs:
                self._active_repairs[repair_id]['status'] = 'cancelled'
                return True
            
            return False
        except Exception:
            return False


class SettingsPanel:
    """
    Panel for managing application settings and configuration.
    
    Provides UI for viewing and modifying runtime settings,
    provider configurations, and system preferences.
    Supports auto-fill, settings profiles, and agent-accessible APIs.
    """
    
    # Default settings profiles
    PROFILES = {
        "development": {
            "environment": "development",
            "debug": True,
            "timeout_seconds": 120,
            "max_retries": 3,
        },
        "production": {
            "environment": "production",
            "debug": False,
            "timeout_seconds": 300,
            "max_retries": 5,
        },
        "testing": {
            "environment": "testing",
            "debug": True,
            "timeout_seconds": 30,
            "max_retries": 1,
        },
    }
    
    def __init__(self, settings_api: Optional[Any] = None):
        self.settings_api = settings_api
        self._settings: Dict[str, Any] = {}
        self._defaults: Dict[str, Any] = {}
        self._profiles: Dict[str, Dict[str, Any]] = self.PROFILES.copy()
        self._autofill_enabled: bool = True
    
    async def get_settings(self, category: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all current settings, optionally filtered by category.
        
        Args:
            category: Optional category to filter settings.
            
        Returns:
            Dictionary containing settings.
        """
        try:
            if self.settings_api:
                if hasattr(self.settings_api, 'get_settings'):
                    if category:
                        return await self.settings_api.get_settings(category)
                    return await self.settings_api.get_settings()
                elif hasattr(self.settings_api, 'settings'):
                    settings = getattr(self.settings_api, 'settings', {})
                    if category:
                        return {category: settings.get(category, {})}
                    return {"settings": settings}
            
            if category:
                return {category: self._settings.get(category, {})}
            
            return {"settings": self._settings}
        except Exception as e:
            return {
                "settings": {},
                "error": str(e),
            }
    
    async def update_setting(self, key: str, value: Any) -> Dict[str, Any]:
        """
        Update a specific setting value.
        
        Args:
            key: The setting key to update.
            value: The new value for the setting.
            
        Returns:
            Dictionary confirming the update.
        """
        try:
            if self.settings_api and hasattr(self.settings_api, 'update_setting'):
                result = await self.settings_api.update_setting(key, value)
                if isinstance(result, dict):
                    return result
            
            keys = key.split('.')
            if len(keys) > 1:
                category = keys[0]
                setting_key = '.'.join(keys[1:])
                if category not in self._settings:
                    self._settings[category] = {}
                self._settings[category][setting_key] = value
            else:
                self._settings[key] = value
            
            return {
                "key": key,
                "value": value,
                "status": "updated",
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            return {
                "key": key,
                "error": str(e),
                "status": "failed",
            }
    
    async def reset_to_defaults(self, category: Optional[str] = None) -> Dict[str, Any]:
        """
        Reset settings to default values.
        
        Args:
            category: Optional category to reset. If None, resets all.
            
        Returns:
            Dictionary confirming the reset operation.
        """
        try:
            if self.settings_api and hasattr(self.settings_api, 'reset_to_defaults'):
                result = await self.settings_api.reset_to_defaults(category)
                if isinstance(result, dict):
                    return result
            
            if category:
                if category in self._settings:
                    del self._settings[category]
                if category in self._defaults:
                    self._settings[category] = self._defaults[category].copy()
                return {
                    "status": "reset",
                    "category": category,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            
            self._settings = self._defaults.copy() if self._defaults else {}
            return {
                "status": "reset",
                "category": None,
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
            }
    
    # ============================================================
    # Auto-fill Settings Integration
    # ============================================================
    
    async def auto_fill_settings(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Auto-fill settings based on context (platform, task type, etc.).
        
        This method integrates with SettingsAutofill to provide
        intelligent auto-completion of settings.
        
        Args:
            context: Context with platform, task_type, profile, etc.
            
        Returns:
            Auto-filled settings with metadata.
        """
        try:
            from src.kilocode.runtime_sync import SettingsAutofill
            
            autofill = SettingsAutofill(runtime_sync=None)
            result = await autofill.auto_complete_settings(self._settings, context)
            
            # Update internal settings
            self._settings = result.get("settings", self._settings)
            
            return {
                "settings": self._settings,
                "auto_filled": result.get("applied", 0),
                "auto_filled_keys": result.get("auto_filled_keys", []),
                "explicit_keys": result.get("explicit_keys", []),
                "status": "completed",
            }
        except Exception as e:
            return {
                "settings": self._settings,
                "error": str(e),
                "status": "failed",
            }
    
    async def apply_profile(self, profile_name: str) -> Dict[str, Any]:
        """
        Apply a settings profile (development, production, testing).
        
        Args:
            profile_name: Name of the profile to apply.
            
        Returns:
            Updated settings after applying profile.
        """
        if profile_name not in self._profiles:
            return {
                "status": "error",
                "error": f"Unknown profile: {profile_name}",
                "available_profiles": list(self._profiles.keys()),
            }
        
        profile = self._profiles[profile_name]
        updated = {}
        
        for key, value in profile.items():
            await self.update_setting(key, value)
            updated[key] = value
        
        return {
            "status": "applied",
            "profile": profile_name,
            "applied_settings": updated,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    def get_available_profiles(self) -> List[Dict[str, Any]]:
        """Get list of available settings profiles."""
        return [
            {"name": name, "settings": settings}
            for name, settings in self._profiles.items()
        ]
    
    async def add_custom_profile(self, name: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a custom settings profile.
        
        Args:
            name: Profile name.
            settings: Profile settings.
            
        Returns:
            Confirmation of profile creation.
        """
        self._profiles[name] = settings
        return {
            "status": "created",
            "profile": name,
            "settings": settings,
        }
    
    # ============================================================
    # Agent-Accessible Settings Endpoints
    # ============================================================
    
    async def agent_complete_settings(self, agent_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Agent-accessible endpoint for completing settings.
        
        Agents can call this to auto-complete settings for users
        based on the current context.
        
        Args:
            agent_id: ID of the agent making the request.
            context: Context for auto-fill decisions.
            
        Returns:
            Complete settings ready for use.
        """
        result = await self.auto_fill_settings(context)
        result["agent_id"] = agent_id
        result["completed_by"] = "agent"
        return result
    
    async def agent_update_setting(self, agent_id: str, key: str, value: Any) -> Dict[str, Any]:
        """
        Agent-accessible endpoint for updating a setting.
        
        Args:
            agent_id: ID of the agent making the request.
            key: Setting key to update.
            value: New value.
            
        Returns:
            Update confirmation.
        """
        result = await self.update_setting(key, value)
        result["agent_id"] = agent_id
        result["updated_by"] = "agent"
        return result
    
    async def agent_batch_update(self, agent_id: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Agent-accessible batch update of settings.
        
        Args:
            agent_id: ID of the agent making the request.
            settings: Dictionary of settings to update.
            
        Returns:
            Batch update results.
        """
        results = []
        for key, value in settings.items():
            result = await self.update_setting(key, value)
            results.append({"key": key, "status": result.get("status"), "error": result.get("error")})
        
        return {
            "agent_id": agent_id,
            "updated_by": "agent",
            "results": results,
            "success_count": sum(1 for r in results if r.get("status") == "updated"),
            "failure_count": sum(1 for r in results if r.get("error")),
        }
    
    # ============================================================
    # Settings Validation
    # ============================================================
    
    async def validate_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate settings against expected schema.
        
        Args:
            settings: Settings to validate.
            
        Returns:
            Validation results with any errors.
        """
        errors = []
        warnings = []
        
        # Check required provider settings
        if "providers" not in settings:
            errors.append("Missing required section: providers")
        else:
            providers = settings["providers"]
            if "minimax" not in providers:
                warnings.append("MiniMax provider not configured")
            if "anthropic" not in providers:
                warnings.append("Anthropic provider not configured")
        
        # Check automation settings
        if "automation" in settings:
            auto = settings["automation"]
            if "max_concurrent_tasks" in auto:
                if auto["max_concurrent_tasks"] > 256:
                    errors.append("max_concurrent_tasks exceeds maximum (256)")
            if "retry_attempts" in auto:
                if auto["retry_attempts"] > 10:
                    warnings.append("retry_attempts is very high (max 10)")
        
        # Check modes settings
        if "modes" in settings:
            modes = settings["modes"]
            if "allowed_modes" not in modes:
                errors.append("Missing required field: modes.allowed_modes")
            if "default_mode" not in modes:
                errors.append("Missing required field: modes.default_mode")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "settings_count": len(settings),
        }
    
    # ============================================================
    # Settings Import/Export
    # ============================================================
    
    async def export_settings(self) -> Dict[str, Any]:
        """
        Export current settings as a portable dictionary.
        
        Returns:
            Exportable settings with metadata.
        """
        return {
            "settings": self._settings,
            "profiles": self._profiles,
            "exported_at": datetime.utcnow().isoformat(),
            "version": "1.0",
        }
    
    async def import_settings(self, data: Dict[str, Any], merge: bool = True) -> Dict[str, Any]:
        """
        Import settings from exported data.
        
        Args:
            data: Exported settings data.
            merge: If True, merge with existing; if False, replace.
            
        Returns:
            Import results.
        """
        try:
            settings = data.get("settings", {})
            profiles = data.get("profiles", {})
            
            if merge:
                # Deep merge
                for key, value in settings.items():
                    if key in self._settings and isinstance(self._settings[key], dict) and isinstance(value, dict):
                        self._settings[key].update(value)
                    else:
                        self._settings[key] = value
            else:
                self._settings = settings
            
            # Import profiles
            if profiles:
                self._profiles.update(profiles)
            
            return {
                "status": "imported",
                "settings_count": len(self._settings),
                "profiles_count": len(self._profiles),
                "merge": merge,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }
    
    # ============================================================
    # Missing Settings Detection
    # ============================================================
    
    async def get_missing_settings(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get list of settings that should be configured.
        
        Analyzes context and returns settings that are missing
        or need attention.
        
        Args:
            context: Current context for auto-fill analysis.
            
        Returns:
            Missing settings with suggestions.
        """
        from src.kilocode.runtime_sync import SettingsAutofill
        
        autofill = SettingsAutofill(runtime_sync=None)
        suggestions = await autofill.get_autofill_suggestions(context)
        
        missing = []
        for suggestion in suggestions.get("suggestions", []):
            key = suggestion.get("key")
            if key not in self._settings or self._settings.get(key) is None:
                missing.append({
                    "key": key,
                    "suggested_value": suggestion.get("value"),
                    "reason": suggestion.get("reason"),
                    "priority": "high" if suggestion.get("reason", "").startswith("Required") else "normal",
                })
        
        return {
            "missing_count": len(missing),
            "missing_settings": missing,
            "context": context,
        }
