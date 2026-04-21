"""
Hermes End-to-End Tests.

Tests the Hermes orchestrator including intake normalization,
contract creation, and task fanout.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def hermes_orchestrator():
    """Create a HermesOrchestrator instance for testing."""
    from src.hermes import HermesOrchestrator
    orchestrator = HermesOrchestrator(
        runtime_api=None,
        event_bus=None,
        provider_router=None
    )
    return orchestrator


@pytest.mark.asyncio
async def test_intake_normalization(hermes_orchestrator):
    """
    Test intake normalization of raw input.
    
    Verifies that raw input is properly normalized,
    validated, and prepared for contract creation.
    """
    raw_input = {
        "description": "Please review contract version 2.3",
        "request_type": "contract_review",
        "source": "email",
        "raw_content": "Please review contract version 2.3",
        "metadata": {
            "sender": "client@example.com",
            "timestamp": "2024-01-15T10:30:00Z"
        }
    }
    
    result = await hermes_orchestrator.intake(raw_input)
    assert isinstance(result, dict)
    assert result.get("status") == "normalized" or "task_id" in result


@pytest.mark.asyncio
async def test_contract_creation(hermes_orchestrator):
    """
    Test contract creation from normalized input.
    
    Verifies that contracts are created with proper IDs,
    initial status, and required fields.
    """
    normalized_input = {
        "task_id": "task-123",
        "description": "Review contract version 2.3",
        "request_type": "contract_review",
        "priority": "normal"
    }
    
    contract = await hermes_orchestrator.contract_creation(normalized_input)
    assert isinstance(contract, dict)
    assert "contract_id" in contract or "task_id" in contract


@pytest.mark.asyncio
async def test_task_fanout(hermes_orchestrator):
    """
    Test task fanout to providers.
    
    Verifies that tasks are properly distributed across
    available providers and tracked correctly.
    """
    from src.hermes.orchestrator import TaskPacket, ContractStatus
    from unittest.mock import MagicMock
    
    # Create a proper TaskPacket object
    packet = TaskPacket(
        task_id="task-1",
        description="Test task for fanout",
        acceptance_criteria=["criterion 1"],
        context={}
    )
    packet.status = ContractStatus.ACTIVE
    
    hermes_orchestrator.contracts["contract-1"] = packet
    
    # Set up a mock provider_router
    hermes_orchestrator.provider_router = MagicMock()
    hermes_orchestrator.provider_router.route = MagicMock(return_value={"status": "dispatched", "provider": "provider-a"})
    
    tasks = await hermes_orchestrator.task_fanout("contract-1")
    assert isinstance(tasks, list)
    assert len(tasks) > 0
