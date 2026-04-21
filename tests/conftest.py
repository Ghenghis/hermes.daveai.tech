"""
Pytest Configuration and Fixtures for Contract Kit Tests.

Provides shared fixtures for runtime API, event bus, and
hermes orchestrator testing.
"""

import pytest
import asyncio
import hashlib
import time
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Generator


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """
    Create an event loop for the test session.
    
    Yields:
        The event loop instance.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_runtime_api():
    """Create a mock RuntimeCoreAPI for testing."""
    mock_api = MagicMock()
    mock_api.get_settings = AsyncMock(return_value={
        "setting_a": "value_a",
        "setting_b": "value_b"
    })
    mock_api.update_setting = AsyncMock(return_value={
        "key": "test_key",
        "value": "test_value",
        "updated": True
    })
    mock_api.health_check = AsyncMock(return_value={
        "status": "healthy",
        "components": {
            "runtime_api": "healthy",
            "event_bus": "healthy"
        }
    })
    return mock_api


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
def hermes_orchestrator(mock_runtime_api):
    """Create a HermesOrchestrator instance for testing."""
    from src.hermes import HermesOrchestrator
    orchestrator = HermesOrchestrator(
        runtime_api=mock_runtime_api,
        event_bus=None,
        provider_router=None
    )
    return orchestrator


@pytest.fixture
def mock_provider_router():
    """Create a mock ProviderRouter for testing."""
    mock_router = MagicMock()
    mock_router.route = AsyncMock(return_value={
        "status": "success",
        "provider": "provider-a",
        "response": {"result": "ok"}
    })
    mock_router.get_provider_health = AsyncMock(return_value={
        "provider": "provider-a",
        "status": "healthy",
        "latency_ms": 50
    })
    return mock_router


@pytest.fixture
def sample_contract():
    """Create a sample contract for testing."""
    return {
        "contract_id": "contract-test-1",
        "status": "active",
        "request_type": "contract_review",
        "normalized_content": "Test contract content",
        "tasks": [],
        "evidence": []
    }


@pytest.fixture
def sample_evidence():
    """Create sample evidence items for testing."""
    return [
        {
            "evidence_id": "ev-1",
            "type": "screenshot",
            "content": "test screenshot data",
            "timestamp": "2024-01-15T10:30:00Z"
        },
        {
            "evidence_id": "ev-2",
            "type": "log",
            "content": "test log output",
            "timestamp": "2024-01-15T10:31:00Z"
        }
    ]


# ============================================================
# Blockchain Audit Fixtures (from conftest_blockchain.py)
# ============================================================

class MockBlock:
    """Mock blockchain block for testing."""

    def __init__(
        self,
        block_id: str,
        previous_hash: str = None,
        transactions: list = None,
        timestamp: float = None,
        complexity: float = 0.5,
    ):
        self.block_id = block_id
        self.previous_hash = previous_hash or "genesis"
        self.transactions = transactions or []
        self.timestamp = timestamp or time.time()
        self.complexity = complexity
        self.hash = self._compute_hash()

    def _compute_hash(self) -> str:
        data = f"{self.block_id}{self.previous_hash}{self.timestamp}{self.complexity}"
        return hashlib.sha256(data.encode()).hexdigest()


class MockTransaction:
    """Mock transaction for testing."""

    def __init__(
        self,
        tx_id: str,
        sender: str,
        recipient: str,
        amount: float,
        timestamp: float = None,
    ):
        self.tx_id = tx_id
        self.sender = sender
        self.recipient = recipient
        self.amount = amount
        self.timestamp = timestamp or time.time()
        self.signature = hashlib.sha256(f"{tx_id}{sender}{recipient}{amount}".encode()).hexdigest()


class MockIssue:
    """Mock issue for testing."""

    def __init__(
        self,
        issue_id: str,
        severity: str,
        component: str,
        description: str,
        affected_components: list = None,
        transitive: bool = False,
    ):
        self.issue_id = issue_id
        self.severity = severity
        self.component = component
        self.description = description
        self.affected_components = affected_components or []
        self.transitive = transitive
        self.detected_at = time.time()


class MockAuditResult:
    """Mock audit result for testing."""

    def __init__(
        self,
        audit_id: str,
        layer_id: int,
        blocks_audited: list,
        issues_found: int,
        consensus_reached: bool,
        proof: dict = None,
    ):
        self.audit_id = audit_id
        self.layer_id = layer_id
        self.blocks_audited = blocks_audited
        self.issues_found = issues_found
        self.consensus_reached = consensus_reached
        self.proof = proof or {}
        self.timestamp = time.time()


@pytest.fixture
def audit_config():
    """Create an AuditConfig for testing."""
    from src.blockchain_audit import AuditConfig

    config = AuditConfig()
    # Set up test-specific values
    config.OVERLAP_MIN = 0.25
    config.OVERLAP_MAX = 0.65
    return config


@pytest.fixture
def default_audit_config():
    """Create an AuditConfig with default values for testing."""
    from src.blockchain_audit import AuditConfig

    return AuditConfig()


@pytest.fixture
def mock_blockchain():
    """Create a mock blockchain for testing."""
    mock_chain = MagicMock()

    blocks = []
    for i in range(10):
        prev_hash = blocks[-1].hash if blocks else "genesis"
        block = MockBlock(
            block_id=f"block-{i:03d}",
            previous_hash=prev_hash,
            transactions=[
                MockTransaction(
                    tx_id=f"tx-{i}-{j}",
                    sender=f"sender-{j}",
                    recipient=f"recipient-{j}",
                    amount=100.0 * j,
                )
                for j in range(3)
            ],
            complexity=0.3 + (i * 0.05),
        )
        blocks.append(block)

    mock_chain.blocks = blocks
    mock_chain.genesis = blocks[0]
    mock_chain.head = blocks[-1]
    mock_chain.length = len(blocks)

    mock_chain.get_block = MagicMock(side_effect=lambda bid: next((b for b in blocks if b.block_id == bid), None))
    mock_chain.get_previous_block = MagicMock(side_effect=lambda bid: next((b for b in blocks if b.block_id == bid and b.previous_hash == b.hash), None))
    mock_chain.is_valid_chain = MagicMock(return_value=True)
    mock_chain.add_block = MagicMock(return_value=True)
    mock_chain.get_chain_length = MagicMock(return_value=len(blocks))

    return mock_chain


@pytest.fixture
def audit_chain(audit_config, mock_blockchain):
    """Create an AuditChain instance for testing."""
    from src.blockchain_audit import AuditChain

    chain = AuditChain(audit_config)
    chain.blockchain = mock_blockchain
    return chain


@pytest.fixture
def simple_audit_chain(mock_blockchain):
    """Create an AuditChain with minimal config for testing."""
    from src.blockchain_audit import AuditConfig, AuditChain

    config = AuditConfig()
    chain = AuditChain(config)
    chain.blockchain = mock_blockchain
    return chain


@pytest.fixture
def audit_agents(audit_chain, audit_config):
    """Create 5 overlapping audit agents for testing."""
    from src.blockchain_audit import AuditAgent

    agents = []
    for i in range(5):
        agent = AuditAgent(
            agent_id=f"agent-{i}",
            audit_chain=audit_chain,
            config=audit_config,
            layer_id=i,
            overlap_percent=30 + (i * 5),
        )
        agents.append(agent)
    return agents


@pytest.fixture
def consensus_engine(audit_config):
    """Create a ConsensusEngine instance for testing."""
    from src.blockchain_audit import ConsensusEngine

    engine = ConsensusEngine(audit_config)
    return engine


@pytest.fixture
def issue_detector(audit_config):
    """Create an IssueDetector instance for testing."""
    from src.blockchain_audit import IssueDetector

    detector = IssueDetector(audit_config)
    return detector


@pytest.fixture
def correction_validator(audit_config):
    """Create a CorrectionValidator instance for testing."""
    from src.blockchain_audit import CorrectionValidator

    validator = CorrectionValidator(audit_config)
    return validator


@pytest.fixture
def sample_audit_results():
    """Create sample audit results for testing."""
    return [
        MockAuditResult(
            audit_id=f"audit-{i}",
            layer_id=i,
            blocks_audited=[f"block-{j:03d}" for j in range(i * 2, i * 2 + 5)],
            issues_found=i,
            consensus_reached=i % 2 == 0,
            proof={"hash": hashlib.sha256(f"proof-{i}".encode()).hexdigest()},
        )
        for i in range(5)
    ]


@pytest.fixture
def sample_issues():
    """Create sample issues for testing."""
    return [
        MockIssue(
            issue_id="issue-1",
            severity="high",
            component="block-003",
            description="Consensus rule violated",
            affected_components=["block-003", "block-004"],
            transitive=False,
        ),
        MockIssue(
            issue_id="issue-2",
            severity="critical",
            component="block-005",
            description="Double-spend detected",
            affected_components=["block-005"],
            transitive=True,
        ),
        MockIssue(
            issue_id="issue-3",
            severity="medium",
            component="block-007",
            description="Transaction ordering issue",
            affected_components=["block-007", "block-008", "block-009"],
            transitive=True,
        ),
    ]


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton states between tests."""
    yield
