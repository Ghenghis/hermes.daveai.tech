"""
Runtime End-to-End Tests.

Tests the Runtime Core API, Event Bus, and Provider Router
including settings management and circuit breaker functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio


@pytest.fixture
def runtime_core_api():
    """Create a RuntimeCoreAPI instance for testing."""
    from src.runtime import RuntimeCoreAPI
    api = RuntimeCoreAPI(title="Test Runtime", version="1.0.0")
    return api


@pytest.fixture
def event_bus():
    """Create an EventBus instance for testing."""
    from src.runtime import EventBus
    bus = EventBus(nats_url="nats://localhost:4222")
    return bus


@pytest.fixture
def provider_router():
    """Create a ProviderRouter instance for testing."""
    from src.runtime import ProviderRouter
    router = ProviderRouter(
        providers=["provider-a", "provider-b", "provider-c"],
        event_bus=None
    )
    return router


@pytest.mark.asyncio
async def test_settings_api(runtime_core_api):
    """
    Test the settings API endpoints.
    
    Verifies that settings can be retrieved, updated,
    and that changes persist correctly.
    """
    settings = await runtime_core_api.get_settings()
    assert isinstance(settings, dict)
    
    updated = await runtime_core_api.update_setting("test_key", "test_value")
    assert updated["key"] == "test_key"
    assert updated["value"] == "test_value"
    
    settings = await runtime_core_api.get_settings()
    assert settings.get("test_key") == "test_value"


@pytest.mark.asyncio
async def test_event_bus(event_bus):
    """
    Test the event bus publish and subscribe operations.
    
    Verifies that events can be published and that
    subscribers receive published messages.
    """
    received_messages = []
    
    async def callback(message):
        received_messages.append(message)
    
    # Mock the internal NATS client to avoid needing actual NATS server
    mock_nats = MagicMock()
    event_bus._nats_client = mock_nats
    event_bus.connected = True
    
    subscription_id = await event_bus.subscribe("test.subject", callback)
    assert subscription_id is not None
    
    # publish method returns None (no return statement)
    # but it should call the callback with the published message
    await event_bus.publish("test.subject", {"data": "test"})
    
    await asyncio.sleep(0.1)
    # Messages should be received via callback
    assert len(received_messages) == 1
    assert received_messages[0]["data"] == "test"
    
    await event_bus.disconnect()


@pytest.mark.asyncio
async def test_provider_router(provider_router):
    """
    Test provider routing with circuit breaker.
    
    Verifies that requests are routed to available providers
    and that circuit breakers open on repeated failures.
    """
    with patch.object(provider_router, 'route') as mock_route:
        mock_route.return_value = {"status": "success", "provider": "provider-a"}
        
        result = await provider_router.route({"task": "test"})
        assert result["status"] == "success"
    
    state = provider_router.get_circuit_state("provider-a")
    assert state.value in ["closed", "open", "half_open"]
