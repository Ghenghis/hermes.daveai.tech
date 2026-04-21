"""
Audit Dashboard - Real-time audit monitoring and visualization.
"""
import asyncio
import hashlib
import json
import logging
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from .audit_config import AuditConfig, AuditMetrics
from .audit_chain import AuditChain
from .audit_agent import AuditAgent

logger = logging.getLogger(__name__)


class DashboardStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class LayerCoverage:
    layer_id: str
    agent_id: str
    start_height: int
    end_height: int
    overlap_regions: List[Dict[str, int]] = field(default_factory=list)
    coverage_percentage: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "layer_id": self.layer_id,
            "agent_id": self.agent_id,
            "start_height": self.start_height,
            "end_height": self.end_height,
            "overlap_regions": self.overlap_regions,
            "coverage_percentage": self.coverage_percentage,
        }


@dataclass
class IssueResolution:
    issue_id: str
    issue_type: str
    block_height: int
    severity: str
    status: str
    detected_at: int
    resolved_at: Optional[int] = None
    resolution_time_ms: float = 0.0
    agents_involved: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue_id": self.issue_id,
            "issue_type": self.issue_type,
            "block_height": self.block_height,
            "severity": self.severity,
            "status": self.status,
            "detected_at": self.detected_at,
            "resolved_at": self.resolved_at,
            "resolution_time_ms": self.resolution_time_ms,
            "agents_involved": self.agents_involved,
        }


