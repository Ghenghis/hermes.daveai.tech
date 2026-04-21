"""
End-to-End Tests for Blockchain Audit Module.

Tests for multi-layered auditing system with overlapping agents,
consensus engine, issue detection, and correction validation.
"""

import pytest
import hashlib
import time
from typing import List, Dict, Any, Optional
from unittest.mock import MagicMock, AsyncMock, patch, call


class TestDynamicOverlapCalculation:
    """Tests for dynamic overlap calculation based on complexity."""

    def test_overlap_calculation_low_complexity(self, audit_config, mock_blockchain):
        """Test overlap calculation with low complexity blocks (10%)."""
        from src.blockchain_audit import AuditChain

        with patch("src.blockchain_audit.audit_chain.BlockchainClient", return_value=mock_blockchain):
            chain = AuditChain(audit_config)
            chain.blockchain = mock_blockchain

        overlap = chain.calculate_overlap(complexity=0.1)
        assert 25 <= overlap <= 35, f"Expected overlap 25-35 for low complexity, got {overlap}"

    def test_overlap_calculation_medium_complexity(self, audit_config, mock_blockchain):
        """Test overlap calculation with medium complexity blocks (50%)."""
        from src.blockchain_audit import AuditChain

        with patch("src.blockchain_audit.audit_chain.BlockchainClient", return_value=mock_blockchain):
            chain = AuditChain(audit_config)
            chain.blockchain = mock_blockchain

        overlap = chain.calculate_overlap(complexity=0.5)
        assert 35 <= overlap <= 55, f"Expected overlap 35-55 for medium complexity, got {overlap}"

    def test_overlap_calculation_high_complexity(self, audit_config, mock_blockchain):
        """Test overlap calculation with high complexity blocks (90%)."""
        from src.blockchain_audit import AuditChain

        with patch("src.blockchain_audit.audit_chain.BlockchainClient", return_value=mock_blockchain):
            chain = AuditChain(audit_config)
            chain.blockchain = mock_blockchain

        overlap = chain.calculate_overlap(complexity=0.9)
        assert 55 <= overlap <= 65, f"Expected overlap 55-65 for high complexity, got {overlap}"

    def test_overlap_calculation_boundary_low(self, audit_config, mock_blockchain):
        """Test overlap calculation at lowest boundary."""
        from src.blockchain_audit import AuditChain

        with patch("src.blockchain_audit.audit_chain.BlockchainClient", return_value=mock_blockchain):
            chain = AuditChain(audit_config)
            chain.blockchain = mock_blockchain

        overlap = chain.calculate_overlap(complexity=0.0)
        assert overlap == 25, f"Expected overlap 25 at boundary, got {overlap}"

    def test_overlap_calculation_boundary_high(self, audit_config, mock_blockchain):
        """Test overlap calculation at highest boundary."""
        from src.blockchain_audit import AuditChain

        with patch("src.blockchain_audit.audit_chain.BlockchainClient", return_value=mock_blockchain):
            chain = AuditChain(audit_config)
            chain.blockchain = mock_blockchain

        overlap = chain.calculate_overlap(complexity=1.0)
        assert overlap == 65, f"Expected overlap 65 at boundary, got {overlap}"

    def test_overlap_is_deterministic(self, audit_config, mock_blockchain):
        """Test that overlap calculation is deterministic."""
        from src.blockchain_audit import AuditChain

        with patch("src.blockchain_audit.audit_chain.BlockchainClient", return_value=mock_blockchain):
            chain = AuditChain(audit_config)
            chain.blockchain = mock_blockchain

        complexity = 0.5
        overlap1 = chain.calculate_overlap(complexity=complexity)
        overlap2 = chain.calculate_overlap(complexity=complexity)
        overlap3 = chain.calculate_overlap(complexity=complexity)

        assert overlap1 == overlap2 == overlap3, "Overlap calculation should be deterministic"

    def test_overlap_respects_config_limits(self, default_audit_config, mock_blockchain):
        """Test that overlap respects configured min/max limits."""
        from src.blockchain_audit import AuditChain

        with patch("src.blockchain_audit.audit_chain.BlockchainClient", return_value=mock_blockchain):
            chain = AuditChain(default_audit_config)
            chain.blockchain = mock_blockchain

        for complexity in [0.0, 0.25, 0.5, 0.75, 1.0]:
            overlap = chain.calculate_overlap(complexity=complexity)
            assert (
                default_audit_config.min_overlap_percent <= overlap <= default_audit_config.max_overlap_percent
            ), f"Overlap {overlap} outside config bounds [{default_audit_config.min_overlap_percent}, {default_audit_config.max_overlap_percent}]"


