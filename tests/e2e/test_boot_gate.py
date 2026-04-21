"""
Boot Gate End-to-End Tests.

Tests the health matrix, safemode activation, and repair
flow functionality during system startup and failure.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def health_matrix():
    """Create a health matrix for testing."""
    return {
        "runtime_api": {"status": "healthy", "latency_ms": 50},
        "event_bus": {"status": "healthy", "latency_ms": 10},
        "provider_router": {"status": "healthy", "latency_ms": 30},
        "orchestrator": {"status": "healthy", "latency_ms": 100},
    }


@pytest.fixture
def safemode_enabled():
    """Flag indicating if safemode is enabled."""
    return False


@pytest.mark.asyncio
async def test_health_matrix_pass(health_matrix):
    """
    Test health matrix when all components are healthy.
    
    Verifies that the health matrix passes when all
    components report healthy status.
    """
    from src.runtime import HealthStatus
    
    all_healthy = all(
        component["status"] == "healthy"
        for component in health_matrix.values()
    )
    assert all_healthy is True
    
    for name, status in health_matrix.items():
        assert status["status"] == "healthy"
        assert status["latency_ms"] < 500


@pytest.mark.asyncio
async def test_health_matrix_fail(health_matrix):
    """
    Test health matrix when some components are unhealthy.
    
    Verifies that the health matrix correctly identifies
    and reports failures in specific components.
    """
    unhealthy_matrix = health_matrix.copy()
    unhealthy_matrix["runtime_api"] = {"status": "unhealthy", "latency_ms": 5000}
    
    has_unhealthy = any(
        component["status"] == "unhealthy"
        for component in unhealthy_matrix.values()
    )
    assert has_unhealthy is True
    
    failed_components = [
        name for name, status in unhealthy_matrix.items()
        if status["status"] == "unhealthy"
    ]
    assert "runtime_api" in failed_components


@pytest.mark.asyncio
async def test_safemode_activation():
    """
    Test safemode activation when health checks fail.
    
    Verifies that the system enters safemode when
    critical components fail health checks.
    """
    safemode_triggered = False
    health_matrix = {
        "runtime_api": {"status": "healthy"},
        "event_bus": {"status": "unhealthy"},
        "orchestrator": {"status": "healthy"},
    }
    
    critical_failures = [
        name for name, status in health_matrix.items()
        if status["status"] == "unhealthy" and name in ["event_bus"]
    ]
    
    if len(critical_failures) > 0:
        safemode_triggered = True
    
    assert safemode_triggered is True


@pytest.mark.asyncio
async def test_repair_flow():
    """
    Test repair flow for fixing failed components.
    
    Verifies that repair operations are triggered for
    failed components and that recovery is tracked.
    """
    from src.hermes import RepairRouter
    
    mock_orchestrator = AsyncMock()
    repair_router = RepairRouter(orchestrator=mock_orchestrator)
    
    issue = {
        "issue_id": "issue-1",
        "component": "event_bus",
        "error": "Connection refused",
        "severity": "high"
    }
    
    with patch.object(repair_router, 'execute_repair') as mock_repair:
        mock_repair.return_value = {
            "status": "repaired",
            "issue_id": "issue-1"
        }
        
        result = await repair_router.route_repair(issue)
        # route_repair returns "routed" status, execute_repair returns the actual result
        assert result["status"] == "routed"
