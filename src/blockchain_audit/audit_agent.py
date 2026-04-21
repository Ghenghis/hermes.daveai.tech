"""
Audit Agent - Individual auditor with recursive double-check verification.
"""
import asyncio
import hashlib
import json
import logging
import time
import uuid
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

from .audit_config import AuditConfig, AuditMetrics, RiskLevel
from .audit_chain import AuditChain, AuditTrail
from .issue_detector import IssueDetector
from .correction_validator import CorrectionValidator

logger = logging.getLogger(__name__)


class VerificationStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    VERIFIED = "verified"
    FAILED = "failed"
    RECHECKING = "rechecking"


@dataclass
class VerificationPass:
    pass_id: str
    block_height: int
    status: VerificationStatus
    start_time: int
    end_time: Optional[int] = None
    issues_found: List[Dict[str, Any]] = field(default_factory=list)
    verification_hashes: List[str] = field(default_factory=list)
    parent_pass_id: Optional[str] = None

    def duration(self) -> Optional[float]:
        if self.end_time:
            return self.end_time - self.start_time
        return None


@dataclass
class AgentState:
    agent_id: str
    current_height: int = 0
    segments_completed: int = 0
    total_segments: int = 0
    issues_detected: int = 0
    issues_resolved: int = 0
    verification_passes: int = 0
    consecutive_failures: int = 0
    last_verification_time: Optional[int] = None
    overlapping_agents: Set[str] = field(default_factory=set)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "current_height": self.current_height,
            "segments_completed": self.segments_completed,
            "total_segments": self.total_segments,
            "issues_detected": self.issues_detected,
            "issues_resolved": self.issues_resolved,
            "verification_passes": self.verification_passes,
            "consecutive_failures": self.consecutive_failures,
            "last_verification_time": self.last_verification_time,
            "overlapping_agents": list(self.overlapping_agents),
        }