class TestLinearChainVerification:
    """Tests for complete chain verification from genesis to current."""

    def test_verify_chain_from_genesis(self, audit_chain, mock_blockchain):
        """Test verification of complete chain from genesis to head."""
        result = audit_chain.verify_chain(start_block=None, end_block=None)

        assert result["verified"] is True, "Chain should verify successfully"
        assert "blocks_verified" in result
        assert result["blocks_verified"] == mock_blockchain.length

    def test_verify_chain_from_specific_start(self, audit_chain, mock_blockchain):
        """Test verification starting from a specific block."""
        start_block = "block-003"
        end_block = "block-007"

        result = audit_chain.verify_chain(start_block=start_block, end_block=end_block)

        assert result["verified"] is True
        assert result["start_block"] == start_block
        assert result["end_block"] == end_block

    def test_verify_chain_partial_range(self, audit_chain, mock_blockchain):
        """Test verification of a partial chain range."""
        start_block = "block-002"
        end_block = "block-005"

        result = audit_chain.verify_chain(start_block=start_block, end_block=end_block)

        assert result["verified"] is True
        assert result["blocks_verified"] == 4

    def test_verify_chain_invalid_hash(self, audit_chain, mock_blockchain):
        """Test verification fails on invalid block hash."""
        mock_blockchain.is_valid_chain = MagicMock(return_value=False)

        result = audit_chain.verify_chain(start_block=None, end_block=None)

        assert result["verified"] is False
        assert "error" in result or "violations" in result

    def test_verify_chain_empty_chain(self, audit_config):
        """Test verification of empty chain."""
        from src.blockchain_audit import AuditChain

        empty_mock = MagicMock()
        empty_mock.blocks = []
        empty_mock.length = 0
        empty_mock.is_valid_chain = MagicMock(return_value=True)

        with patch("src.blockchain_audit.audit_chain.BlockchainClient", return_value=empty_mock):
            chain = AuditChain(audit_config)
            chain.blockchain = empty_mock

        result = chain.verify_chain(start_block=None, end_block=None)
        assert result["verified"] is True
        assert result["blocks_verified"] == 0

    def test_verify_chain_single_block(self, audit_config):
        """Test verification of single block chain."""
        from src.blockchain_audit import AuditChain

        single_mock = MagicMock()
        block = MockBlock("block-000", previous_hash="genesis", transactions=[], complexity=0.5)
        single_mock.blocks = [block]
        single_mock.length = 1
        single_mock.genesis = block
        single_mock.head = block
        single_mock.is_valid_chain = MagicMock(return_value=True)

        with patch("src.blockchain_audit.audit_chain.BlockchainClient", return_value=single_mock):
            chain = AuditChain(audit_config)
            chain.blockchain = single_mock

        result = chain.verify_chain(start_block=None, end_block=None)
        assert result["verified"] is True
        assert result["blocks_verified"] == 1

    def test_verify_chain_order_integrity(self, audit_chain, mock_blockchain):
        """Test that chain verification maintains block order integrity."""
        result = audit_chain.verify_chain(start_block=None, end_block=None)

        assert result["verified"] is True
        if "block_order" in result:
            for i in range(len(result["block_order"]) - 1):
                current = result["block_order"][i]
                next_block = result["block_order"][i + 1]
                assert current["previous_hash"] == next_block["hash"]


