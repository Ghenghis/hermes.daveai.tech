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
                "total_count": len(self._providers)
            }
        except Exception as e:
            return {"providers": [], "healthy_count": 0, "error": str(e)}
    
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get provider metrics.
        
        Returns:
            Dictionary containing latency and error rate metrics.
        """
        try:
            latency_ms = 0
            error_rate = 0.0
            
            if self.provider_router and hasattr(self.provider_router, 'get_metrics'):
                metrics = await self.provider_router.get_metrics()
                latency_ms = metrics.get('latency_ms', 0)
                error_rate = metrics.get('error_rate', 0.0)
            
            return {
                "latency_ms": latency_ms,
                "error_rate": error_rate,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {"latency_ms": 0, "error_rate": 0.0, "error": str(e)}


class AgentPanel:
    """
    Panel for monitoring and managing agent status.
    
    Displays agent health, task queues, and performance metrics.
    """
    
    def __init__(self, orchestrator: Optional[Any] = None):
        self.orchestrator = orchestrator
        self._agents: Dict[str, Dict[str, Any]] = {}
    
    async def get_active_agents(self) -> List[Dict[str, Any]]:
        """
        Get list of active agents.
        
        Returns:
            List of agent status dictionaries.
        """
        try:
            agents = []
            
            if self.orchestrator:
                if hasattr(self.orchestrator, 'get_agents'):
                    agents = await self.orchestrator.get_agents()
                elif hasattr(self.orchestrator, 'agents'):
                    agents = getattr(self.orchestrator, 'agents', [])
            
            for agent in agents:
                if isinstance(agent, dict):
                    agent_id = agent.get('id', str(uuid.uuid4()))
                    self._agents[agent_id] = agent
                elif hasattr(agent, 'id'):
                    agent_id = agent.id
                    self._agents[agent_id] = {
                        'id': agent_id,
                        'status': getattr(agent, 'status', 'unknown'),
                        'name': getattr(agent, 'name', agent_id),
                    }
            
            return list(self._agents.values())
        except Exception as e:
            return []
    
    async def get_agent_state(self, agent_id: str) -> Dict[str, Any]:
        """
        Get state of a specific agent.
        
        Args:
            agent_id: Agent identifier.
            
        Returns:
            Agent state dictionary.
        """
        try:
            if agent_id in self._agents:
                return self._agents[agent_id]
            
            if self.orchestrator and hasattr(self.orchestrator, 'get_agent'):
                return await self.orchestrator.get_agent(agent_id)
            
            return {"error": "Agent not found", "agent_id": agent_id}
        except Exception as e:
            return {"error": str(e), "agent_id": agent_id}


class WorkflowPanel:
    """
    Panel for monitoring and managing workflows.
    
    Displays workflow status, task progress, and completion rates.
    """
    
    def __init__(self, orchestrator: Optional[Any] = None):
        self.orchestrator = orchestrator
        self._workflows: Dict[str, Dict[str, Any]] = {}
    
    async def get_active_workflows(self) -> List[Dict[str, Any]]:
        """
        Get list of active workflows.
        
        Returns:
            List of workflow status dictionaries.
        """
        try:
            workflows = []
            
            if self.orchestrator:
                if hasattr(self.orchestrator, 'get_workflows'):
                    workflows = await self.orchestrator.get_workflows()
                elif hasattr(self.orchestrator, 'workflows'):
                    workflows = getattr(self.orchestrator, 'workflows', [])
            
            for workflow in workflows:
                if isinstance(workflow, dict):
                    workflow_id = workflow.get('id', str(uuid.uuid4()))
                    self._workflows[workflow_id] = workflow
                elif hasattr(workflow, 'id'):
                    workflow_id = workflow.id
                    self._workflows[workflow_id] = {
                        'id': workflow_id,
                        'status': getattr(workflow, 'status', 'unknown'),
                        'name': getattr(workflow, 'name', workflow_id),
                    }
            
            return list(self._workflows.values())
        except Exception as e:
            return []
    
    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get status of a specific workflow.
        
        Args:
            workflow_id: Workflow identifier.
            
        Returns:
            Workflow status dictionary.
        """
        try:
            if workflow_id in self._workflows:
                return self._workflows[workflow_id]
            
            if self.orchestrator and hasattr(self.orchestrator, 'get_workflow'):
                return await self.orchestrator.get_workflow(workflow_id)
            
            return {"error": "Workflow not found", "workflow_id": workflow_id}
        except Exception as e:
            return {"error": str(e), "workflow_id": workflow_id}


class EvidencePanel:
    """
    Panel for managing evidence collection and review.
    
    Displays evidence artifacts, metadata, and export capabilities.
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path
        self._evidence: Dict[str, Dict[str, Any]] = {}
    
    async def list_evidence(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        List evidence items with optional filtering.
        
        Args:
            filters: Optional filter dictionary.
            
        Returns:
            List of evidence dictionaries.
        """
        try:
            evidence_list = list(self._evidence.values())
            
            if filters:
                if 'contract_id' in filters:
                    evidence_list = [e for e in evidence_list if e.get('contract_id') == filters['contract_id']]
                if 'type' in filters:
                    evidence_list = [e for e in evidence_list if e.get('type') == filters['type']]
                if 'date_from' in filters:
                    evidence_list = [e for e in evidence_list if e.get('timestamp', 0) >= filters['date_from']]
            
            return evidence_list
        except Exception as e:
            return []
    
    async def get_evidence(self, evidence_id: str) -> Dict[str, Any]:
        """
        Get specific evidence item.
        
        Args:
            evidence_id: Evidence identifier.
            
        Returns:
            Evidence dictionary.
        """
        try:
            if evidence_id in self._evidence:
                return self._evidence[evidence_id]
            
            return {"error": "Evidence not found", "evidence_id": evidence_id}
        except Exception as e:
            return {"error": str(e), "evidence_id": evidence_id}
    
    async def export_evidence(self, evidence_id: str, format: str = "json") -> Dict[str, Any]:
        """
        Export evidence in specified format.
        
        Args:
            evidence_id: Evidence identifier.
            format: Export format (json, csv, pdf).
            
        Returns:
            Export result dictionary.
        """
        try:
            evidence = await self.get_evidence(evidence_id)
            
            if "error" in evidence:
                return evidence
            
            if format == "json":
                return {
                    "format": "json",
                    "data": evidence,
                    "evidence_id": evidence_id,
                }
            elif format == "csv":
                return {
                    "format": "csv",
                    "data": json.dumps(evidence),
                    "evidence_id": evidence_id,
                }
            elif format == "pdf":
                export_id = str(uuid.uuid4())
                export_filename = f"evidence_{evidence_id}_{export_id}.pdf"
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
    """
    
    def __init__(self, settings_api: Optional[Any] = None):
        self.settings_api = settings_api
        self._settings: Dict[str, Any] = {}
        self._defaults: Dict[str, Any] = {}
    
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
