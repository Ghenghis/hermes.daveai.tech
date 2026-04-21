"""
Audit Chain - Linear blockchain verification from genesis to current state.
"""
import asyncio
import hashlib
import json
import logging
from typing import Dict, List, Any, Optional, Callable, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum

from .audit_config import AuditConfig, AuditCheckpoint, AuditMetrics, RiskLevel

logger = logging.getLogger(__name__)


class ChainIntegrityStatus(Enum):
    VALID = "valid"
    INVALID = "invalid"
    UNKNOWN = "unknown"
    VERIFYING = "verifying"


@dataclass
class BlockHeader:
    height: int
    hash: str
    prev_hash: str
    timestamp: int
    merkle_root: str
    state_root: str
    receipt_root: str
    gas_used: int
    gas_limit: int
    validator: str
    signature: Optional[str] = None
    extra_data: Optional[bytes] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "height": self.height,
            "hash": self.hash,
            "prev_hash": self.prev_hash,
            "timestamp": self.timestamp,
            "merkle_root": self.merkle_root,
            "state_root": self.state_root,
            "receipt_root": self.receipt_root,
            "gas_used": self.gas_used,
            "gas_limit": self.gas_limit,
            "validator": self.validator,
            "signature": self.signature,
            "extra_data": self.extra_data.hex() if self.extra_data else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BlockHeader":
        return cls(
            height=data["height"],
            hash=data["hash"],
            prev_hash=data["prev_hash"],
            timestamp=data["timestamp"],
            merkle_root=data["merkle_root"],
            state_root=data["state_root"],
            receipt_root=data["receipt_root"],
            gas_used=data["gas_used"],
            gas_limit=data["gas_limit"],
            validator=data["validator"],
            signature=data.get("signature"),
            extra_data=bytes.fromhex(data["extra_data"]) if data.get("extra_data") else None,
        )


@dataclass
class Transaction:
    tx_hash: str
    block_height: int
    from_addr: str
    to_addr: Optional[str]
    value: int
    gas_price: int
    gas_limit: int
    data: bytes
    nonce: int
    signature: Optional[str] = None
    tx_type: str = "transfer"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tx_hash": self.tx_hash,
            "block_height": self.block_height,
            "from_addr": self.from_addr,
            "to_addr": self.to_addr,
            "value": self.value,
            "gas_price": self.gas_price,
            "gas_limit": self.gas_limit,
            "data": self.data.hex() if self.data else None,
            "nonce": self.nonce,
            "signature": self.signature,
            "type": self.tx_type,
        }


@dataclass
class AuditTrail:
    agent_id: str
    timestamp: int
    operation: str
    block_height: int
    block_hash: str
    verification_result: Dict[str, Any]
    cryptographic_proof: Optional[str] = None
    parent_trail_hash: Optional[str] = None

    def compute_hash(self) -> str:
        data = (
            f"{self.agent_id}:{self.timestamp}:{self.operation}:"
            f"{self.block_height}:{self.block_hash}:{json.dumps(self.verification_result, sort_keys=True)}"
        )
        return hashlib.sha256(data.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "timestamp": self.timestamp,
            "operation": self.operation,
            "block_height": self.block_height,
            "block_hash": self.block_hash,
            "verification_result": self.verification_result,
            "cryptographic_proof": self.cryptographic_proof,
            "parent_trail_hash": self.parent_trail_hash,
            "trail_hash": self.compute_hash(),
        }