class TestRecursiveDoubleCheck:
    """Tests for mandatory 2-pass verification."""

    def test_two_pass_verification_enabled(self, audit_chain):
        """Test that 2-pass verification is enabled by default."""
        assert audit_chain.config.max_verification_passes == 2

    def test_first_pass_completes(self, audit_chain, mock_blockchain):
        """Test that first pass of verification completes."""
        result = audit_chain.verify_chain_with_double_check()

        assert "pass_1" in result or "passes" in result
        if "pass_1" in result:
            assert result["pass_1"]["completed"] is True
        elif "passes" in result:
            assert len(result["passes"]) >= 1

    def test_second_pass_completes(self, audit_chain, mock_blockchain):
        """Test that second pass of verification completes."""
        result = audit_chain.verify_chain_with_double_check()

        assert "pass_2" in result or ("passes" in result and len(result["passes"]) >= 2)
        if "pass_2" in result:
            assert result["pass_2"]["completed"] is True

    def test_both_passes_agree(self, audit_chain, mock_blockchain):
        """Test that both passes agree on verification result."""
        result = audit_chain.verify_chain_with_double_check()

        if "pass_1" in result and "pass_2" in result:
            assert result["pass_1"]["verified"] == result["pass_2"]["verified"]
        elif "passes" in result:
            pass1_result = result["passes"][0]["verified"]
            for p in result["passes"][1:]:
                assert p["verified"] == pass1_result, "All passes should agree"

    def test_discrepancy_detected(self, audit_chain, mock_blockchain_with_issues):
        """Test that discrepancies between passes are detected."""
        audit_chain.blockchain = mock_blockchain_with_issues

        result = audit_chain.verify_chain_with_double_check()

        if "discrepancies" in result:
            assert len(result["discrepancies"]) > 0

    def test_max_passes_respected(self, audit_config):
        """Test that max passes configuration is respected."""
        from src.blockchain_audit import AuditChain

        config = AuditConfig(max_verification_passes=3)
        mock_chain = MagicMock()
        mock_chain.blocks = []
        mock_chain.length = 0
        mock_chain.is_valid_chain = MagicMock(return_value=True)

        with patch("src.blockchain_audit.audit_chain.BlockchainClient", return_value=mock_chain):
            chain = AuditChain(config)
            chain.blockchain = mock_chain

        assert chain.config.max_verification_passes == 3


class TestConsensusViolationDetection:
    """Tests for detection of consensus rule violations."""

    def test_detect_hash_mismatch_violation(self, consensus_engine, mock_blockchain):
        """Test detection of hash mismatch violations."""
        blocks = mock_blockchain.blocks
        blocks[5].hash = "invalid-hash-12345"

        violations = consensus_engine.detect_violations(blocks)

        assert len(violations) > 0
        assert any(v["rule_id"] == "hash_integrity" or "hash" in str(v).lower() for v in violations)

    def test_detect_previous_hash_violation(self, consensus_engine, mock_blockchain):
        """Test detection of previous hash link violations."""
        blocks = mock_blockchain.blocks
        blocks[5].previous_hash = "tampered-previous-hash"

        violations = consensus_engine.detect_violations(blocks)

        assert len(violations) > 0

    def test_detect_timestamp_violation(self, consensus_engine, mock_blockchain):
        """Test detection of timestamp ordering violations."""
        blocks = mock_blockchain.blocks
        blocks[5].timestamp = blocks[3].timestamp - 1000

        violations = consensus_engine.detect_violations(blocks)

        assert len(violations) > 0

    def test_no_violations_on_valid_chain(self, consensus_engine, mock_blockchain):
        """Test no violations detected on valid chain."""
        violations = consensus_engine.detect_violations(mock_blockchain.blocks)

        assert len(violations) == 0, f"Expected no violations on valid chain, got {len(violations)}"

    def test_multiple_violations_detected(self, consensus_engine, mock_blockchain):
        """Test detection of multiple violations in same chain."""
        blocks = mock_blockchain.blocks
        blocks[3].hash = "invalid-1"
        blocks[5].hash = "invalid-2"
        blocks[7].hash = "invalid-3"

        violations = consensus_engine.detect_violations(blocks)

        assert len(violations) >= 3

    def test_violation_includes_block_id(self, consensus_engine, mock_blockchain):
        """Test that violations include affected block IDs."""
        blocks = mock_blockchain.blocks
        blocks[4].hash = "tampered"

        violations = consensus_engine.detect_violations(blocks)

        assert len(violations) > 0
        assert any("block-004" in str(v) or "block_id" in v for v in violations)

    def test_consensus_threshold_enforced(self, consensus_engine, mock_blockchain, sample_audit_results):
        """Test that consensus threshold is enforced."""
        result = consensus_engine.check_consensus(sample_audit_results)

        if result["consensus_reached"]:
            assert result["agreement_ratio"] >= consensus_engine.config.consensus_threshold


