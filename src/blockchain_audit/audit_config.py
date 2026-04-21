"""
Audit Configuration - Dynamic overlap and verification settings.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from enum import Enum
import hashlib
import time


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditPhase(Enum):
    INITIALIZATION = "initialization"
    VERIFICATION = "verification"
    DETECTION = "detection"
    CORRECTION = "correction"
    CONSENSUS = "consensus"
    FINALIZATION = "finalization"


@dataclass
class AuditConfig:
    OVERLAP_MIN = 0.25
    OVERLAP_MAX = 0.65

    BLOCK_COMPLEXITY_THRESHOLD = 100
    TX_VOLUME_HIGH_THRESHOLD = 1000
    RISK_THRESHOLD_HIGH = 0.8

    MIN_VERIFICATION_PASSES = 2
    MAX_CONSECUTIVE_FAILURES = 3

    GENESIS_HASH = "0" * 64
    AUDIT_INTERVAL = 10

    MAX_AUDIT_DEPTH = 10000
    CHECKPOINT_INTERVAL = 100
    TIMEOUT_SECONDS = 300
    RETRY_ATTEMPTS = 3

    def __init__(self):
        self._overlap_adjustments: Dict[int, float] = {}
        self._risk_cache: Dict[int, RiskLevel] = {}
        self._complexity_cache: Dict[int, int] = {}

    def get_overlap_for_height(self, height: int) -> float:
        if height in self._overlap_adjustments:
            return self._overlap_adjustments[height]
        base_overlap = (self.OVERLAP_MIN + self.OVERLAP_MAX) / 2
        return base_overlap

    def set_overlap_adjustment(self, height: int, overlap: float) -> None:
        clamped_overlap = max(self.OVERLAP_MIN, min(self.OVERLAP_MAX, overlap))
        self._overlap_adjustments[height] = clamped_overlap

    def get_risk_level(self, height: int, block_data: Dict[str, Any]) -> RiskLevel:
        if height in self._risk_cache:
            return self._risk_cache[height]

        risk_score = self._calculate_risk_score(block_data)

        if risk_score >= 0.8:
            level = RiskLevel.CRITICAL
        elif risk_score >= 0.6:
            level = RiskLevel.HIGH
        elif risk_score >= 0.3:
            level = RiskLevel.MEDIUM
        else:
            level = RiskLevel.LOW

        self._risk_cache[height] = level
        return level

    def _calculate_risk_score(self, block_data: Dict[str, Any]) -> float:
        score = 0.0

        tx_count = block_data.get("transaction_count", 0)
        if tx_count > self.TX_VOLUME_HIGH_THRESHOLD:
            score += 0.3
        elif tx_count > self.TX_VOLUME_HIGH_THRESHOLD // 2:
            score += 0.15

        complexity = block_data.get("complexity_score", 0)
        if complexity > self.BLOCK_COMPLEXITY_THRESHOLD:
            score += 0.3
        elif complexity > self.BLOCK_COMPLEXITY_THRESHOLD // 2:
            score += 0.15

        has_smart_contracts = block_data.get("has_smart_contracts", False)
        if has_smart_contracts:
            score += 0.2

        has_large_transfers = block_data.get("has_large_transfers", False)
        if has_large_transfers:
            score += 0.15

        is_checkpoint = block_data.get("is_checkpoint", False)
        if is_checkpoint:
            score += 0.1

        return min(score, 1.0)

    def get_complexity_score(self, block: Dict[str, Any]) -> int:
        height = block.get("height", 0)
        if height in self._complexity_cache:
            return self._complexity_cache[height]

        complexity = 0

        tx_count = block.get("transaction_count", 0)
        complexity += tx_count

        for tx in block.get("transactions", []):
            if tx.get("type") == "contract_deployment":
                complexity += 50
            elif tx.get("type") == "contract_call":
                complexity += 10
            if tx.get("has_internal_transactions"):
                complexity += 5

        if block.get("has_state_changes"):
            complexity += 20

        if block.get("has_cross_chain_operations"):
            complexity += 30

        self._complexity_cache[height] = complexity
        return complexity

    def should_adjust_overlap(self, block: Dict[str, Any]) -> bool:
        risk = self.get_risk_level(block.get("height", 0), block)
        return risk in (RiskLevel.HIGH, RiskLevel.CRITICAL)

    def calculate_adaptive_overlap(self, block: Dict[str, Any]) -> float:
        if not self.should_adjust_overlap(block):
            return self.get_overlap_for_height(block.get("height", 0))

        risk = self.get_risk_level(block.get("height", 0), block)
        base_overlap = self.get_overlap_for_height(block.get("height", 0))

        if risk == RiskLevel.CRITICAL:
            return min(base_overlap * 1.3, self.OVERLAP_MAX)
        elif risk == RiskLevel.HIGH:
            return min(base_overlap * 1.15, self.OVERLAP_MAX)
        return base_overlap

    def get_verification_depth(self, risk_level: RiskLevel) -> int:
        depths = {
            RiskLevel.LOW: 1,
            RiskLevel.MEDIUM: 2,
            RiskLevel.HIGH: 3,
            RiskLevel.CRITICAL: 5,
        }
        return depths.get(risk_level, 1)

    def get_timeout_for_operation(self, operation: str, risk_level: RiskLevel) -> int:
        base_timeouts = {
            "block_verification": 30,
            "transaction_validation": 20,
            "consensus_reach": 60,
            "correction_apply": 45,
            "cryptographic_proof": 30,
        }
        base = base_timeouts.get(operation, 30)
        multiplier = {
            RiskLevel.LOW: 1.0,
            RiskLevel.MEDIUM: 1.5,
            RiskLevel.HIGH: 2.0,
            RiskLevel.CRITICAL: 3.0,
        }
        return int(base * multiplier.get(risk_level, 1.0))


@dataclass
class AuditMetrics:
    total_blocks_audited: int = 0
    total_issues_found: int = 0
    total_issues_resolved: int = 0
    total_corrections_applied: int = 0
    consensus_rounds: int = 0
    average_verification_time: float = 0.0
    false_positive_rate: float = 0.0

    issues_by_severity: Dict[str, int] = field(default_factory=dict)
    issues_by_type: Dict[str, int] = field(default_factory=dict)

    agent_performance: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def record_issue(self, severity: str, issue_type: str) -> None:
        self.total_issues_found += 1
        self.issues_by_severity[severity] = self.issues_by_severity.get(severity, 0) + 1
        self.issues_by_type[issue_type] = self.issues_by_type.get(issue_type, 0) + 1

    def record_resolution(self) -> None:
        self.total_issues_resolved += 1

    def record_correction(self) -> None:
        self.total_corrections_applied += 1

    def update_verification_time(self, elapsed: float) -> None:
        if self.total_blocks_audited == 0:
            self.average_verification_time = elapsed
        else:
            self.average_verification_time = (
                (self.average_verification_time * self.total_blocks_audited + elapsed)
                / (self.total_blocks_audited + 1)
            )

    def get_summary(self) -> Dict[str, Any]:
        return {
            "total_blocks_audited": self.total_blocks_audited,
            "total_issues_found": self.total_issues_found,
            "total_issues_resolved": self.total_issues_resolved,
            "total_corrections_applied": self.total_corrections_applied,
            "consensus_rounds": self.consensus_rounds,
            "average_verification_time": self.average_verification_time,
            "false_positive_rate": self.false_positive_rate,
            "issues_by_severity": self.issues_by_severity,
            "issues_by_type": self.issues_by_type,
        }


@dataclass
class AuditCheckpoint:
    height: int
    block_hash: str
    timestamp: int
    audit_agent_ids: list
    verification_summary: Dict[str, Any]
    merkle_root: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "height": self.height,
            "block_hash": self.block_hash,
            "timestamp": self.timestamp,
            "audit_agent_ids": self.audit_agent_ids,
            "verification_summary": self.verification_summary,
            "merkle_root": self.merkle_root,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditCheckpoint":
        return cls(
            height=data["height"],
            block_hash=data["block_hash"],
            timestamp=data["timestamp"],
            audit_agent_ids=data["audit_agent_ids"],
            verification_summary=data["verification_summary"],
            merkle_root=data["merkle_root"],
        )

    def compute_hash(self) -> str:
        data = f"{self.height}:{self.block_hash}:{self.timestamp}:{','.join(sorted(self.audit_agent_ids))}"
        return hashlib.sha256(data.encode()).hexdigest()