class AuditChain:
    def __init__(self, config: AuditConfig):
        self.config = config
        self.blocks: List[Dict[str, Any]] = []
        self.audit_trails: Dict[str, List[AuditTrail]] = {}
        self.checkpoints: List[AuditCheckpoint] = []
        self.metrics = AuditMetrics()
        self._integrity_cache: Dict[int, ChainIntegrityStatus] = {}
        self._utxo_set: set = set()
        self._state_cache: Dict[int, Dict[str, Any]] = {}
        self._block_provider: Optional[Callable] = None

    async def load_from_genesis(
        self, block_provider: Callable[[int], AsyncGenerator[Dict[str, Any], None]]
    ) -> int:
        self._block_provider = block_provider
        current_height = 0
        prev_hash = self.config.GENESIS_HASH

        logger.info("Loading blockchain from genesis...")

        async for block in block_provider(0):
            if not await self._validate_block_structure(block):
                logger.error(f"Invalid block structure at height {current_height}")
                continue

            if block["height"] != current_height:
                logger.warning(f"Height mismatch: expected {current_height}, got {block['height']}")
                current_height = block["height"]

            if block["prev_hash"] != prev_hash:
                logger.error(f"Chain broken at height {current_height}: prev_hash mismatch")
                break

            self.blocks.append(block)
            self._update_caches(block)
            prev_hash = block["hash"]
            current_height += 1

        logger.info(f"Loaded {len(self.blocks)} blocks from genesis")
        return len(self.blocks)

    def _update_caches(self, block: Dict[str, Any]) -> None:
        height = block["height"]
        self._integrity_cache[height] = ChainIntegrityStatus.UNKNOWN

        for tx in block.get("transactions", []):
            if tx.get("tx_type") == "transfer":
                self._utxo_set.add(tx["tx_hash"])

        self._state_cache[height] = block.get("state_root", {})

    async def verify_linear_integrity(self, agent_id: str) -> Dict[str, Any]:
        logger.info(f"Agent {agent_id} starting linear chain verification")

        results = {
            "agent_id": agent_id,
            "blocks_verified": 0,
            "blocks_failed": 0,
            "chain_intact": True,
            "issues": [],
            "verification_hashes": [],
            "start_time": 0,
            "end_time": 0,
        }

        import time
        results["start_time"] = int(time.time())

        prev_hash = self.config.GENESIS_HASH

        for i, block in enumerate(self.blocks):
            height = block["height"]

            if height % self.config.AUDIT_INTERVAL != 0 and height != len(self.blocks) - 1:
                continue

            chain_valid = await self._verify_block_link(block, prev_hash)
            hash_valid = await self._verify_block_hash(block)
            consensus_valid = await self._verify_consensus_rules(block)

            trail = AuditTrail(
                agent_id=agent_id,
                timestamp=int(time.time()),
                operation="linear_verification",
                block_height=height,
                block_hash=block["hash"],
                verification_result={
                    "chain_valid": chain_valid,
                    "hash_valid": hash_valid,
                    "consensus_valid": consensus_valid,
                },
            )
            await self.record_audit_trail(block["hash"], trail)

            results["verification_hashes"].append(trail.compute_hash())

            if not (chain_valid and hash_valid and consensus_valid):
                results["blocks_failed"] += 1
                results["chain_intact"] = False
                results["issues"].append({
                    "height": height,
                    "hash": block["hash"],
                    "chain_valid": chain_valid,
                    "hash_valid": hash_valid,
                    "consensus_valid": consensus_valid,
                })
            else:
                results["blocks_verified"] += 1

            prev_hash = block["hash"]

            if height % self.config.CHECKPOINT_INTERVAL == 0:
                checkpoint = AuditCheckpoint(
                    height=height,
                    block_hash=block["hash"],
                    timestamp=block["timestamp"],
                    audit_agent_ids=[agent_id],
                    verification_summary={"blocks_verified": results["blocks_verified"]},
                    merkle_root=block.get("merkle_root", ""),
                )
                self.checkpoints.append(checkpoint)

        results["end_time"] = int(time.time())
        self.metrics.total_blocks_audited += results["blocks_verified"]

        logger.info(
            f"Agent {agent_id} completed verification: "
            f"{results['blocks_verified']} verified, {results['blocks_failed']} failed"
        )

        return results

    async def _verify_block_link(self, block: Dict[str, Any], expected_prev_hash: str) -> bool:
        return block.get("prev_hash") == expected_prev_hash

    async def _verify_block_hash(self, block: Dict[str, Any]) -> bool:
        computed_hash = await self._compute_block_hash(block)
        return computed_hash == block.get("hash")

    async def _compute_block_hash(self, block: Dict[str, Any]) -> str:
        header_data = {
            "height": block["height"],
            "prev_hash": block["prev_hash"],
            "timestamp": block["timestamp"],
            "merkle_root": block["merkle_root"],
            "state_root": block.get("state_root", ""),
            "receipt_root": block.get("receipt_root", ""),
            "gas_used": block.get("gas_used", 0),
            "gas_limit": block.get("gas_limit", 0),
            "validator": block.get("validator", ""),
        }
        data_str = json.dumps(header_data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()

    async def _verify_consensus_rules(self, block: Dict[str, Any]) -> bool:
        if block.get("timestamp", 0) <= 0:
            return False

        gas_limit = block.get("gas_limit", 0)
        gas_used = block.get("gas_used", 0)
        if gas_used > gas_limit:
            return False

        return True

    async def get_block_range(
        self, start_height: int, end_height: int
    ) -> List[Dict[str, Any]]:
        if start_height < 0:
            start_height = 0
        if end_height > len(self.blocks):
            end_height = len(self.blocks)

        return [block for block in self.blocks if start_height <= block["height"] < end_height]

    async def record_audit_trail(self, block_hash: str, trail: AuditTrail) -> None:
        if block_hash not in self.audit_trails:
            self.audit_trails[block_hash] = []

        self.audit_trails[block_hash].append(trail)

        logger.debug(
            f"Recorded audit trail for block {block_hash[:8]}... by agent {trail.agent_id}"
        )

    def calculate_dynamic_overlap(self, block_height: int) -> float:
        if block_height >= len(self.blocks):
            return self.config.get_overlap_for_height(block_height)

        block = self.blocks[block_height]
        return self.config.calculate_adaptive_overlap(block)

    async def get_overlap_range(
        self, agent_index: int, total_agents: int, segment_start: int, segment_end: int
    ) -> tuple[int, int]:
        segment_size = segment_end - segment_start
        overlap_size = int(segment_size * self.calculate_dynamic_overlap(segment_start))

        step = segment_size // total_agents
        start = segment_start + (agent_index * step)
        end = start + step

        if agent_index > 0:
            overlap_start = start - overlap_size
            start = max(segment_start, overlap_start)

        if agent_index < total_agents - 1:
            next_start = segment_start + ((agent_index + 1) * step)
            overlap_end = end + overlap_size
            end = min(segment_end, overlap_end)

        return start, end

    async def get_audit_trail_for_block(self, block_hash: str) -> List[Dict[str, Any]]:
        trails = self.audit_trails.get(block_hash, [])
        return [trail.to_dict() for trail in trails]

    async def get_checkpoints(self) -> List[Dict[str, Any]]:
        return [cp.to_dict() for cp in self.checkpoints]

    async def verify_checkpoint_merkle_proof(
        self, checkpoint: AuditCheckpoint, proof: List[str]
    ) -> bool:
        current_hash = checkpoint.merkle_root

        for sibling in proof:
            combined = hashlib.sha256(
                (current_hash + sibling).encode()
            ).hexdigest()
            current_hash = combined

        return current_hash == checkpoint.merkle_root

    async def get_chain_state_at_height(self, height: int) -> Optional[Dict[str, Any]]:
        if height in self._state_cache:
            return self._state_cache[height]
        return None

    async def get_utxo_set(self) -> set:
        return self._utxo_set.copy()

    def get_latest_block(self) -> Optional[Dict[str, Any]]:
        if self.blocks:
            return self.blocks[-1]
        return None

    def get_block_by_height(self, height: int) -> Optional[Dict[str, Any]]:
        for block in self.blocks:
            if block["height"] == height:
                return block
        return None

    def get_total_blocks(self) -> int:
        return len(self.blocks)

    async def reorg_chains(self, fork_heights: List[int], new_blocks: List[Dict[str, Any]]) -> bool:
        for height in sorted(fork_heights, reverse=True):
            if 0 <= height < len(self.blocks):
                self.blocks = self.blocks[:height]
                self._state_cache = {k: v for k, v in self._state_cache.items() if k < height}
                self._integrity_cache = {k: v for k, v in self._integrity_cache.items() if k < height}

        self.blocks.extend(new_blocks)
        for block in new_blocks:
            self._update_caches(block)

        return True

    async def validate_block_structure(self, block: Dict[str, Any]) -> bool:
        required_fields = [
            "height", "hash", "prev_hash", "timestamp",
            "merkle_root", "transactions", "gas_used", "gas_limit"
        ]

        for field_name in required_fields:
            if field_name not in block:
                return False

        if not isinstance(block.get("transactions", []), list):
            return False

        return True

    async def _validate_block_structure(self, block: Dict[str, Any]) -> bool:
        return await self.validate_block_structure(block)