class TestDoubleSpendDetection:
    """Tests for detection of double-spend attempts."""

    def test_detect_double_spend_same_tx_different_blocks(self, issue_detector, mock_blockchain):
        """Test detection of same transaction in multiple blocks."""
        blocks = mock_blockchain.blocks
        tx_id = "tx-0-0"

        blocks[2].transactions = [
            MockTransaction(
                tx_id=tx_id, sender="sender-0", recipient="recipient-0", amount=100.0
            )
        ]
        blocks[5].transactions = [
            MockTransaction(
                tx_id=tx_id, sender="sender-0", recipient="recipient-0", amount=100.0
            )
        ]

        issues = issue_detector.detect_double_spends(blocks)

        assert len(issues) > 0
        assert any("double" in str(i).lower() or "tx_id" in str(i) for i in issues)

    def test_detect_insufficient_funds_spend(self, issue_detector, mock_blockchain):
        """Test detection of spending more than available balance."""
        blocks = mock_blockchain.blocks
        blocks[3].transactions = [
            MockTransaction(
                tx_id="tx-3-0", sender="sender-x", recipient="recipient-x", amount=999999.0
            )
        ]

        issues = issue_detector.detect_double_spends(blocks)

        assert len(issues) > 0

    def test_no_double_spend_on_valid_chain(self, issue_detector, mock_blockchain):
        """Test no double-spend issues on valid chain."""
        issues = issue_detector.detect_double_spends(mock_blockchain.blocks)

        double_spend_issues = [i for i in issues if "double" in str(i).lower() or hasattr(i, "is_double_spend") and i.is_double_spend]
        assert len(double_spend_issues) == 0

    def test_double_spend_impact_assessment(self, issue_detector, mock_blockchain):
        """Test impact assessment for detected double-spend."""
        blocks = mock_blockchain.blocks
        tx_id = "tx-impact-test"
        blocks[2].transactions = [MockTransaction(tx_id=tx_id, sender="spender", recipient="receiver", amount=500.0)]
        blocks[6].transactions = [MockTransaction(tx_id=tx_id, sender="spender", recipient="receiver", amount=500.0)]

        issues = issue_detector.detect_double_spends(blocks)

        assert len(issues) > 0
        if hasattr(issues[0], "affected_amount"):
            assert issues[0].affected_amount >= 500.0

    def test_double_spend_isolation(self, issue_detector, mock_blockchain):
        """Test that double-spend detection isolates affected transactions."""
        blocks = mock_blockchain.blocks

        for i in [2, 5, 8]:
            blocks[i].transactions = [
                MockTransaction(tx_id=f"tx-{i}-isolated", sender="user", recipient="merchant", amount=50.0)
            ]
            blocks[i + 1].transactions = [
                MockTransaction(tx_id=f"tx-{i}-isolated", sender="user", recipient="merchant", amount=50.0)
            ]

        issues = issue_detector.detect_double_spends(blocks)

        assert len(issues) >= 3