class AuditDashboard:
    def __init__(
        self,
        config: AuditConfig,
        chain: AuditChain,
        agents: List[AuditAgent],
    ):
        self.config = config
        self.chain = chain
        self.agents = {agent.agent_id: agent for agent in agents}
        self.status = DashboardStatus.IDLE
        self._layer_coverages: Dict[str, LayerCoverage] = {}
        self._issue_resolutions: Dict[str, IssueResolution] = {}
        self._event_log: List[Dict[str, Any]] = []
        self._metrics = AuditMetrics()
        self._start_time: Optional[int] = None
        self._pause_time: Optional[int] = None
        self._total_pause_duration: int = 0

    async def get_audit_status(self) -> Dict[str, Any]:
        latest_block = self.chain.get_latest_block()
        total_blocks = self.chain.get_total_blocks()

        agent_states = []
        for agent_id, agent in self.agents.items():
            state = await agent.get_agent_state()
            agent_states.append(state)

        active_agents = sum(
            1 for s in agent_states
            if s.get("current_height", 0) > 0
        )

        status = {
            "dashboard_status": self.status.value,
            "chain_info": {
                "latest_block_height": latest_block.get("height", 0) if latest_block else 0,
                "latest_block_hash": latest_block.get("hash", "")[:16] + "..." if latest_block else "",
                "total_blocks": total_blocks,
            },
            "agents": {
                "total": len(self.agents),
                "active": active_agents,
                "states": agent_states,
            },
            "metrics": self._metrics.get_summary(),
            "timing": {
                "start_time": self._start_time,
                "elapsed_seconds": self._calculate_elapsed(),
                "is_paused": self.status == DashboardStatus.PAUSED,
            },
        }

        return status

    async def get_overlap_visualization(self) -> Dict[str, Any]:
        coverage_data = []

        for layer_id, coverage in self._layer_coverages.items():
            coverage_data.append(coverage.to_dict())

        overlap_visualization = {
            "total_layers": len(self._layer_coverages),
            "layers": coverage_data,
            "overlap_summary": self._calculate_overlap_summary(),
            "visualization": {
                "type": "heatmap",
                "data": self._generate_overlap_heatmap(),
            },
        }

        return overlap_visualization

    async def get_issue_resolution_progress(self) -> Dict[str, Any]:
        total_issues = len(self._issue_resolutions)
        resolved_issues = sum(
            1 for i in self._issue_resolutions.values()
            if i.status == "resolved"
        )
        pending_issues = total_issues - resolved_issues

        by_severity = {}
        by_type = {}
        for issue_res in self._issue_resolutions.values():
            severity = issue_res.severity
            by_severity[severity] = by_severity.get(severity, 0) + 1

            issue_type = issue_res.issue_type
            by_type[issue_type] = by_type.get(issue_type, 0) + 1

        avg_resolution_time = 0.0
        resolved_list = [
            i for i in self._issue_resolutions.values()
            if i.status == "resolved" and i.resolution_time_ms > 0
        ]
        if resolved_list:
            avg_resolution_time = sum(
                i.resolution_time_ms for i in resolved_list
            ) / len(resolved_list)

        progress = {
            "summary": {
                "total_detected": total_issues,
                "resolved": resolved_issues,
                "pending": pending_issues,
                "resolution_rate": resolved_issues / total_issues if total_issues > 0 else 0.0,
            },
            "by_severity": by_severity,
            "by_type": by_type,
            "average_resolution_time_ms": avg_resolution_time,
            "issues": [i.to_dict() for i in self._issue_resolutions.values()],
        }

        return progress

    async def start_dashboard(self) -> Dict[str, Any]:
        self.status = DashboardStatus.RUNNING
        self._start_time = int(time.time())

        self._event_log.append({
            "event": "dashboard_started",
            "timestamp": self._start_time,
            "agent_count": len(self.agents),
        })

        logger.info("Audit dashboard started")

        return {
            "status": "started",
            "timestamp": self._start_time,
            "agents_tracked": len(self.agents),
        }

    async def pause_dashboard(self) -> Dict[str, Any]:
        if self.status == DashboardStatus.RUNNING:
            self.status = DashboardStatus.PAUSED
            self._pause_time = int(time.time())

            self._event_log.append({
                "event": "dashboard_paused",
                "timestamp": self._pause_time,
            })

            logger.info("Audit dashboard paused")

            return {
                "status": "paused",
                "timestamp": self._pause_time,
            }

        return {"status": "not_running", "timestamp": int(time.time())}

    async def resume_dashboard(self) -> Dict[str, Any]:
        if self.status == DashboardStatus.PAUSED and self._pause_time:
            pause_duration = int(time.time()) - self._pause_time
            self._total_pause_duration += pause_duration
            self.status = DashboardStatus.RUNNING

            self._event_log.append({
                "event": "dashboard_resumed",
                "timestamp": int(time.time()),
                "pause_duration": pause_duration,
            })

            logger.info("Audit dashboard resumed")

            return {
                "status": "resumed",
                "timestamp": int(time.time()),
                "pause_duration": pause_duration,
            }

        return {"status": "not_paused", "timestamp": int(time.time())}

    async def stop_dashboard(self) -> Dict[str, Any]:
        self.status = DashboardStatus.COMPLETED

        stop_time = int(time.time())

        summary = {
            "status": "stopped",
            "timestamp": stop_time,
            "total_duration": self._calculate_elapsed(),
            "events_logged": len(self._event_log),
            "metrics": self._metrics.get_summary(),
        }

        self._event_log.append({
            "event": "dashboard_stopped",
            "timestamp": stop_time,
            "summary": summary,
        })

        logger.info("Audit dashboard stopped")
        return summary

    async def record_layer_coverage(
        self,
        layer_id: str,
        agent_id: str,
        start_height: int,
        end_height: int,
        overlap_regions: List[Dict[str, int]],
    ) -> None:
        total_height = end_height - start_height
        covered_height = total_height

        for region in overlap_regions:
            covered_height -= region.get("overlap_size", 0)

        coverage_pct = (covered_height / total_height * 100) if total_height > 0 else 0

        coverage = LayerCoverage(
            layer_id=layer_id,
            agent_id=agent_id,
            start_height=start_height,
            end_height=end_height,
            overlap_regions=overlap_regions,
            coverage_percentage=coverage_pct,
        )

        self._layer_coverages[layer_id] = coverage

        self._event_log.append({
            "event": "layer_coverage_recorded",
            "timestamp": int(time.time()),
            "layer_id": layer_id,
            "coverage_percentage": coverage_pct,
        })

    async def record_issue_detection(
        self,
        issue_type: str,
        block_height: int,
        severity: str,
        agent_id: str,
    ) -> str:
        issue_id = hashlib.sha256(
            f"{issue_type}_{block_height}_{agent_id}_{time.time()}".encode()
        ).hexdigest()[:16]

        resolution = IssueResolution(
            issue_id=issue_id,
            issue_type=issue_type,
            block_height=block_height,
            severity=severity,
            status="detected",
            detected_at=int(time.time()),
            agents_involved=[agent_id],
        )

        self._issue_resolutions[issue_id] = resolution

        self._metrics.record_issue(severity, issue_type)

        self._event_log.append({
            "event": "issue_detected",
            "timestamp": int(time.time()),
            "issue_id": issue_id,
            "issue_type": issue_type,
            "severity": severity,
            "agent_id": agent_id,
        })

        logger.info(f"Issue detected: {issue_type} at height {block_height}")
        return issue_id

    async def record_issue_resolution(
        self,
        issue_id: str,
        resolved: bool = True,
    ) -> None:
        if issue_id not in self._issue_resolutions:
            logger.warning(f"Issue {issue_id} not found in resolutions")
            return

        resolution = self._issue_resolutions[issue_id]
        resolution.status = "resolved" if resolved else "failed"
        resolution.resolved_at = int(time.time())
        resolution.resolution_time_ms = (
            resolution.resolved_at - resolution.detected_at
        ) * 1000

        if resolved:
            self._metrics.record_resolution()

        self._event_log.append({
            "event": "issue_resolved",
            "timestamp": int(time.time()),
            "issue_id": issue_id,
            "resolved": resolved,
            "resolution_time_ms": resolution.resolution_time_ms,
        })

        logger.info(
            f"Issue {issue_id} resolution: {resolution.status} "
            f"in {resolution.resolution_time_ms:.2f}ms"
        )

    def _calculate_elapsed(self) -> int:
        if not self._start_time:
            return 0

        elapsed = int(time.time()) - self._start_time

        if self.status == DashboardStatus.PAUSED and self._pause_time:
            elapsed -= (int(time.time()) - self._pause_time)

        elapsed -= self._total_pause_duration

        return max(0, elapsed)

    def _calculate_overlap_summary(self) -> Dict[str, Any]:
        if not self._layer_coverages:
            return {
                "total_layers": 0,
                "average_coverage": 0.0,
                "total_overlap_regions": 0,
            }

        total_coverage = sum(
            c.coverage_percentage for c in self._layer_coverages.values()
        )
        avg_coverage = total_coverage / len(self._layer_coverages)

        total_overlap_regions = sum(
            len(c.overlap_regions) for c in self._layer_coverages.values()
        )

        return {
            "total_layers": len(self._layer_coverages),
            "average_coverage": avg_coverage,
            "total_overlap_regions": total_overlap_regions,
        }

    def _generate_overlap_heatmap(self) -> List[Dict[str, Any]]:
        heatmap = []

        for layer_id, coverage in self._layer_coverages.items():
            for region in coverage.overlap_regions:
                heatmap.append({
                    "layer_id": layer_id,
                    "start": region.get("start", coverage.start_height),
                    "end": region.get("end", coverage.end_height),
                    "intensity": region.get("overlap_size", 0) / (coverage.end_height - coverage.start_height),
                })

        return heatmap

    async def get_event_log(
        self, event_type: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        if event_type:
            filtered = [
                e for e in self._event_log if e.get("event") == event_type
            ]
            return filtered[-limit:]
        return self._event_log[-limit:]

    async def get_agent_comparison(self) -> Dict[str, Any]:
        comparison = {}

        for agent_id, agent in self.agents.items():
            summary = await agent.get_verification_summary()
            comparison[agent_id] = summary

        return comparison

    async def get_efficiency_metrics(self) -> Dict[str, Any]:
        total_blocks = self.chain.get_total_blocks()

        agent_stats = []
        for agent in self.agents.values():
            state = await agent.get_agent_state()
            summary = await agent.get_verification_summary()

            blocks_per_second = 0
            elapsed = self._calculate_elapsed()
            if elapsed > 0:
                blocks_per_second = state.get("current_height", 0) / elapsed

            agent_stats.append({
                "agent_id": agent.agent_id,
                "blocks_verified": state.get("current_height", 0),
                "issues_detected": summary.get("issues_detected", 0),
                "issues_resolved": summary.get("issues_resolved", 0),
                "blocks_per_second": blocks_per_second,
                "consecutive_failures": state.get("consecutive_failures", 0),
            })

        return {
            "total_blocks": total_blocks,
            "elapsed_seconds": self._calculate_elapsed(),
            "agent_stats": agent_stats,
            "efficiency_score": self._calculate_efficiency_score(agent_stats),
        }

    def _calculate_efficiency_score(self, agent_stats: List[Dict[str, Any]]) -> float:
        if not agent_stats:
            return 0.0

        total_issues_resolved = sum(s.get("issues_resolved", 0) for s in agent_stats)
        total_failures = sum(s.get("consecutive_failures", 0) for s in agent_stats)

        base_score = total_issues_resolved * 10
        penalty = total_failures * 5

        return max(0.0, base_score - penalty)
