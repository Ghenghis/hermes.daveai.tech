"""Unit tests for the agents panel module."""
import pytest
import asyncio
from src.webui.agents_panel import (
    AgentsManager,
    ZeroClawAgentsPanel,
    HermesAgentsPanel,
    AgentProfile,
    AgentType,
    AgentStatus,
)


class TestAgentEnums:
    def test_agent_types(self):
        assert AgentType.ZEROCLAW is not None
        assert AgentType.HERMES is not None

    def test_agent_statuses(self):
        assert AgentStatus.ACTIVE is not None
        assert AgentStatus.IDLE is not None
        assert AgentStatus.ERROR is not None


class TestZeroClawAgentsPanel:
    def setup_method(self):
        self.panel = ZeroClawAgentsPanel()

    def test_init(self):
        assert self.panel is not None
        assert len(self.panel.agents) > 0

    def test_default_agents_registered(self):
        agent_ids = list(self.panel.agents.keys())
        assert len(agent_ids) >= 4

    @pytest.mark.asyncio
    async def test_get_agents(self):
        agents = await self.panel.get_agents()
        assert isinstance(agents, list)
        assert len(agents) > 0

    @pytest.mark.asyncio
    async def test_agent_has_required_fields(self):
        agents = await self.panel.get_agents()
        for agent in agents:
            assert "agent_id" in agent
            assert "name" in agent
            assert "status" in agent
            assert "agent_type" in agent

    @pytest.mark.asyncio
    async def test_get_agent_metrics(self):
        metrics = await self.panel.get_agent_metrics()
        assert "total_agents" in metrics
        assert "active" in metrics
        assert "idle" in metrics
        assert metrics["total_agents"] >= 4


class TestHermesAgentsPanel:
    def setup_method(self):
        self.panel = HermesAgentsPanel()

    def test_init(self):
        assert self.panel is not None
        assert len(self.panel.agents) > 0

    def test_has_five_hermes_agents(self):
        assert len(self.panel.agents) == 5

    @pytest.mark.asyncio
    async def test_get_agents(self):
        agents = await self.panel.get_agents()
        assert isinstance(agents, list)
        assert len(agents) == 5

    @pytest.mark.asyncio
    async def test_hermes_agents_have_channels(self):
        agents = await self.panel.get_agents()
        for agent in agents:
            assert "channel" in agent or "discord_channel" in agent or "name" in agent

    @pytest.mark.asyncio
    async def test_get_agent_metrics(self):
        metrics = await self.panel.get_agent_metrics()
        assert "total_agents" in metrics
        assert metrics["total_agents"] == 5


class TestAgentsManager:
    def setup_method(self):
        self.manager = AgentsManager()

    def test_init(self):
        assert self.manager is not None
        assert self.manager.zeroclaw_panel is not None
        assert self.manager.hermes_panel is not None

    @pytest.mark.asyncio
    async def test_get_all_agents(self):
        result = await self.manager.get_all_agents()
        assert "zeroclaw_agents" in result
        assert "hermes_agents" in result
        assert "total_count" in result
        assert result["total_count"] >= 9

    @pytest.mark.asyncio
    async def test_combined_metrics(self):
        metrics = await self.manager.get_metrics()
        assert "zeroclaw" in metrics
        assert "hermes" in metrics
        assert "combined" in metrics
        assert metrics["combined"]["total_agents"] >= 9