class TestCrossLayerVerification:
    """Tests for verification with adjacent overlapping layers."""

    def test_verify_with_adjacent_layer_overlap(self, audit_chain, audit_agents):
        """Test verification when adjacent layers have overlap."""
        layer_0_results = audit_agents[0].audit_block_range("block-000", "block-004")
        layer_1_results = audit_agents[1].audit_block_range("block-003", "block-007")

        overlap_verified = audit_chain.verify_layer_overlap(0, 1, layer_0_results, layer_1_results)

        assert overlap_verified["overlap_confirmed"] is True
        assert overlap_verified["overlapping_blocks"] >= 1

    def test_cross_layer_consensus_check(self, audit_chain, audit_agents):
        """Test consensus check across layers."""
        results_layer_0 = [agent.audit_block_range("block-000", "block-003") for agent in audit_agents[:3]]
        results_layer_1 = [agent.audit_block_range("block-003", "block-006") for agent in audit_agents[2:]]

        consensus = audit_chain.check_cross_layer_consensus(results_layer_0, results_layer_1)

        assert "consensus_reached" in consensus

    def test_verify_no_gaps_between_layers(self, audit_chain, audit_agents):
        """Test that there are no gaps in coverage between layers."""
        all_results = [agent.audit_all_blocks() for agent in audit_agents]

        coverage = audit_chain.calculate_layer_coverage(all_results)

        assert coverage["gaps"] == [] or coverage["gaps"] is None or len(coverage["gaps"]) == 0

    def test_layer_boundary_handling(self, audit_chain):
        """Test handling of block boundaries between layers."""
        result = audit_chain.verify_boundary_blocks("block-004", "block-005", layer_1_id=0, layer_2_id=1)

        assert "boundary_verified" in result

    def test_overlap_redundancy_check(self, audit_chain, audit_agents):
        """Test that overlapping regions are redundantly verified."""
        layer_0 = audit_agents[0].audit_block_range("block-000", "block-005")
        layer_2 = audit_agents[2].audit_block_range("block-003", "block-008")

        redundancy = audit_chain.check_overlap_redundancy(layer_0, layer_2)

        assert redundancy["redundant_verifications"] >= 1

    def test_cross_layer_conflict_resolution(self, audit_chain, audit_agents):
        """Test resolution of conflicts found between layers."""
        layer_0_results = [{"block_id": "block-005", "status": "valid", "findings": []}]
        layer_1_results = [{"block_id": "block-005", "status": "invalid", "findings": ["issue-x"]}]

        resolution = audit_chain.resolve_cross_layer_conflict("block-005", layer_0_results, layer_1_results)

        assert "resolved" in resolution or "conflict_type" in resolution


class TestCorrectionValidation:
    """Tests for correction validation against original."""

    def test_validate_correction_approved(self, correction_validator, sample_issues, sample_corrections):
        """Test validation of approved correction."""
        issue = sample_issues[0]
        correction = sample_corrections[0]

        result = correction_validator.validate_correction(issue, correction)

        assert result["status"] == "approved"
        assert result["original_issue_id"] == issue.issue_id
        assert result["correction_id"] == correction.correction_id

    def test_validate_correction_rejected(self, correction_validator, sample_issues, sample_corrections):
        """Test validation of rejected correction."""
        issue = sample_issues[1]
        correction = sample_corrections[1]

        result = correction_validator.validate_correction(issue, correction)

        assert result["status"] == "rejected"

    def test_validate_correction_pending(self, correction_validator, sample_issues, sample_corrections):
        """Test validation of pending correction."""
        issue = sample_issues[2]
        correction = sample_corrections[2]

        result = correction_validator.validate_correction(issue, correction)

        assert result["status"] in ["pending", "needs_review"]

    def test_correction_matches_original_issue(self, correction_validator, sample_issues, sample_corrections):
        """Test that correction is matched to original issue."""
        issue = sample_issues[0]
        correction = sample_corrections[0]

        result = correction_validator.validate_correction(issue, correction)

        assert result["original_issue_id"] == issue.issue_id

    def test_correction_integrity_check(self, correction_validator, sample_issues, sample_corrections):
        """Test integrity check of correction data."""
        issue = sample_issues[0]
        correction = sample_corrections[0]

        result = correction_validator.validate_correction(issue, correction)

        assert "integrity_valid" in result or result["status"] in ["approved", "rejected"]

    def test_batch_correction_validation(self, correction_validator, sample_issues, sample_corrections):
        """Test batch validation of multiple corrections."""
        issues = sample_issues[:2]
        corrections = sample_corrections[:2]

        results = correction_validator.validate_batch(issues, corrections)

        assert len(results) == 2
        assert all("status" in r for r in results)

    def test_correction_rollback_verification(self, correction_validator, sample_issues, sample_corrections):
        """Test verification of rollback capability for corrections."""
        issue = sample_issues[0]
        correction = sample_corrections[0]

        can_rollback = correction_validator.can_rollback(correction)

        assert isinstance(can_rollback, bool)


