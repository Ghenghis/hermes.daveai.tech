"""
Agents Panel - Comprehensive agent management for WebUI.

Provides separate panels for ZeroClaw agents and Hermes agents,
each with their own profiles, configurations, and monitoring.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum


class AgentType(Enum):
    """Agent type classification."""
    ZEROCLAW = "zeroclaw"
    HERMES = "hermes"


class AgentStatus(Enum):
    """Agent status states."""
    IDLE = "idle"
    ACTIVE = "active"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"


class AgentProfile:
    """
    Agent profile with configuration and metadata.
    
    Defines an agent's capabilities, settings, and runtime info.
    """
    
    def __init__(
        self,
        agent_id: str,
        agent_type: AgentType,
        name: str,
        role: str,
        description: str = "",
        capabilities: List[str] = None,
        config: Dict[str, Any] = None
    ):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.name = name
        self.role = role
        self.description = description
        self.capabilities = capabilities or []
        self.config = config or {}
        self.status = AgentStatus.IDLE
        self.last_active = None
        self.task_count = 0
        self.error_count = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary."""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type.value,
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "capabilities": self.capabilities,
            "config": self.config,
            "status": self.status.value,
            "last_active": self.last_active.isoformat() if self.last_active else None,
            "task_count": self.task_count,
            "error_count": self.error_count,
        }


