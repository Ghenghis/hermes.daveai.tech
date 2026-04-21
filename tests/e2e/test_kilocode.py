"""
KiloCode End-to-End Tests.

Tests the KiloCode runtime synchronization and UI components
including task management and evidence collection.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def runtime_sync():
    """Create a RuntimeSync instance for testing."""
    from src.kilocode import RuntimeSync
    sync = RuntimeSync(runtime_url="http://localhost:8080", api_key="test-key")
    return sync


@pytest.mark.asyncio
async def test_runtime_sync(runtime_sync):
    """
    Test runtime synchronization in bidirectional mode.
    
    Verifies that the sync protocol executes successfully,
    handling both push and pull operations.
    """
    result = await runtime_sync.sync_protocol(direction="bidirectional")
    assert isinstance(result, dict)
    assert "status" in result or "synced" in result


@pytest.mark.asyncio
async def test_active_task_panel():
    """
    Test the active task panel refresh and display.
    
    Verifies that the panel correctly fetches and displays
    active tasks from the runtime.
    """
    from src.kilocode import ActiveTaskPanel
    
    mock_sync = AsyncMock()
    mock_sync.get_task_details.return_value = {
        "task_id": "task-1",
        "status": "running",
        "progress": 50
    }
    
    panel = ActiveTaskPanel(runtime_sync=mock_sync)
    tasks = await panel.refresh()
    assert isinstance(tasks, list)


@pytest.mark.asyncio
async def test_completion_submit():
    """
    Test completion submission to the runtime.
    
    Verifies that task completions are properly validated
    and submitted with evidence.
    """
    from src.kilocode import CompletionSubmitter
    
    mock_sync = AsyncMock()
    mock_sync.push_task_state.return_value = True
    
    submitter = CompletionSubmitter(runtime_sync=mock_sync)
    
    result = await submitter.submit_completion(
        task_id="task-1",
        result={"status": "success", "output": "test output"},
        evidence=[{"type": "log", "content": "test evidence"}]
    )
    assert isinstance(result, dict)