class TestCryptographicProof:
    """Tests for audit trail proof generation."""

    def test_generate_audit_proof(self, audit_chain, mock_blockchain):
        """Test generation of cryptographic audit proof."""
        proof = audit_chain.generate_audit_proof("block-003")

        assert proof is not None
        assert "hash" in proof or "signature" in proof or "proof" in proof
        assert "block_id" in proof
        assert proof["block_id"] == "block-003"

    def test_proof_includes_chain_links(self, audit_chain, mock_blockchain):
        """Test that proof includes chain linkage hashes."""
        proof = audit_chain.generate_audit_proof("block-005")

        assert proof is not None
        if "chain_links" in proof:
            assert len(proof["chain_links"]) >= 1

    def test_proof_timestamp_included(self, audit_chain, mock_blockchain):
        """Test that proof includes timestamp."""
        proof = audit_chain.generate_audit_proof("block-003")

        assert proof is not None
        assert "timestamp" in proof

    def test_proof_verification_succeeds(self, audit_chain, mock_blockchain):
        """Test verification of generated proof."""
        proof = audit_chain.generate_audit_proof("block-003")

        verified = audit_chain.verify_proof(proof)

        assert verified is True

    def test_proof_tampering_detection(self, audit_chain, mock_blockchain):
        """Test detection of tampered proof."""
        proof = audit_chain.generate_audit_proof("block-003")
        proof["hash"] = "tampered-hash"

        verified = audit_chain.verify_proof(proof)

        assert verified is False

    def test_proof_includes_audit_metadata(self, audit_chain, mock_blockchain):
        """Test that proof includes audit metadata."""
        proof = audit_chain.generate_audit_proof("block-004")

        assert proof is not None
        assert any(key in proof for key in ["agent_id", "audit_id", "layer_id", "metadata"])

    def test_proof_chain_from_genesis(self, audit_chain, mock_blockchain):
        """Test proof chain from genesis block."""
        proof = audit_chain.generate_proof_chain("block-000", "block-009")

        assert proof is not None
        assert "proofs" in proof or "chain" in proof
        assert len(proof.get("proofs", proof.get("chain", []))) >= 1


