"""
repair_agent.py — Autonomous repair agent.
Reads failed checks, executes fixes, streams progress via asyncio queue.
"""
from __future__ import annotations
import asyncio
import json
import os
import subprocess
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import AsyncGenerator, Callable, List, Optional

from health_checks import CheckResult, Severity, run_all_checks, summary, is_safemode_required


MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY", "")
MINIMAX_BASE = "https://api.minimax.io/v1"
REPAIR_LOG = Path("/opt/repair/repair.log")
KNOWLEDGE_DB = Path("/opt/repair/knowledge.json")


@dataclass
class RepairEvent:
    agent: str
    action: str
    detail: str
    ok: bool = True
    progress: int = 0  # 0–100


# ── Repair knowledge base ─────────────────────────────────────────────────────

def load_knowledge() -> dict:
    try:
        return json.loads(KNOWLEDGE_DB.read_text())
    except Exception:
        return {"failures": {}, "fixes_applied": 0}


def save_knowledge(db: dict) -> None:
    KNOWLEDGE_DB.parent.mkdir(parents=True, exist_ok=True)
    KNOWLEDGE_DB.write_text(json.dumps(db, indent=2))


def record_failure(check_name: str, detail: str) -> None:
    db = load_knowledge()
    db["failures"].setdefault(check_name, {"count": 0, "last": "", "fixes": []})
    db["failures"][check_name]["count"] += 1
    db["failures"][check_name]["last"] = detail
    save_knowledge(db)


# ── Low-level repair executors ───────────────────────────────────────────────

def _run_fix(cmd: str, timeout: int = 60) -> tuple[bool, str]:
    """Execute a shell fix command. Returns (success, output)."""
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return r.returncode == 0, (r.stdout + r.stderr).strip()[:500]
    except subprocess.TimeoutExpired:
        return False, f"Timeout after {timeout}s"
    except Exception as e:
        return False, str(e)


def _log(msg: str) -> None:
    REPAIR_LOG.parent.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}\n"
    REPAIR_LOG.open("a").write(line)


# ── Agent-specific repair strategies ─────────────────────────────────────────

REPAIR_STRATEGIES: dict[str, Callable[[CheckResult], list[str]]] = {
    "docker_running": lambda r: [
        "systemctl start docker",
        "sleep 5",
        "docker info",
    ],
    "container_open-webui": lambda r: [
        "docker start open-webui || docker compose -f /opt/docker-compose.yml up -d open-webui",
        "sleep 8",
        "docker inspect --format='{{.State.Status}}' open-webui",
    ],
    "container_litellm": lambda r: [
        "systemctl restart litellm || docker restart litellm",
        "sleep 10",
        "curl -sf http://localhost:4000/health",
    ],
    "container_hermes1": lambda r: ["docker restart hermes1", "sleep 5"],
    "container_hermes2": lambda r: ["docker restart hermes2", "sleep 5"],
    "container_hermes3": lambda r: ["docker restart hermes3", "sleep 5"],
    "container_hermes4": lambda r: ["docker restart hermes4", "sleep 5"],
    "container_hermes5": lambda r: ["docker restart hermes5", "sleep 5"],
    "litellm_health": lambda r: [
        "pkill -f litellm || true",
        "sleep 3",
        "systemctl restart litellm || (cd /opt/litellm && nohup litellm --config config.yaml --port 4000 >> /var/log/litellm.log 2>&1 &)",
        "sleep 10",
        "curl -sf http://localhost:4000/health",
    ],
    "no_claude_model_names": lambda r: [
        "for i in 1 2 3 4 5; do "
        "docker exec hermes$i bash -c \""
        "sed -i 's/HERMES_MODEL=claude-.*/HERMES_MODEL=MiniMax-M2.7-highspeed/' /opt/data/.env 2>/dev/null || true; "
        "sed -i 's/HERMES_PROVIDER=anthropic/HERMES_PROVIDER=minimax/' /opt/data/.env 2>/dev/null || true"
        "\" 2>/dev/null || true; done",
        "for i in 1 2 3 4 5; do docker restart hermes$i; done",
        "sleep 10",
    ],
    "hermes1_model": lambda r: [
        "docker exec hermes1 bash -c \"sed -i 's/HERMES_MODEL=.*/HERMES_MODEL=MiniMax-M2.7-highspeed/' /opt/data/.env 2>/dev/null\"",
        "docker restart hermes1",
        "sleep 6",
    ],
    "anthropic_base_url": lambda r: [
        "for i in 1 2 3 4 5; do "
        "docker exec hermes$i bash -c \""
        "grep -q ANTHROPIC_BASE_URL /opt/data/.env && "
        "sed -i 's|ANTHROPIC_BASE_URL=.*|ANTHROPIC_BASE_URL=https://api.minimax.io/anthropic|' /opt/data/.env || "
        "echo 'ANTHROPIC_BASE_URL=https://api.minimax.io/anthropic' >> /opt/data/.env"
        "\" 2>/dev/null || true; done",
        "for i in 1 2 3 4 5; do docker restart hermes$i; done",
    ],
    "disk_space": lambda r: [
        "docker system prune -f --volumes 2>/dev/null || docker system prune -f",
        "find /tmp -mtime +1 -type f -delete 2>/dev/null || true",
        "journalctl --vacuum-size=200M 2>/dev/null || true",
        "find /var/log -name '*.gz' -mtime +7 -delete 2>/dev/null || true",
    ],
    "nginx": lambda r: [
        "systemctl restart nginx",
        "sleep 3",
        "nginx -t",
    ],
    "webui_db": lambda r: [
        "DB=/var/lib/docker/volumes/open-webui/_data/webui.db; "
        "BACKUP=$(ls /opt/backups/webui.db.* 2>/dev/null | tail -1); "
        "[ -n \"$BACKUP\" ] && cp \"$BACKUP\" \"$DB\" && echo Restored || "
        "docker restart open-webui",
    ],
}


