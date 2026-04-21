"""
Consensus Engine - Reaches consensus among overlapping audit agents.
"""
import asyncio
import hashlib
import json
import logging
import time
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

from .audit_config import AuditConfig

logger = logging.getLogger(__name__)


class ConsensusState(Enum):
    PENDING = "pending"
    GATHERING = "gathering"
    DELIBERATING = "deliberating"
    REACHED = "reached"
    FAILED = "failed"


@dataclass
class AgentVote:
    agent_id: str
    vote: str
    reasoning: str
    timestamp: int
    signature: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "vote": self.vote,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp,
            "signature": self.signature,
        }


@dataclass
class ConsensusResult:
    consensus_reached: bool
    state: ConsensusState
    votes: List[AgentVote]
    resolution: Optional[Dict[str, Any]]
    timestamp: int
    duration_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "consensus_reached": self.consensus_reached,
            "state": self.state.value,
            "votes": [v.to_dict() for v in self.votes],
            "resolution": self.resolution,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
        }


class ConsensusEngine:
    def __init__(self, config: AuditConfig):
        self.config = config
        self.agent_results: Dict[str, Dict[str, Any]] = {}
        self.pending_issues: Dict[str, Dict[str, Any]] = {}
        self.consensus_history: List[ConsensusResult] = []
        self._active_consensus: Dict[str, ConsensusState] = {}
        self._vote_cache: Dict[str, List[AgentVote]] = {}

    async def gather_results(
        self, agent_id: str, results: Dict[str, Any]
    ) -> None:
        logger.info(f"Consensus engine gathering results from agent {agent_id}")

        self.agent_results[agent_id] = {
            "results": results,
            "timestamp": int(time.time()),
            "blocks_verified": results.get("blocks_audited", 0),
            "issues_found": len(results.get("issues_detected", [])),
            "issues_resolved": len(results.get("issues_resolved", [])),
        }

        issue_key = self._get_issue_key_from_results(results)
        if issue_key:
            self.pending_issues[issue_key] = {
                "issue": results.get("issues_detected", [{}])[0] if results.get("issues_detected") else {},
                "reporting_agents": list(self.agent_results.keys()),
            }

        logger.debug(f"Agent results count: {len(self.agent_results)}")

    def _get_issue_key_from_results(self, results: Dict[str, Any]) -> Optional[str]:
        issues = results.get("issues_detected", [])
        if not issues:
            return None

        issue = issues[0]
        return f"{issue.get('type')}_{issue.get('block_height')}"

    async def reach_consensus(self, issue: Dict[str, Any]) -> ConsensusResult:
        start_time = time.time()
        issue_key = f"{issue.get('type')}_{issue.get('block_height')}"

        logger.info(f"Consensus engine reaching consensus for issue: {issue_key}")

        self._active_consensus[issue_key] = ConsensusState.GATHERING

        required_agents = max(3, len(self.agent_results) // 2 + 1)
        required_votes = max(2, required_agents // 2)

        gathering_timeout = 30
        gathering_start = time.time()

        while len(self.agent_results) < required_agents:
            if time.time() - gathering_start > gathering_timeout:
                logger.warning(f"Gathering timeout for issue {issue_key}")
                self._active_consensus[issue_key] = ConsensusState.FAILED
                return ConsensusResult(
                    consensus_reached=False,
                    state=ConsensusState.FAILED,
                    votes=[],
                    resolution=None,
                    timestamp=int(time.time()),
                    duration_ms=(time.time() - start_time) * 1000,
                )
            await asyncio.sleep(0.1)

        self._active_consensus[issue_key] = ConsensusState.DELIBERATING

        votes = await self._collect_votes(issue, required_votes)

        vote_agreement = await self._analyze_vote_agreement(votes)

        consensus_reached = vote_agreement["agreement_ratio"] >= 0.66

        resolution = None
        if consensus_reached:
            resolution = await self._generate_resolution(issue, votes)
            self._active_consensus[issue_key] = ConsensusState.REACHED
        else:
            self._active_consensus[issue_key] = ConsensusState.FAILED

        result = ConsensusResult(
            consensus_reached=consensus_reached,
            state=self._active_consensus[issue_key],
            votes=votes,
            resolution=resolution,
            timestamp=int(time.time()),
            duration_ms=(time.time() - start_time) * 1000,
        )

        self.consensus_history.append(result)

        logger.info(
            f"Consensus {'reached' if consensus_reached else 'failed'} for issue {issue_key} "
            f"in {result.duration_ms:.2f}ms"
        )

        return result

    async def _collect_votes(
        self, issue: Dict[str, Any], required_votes: int
    ) -> List[AgentVote]:
        votes = []
        vote_timeout = 20
        vote_start = time.time()

        for agent_id, agent_data in self.agent_results.items():
            if len(votes) >= required_votes:
                break

            if time.time() - vote_start > vote_timeout:
                break

            agent_vote = await self._request_agent_vote(agent_id, issue)
            if agent_vote:
                votes.append(agent_vote)

            await asyncio.sleep(0.05)

        return votes

    async def _request_agent_vote(
        self, agent_id: str, issue: Dict[str, Any]
    ) -> Optional[AgentVote]:
        issue_type = issue.get("type", "unknown")
        block_height = issue.get("block_height", 0)

        agent_data = self.agent_results.get(agent_id, {})
        results = agent_data.get("results", {})
        issues = results.get("issues_detected", [])

        issue_match = False
        for detected_issue in issues:
            if (detected_issue.get("type") == issue_type and
                detected_issue.get("block_height") == block_height):
                issue_match = True
                break

        if issue_match:
            vote = AgentVote(
                agent_id=agent_id,
                vote="confirm",
                reasoning=f"Agent confirms issue {issue_type} at height {block_height}",
                timestamp=int(time.time()),
                signature=self._sign_vote(agent_id, issue_type, block_height, "confirm"),
            )
        else:
            vote = AgentVote(
                agent_id=agent_id,
                vote="reject",
                reasoning=f"Agent does not confirm issue {issue_type} at height {block_height}",
                timestamp=int(time.time()),
                signature=self._sign_vote(agent_id, issue_type, block_height, "reject"),
            )

        return vote

    async def _analyze_vote_agreement(
        self, votes: List[AgentVote]
    ) -> Dict[str, Any]:
        if not votes:
            return {"agreement_ratio": 0.0, "votes_for": 0, "votes_against": 0}

        votes_for = sum(1 for v in votes if v.vote == "confirm")
        votes_against = sum(1 for v in votes if v.vote == "reject")
        total = len(votes)

        agreement_ratio = votes_for / total if total > 0 else 0

        return {
            "agreement_ratio": agreement_ratio,
            "votes_for": votes_for,
            "votes_against": votes_against,
            "total_votes": total,
        }

    async def _generate_resolution(
        self, issue: Dict[str, Any], votes: List[AgentVote]
    ) -> Dict[str, Any]:
        resolution = {
            "issue": issue,
            "confirmed": True,
            "severity": issue.get("severity", "unknown"),
            "affected_agents": [v.agent_id for v in votes],
            "correction_required": issue.get("severity") in ("critical", "high"),
            "correction_type": self._determine_correction_type(issue),
            "timestamp": int(time.time()),
        }

        return resolution

    def _determine_correction_type(self, issue: Dict[str, Any]) -> str:
        issue_type = issue.get("type", "")

        type_mapping = {
            "chain_linkage_violation": "block_hash_correction",
            "hash_mismatch": "block_hash_correction",
            "state_inconsistency": "state_root_correction",
            "consensus_violation": "consensus_correction",
            "double_spend": "transaction_correction",
            "signature_failure": "transaction_correction",
        }

        return type_mapping.get(issue_type, "generic_correction")

    async def check_overlap_coverage(self, layers: List[Dict[str, Any]]) -> float:
        if len(layers) < 2:
            return 0.0

        coverage_points = set()
        total_possible = 0

        for layer in layers:
            layer_start = layer.get("start_height", 0)
            layer_end = layer.get("end_height", 0)
            agent_id = layer.get("agent_id", "")

            for height in range(layer_start, layer_end):
                coverage_points.add((height, agent_id))
                total_possible += 1

        unique_heights = len(set(h for h, _ in coverage_points))

        if total_possible == 0:
            return 0.0

        coverage_ratio = unique_heights / (total_possible / len(layers))

        return min(coverage_ratio, 1.0)

    async def finalize_resolution(
        self, issue: Dict[str, Any]
    ) -> Dict[str, Any]:
        issue_key = f"{issue.get('type')}_{issue.get('block_height')}"

        finalization = {
            "issue_key": issue_key,
            "finalized": False,
            "consensus_result": None,
            "correction": None,
            "timestamp": int(time.time()),
        }

        for result in reversed(self.consensus_history):
            if result.resolution and self._matches_issue(result.resolution, issue):
                finalization["consensus_result"] = result.to_dict()
                if result.consensus_reached:
                    finalization["correction"] = await self._build_correction(issue)
                    finalization["finalized"] = True
                break

        logger.info(f"Finalized resolution for issue {issue_key}: {finalization['finalized']}")
        return finalization

    def _matches_issue(self, resolution: Dict[str, Any], issue: Dict[str, Any]) -> bool:
        res_issue = resolution.get("issue", {})
        return (
            res_issue.get("type") == issue.get("type") and
            res_issue.get("block_height") == issue.get("block_height")
        )

    async def _build_correction(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "type": self._determine_correction_type(issue),
            "original_issue_hash": self._hash_issue(issue),
            "block_height": issue.get("block_height"),
            "block_hash": issue.get("block_hash"),
            "severity": issue.get("severity"),
            "timestamp": int(time.time()),
        }

    def _hash_issue(self, issue: Dict[str, Any]) -> str:
        data = json.dumps(issue, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()

    def _sign_vote(
        self, agent_id: str, issue_type: str, block_height: int, vote: str
    ) -> str:
        data = f"{agent_id}:{issue_type}:{block_height}:{vote}"
        return hashlib.sha256(data.encode()).hexdigest()

    def get_consensus_stats(self) -> Dict[str, Any]:
        total = len(self.consensus_history)
        reached = sum(1 for r in self.consensus_history if r.consensus_reached)
        failed = total - reached

        return {
            "total_consensus_attempts": total,
            "consensus_reached": reached,
            "consensus_failed": failed,
            "success_rate": reached / total if total > 0 else 0.0,
            "active_consensus_count": sum(
                1 for s in self._active_consensus.values()
                if s in (ConsensusState.GATHERING, ConsensusState.DELIBERATING)
            ),
            "agents_registered": len(self.agent_results),
        }
