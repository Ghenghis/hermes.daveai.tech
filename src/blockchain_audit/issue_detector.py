"""
Issue Detector - Comprehensive blockchain issue detection.
"""
import asyncio
import hashlib
import logging
import re
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field

from .audit_config import AuditConfig, RiskLevel

logger = logging.getLogger(__name__)


@dataclass
class Issue:
    type: str
    severity: str
    block_height: int
    tx_hash: Optional[str] = None
    description: str = ""
    affected_components: List[str] = field(default_factory=list)
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "severity": self.severity,
            "block_height": self.block_height,
            "tx_hash": self.tx_hash,
            "description": self.description,
            "affected_components": self.affected_components,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


class IssueDetector:
    def __init__(self, config: AuditConfig):
        self.config = config
        self._detected_issues: Dict[str, List[Issue]] = {}
        self._issue_cache: Dict[str, bool] = {}
        self._known_vulnerabilities: Dict[str, str] = self._load_known_vulnerabilities()

    def _load_known_vulnerabilities(self) -> Dict[str, str]:
        return {
            "reentrancy": "Reentrancy vulnerability detected in smart contract",
            "integer_overflow": "Integer overflow/underflow vulnerability",
            "access_control": "Missing or improper access control",
            "front_running": "Potential front-running vulnerability",
            "timestamp_dependency": "Contract depends on block timestamp",
            "tx.origin_usage": "Use of tx.origin for authorization",
        }

    async def detect_consensus_violations(
        self, tx: Dict[str, Any], prev_block: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        issues = []

        if tx.get("nonce", 0) < 0:
            issues.append({
                "type": "consensus_violation",
                "severity": "critical",
                "block_height": tx.get("block_height", 0),
                "tx_hash": tx.get("tx_hash"),
                "description": "Transaction has invalid nonce",
                "affected_components": ["transaction", "mempool"],
                "confidence": 1.0,
            })

        if tx.get("gas_limit", 0) > 8000000:
            issues.append({
                "type": "consensus_violation",
                "severity": "high",
                "block_height": tx.get("block_height", 0),
                "tx_hash": tx.get("tx_hash"),
                "description": "Gas limit exceeds maximum block gas limit",
                "affected_components": ["block", "gas_calculation"],
                "confidence": 0.9,
            })

        return issues

    async def detect_smart_contract_vulnerabilities(
        self, tx: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        issues = []
        tx_type = tx.get("tx_type", "")
        data = tx.get("data", b"")

        if isinstance(data, str):
            data = data.encode()

        if tx_type == "contract_deployment":
            if self._contains_reentrancy_pattern(data):
                issues.append({
                    "type": "smart_contract_vulnerability",
                    "severity": "critical",
                    "block_height": tx.get("block_height", 0),
                    "tx_hash": tx.get("tx_hash"),
                    "description": "Potential reentrancy vulnerability in deployed contract",
                    "affected_components": ["smart_contract", "external_calls"],
                    "confidence": 0.85,
                    "metadata": {"vulnerability_type": "reentrancy"},
                })

            if self._contains_integer_overflow_pattern(data):
                issues.append({
                    "type": "smart_contract_vulnerability",
                    "severity": "critical",
                    "block_height": tx.get("block_height", 0),
                    "tx_hash": tx.get("tx_hash"),
                    "description": "Potential integer overflow/underflow in arithmetic operations",
                    "affected_components": ["smart_contract", "arithmetic"],
                    "confidence": 0.8,
                    "metadata": {"vulnerability_type": "integer_overflow"},
                })

            if self._contains_access_control_issue(data):
                issues.append({
                    "type": "smart_contract_vulnerability",
                    "severity": "high",
                    "block_height": tx.get("block_height", 0),
                    "tx_hash": tx.get("tx_hash"),
                    "description": "Missing or improper access control mechanisms",
                    "affected_components": ["smart_contract", "access_control"],
                    "confidence": 0.75,
                    "metadata": {"vulnerability_type": "access_control"},
                })

        elif tx_type == "contract_call":
            if self._detect_frontrunning_pattern(tx):
                issues.append({
                    "type": "smart_contract_vulnerability",
                    "severity": "medium",
                    "block_height": tx.get("block_height", 0),
                    "tx_hash": tx.get("tx_hash"),
                    "description": "Transaction may be susceptible to front-running",
                    "affected_components": ["mempool", "transaction_order"],
                    "confidence": 0.7,
                    "metadata": {"vulnerability_type": "front_running"},
                })

        return issues

    async def detect_double_spend(
        self, tx: Dict[str, Any], utxo_set: Set[str]
    ) -> List[Dict[str, Any]]:
        issues = []
        tx_hash = tx.get("tx_hash", "")

        if tx_hash in utxo_set:
            issues.append({
                "type": "double_spend",
                "severity": "critical",
                "block_height": tx.get("block_height", 0),
                "tx_hash": tx_hash,
                "description": "Transaction input already spent",
                "affected_components": ["utxo_set", "transaction_inputs"],
                "confidence": 1.0,
            })

        return issues

    async def detect_transaction_malleability(
        self, tx: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        issues = []
        tx_hash = tx.get("tx_hash", "")

        if tx.get("signature") and len(tx.get("signature", "")) < 64:
            issues.append({
                "type": "transaction_malleability",
                "severity": "medium",
                "block_height": tx.get("block_height", 0),
                "tx_hash": tx_hash,
                "description": "Transaction signature has unexpected length",
                "affected_components": ["transaction", "signature"],
                "confidence": 0.6,
            })

        if self._has_non_canonical_signature(tx):
            issues.append({
                "type": "transaction_malleability",
                "severity": "low",
                "block_height": tx.get("block_height", 0),
                "tx_hash": tx_hash,
                "description": "Transaction uses non-canonical signature encoding",
                "affected_components": ["transaction", "signature_encoding"],
                "confidence": 0.5,
            })

        return issues

    async def detect_orphaned_blocks(
        self, block: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        issues = []

        if block.get("is_orphaned"):
            issues.append({
                "type": "orphaned_block",
                "severity": "medium",
                "block_height": block["height"],
                "block_hash": block.get("hash"),
                "description": "Block is orphaned or on a minority fork",
                "affected_components": ["chain_reorganization", "block_tree"],
                "confidence": 1.0,
                "metadata": {
                    "fork_depth": block.get("fork_depth", 0),
                    "orphan_reason": block.get("orphan_reason", "unknown"),
                },
            })

        if block.get("is_stale"):
            issues.append({
                "type": "stale_block",
                "severity": "low",
                "block_height": block["height"],
                "block_hash": block.get("hash"),
                "description": "Block is stale - not part of longest chain",
                "affected_components": ["chain_selection", "block_status"],
                "confidence": 0.9,
            })

        return issues

    async def detect_state_inconsistencies(
        self, state: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        issues = []

        expected_root = state.get("expected_state_root")
        actual_root = state.get("actual_state_root")

        if expected_root and actual_root and expected_root != actual_root:
            issues.append({
                "type": "state_inconsistency",
                "severity": "critical",
                "block_height": state.get("height", 0),
                "description": "State trie root mismatch",
                "affected_components": ["state_trie", "merkle_proof"],
                "confidence": 1.0,
                "metadata": {
                    "expected_root": expected_root,
                    "actual_root": actual_root,
                },
            })

        account_nonce_mismatch = state.get("account_nonce_mismatch", False)
        if account_nonce_mismatch:
            issues.append({
                "type": "state_inconsistency",
                "severity": "high",
                "block_height": state.get("height", 0),
                "description": "Account nonce does not match transaction nonce",
                "affected_components": ["account_state", "nonce_tracking"],
                "confidence": 0.95,
            })

        balance_inconsistency = state.get("balance_inconsistency", False)
        if balance_inconsistency:
            issues.append({
                "type": "state_inconsistency",
                "severity": "high",
                "block_height": state.get("height", 0),
                "description": "Account balance inconsistency detected",
                "affected_components": ["account_state", "balance_tracking"],
                "confidence": 0.95,
            })

        return issues

    async def detect_signature_failures(
        self, tx: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        issues = []

        if not tx.get("signature"):
            issues.append({
                "type": "signature_failure",
                "severity": "critical",
                "block_height": tx.get("block_height", 0),
                "tx_hash": tx.get("tx_hash"),
                "description": "Transaction is missing required signature",
                "affected_components": ["transaction", "signature_verification"],
                "confidence": 1.0,
            })
            return issues

        signature = tx.get("signature", "")
        if len(signature) < 64:
            issues.append({
                "type": "signature_failure",
                "severity": "high",
                "block_height": tx.get("block_height", 0),
                "tx_hash": tx.get("tx_hash"),
                "description": "Signature length is invalid",
                "affected_components": ["transaction", "signature_verification"],
                "confidence": 0.9,
            })

        if self._signature_has_null_bytes(signature):
            issues.append({
                "type": "signature_failure",
                "severity": "high",
                "block_height": tx.get("block_height", 0),
                "tx_hash": tx.get("tx_hash"),
                "description": "Signature contains null bytes which may indicate corruption",
                "affected_components": ["transaction", "signature_encoding"],
                "confidence": 0.8,
            })

        return issues

    async def detect_gas_optimization_issues(
        self, tx: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        issues = []

        gas_used = tx.get("gas_used", 0)
        gas_limit = tx.get("gas_limit", 1)
        gas_ratio = gas_used / gas_limit if gas_limit > 0 else 0

        if gas_ratio < 0.1:
            issues.append({
                "type": "gas_optimization",
                "severity": "low",
                "block_height": tx.get("block_height", 0),
                "tx_hash": tx.get("tx_hash"),
                "description": "Transaction uses less than 10% of allocated gas - potential over-estimation",
                "affected_components": ["gas_estimation", "transaction_cost"],
                "confidence": 0.6,
                "metadata": {"gas_used_ratio": gas_ratio},
            })

        if gas_ratio > 0.95 and tx.get("tx_type") == "contract_call":
            issues.append({
                "type": "gas_optimization",
                "severity": "medium",
                "block_height": tx.get("block_height", 0),
                "tx_hash": tx.get("tx_hash"),
                "description": "Contract execution consumes over 95% of gas limit",
                "affected_components": ["gas_limit", "contract_execution"],
                "confidence": 0.7,
                "metadata": {"gas_used_ratio": gas_ratio},
            })

        if self._has_unnecessary_storage_ops(tx):
            issues.append({
                "type": "gas_optimization",
                "severity": "low",
                "block_height": tx.get("block_height", 0),
                "tx_hash": tx.get("tx_hash"),
                "description": "Transaction performs unnecessary storage operations",
                "affected_components": ["storage", "gas_cost"],
                "confidence": 0.5,
            })

        return issues

    async def detect_transitively_affected(
        self, issue: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        affected = []
        issue_type = issue.get("type", "")
        block_height = issue.get("block_height", 0)

        if issue_type == "consensus_violation":
            affected.append({
                "type": "related_consensus_issue",
                "severity": "medium",
                "block_height": block_height + 1,
                "description": "Transitively affected by consensus violation",
                "affected_components": ["chain_continuity"],
                "confidence": 0.6,
            })

        elif issue_type == "state_inconsistency":
            affected.append({
                "type": "related_state_issue",
                "severity": "high",
                "block_height": block_height + 1,
                "description": "Next block may have state inconsistencies due to prior issue",
                "affected_components": ["state_tie", "block_validation"],
                "confidence": 0.75,
            })

        elif issue_type == "double_spend":
            affected.append({
                "type": "related_double_spend",
                "severity": "critical",
                "block_height": block_height,
                "description": "Double spend may affect subsequent transactions using same inputs",
                "affected_components": ["utxo_set", "transaction_graph"],
                "confidence": 0.9,
            })

        return affected

    def _contains_reentrancy_pattern(self, data: bytes) -> bool:
        if isinstance(data, str):
            data = data.encode()

        patterns = [
            b"call\\.value",
            b"send\\.",
            b"transfer\\(",
            b"call\\(",
        ]

        try:
            data_str = data.decode("utf-8", errors="ignore")
            for pattern in patterns:
                if re.search(pattern.decode("utf-8", errors="ignore"), data_str):
                    return True
        except Exception:
            pass

        return False

    def _contains_integer_overflow_pattern(self, data: bytes) -> bool:
        if isinstance(data, str):
            data = data.encode()

        try:
            data_str = data.decode("utf-8", errors="ignore")
            dangerous_ops = [
                r"\+\s*\d+",
                r"-\s*\d+",
                r"\*\s*\d+",
                r"/\s*\d+",
                r"%\s*\d+",
            ]

            for op in dangerous_ops:
                if re.search(op, data_str):
                    return True
        except Exception:
            pass

        return False

    def _contains_access_control_issue(self, data: bytes) -> bool:
        if isinstance(data, str):
            data = data.encode()

        try:
            data_str = data.decode("utf-8", errors="ignore")
            if "public" in data_str and "onlyOwner" not in data_str:
                return True
            if "external" in data_str and "access" not in data_str.lower():
                return True
        except Exception:
            pass

        return False

    def _detect_frontrunning_pattern(self, tx: Dict[str, Any]) -> bool:
        to_addr = tx.get("to_addr", "")
        value = tx.get("value", 0)

        if value > 1000000:
            return True

        return False

    def _has_non_canonical_signature(self, tx: Dict[str, Any]) -> bool:
        signature = tx.get("signature", "")
        if len(signature) != 64:
            return True

        try:
            first_byte = int(signature[:2], 16)
            if first_byte >= 27:
                return True
        except Exception:
            return True

        return False

    def _signature_has_null_bytes(self, signature: str) -> bool:
        if len(signature) < 128:
            return False

        try:
            sig_bytes = bytes.fromhex(signature)
            return b"\\x00" in sig_bytes or sig_bytes[0] == 0 or sig_bytes[32] == 0
        except Exception:
            return False

    def _has_unnecessary_storage_ops(self, tx: Dict[str, Any]) -> bool:
        data = tx.get("data", b"")
        if isinstance(data, str):
            data = data.encode()

        storage_patterns = [b"SSTORE", b"SLOAD"]
        try:
            data_str = data.decode("utf-8", errors="ignore")
            count = sum(1 for p in storage_patterns if p.decode() in data_str)
            return count > 10
        except Exception:
            return False
