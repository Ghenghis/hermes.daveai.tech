"""
Pytest Configuration and Fixtures for Blockchain Audit Tests.

Provides shared fixtures for audit chain, audit agents, consensus engine,
issue detector, and correction validator testing.
"""

import pytest
import hashlib
import time
from typing import Dict, List, Optional, Any
from unittest.mock import MagicMock, AsyncMock, patch, PropertyMock


class MockBlock:
    """Mock blockchain block for testing."""

    def __init__(
        self,
        block_id: str,
        previous_hash: Optional[str] = None,
        transactions: Optional[List[Dict]] = None,
        timestamp: Optional[float] = None,
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
        timestamp: Optional[float] = None,
    ):
        self.tx_id = tx_id
        self.sender = sender
        self.recipient = recipient
        self.amount = amount
        self.timestamp = timestamp or time.time()
        self.signature = hashlib.sha256(f"{tx_id}{sender}{recipient}{amount}".encode()).hexdigest()


class MockConsensusRule:
    """Mock consensus rule for testing."""

    def __init__(self, rule_id: str, validator_fn=None):
        self.rule_id = rule_id
        self.validator_fn = validator_fn or (lambda x: True)
        self.violations: List[Dict] = []

    def validate(self, block: MockBlock) -> bool:
        result = self.validator_fn(block)
        if not result:
            self.violations.append({"block_id": block.block_id, "rule_id": self.rule_id})
        return result


class MockIssue:
    """Mock issue for testing."""

    def __init__(
        self,
        issue_id: str,
        severity: str,
        component: str,
        description: str,
        affected_components: Optional[List[str]] = None,
        transitive: bool = False,
    ):
        self.issue_id = issue_id
        self.severity = severity
        self.component = component
        self.description = description
        self.affected_components = affected_components or []
        self.transitive = transitive
        self.detected_at = time.time()


class MockCorrection:
    """Mock correction for testing."""

    def __init__(
        self,
        correction_id: str,
        original_issue_id: str,
        validation_status: str,
        corrections: Optional[Dict] = None,
    ):
        self.correction_id = correction_id
        self.original_issue_id = original_issue_id
        self.validation_status = validation_status
        self.corrections = corrections or {}
        self.timestamp = time.time()


class MockAuditResult:
    """Mock audit result for testing."""

    def __init__(
        self,
        audit_id: str,
        layer_id: int,
        blocks_audited: List[str],
        issues_found: int,
        consensus_reached: bool,
        proof: Optional[Dict] = None,
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

    config = AuditConfig(
        min_overlap_percent=25,
        max_overlap_percent=65,
        consensus_threshold=0.75,
        max_verification_passes=2,
        chain_length=100,
    )
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
def mock_blockchain_with_issues():
    """Create a mock blockchain with known issues for testing."""
    mock_chain = MagicMock()

    blocks = []
    for i in range(10):
        prev_hash = blocks[-1].hash if blocks else "genesis"
        complexity = 0.8 if i == 5 else 0.3 + (i * 0.05)
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
            complexity=complexity,
        )
        blocks.append(block)

    mock_chain.blocks = blocks
    mock_chain.genesis = blocks[0]
    mock_chain.head = blocks[-1]
    mock_chain.length = len(blocks)

    mock_chain.get_block = MagicMock(side_effect=lambda bid: next((b for b in blocks if b.block_id == bid), None))
    mock_chain.is_valid_chain = MagicMock(return_value=False)
    mock_chain.add_block = MagicMock(return_value=True)
    mock_chain.get_chain_length = MagicMock(return_value=len(blocks))

    return mock_chain


@pytest.fixture
def audit_chain(audit_config, mock_blockchain):
    """Create an AuditChain instance for testing."""
    from src.blockchain_audit import AuditChain

    with patch("src.blockchain_audit.audit_chain.BlockchainClient", return_value=mock_blockchain):
        chain = AuditChain(audit_config)
        chain.blockchain = mock_blockchain
    return chain


@pytest.fixture
def simple_audit_chain(mock_blockchain):
    """Create an AuditChain with minimal config for testing."""
    from src.blockchain_audit import AuditConfig, AuditChain

    config = AuditConfig(min_overlap_percent=25, max_overlap_percent=65)
    with patch("src.blockchain_audit.audit_chain.BlockchainClient", return_value=mock_blockchain):
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


@pytest.fixture
def sample_corrections():
    """Create sample corrections for testing."""
    return [
        MockCorrection(
            correction_id="corr-1",
            original_issue_id="issue-1",
            validation_status="approved",
            corrections={"block-003": {"hash": "new-hash-003"}, "block-004": {"hash": "new-hash-004"}},
        ),
        MockCorrection(
            correction_id="corr-2",
            original_issue_id="issue-2",
            validation_status="rejected",
            corrections={"block-005": {"hash": "original-hash-005"}},
        ),
        MockCorrection(
            correction_id="corr-3",
            original_issue_id="issue-3",
            validation_status="pending",
            corrections={},
        ),
    ]


@pytest.fixture
def consensus_rules():
    """Create consensus rules for testing."""
    return [
        MockConsensusRule(
            rule_id="rule-1",
            validator_fn=lambda b: b.complexity < 0.9,
        ),
        MockConsensusRule(
            rule_id="rule-2",
            validator_fn=lambda b: b.previous_hash != b.hash,
        ),
        MockConsensusRule(
            rule_id="rule-3",
            validator_fn=lambda b: len(b.transactions) > 0,
        ),
    ]


@pytest.fixture
def overlap_test_cases():
    """Create test cases for overlap calculation testing."""
    return [
        {"complexity": 0.1, "expected_min": 25, "expected_max": 35},
        {"complexity": 0.3, "expected_min": 25, "expected_max": 45},
        {"complexity": 0.5, "expected_min": 35, "expected_max": 55},
        {"complexity": 0.7, "expected_min": 45, "expected_max": 65},
        {"complexity": 0.9, "expected_min": 55, "expected_max": 65},
    ]


@pytest.fixture(autouse=True)
def reset_audit_state():
    """Reset audit state between tests."""
    yield