class ZeroClawAgentsPanel:
    """
    Panel for managing ZeroClaw adapter agents.
    
    Handles Git, Shell, Filesystem, and Research adapters
    as individual agents with their own profiles.
    """
    
    def __init__(self):
        self.agents: Dict[str, AgentProfile] = {}
        self._initialize_default_agents()
    
    def _initialize_default_agents(self):
        """Initialize default ZeroClaw agent profiles."""
        
        # Git Adapter Agent
        self.register_agent(AgentProfile(
            agent_id="zeroclaw-git-01",
            agent_type=AgentType.ZEROCLAW,
            name="Git Adapter",
            role="Version Control Specialist",
            description="Handles Git operations: clone, commit, push, pull, branch management",
            capabilities=[
                "git_clone", "git_commit", "git_push", "git_pull",
                "git_branch", "git_merge", "git_status", "git_log"
            ],
            config={
                "auto_commit": False,
                "sign_commits": True,
                "default_branch": "main",
            }
        ))
        
        # Shell Adapter Agent
        self.register_agent(AgentProfile(
            agent_id="zeroclaw-shell-01",
            agent_type=AgentType.ZEROCLAW,
            name="Shell Adapter",
            role="Command Execution Specialist",
            description="Executes shell commands and manages command pipelines",
            capabilities=[
                "run_command", "stream_command", "pipe_commands",
                "background_process", "process_management"
            ],
            config={
                "timeout_seconds": 300,
                "max_output_size": 1000000,
                "allow_sudo": False,
            }
        ))
        
        # Filesystem Adapter Agent
        self.register_agent(AgentProfile(
            agent_id="zeroclaw-fs-01",
            agent_type=AgentType.ZEROCLAW,
            name="Filesystem Adapter",
            role="File Operations Specialist",
            description="Handles file operations: read, write, copy, move, delete",
            capabilities=[
                "read_file", "write_file", "copy_file", "move_file",
                "delete_file", "list_directory", "create_directory",
                "file_search", "file_watch"
            ],
            config={
                "max_file_size": 100_000_000,  # 100MB
                "allowed_extensions": [".py", ".js", ".ts", ".json", ".md", ".txt", ".yaml", ".yml"],
                "backup_on_write": True,
            }
        ))
        
        # Research Adapter Agent
        self.register_agent(AgentProfile(
            agent_id="zeroclaw-research-01",
            agent_type=AgentType.ZEROCLAW,
            name="Research Adapter",
            role="Information Gathering Specialist",
            description="Performs web research and information gathering",
            capabilities=[
                "web_search", "scrape_page", "extract_data",
                "analyze_content", "summarize_text", "fact_check"
            ],
            config={
                "search_engine": "duckduckgo",
                "max_results": 10,
                "timeout_seconds": 60,
            }
        ))
    
    def register_agent(self, profile: AgentProfile) -> bool:
        """
        Register a new agent profile.
        
        Args:
            profile: AgentProfile to register
            
        Returns:
            True if registered successfully
        """
        if profile.agent_id in self.agents:
            return False
        
        self.agents[profile.agent_id] = profile
        return True
    
    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent."""
        if agent_id in self.agents:
            del self.agents[agent_id]
            return True
        return False
    
    async def get_agents(self, status: Optional[AgentStatus] = None) -> List[Dict[str, Any]]:
        """
        Get all ZeroClaw agents, optionally filtered by status.
        
        Args:
            status: Filter by status (optional)
            
        Returns:
            List of agent profile dictionaries
        """
        agents = []
        for profile in self.agents.values():
            if status is None or profile.status == status:
                agents.append(profile.to_dict())
        return agents
    
    async def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get specific agent profile."""
        profile = self.agents.get(agent_id)
        return profile.to_dict() if profile else None
    
    async def update_agent_config(self, agent_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update agent configuration."""
        profile = self.agents.get(agent_id)
        if not profile:
            return {"error": "Agent not found", "agent_id": agent_id}
        
        profile.config.update(config)
        return {"success": True, "agent_id": agent_id, "config": profile.config}
    
    async def get_agent_metrics(self) -> Dict[str, Any]:
        """Get metrics for all ZeroClaw agents."""
        total = len(self.agents)
        active = sum(1 for a in self.agents.values() if a.status == AgentStatus.ACTIVE)
        idle = sum(1 for a in self.agents.values() if a.status == AgentStatus.IDLE)
        errors = sum(a.error_count for a in self.agents.values())
        tasks = sum(a.task_count for a in self.agents.values())
        
        return {
            "total_agents": total,
            "active": active,
            "idle": idle,
            "error_count": errors,
            "total_tasks": tasks,
            "agents": [a.to_dict() for a in self.agents.values()],
        }


class HermesAgentsPanel:
    """
    Panel for managing Hermes orchestration agents.
    
    Handles the 5 Hermes agents (H1-H5) each with unique roles:
    - H1: Planning Strategist
    - H2: Creative Brainstormer
    - H3: System Architect
    - H4: Bug Triage Specialist
    - H5: Root Cause Analyst
    """
    
    def __init__(self):
        self.agents: Dict[str, AgentProfile] = {}
        self._initialize_hermes_agents()
    
    def _initialize_hermes_agents(self):
        """Initialize the 5 Hermes agent profiles."""
        
        # H1: Planning Strategist
        self.register_agent(AgentProfile(
            agent_id="hermes-h1",
            agent_type=AgentType.HERMES,
            name="Hermes H1",
            role="Planning Strategist",
            description="Long-term planning, roadmaps, milestone definition, resource allocation",
            capabilities=[
                "strategic_planning", "roadmap_creation", "milestone_definition",
                "resource_allocation", "timeline_estimation", "risk_assessment"
            ],
            config={
                "discord_channel": "#general",
                "personality": "analytical",
                "planning_horizon": "quarterly",
            }
        ))
        
        # H2: Creative Brainstormer
        self.register_agent(AgentProfile(
            agent_id="hermes-h2",
            agent_type=AgentType.HERMES,
            name="Hermes H2",
            role="Creative Brainstormer",
            description="Idea generation, feature exploration, creative problem solving",
            capabilities=[
                "brainstorming", "idea_generation", "feature_exploration",
                "creative_solutions", "innovation_workshop", "design_thinking"
            ],
            config={
                "discord_channel": "#planning",
                "personality": "creative",
                "idea_output_mode": "divergent",
            }
        ))
        
        # H3: System Architect
        self.register_agent(AgentProfile(
            agent_id="hermes-h3",
            agent_type=AgentType.HERMES,
            name="Hermes H3",
            role="System Architect",
            description="Architecture design, component relationships, technical standards",
            capabilities=[
                "architecture_design", "system_modeling", "component_mapping",
                "api_design", "technical_standards", "integration_planning"
            ],
            config={
                "discord_channel": "#design",
                "personality": "structured",
                "architecture_style": "modular",
            }
        ))
        
        # H4: Bug Triage Specialist
        self.register_agent(AgentProfile(
            agent_id="hermes-h4",
            agent_type=AgentType.HERMES,
            name="Hermes H4",
            role="Bug Triage Specialist",
            description="Issue classification, severity assessment, assignment routing",
            capabilities=[
                "bug_triage", "severity_assessment", "issue_classification",
                "assignment_routing", "priority_scoring", "duplicate_detection"
            ],
            config={
                "discord_channel": "#issues",
                "personality": "detail-oriented",
                "auto_assign": True,
            }
        ))
        
        # H5: Root Cause Analyst
        self.register_agent(AgentProfile(
            agent_id="hermes-h5",
            agent_type=AgentType.HERMES,
            name="Hermes H5",
            role="Root Cause Analyst",
            description="Deep analysis of problems, identifying underlying causes",
            capabilities=[
                "root_cause_analysis", "fishbone_analysis", "five_whys",
                "pattern_analysis", "anomaly_detection", "correlation_analysis"
            ],
            config={
                "discord_channel": "#problems",
                "personality": "investigative",
                "analysis_depth": "comprehensive",
            }
        ))
    
    def register_agent(self, profile: AgentProfile) -> bool:
        """Register a Hermes agent profile."""
        if profile.agent_id in self.agents:
            return False
        
        self.agents[profile.agent_id] = profile
        return True
    
    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister a Hermes agent."""
        if agent_id in self.agents:
            del self.agents[agent_id]
            return True
        return False
    
    async def get_agents(self, status: Optional[AgentStatus] = None) -> List[Dict[str, Any]]:
        """
        Get all Hermes agents, optionally filtered by status.
        
        Args:
            status: Filter by status (optional)
            
        Returns:
            List of agent profile dictionaries
        """
        agents = []
        for profile in self.agents.values():
            if status is None or profile.status == status:
                agents.append(profile.to_dict())
        return agents
    
    async def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get specific Hermes agent profile."""
        profile = self.agents.get(agent_id)
        return profile.to_dict() if profile else None
    
    async def update_agent_config(self, agent_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update Hermes agent configuration."""
        profile = self.agents.get(agent_id)
        if not profile:
            return {"error": "Agent not found", "agent_id": agent_id}
        
        profile.config.update(config)
        return {"success": True, "agent_id": agent_id, "config": profile.config}
    
    async def get_discord_assignments(self) -> Dict[str, Any]:
        """Get Discord channel assignments for Hermes agents."""
        assignments = {}
        for profile in self.agents.values():
            assignments[profile.agent_id] = {
                "name": profile.name,
                "role": profile.role,
                "discord_channel": profile.config.get("discord_channel", "#general"),
                "personality": profile.config.get("personality", "default"),
            }
        return {
            "guild_id": "1490068195208331334",
            "assignments": assignments,
        }
    
    async def get_agent_metrics(self) -> Dict[str, Any]:
        """Get metrics for all Hermes agents."""
        total = len(self.agents)
        active = sum(1 for a in self.agents.values() if a.status == AgentStatus.ACTIVE)
        idle = sum(1 for a in self.agents.values() if a.status == AgentStatus.IDLE)
        errors = sum(a.error_count for a in self.agents.values())
        tasks = sum(a.task_count for a in self.agents.values())
        
        return {
            "total_agents": total,
            "active": active,
            "idle": idle,
            "error_count": errors,
            "total_tasks": tasks,
            "agents": [a.to_dict() for a in self.agents.values()],
        }


class AgentsManager:
    """
    Unified manager for all agent panels.
    
    Provides a single interface to manage both ZeroClaw and Hermes agents.
    """
    
    def __init__(self):
        self.zeroclaw_panel = ZeroClawAgentsPanel()
        self.hermes_panel = HermesAgentsPanel()
    
    async def get_all_agents(self) -> Dict[str, Any]:
        """Get all agents from both panels."""
        zeroclaw = await self.zeroclaw_panel.get_agents()
        hermes = await self.hermes_panel.get_agents()
        
        return {
            "zeroclaw_agents": zeroclaw,
            "hermes_agents": hermes,
            "total_count": len(zeroclaw) + len(hermes),
            "zeroclaw_count": len(zeroclaw),
            "hermes_count": len(hermes),
        }
    
    async def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent from either panel."""
        # Try Zeroclaw first
        agent = await self.zeroclaw_panel.get_agent(agent_id)
        if agent:
            return agent
        
        # Try Hermes
        agent = await self.hermes_panel.get_agent(agent_id)
        if agent:
            return agent
        
        return None
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get combined metrics from both panels."""
        zeroclaw_metrics = await self.zeroclaw_panel.get_agent_metrics()
        hermes_metrics = await self.hermes_panel.get_agent_metrics()
        
        return {
            "zeroclaw": zeroclaw_metrics,
            "hermes": hermes_metrics,
            "combined": {
                "total_agents": zeroclaw_metrics["total_agents"] + hermes_metrics["total_agents"],
                "total_active": zeroclaw_metrics["active"] + hermes_metrics["active"],
                "total_idle": zeroclaw_metrics["idle"] + hermes_metrics["idle"],
                "total_errors": zeroclaw_metrics["error_count"] + hermes_metrics["error_count"],
                "total_tasks": zeroclaw_metrics["total_tasks"] + hermes_metrics["total_tasks"],
            }
        }