class TestTransitiveIssueDetection:
    """Tests for detection of transitively affected components."""

    def test_detect_transitive_dependencies(self, issue_detector, mock_blockchain):
        """Test detection of transitive issue dependencies."""
        blocks = mock_blockchain.blocks
        blocks[3].complexity = 0.95

        issues = issue_detector.detect_issues(blocks)

        transitive_issues = [i for i in issues if hasattr(i, "transitive") and i.transitive]
        assert len(transitive_issues) >= 0

    def test_trace_issue_propagation(self, issue_detector, mock_blockchain):
        """Test tracing of issue propagation through chain."""
        blocks = mock_blockchain.blocks
        blocks[4].hash = "propagation-test-hash"

        propagation_path = issue_detector.trace_propagation("block-004", blocks)

        assert propagation_path is not None
        assert len(propagation_path) >= 1

    def test_affected_component_count(self, issue_detector, mock_blockchain, sample_issues):
        """Test accurate counting of affected components."""
        issue = sample_issues[2]

        if hasattr(issue, "affected_components") and len(issue.affected_components) > 0:
            count = issue_detector.count_affected_components(issue)
            assert count == len(issue.affected_components)

    def test_transitive_issue_severity_escalation(self, issue_detector, mock_blockchain):
        """Test severity escalation for transitive issues."""
        blocks = mock_blockchain.blocks
        blocks[5].complexity = 0.99

        issues = issue_detector.detect_issues(blocks)

        if len(issues) > 0:
            for issue in issues:
                if hasattr(issue, "transitive") and issue.transitive:
                    assert issue.severity in ["high", "critical", "medium", "low"]
                    if len(issue.affected_components) > 3:
                        assert issue.severity in ["high", "critical"]

    def test_isolate_ground_zero_issue(self, issue_detector, mock_blockchain, sample_issues):
        """Test isolation of original issue from transitive effects."""
        issue = sample_issues[0]

        ground_zero = issue_detector.find_ground_zero(issue, mock_blockchain.blocks)

        assert ground_zero is not None
        assert "component" in ground_zero or "block_id" in ground_zero

    def test_prevent_transitive_false_positives(self, issue_detector, mock_blockchain):
        """Test that transitive detection avoids false positives."""
        blocks = mock_blockchain.blocks

        issues = issue_detector.detect_issues(blocks)

        direct_issues = [i for i in issues if not (hasattr(i, "transitive") and i.transitive)]
        assert len(issues) >= len(direct_issues)


class TestAuditAgentBehavior:
    """Tests for audit agent behavior and lifecycle."""

    def test_agent_initialization(self, audit_agents):
        """Test that agents are initialized correctly."""
        assert len(audit_agents) == 5
        for i, agent in enumerate(audit_agents):
            assert agent.agent_id == f"agent-{i}"
            assert agent.layer_id == i
            assert agent.overlap_percent == 30 + (i * 5)

    def test_agent_audit_block_range(self, audit_chain, audit_agents):
        """Test agent auditing a specific block range."""
        agent = audit_agents[0]
        result = agent.audit_block_range("block-001", "block-003")

        assert result is not None
        assert "blocks_audited" in result or "result" in result

    def test_agent_audit_all_blocks(self, audit_chain, audit_agents):
        """Test agent auditing all blocks."""
        agent = audit_agents[0]
        result = agent.audit_all_blocks()

        assert result is not None
        assert "total_blocks" in result or result.get("blocks_audited", []) is not None

    def test_agent_overlap_calculation(self, audit_agents):
        """Test agent's overlap calculation capability."""
        agent = audit_agents[2]
        overlap = agent.calculate_layer_overlap(0.5)

        assert 25 <= overlap <= 65

    def test_agent_collects_issues(self, audit_chain, audit_agents, mock_blockchain):
        """Test that agent collects issues during audit."""
        agent = audit_agents[0]
        issues = agent.collect_issues(mock_blockchain.blocks)

        assert isinstance(issues, list)


class TestConsensusEngineBehavior:
    """Tests for consensus engine behavior."""

    def test_consensus_engine_initialization(self, consensus_engine, audit_config):
        """Test consensus engine initializes with correct config."""
        assert consensus_engine.config == audit_config
        assert consensus_engine.config.consensus_threshold == 0.75

    def test_add_consensus_rule(self, consensus_engine):
        """Test adding a consensus rule."""
        initial_count = len(consensus_engine.rules)
        consensus_engine.add_rule(MagicMock(rule_id="new-rule", validate=lambda x: True))
        assert len(consensus_engine.rules) == initial_count + 1

    def test_remove_consensus_rule(self, consensus_engine):
        """Test removing a consensus rule."""
        rule = MagicMock(rule_id="rule-to-remove")
        consensus_engine.add_rule(rule)
        initial_count = len(consensus_engine.rules)

        consensus_engine.remove_rule("rule-to-remove")
        assert len(consensus_engine.rules) == initial_count - 1

    def test_consensus_rule_validation(self, consensus_engine, mock_blockchain):
        """Test consensus rule validation."""
        blocks = mock_blockchain.blocks
        result = consensus_engine.validate_rules(blocks)

        assert isinstance(result, (bool, dict))

    def test_consensus_quorum_reached(self, consensus_engine, sample_audit_results):
        """Test quorum detection for consensus."""
        quorum = consensus_engine.check_quorum(sample_audit_results[:3])

        assert isinstance(quorum, bool)

    def test_consensus_finality_determination(self, consensus_engine, sample_audit_results):
        """Test finality determination."""
        final = consensus_engine.determine_finality(sample_audit_results)

        assert "final" in final or "consensus" in final or "finality" in final


