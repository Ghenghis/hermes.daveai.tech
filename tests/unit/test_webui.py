"""Unit tests for WebUI control center."""
import pytest
from src.webui.control_center import (
    ControlCenterApp,
    ProviderPanel,
    AgentPanel,
    WorkflowPanel,
    SettingsPanel,
)


class TestControlCenterApp:
    def setup_method(self):
        self.app = ControlCenterApp()

    def test_init(self):
        assert self.app is not None

    def test_panels_registered(self):
        assert isinstance(self.app._panels, dict)

    def test_config_defaults(self):
        assert isinstance(self.app.config, dict)


class TestProviderPanel:
    def setup_method(self):
        self.panel = ProviderPanel()

    def test_init(self):
        assert self.panel is not None


class TestAgentPanel:
    def setup_method(self):
        self.panel = AgentPanel()

    def test_init(self):
        assert self.panel is not None
        assert isinstance(self.panel.agents, dict)

    @pytest.mark.asyncio
    async def test_get_active_agents_empty(self):
        agents = await self.panel.get_active_agents()
        assert isinstance(agents, list)

    @pytest.mark.asyncio
    async def test_get_agent_state_not_found(self):
        state = await self.panel.get_agent_state("nonexistent")
        assert state["state"] == "not_found"


class TestSettingsPanel:
    def setup_method(self):
        self.panel = SettingsPanel()

    def test_init(self):
        assert self.panel is not None