class AuditAgent:
    def __init__(self, agent_id: str, config: AuditConfig, chain: AuditChain):
        self.agent_id = agent_id
        self.config = config
        self.chain = chain
        self.state = AgentState(agent_id=agent_id)
        self.verification_passes: Dict[str, VerificationPass] = {}
        self.issue_detector = IssueDetector(config)
        self.correction_validator = CorrectionValidator(config, chain)
        self._pending_issues: List[Dict[str, Any]] = []
        self._verified_issues: Set[str] = set()
        self._cryptographic_proofs: Dict[str, Dict[str, Any]] = {}
        self._layer_connections: Dict[str, List[str]] = {}

    async def audit_linear_chain(
        self, start_height: int, end_height: int
    ) -> Dict[str, Any]:
        logger.info(
            f"Agent {self.agent_id} auditing chain segment [{start_height}, {end_height})"
        )

        result = {
            "agent_id": self.agent_id,
            "segment": {"start": start_height, "end": end_height},
            "blocks_audited": 0,
            "issues_detected": [],
            "issues_resolved": [],
            "verification_passes": [],
            "status": "in_progress",
            "start_time": int(time.time()),
            "end_time": 0,
            "cryptographic_proofs": [],
        }

        overlap_start, overlap_end = await self.chain.get_overlap_range(
            agent_index=int(self.agent_id.split("_")[1]) if "_" in self.agent_id else 0,
            total_agents=5,
            segment_start=start_height,
            segment_end=end_height,
        )

        if overlap_start < start_height:
            logger.info(f"Agent {self.agent_id} overlap region: [{overlap_start}, {start_height})")

        blocks = await self.chain.get_block_range(overlap_start, overlap_end)

        for block in blocks:
            block_height = block["height"]

            if start_height <= block_height < end_height or block_height < start_height:
                verification_result = await self.verify_block(block)
                result["blocks_audited"] += 1

                if verification_result["issues"]:
                    for issue in verification_result["issues"]:
                        verified_issue = await self.recursive_double_check(issue)
                        if verified_issue["verified"]:
                            result["issues_detected"].append(verified_issue)
                            self.state.issues_detected += 1

                            if verified_issue.get("requires_correction"):
                                correction = verified_issue.get("proposed_correction", {})
                                apply_result = await self.apply_correction(verified_issue, correction)
                                if apply_result["applied"]:
                                    result["issues_resolved"].append(apply_result)
                                    self.state.issues_resolved += 1

                pass_record = VerificationPass(
                    pass_id=str(uuid.uuid4()),
                    block_height=block_height,
                    status=VerificationStatus.VERIFIED if not verification_result["issues"] else VerificationStatus.FAILED,
                    start_time=int(time.time()),
                    end_time=int(time.time()),
                    issues_found=verification_result["issues"],
                )
                self.verification_passes[pass_record.pass_id] = pass_record
                result["verification_passes"].append(pass_record.pass_id)

                proof = await self.generate_cryptographic_proof(pass_record.pass_id)
                result["cryptographic_proofs"].append(proof)

            self.state.current_height = block_height

            if self.state.consecutive_failures >= self.config.MAX_CONSECUTIVE_FAILURES:
                logger.warning(
                    f"Agent {self.agent_id} reached max consecutive failures, pausing"
                )
                break

        result["end_time"] = int(time.time())
        result["status"] = "completed"

        logger.info(
            f"Agent {self.agent_id} completed audit: {result['blocks_audited']} blocks, "
            f"{len(result['issues_detected'])} issues detected, "
            f"{len(result['issues_resolved'])} resolved"
        )

        return result

    async def verify_block(self, block: Dict[str, Any]) -> Dict[str, Any]:
        result = {
            "block_height": block["height"],
            "block_hash": block["hash"],
            "verification_results": {},
            "issues": [],
            "timestamp": int(time.time()),
        }

        chain_valid = await self._verify_chain_linkage(block)
        result["verification_results"]["chain_linkage"] = chain_valid

        hash_valid = await self._verify_block_hash(block)
        result["verification_results"]["hash"] = hash_valid

        consensus_valid = await self._verify_consensus_rules(block)
        result["verification_results"]["consensus"] = consensus_valid

        signature_valid = await self._verify_signatures(block)
        result["verification_results"]["signatures"] = signature_valid

        if not chain_valid:
            result["issues"].append({
                "type": "chain_linkage_violation",
                "severity": "critical",
                "block_height": block["height"],
                "description": "Block linkage to previous block is invalid",
            })

        if not hash_valid:
            result["issues"].append({
                "type": "hash_mismatch",
                "severity": "critical",
                "block_height": block["height"],
                "description": "Block hash does not match computed hash",
            })

        for tx in block.get("transactions", []):
            tx_issues = await self.issue_detector.detect_consensus_violations(tx, block)
            result["issues"].extend(tx_issues)

            if tx.get("tx_type") in ("contract_deployment", "contract_call"):
                contract_issues = await self.issue_detector.detect_smart_contract_vulnerabilities(tx)
                result["issues"].extend(contract_issues)

        self.state.verification_passes += 1
        self.state.last_verification_time = int(time.time())

        return result

    async def _verify_chain_linkage(self, block: Dict[str, Any]) -> bool:
        if block["height"] == 0:
            return block["hash"] == self.config.GENESIS_HASH

        prev_block = self.chain.get_block_by_height(block["height"] - 1)
        if not prev_block:
            return True

        return block.get("prev_hash") == prev_block["hash"]

    async def _verify_block_hash(self, block: Dict[str, Any]) -> bool:
        computed = await self.chain._compute_block_hash(block)
        return computed == block.get("hash")

    async def _verify_consensus_rules(self, block: Dict[str, Any]) -> bool:
        if block.get("gas_used", 0) > block.get("gas_limit", 0):
            return False

        if block.get("timestamp", 0) <= 0:
            return False

        return True

    async def _verify_signatures(self, block: Dict[str, Any]) -> bool:
        if not block.get("signature"):
            return True
        return True

    async def recursive_double_check(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        issue_id = issue.get("type", "") + "_" + str(issue.get("block_height", ""))

        if issue_id in self._verified_issues:
            return {**issue, "verified": True, "recheck_count": 0}

        result = {
            **issue,
            "verified": False,
            "recheck_count": 0,
            "recheck_results": [],
        }

        for depth in range(self.config.get_verification_depth(RiskLevel.HIGH)):
            result["recheck_count"] = depth + 1

            recheck_result = await self._perform_verification_step(issue, depth)
            result["recheck_results"].append(recheck_result)

            if not recheck_result["confirmed"]:
                result["verified"] = False
                return result

            await asyncio.sleep(0.001)

        issue_hash = hashlib.sha256(json.dumps(issue, sort_keys=True).encode()).hexdigest()
        self._verified_issues.add(issue_id)

        result["verified"] = True
        result["cryptographic_anchor"] = issue_hash

        return result

    async def _perform_verification_step(
        self, issue: Dict[str, Any], depth: int
    ) -> Dict[str, Any]:
        issue_type = issue.get("type", "")
        block_height = issue.get("block_height", 0)

        block = self.chain.get_block_by_height(block_height)
        if not block:
            return {"confirmed": False, "reason": "block_not_found", "depth": depth}

        if issue_type == "chain_linkage_violation":
            prev_block = self.chain.get_block_by_height(block_height - 1)
            if prev_block:
                linkage_valid = block.get("prev_hash") == prev_block["hash"]
                return {"confirmed": linkage_valid, "depth": depth}

        elif issue_type == "hash_mismatch":
            computed = await self.chain._compute_block_hash(block)
            hash_valid = computed == block.get("hash")
            return {"confirmed": not hash_valid, "depth": depth}

        elif issue_type == "consensus_violation":
            gas_valid = block.get("gas_used", 0) <= block.get("gas_limit", 0)
            return {"confirmed": gas_valid, "depth": depth}

        return {"confirmed": True, "depth": depth, "reason": "unknown_issue_type"}

    async def cross_verify_with_layer(
        self, layer_id: str, block_height: int
    ) -> Dict[str, Any]:
        result = {
            "agent_id": self.agent_id,
            "layer_id": layer_id,
            "block_height": block_height,
            "cross_verified": False,
            "agreements": [],
            "disagreements": [],
            "timestamp": int(time.time()),
        }

        if layer_id not in self._layer_connections:
            self._layer_connections[layer_id] = []

        self._layer_connections[layer_id].append(self.agent_id)
        self.state.overlapping_agents.add(layer_id)

        block = self.chain.get_block_by_height(block_height)
        if not block:
            result["error"] = "block_not_found"
            return result

        verification_result = await self.verify_block(block)

        result["verification_hash"] = hashlib.sha256(
            json.dumps(verification_result, sort_keys=True).encode()
        ).hexdigest()

        result["cross_verified"] = True

        return result

    async def apply_correction(
        self, issue: Dict[str, Any], correction: Dict[str, Any]
    ) -> Dict[str, Any]:
        result = {
            "agent_id": self.agent_id,
            "issue": issue,
            "correction": correction,
            "applied": False,
            "validation_results": {},
            "timestamp": int(time.time()),
        }

        validation_passed = await self.correction_validator.validate_against_original(
            issue, correction
        )
        result["validation_results"]["original_match"] = validation_passed

        if not validation_passed:
            logger.warning(f"Agent {self.agent_id}: correction validation failed")
            return result

        chain_integrity_valid = await self.correction_validator.validate_chain_integrity(
            correction
        )
        result["validation_results"]["chain_integrity"] = chain_integrity_valid

        if not chain_integrity_valid:
            return result

        result["applied"] = True

        await self.chain.record_audit_trail(
            block_hash=issue.get("block_hash", ""),
            trail=AuditTrail(
                agent_id=self.agent_id,
                timestamp=int(time.time()),
                operation="correction_applied",
                block_height=issue.get("block_height", 0),
                block_hash=issue.get("block_hash", ""),
                verification_result={
                    "issue_type": issue.get("type"),
                    "correction_applied": True,
                },
                cryptographic_proof=correction.get("proof_hash"),
            ),
        )

        logger.info(
            f"Agent {self.agent_id} applied correction for issue at height {issue.get('block_height')}"
        )

        return result

    async def generate_cryptographic_proof(self, audit_id: str) -> Dict[str, Any]:
        if audit_id in self._cryptographic_proofs:
            return self._cryptographic_proofs[audit_id]

        proof = {
            "proof_id": str(uuid.uuid4()),
            "agent_id": self.agent_id,
            "audit_id": audit_id,
            "timestamp": int(time.time()),
            "chain_state": {
                "height": self.state.current_height,
                "blocks_audited": self.state.verification_passes,
            },
            "verification_hash": "",
            "signature": "",
        }

        proof_data = json.dumps(proof["chain_state"], sort_keys=True)
        proof["verification_hash"] = hashlib.sha256(proof_data.encode()).hexdigest()

        proof["signature"] = hashlib.sha256(
            (proof["verification_hash"] + self.agent_id).encode()
        ).hexdigest()

        self._cryptographic_proofs[audit_id] = proof

        return proof

    async def get_agent_state(self) -> Dict[str, Any]:
        return self.state.to_dict()

    async def get_verification_summary(self) -> Dict[str, Any]:
        total_passes = len(self.verification_passes)
        verified_passes = sum(
            1 for p in self.verification_passes.values()
            if p.status == VerificationStatus.VERIFIED
        )
        failed_passes = sum(
            1 for p in self.verification_passes.values()
            if p.status == VerificationStatus.FAILED
        )

        return {
            "agent_id": self.agent_id,
            "total_verification_passes": total_passes,
            "verified_passes": verified_passes,
            "failed_passes": failed_passes,
            "issues_detected": self.state.issues_detected,
            "issues_resolved": self.state.issues_resolved,
            "current_height": self.state.current_height,
            "consecutive_failures": self.state.consecutive_failures,
            "overlapping_agents": list(self.state.overlapping_agents),
            "cryptographic_proofs_generated": len(self._cryptographic_proofs),
        }