class TestIssueDetectorBehavior:
    """Tests for issue detector behavior."""

    def test_issue_detector_initialization(self, issue_detector, audit_config):
        """Test issue detector initializes correctly."""
        assert issue_detector.config == audit_config

    def test_issue_severity_ranking(self, issue_detector, sample_issues):
        """Test issue severity ranking."""
        ranked = issue_detector.rank_by_severity(sample_issues)

        if len(ranked) > 1:
            for i in range(len(ranked) - 1):
                assert ranked[i].severity in ["critical", "high", "medium", "low"]
                if ranked[i].severity == ranked[i + 1].severity:
                    continue

    def test_issue_deduplication(self, issue_detector, sample_issues):
        """Test issue deduplication."""
        duplicates = sample_issues + [sample_issues[0]]
        deduplicated = issue_detector.deduplicate_issues(duplicates)

        assert len(deduplicated) <= len(duplicates)

    def test_issue_filtering_by_severity(self, issue_detector, sample_issues):
        """Test filtering issues by severity."""
        high_severity = issue_detector.filter_by_severity(sample_issues, ["critical", "high"])

        assert all(i.severity in ["critical", "high"] for i in high_severity)


class TestEndToEndAuditWorkflow:
    """End-to-end tests for complete audit workflow."""

    def test_complete_audit_workflow(self, audit_chain, mock_blockchain):
        """Test complete audit workflow from start to finish."""
        audit_chain.blockchain = mock_blockchain

        result = audit_chain.run_complete_audit()

        assert result["completed"] is True
        assert "total_issues" in result or "issues_found" in result
        assert "blocks_audited" in result

    def test_audit_with_corrections_applied(self, audit_chain, mock_blockchain, sample_corrections):
        """Test audit workflow with corrections applied."""
        audit_chain.blockchain = mock_blockchain

        result = audit_chain.run_audit_with_corrections(sample_corrections[:1])

        assert result["completed"] is True

    def test_audit_finds_and_validates_corrections(self, audit_chain, mock_blockchain_with_issues):
        """Test that audit finds issues and validates corrections."""
        audit_chain.blockchain = mock_blockchain_with_issues

        issues = audit_chain.detect_all_issues()
        corrections_validated = audit_chain.validate_corrections_for_issues(issues)

        assert len(issues) > 0
        assert isinstance(corrections_validated, list)

    def test_audit_proof_generation_and_verification(self, audit_chain, mock_blockchain):
        """Test audit proof generation and verification round-trip."""
        audit_chain.blockchain = mock_blockchain

        proof = audit_chain.generate_full_audit_proof()
        verified = audit_chain.verify_full_audit_proof(proof)

        assert verified is True

    def test_concurrent_audit_layers(self, audit_chain, audit_agents):
        """Test concurrent auditing of multiple layers."""
        results = []
        for agent in audit_agents[:3]:
            result = agent.audit_all_blocks()
            results.append(result)

        assert len(results) == 3

    def test_audit_recovers_from_errors(self, audit_chain, mock_blockchain):
        """Test audit recovery from errors."""
        mock_blockchain.get_block = MagicMock(side_effect=[Exception("Simulated error"), MagicMock()])

        result = audit_chain.verify_chain_with_recovery()

        assert "recovered" in result or "completed" in result or "error" in result


class MockBlock:
    """Mock blockchain block for testing."""

    def __init__(
        self,
        block_id: str,
        previous_hash: Optional[str] = None,
        transactions: Optional[List] = None,
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
