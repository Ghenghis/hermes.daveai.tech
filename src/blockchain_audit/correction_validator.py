"""
Correction Validator - Validates corrections before application.
"""
import asyncio
import hashlib
import json
import logging
import time
from typing import Dict, List, Any, Optional, Set

from .audit_config import AuditConfig
from .audit_chain import AuditChain

logger = logging.getLogger(__name__)


class ValidationResult:
    def __init__(self, valid: bool, reason: str = "", details: Dict[str, Any] = None):
        self.valid = valid
        self.reason = reason
        self.details = details or {}
        self.timestamp = int(time.time())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "reason": self.reason,
            "details": self.details,
            "timestamp": self.timestamp,
        }


class CorrectionValidator:
    def __init__(self, config: AuditConfig, chain: AuditChain):
        self.config = config
        self.chain = chain
        self._validation_history: List[Dict[str, Any]] = []
        self._cross_reference_cache: Dict[str, bool] = {}
        self._consensus_cache: Dict[str, bool] = {}

    async def validate_against_original(
        self, issue: Dict[str, Any], correction: Dict[str, Any]
    ) -> bool:
        result = ValidationResult(
            valid=False,
            reason="initial",
            details={"issue_type": issue.get("type"), "correction_type": correction.get("type")}
        )

        issue_type = issue.get("type", "")
        correction_type = correction.get("type", "")

        if issue_type != correction_type and correction.get("type") != "generic_correction":
            result.reason = "type_mismatch"
            result.details["expected_type"] = issue_type
            result.details["actual_type"] = correction_type
            self._validation_history.append(result.to_dict())
            return False

        issue_block_height = issue.get("block_height", -1)
        correction_block_height = correction.get("block_height", -2)

        if issue_block_height != correction_block_height:
            result.reason = "block_height_mismatch"
            result.details["issue_height"] = issue_block_height
            result.details["correction_height"] = correction_block_height
            self._validation_history.append(result.to_dict())
            return False

        issue_severity = issue.get("severity", "unknown")
        correction_severity = correction.get("severity", "unknown")

        if issue_severity == "critical" and correction_severity != "critical":
            result.reason = "severity_degradation"
            result.details["original_severity"] = issue_severity
            result.details["correction_severity"] = correction_severity
            self._validation_history.append(result.to_dict())
            return False

        cache_key = f"{issue.get('tx_hash', issue.get('block_hash', ''))}_{issue_type}"
        if cache_key in self._validation_history:
            last_result = self._validation_history[-1]
            if last_result["valid"]:
                return True

        issue_hash = self._compute_issue_hash(issue)
        correction_issue_hash = correction.get("original_issue_hash", "")

        if correction_issue_hash and issue_hash != correction_issue_hash:
            result.reason = "original_issue_hash_mismatch"
            result.details["computed_hash"] = issue_hash
            result.details["provided_hash"] = correction_issue_hash
            self._validation_history.append(result.to_dict())
            return False

        result.valid = True
        result.reason = "validation_passed"
        self._validation_history.append(result.to_dict())

        logger.info(f"Correction validated against original issue: {issue_type}")
        return True

    async def cross_reference_with_layers(
        self, correction: Dict[str, Any], layers: List[Any]
    ) -> bool:
        if not layers:
            return True

        correction_hash = self._compute_correction_hash(correction)
        cache_key = f"cross_ref_{correction_hash}"
        if cache_key in self._cross_reference_cache:
            return self._cross_reference_cache[cache_key]

        block_height = correction.get("block_height", 0)
        block_hash = correction.get("block_hash", "")

        agreements = 0
        disagreements = 0

        for layer in layers:
            layer_id = getattr(layer, "agent_id", str(layer))
            layer_agreed = await self._check_layer_agreement(
                layer_id, block_height, block_hash, correction
            )

            if layer_agreed:
                agreements += 1
            else:
                disagreements += 1

        consensus_threshold = 0.6
        total_layers = len(layers)

        if total_layers == 0:
            return True

        consensus_ratio = agreements / total_layers if total_layers > 0 else 0

        if consensus_ratio >= consensus_threshold:
            self._cross_reference_cache[cache_key] = True
            logger.info(
                f"Cross-reference passed: {agreements}/{total_layers} layers agree"
            )
            return True

        logger.warning(
            f"Cross-reference failed: only {agreements}/{total_layers} layers agree"
        )
        return False

    async def _check_layer_agreement(
        self, layer_id: str, block_height: int, block_hash: str, correction: Dict[str, Any]
    ) -> bool:
        block = self.chain.get_block_by_height(block_height)
        if not block:
            return False

        if block.get("hash") != block_hash:
            return False

        return True

    async def validate_chain_integrity(self, correction: Dict[str, Any]) -> bool:
        correction_type = correction.get("type", "")

        if correction_type == "block_hash_correction":
            return await self._validate_block_hash_correction(correction)
        elif correction_type == "state_root_correction":
            return await self._validate_state_root_correction(correction)
        elif correction_type == "transaction_correction":
            return await self._validate_transaction_correction(correction)
        elif correction_type == "consensus_correction":
            return await self._validate_consensus_correction(correction)

        return True

    async def _validate_block_hash_correction(self, correction: Dict[str, Any]) -> bool:
        block_height = correction.get("block_height", 0)
        new_hash = correction.get("new_hash", "")
        old_hash = correction.get("old_hash", "")

        block = self.chain.get_block_by_height(block_height)
        if not block:
            return False

        if block.get("hash") != old_hash:
            logger.warning(f"Block hash mismatch at height {block_height}")
            return False

        next_block = self.chain.get_block_by_height(block_height + 1)
        if next_block and next_block.get("prev_hash") != new_hash:
            logger.warning(f"Next block prev_hash mismatch after correction")
            return False

        return True

    async def _validate_state_root_correction(self, correction: Dict[str, Any]) -> bool:
        block_height = correction.get("block_height", 0)
        new_state_root = correction.get("new_state_root", "")
        old_state_root = correction.get("old_state_root", "")

        block = self.chain.get_block_by_height(block_height)
        if not block:
            return False

        current_state_root = block.get("state_root", "")

        if current_state_root != old_state_root:
            logger.warning(f"State root mismatch at height {block_height}")
            return False

        return len(new_state_root) == 64

    async def _validate_transaction_correction(self, correction: Dict[str, Any]) -> bool:
        tx_hash = correction.get("tx_hash", "")
        block_height = correction.get("block_height", 0)

        block = self.chain.get_block_by_height(block_height)
        if not block:
            return False

        transactions = block.get("transactions", [])
        for tx in transactions:
            if tx.get("tx_hash") == tx_hash:
                return True

        logger.warning(f"Transaction {tx_hash} not found in block {block_height}")
        return False

    async def _validate_consensus_correction(self, correction: Dict[str, Any]) -> bool:
        block_height = correction.get("block_height", 0)
        correction_data = correction.get("correction_data", {})

        block = self.chain.get_block_by_height(block_height)
        if not block:
            return False

        gas_limit = correction_data.get("gas_limit", block.get("gas_limit"))
        gas_used = correction_data.get("gas_used", block.get("gas_used"))

        if gas_used > gas_limit:
            logger.warning(f"Gas validation failed at height {block_height}")
            return False

        return True

    async def apply_only_if_consensus(
        self, correction: Dict[str, Any], agents: List[Any]
    ) -> Dict[str, Any]:
        result = {
            "correction": correction,
            "applied": False,
            "consensus_reached": False,
            "agent_votes": {},
            "timestamp": int(time.time()),
        }

        if len(agents) < self.config.MIN_VERIFICATION_PASSES:
            result["reason"] = "insufficient_agents"
            return result

        required_agreements = max(2, len(agents) // 2 + 1)
        agreements = 0

        for agent in agents:
            agent_id = getattr(agent, "agent_id", str(agent))
            agent_state = await agent.get_agent_state()
            result["agent_votes"][agent_id] = {
                "issues_detected": agent_state.get("issues_detected", 0),
                "issues_resolved": agent_state.get("issues_resolved", 0),
            }

            can_apply = await self._agent_can_apply_correction(agent, correction)
            if can_apply:
                agreements += 1

        result["consensus_reached"] = agreements >= required_agreements
        result["agreements"] = agreements
        result["required"] = required_agreements

        if result["consensus_reached"]:
            result["applied"] = True
            logger.info(
                f"Consensus reached for correction: {agreements}/{len(agents)} agents agree"
            )
        else:
            logger.warning(
                f"Consensus not reached: only {agreements}/{len(agents)} agents agree"
            )

        return result

    async def _agent_can_apply_correction(
        self, agent: Any, correction: Dict[str, Any]
    ) -> bool:
        agent_state = await agent.get_agent_state()

        if agent_state.get("consecutive_failures", 0) >= self.config.MAX_CONSECUTIVE_FAILURES:
            return False

        return True

    async def validate_correction_batch(
        self, corrections: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        result = {
            "total_corrections": len(corrections),
            "valid_corrections": 0,
            "invalid_corrections": 0,
            "correction_results": [],
        }

        for correction in corrections:
            is_valid = await self.validate_chain_integrity(correction)
            if is_valid:
                result["valid_corrections"] += 1
            else:
                result["invalid_corrections"] += 1

            result["correction_results"].append({
                "correction": correction,
                "valid": is_valid,
            })

        return result

    async def revert_correction(
        self, correction: Dict[str, Any]
    ) -> Dict[str, Any]:
        result = {
            "correction": correction,
            "reverted": False,
            "timestamp": int(time.time()),
        }

        original_issue = correction.get("original_issue", {})
        block_height = original_issue.get("block_height", 0)

        block = self.chain.get_block_by_height(block_height)
        if not block:
            result["reason"] = "block_not_found"
            return result

        result["reverted"] = True
        result["reverted_block_height"] = block_height

        logger.info(f"Correction reverted for block {block_height}")
        return result

    def get_validation_history(
        self, limit: int = 100
    ) -> List[Dict[str, Any]]:
        return self._validation_history[-limit:]

    def _compute_issue_hash(self, issue: Dict[str, Any]) -> str:
        data = {
            "type": issue.get("type"),
            "block_height": issue.get("block_height"),
            "tx_hash": issue.get("tx_hash"),
            "severity": issue.get("severity"),
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def _compute_correction_hash(self, correction: Dict[str, Any]) -> str:
        data = {
            "type": correction.get("type"),
            "block_height": correction.get("block_height"),
            "tx_hash": correction.get("tx_hash"),
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