# ── Main repair orchestrator ──────────────────────────────────────────────────

async def run_repairs(
    failed: List[CheckResult],
    event_queue: asyncio.Queue,
) -> bool:
    """
    Run repair strategies for all failed checks.
    Emits RepairEvents to event_queue.
    Returns True if all repairs succeeded.
    """
    total = len(failed)
    all_ok = True

    for idx, check in enumerate(failed):
        progress_base = int((idx / total) * 90)
        agent = "repair-alpha" if idx % 3 == 0 else ("repair-beta" if idx % 3 == 1 else "repair-gamma")

        await event_queue.put(RepairEvent(
            agent=agent,
            action=f"Repairing: {check.name}",
            detail=check.detail,
            ok=True,
            progress=progress_base,
        ))

        record_failure(check.name, check.detail)
        _log(f"REPAIR START: {check.name} — {check.detail}")

        strategies = REPAIR_STRATEGIES.get(check.name, [])
        if not strategies and check.fix_hint:
            strategies = [check.fix_hint]

        if not strategies:
            await event_queue.put(RepairEvent(
                agent=agent,
                action=f"No strategy for: {check.name}",
                detail="Manual intervention required",
                ok=False,
                progress=progress_base + 5,
            ))
            all_ok = False
            continue

        step_ok = True
        for cmd in strategies:
            await event_queue.put(RepairEvent(
                agent=agent,
                action="Executing",
                detail=cmd[:120],
                ok=True,
                progress=progress_base + 3,
            ))
            ok, out = _run_fix(cmd)
            _log(f"  CMD: {cmd[:80]} → {'OK' if ok else 'FAIL'}: {out[:100]}")
            await event_queue.put(RepairEvent(
                agent=agent,
                action="Result",
                detail=out[:120],
                ok=ok,
                progress=progress_base + 6,
            ))
            if not ok:
                step_ok = False

        if step_ok:
            await event_queue.put(RepairEvent(
                agent=agent,
                action=f"Fixed: {check.name}",
                detail="Repair successful",
                ok=True,
                progress=progress_base + 10,
            ))
            _log(f"REPAIR OK: {check.name}")
        else:
            all_ok = False
            _log(f"REPAIR FAILED: {check.name}")

    return all_ok


async def full_repair_cycle(event_queue: asyncio.Queue) -> dict:
    """
    Full cycle: check → repair failing → re-check → return summary.
    """
    await event_queue.put(RepairEvent(
        agent="watchdog",
        action="Starting full health check",
        detail="Running 18 validators...",
        ok=True,
        progress=0,
    ))

    results = run_all_checks()
    s = summary(results)

    await event_queue.put(RepairEvent(
        agent="watchdog",
        action="Health check complete",
        detail=f"{s['passed']}/{s['total']} passed, {s['failed_hard']} hard failures",
        ok=s["failed_hard"] == 0,
        progress=10,
    ))

    if s["failed_hard"] == 0 and s["failed_soft"] == 0:
        await event_queue.put(RepairEvent(
            agent="watchdog",
            action="All checks passed",
            detail="System healthy — no repairs needed",
            ok=True,
            progress=100,
        ))
        return {"status": "healthy", "summary": s}

    failed = [r for r in results if not r.ok]
    await event_queue.put(RepairEvent(
        agent="watchdog",
        action="Entering repair mode",
        detail=f"Fixing {len(failed)} issues...",
        ok=True,
        progress=15,
    ))

    repair_ok = await run_repairs(failed, event_queue)

    # Re-check after repairs
    await event_queue.put(RepairEvent(
        agent="watchdog",
        action="Re-running health checks",
        detail="Verifying repairs...",
        ok=True,
        progress=92,
    ))

    results2 = run_all_checks()
    s2 = summary(results2)

    final_ok = s2["failed_hard"] == 0
    await event_queue.put(RepairEvent(
        agent="watchdog",
        action="Repair cycle complete" if final_ok else "Repair incomplete",
        detail=f"{s2['passed']}/{s2['total']} checks passing",
        ok=final_ok,
        progress=100,
    ))

    return {
        "status": "repaired" if final_ok else "partial",
        "pre_repair": s,
        "post_repair": s2,
    }
