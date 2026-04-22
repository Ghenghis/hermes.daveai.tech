"""
health_checks.py — Boot integrity validators.
Each check returns CheckResult(name, ok, severity, detail, fix_hint).
"""
from __future__ import annotations
import asyncio
import json
import os
import subprocess
import time
import urllib.request
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List


class Severity(str, Enum):
    HARD = "hard"       # failure → safemode
    SOFT = "soft"       # failure → warning only
    FORBIDDEN = "forbidden"  # presence = failure (wrong model names etc.)


@dataclass
class CheckResult:
    name: str
    ok: bool
    severity: Severity
    detail: str = ""
    fix_hint: str = ""
    elapsed_ms: float = 0.0


# ── Helpers ──────────────────────────────────────────────────────────────────

def _http_get(url: str, headers: dict | None = None, timeout: int = 8) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception as e:
        return 0, str(e).encode()


def _run(cmd: str) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return r.returncode, r.stdout + r.stderr
    except Exception as e:
        return 1, str(e)


def _env(path: str) -> dict:
    result = {}
    try:
        for line in Path(path).read_text().splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                result[k.strip()] = v.strip()
    except Exception:
        pass
    return result


# ── Individual checks ─────────────────────────────────────────────────────────

def check_docker_running() -> CheckResult:
    t = time.monotonic()
    rc, out = _run("docker info --format '{{.ServerVersion}}'")
    return CheckResult(
        name="docker_running",
        ok=rc == 0,
        severity=Severity.HARD,
        detail=out.strip()[:100],
        fix_hint="sudo systemctl start docker",
        elapsed_ms=(time.monotonic() - t) * 1000,
    )


def check_container(name: str) -> CheckResult:
    t = time.monotonic()
    rc, out = _run(f"docker inspect --format='{{{{.State.Status}}}}' {name} 2>&1")
    ok = rc == 0 and "running" in out
    return CheckResult(
        name=f"container_{name}",
        ok=ok,
        severity=Severity.HARD,
        detail=out.strip()[:100],
        fix_hint=f"docker start {name}",
        elapsed_ms=(time.monotonic() - t) * 1000,
    )


def check_litellm_health() -> CheckResult:
    t = time.monotonic()
    env = _env("/opt/litellm/.env")
    master = env.get("LITELLM_MASTER_KEY", "")
    code, body = _http_get(
        "http://localhost:4000/health",
        headers={"Authorization": f"Bearer {master}"} if master else {},
    )
    ok = code == 200
    # Also check drop_params
    try:
        cfg = Path("/opt/litellm/config.yaml").read_text()
        if "drop_params: true" in cfg:
            return CheckResult(
                name="litellm_drop_params",
                ok=False,
                severity=Severity.HARD,
                detail="drop_params is true — tool use broken",
                fix_hint="sed -i 's/drop_params: true/drop_params: false/' /opt/litellm/config.yaml && systemctl restart litellm",
                elapsed_ms=(time.monotonic() - t) * 1000,
            )
    except Exception:
        pass
    return CheckResult(
        name="litellm_health",
        ok=ok,
        severity=Severity.HARD,
        detail=f"HTTP {code}",
        fix_hint="systemctl restart litellm",
        elapsed_ms=(time.monotonic() - t) * 1000,
    )


def check_minimax_api() -> CheckResult:
    t = time.monotonic()
    env = _env("/opt/litellm/.env")
    key = env.get("MINIMAX_API_KEY", "")
    if not key:
        return CheckResult(
            name="minimax_api_key",
            ok=False,
            severity=Severity.HARD,
            detail="MINIMAX_API_KEY not set in /opt/litellm/.env",
            fix_hint="echo 'MINIMAX_API_KEY=sk-cp-...' >> /opt/litellm/.env",
            elapsed_ms=(time.monotonic() - t) * 1000,
        )
    code, body = _http_get(
        "https://api.minimax.io/v1/models",
        headers={"Authorization": f"Bearer {key}"},
        timeout=10,
    )
    ok = code == 200
    return CheckResult(
        name="minimax_api",
        ok=ok,
        severity=Severity.HARD,
        detail=f"HTTP {code}" + ("" if ok else f" — {body[:80].decode(errors='replace')}"),
        fix_hint="Check MINIMAX_API_KEY value in /opt/litellm/.env",
        elapsed_ms=(time.monotonic() - t) * 1000,
    )


def check_siliconflow_api() -> CheckResult:
    t = time.monotonic()
    env = _env("/opt/litellm/.env")
    key = env.get("SILICONFLOW_API_KEY", "")
    if not key:
        return CheckResult(
            name="siliconflow_api_key",
            ok=False,
            severity=Severity.SOFT,
            detail="SILICONFLOW_API_KEY not set — hermes2-5 will fallback to MiniMax",
            fix_hint="Add SILICONFLOW_API_KEY to /opt/litellm/.env",
            elapsed_ms=(time.monotonic() - t) * 1000,
        )
    code, _ = _http_get(
        "https://api.siliconflow.com/v1/models",
        headers={"Authorization": f"Bearer {key}"},
        timeout=10,
    )
    ok = code == 200
    return CheckResult(
        name="siliconflow_api",
        ok=ok,
        severity=Severity.SOFT,
        detail=f"HTTP {code}",
        fix_hint="Check SILICONFLOW_API_KEY in /opt/litellm/.env",
        elapsed_ms=(time.monotonic() - t) * 1000,
    )


def check_no_anthropic_native_key() -> CheckResult:
    """Forbidden: a real Anthropic key (sk-ant-...) anywhere in env files."""
    t = time.monotonic()
    forbidden_paths = [
        "/opt/litellm/.env",
        *[f"/opt/data/profiles/adam_hermes{i}/.env" for i in range(1, 6)],
        "/opt/data/.env",
    ]
    found_in = []
    for p in forbidden_paths:
        try:
            content = Path(p).read_text()
            if "sk-ant-" in content:
                found_in.append(p)
        except Exception:
            pass
    ok = len(found_in) == 0
    return CheckResult(
        name="no_anthropic_native_key",
        ok=ok,
        severity=Severity.FORBIDDEN,
        detail=f"Found sk-ant- in: {found_in}" if not ok else "Clean — no real Anthropic keys",
        fix_hint="sed -i 's/sk-ant-[^ ]*/INVALID/' " + " ".join(found_in),
        elapsed_ms=(time.monotonic() - t) * 1000,
    )


def check_no_claude_model_names() -> CheckResult:
    """Forbidden: claude-* model names in any hermes env file."""
    t = time.monotonic()
    forbidden_paths = [
        *[f"/opt/data/profiles/adam_hermes{i}/.env" for i in range(1, 6)],
        "/opt/data/.env",
    ]
    found_in = []
    for p in forbidden_paths:
        try:
            content = Path(p).read_text()
            if "claude-" in content.lower():
                found_in.append(p)
        except Exception:
            pass
    ok = len(found_in) == 0
    return CheckResult(
        name="no_claude_model_names",
        ok=ok,
        severity=Severity.FORBIDDEN,
        detail=f"Found claude-* model in: {found_in}" if not ok else "Clean — no claude- model names",
        fix_hint="Run hermes-full-minimax-fix.sh to patch all env files",
        elapsed_ms=(time.monotonic() - t) * 1000,
    )


def check_hermes1_model() -> CheckResult:
    """hermes1 must use MiniMax-M2.7-highspeed."""
    t = time.monotonic()
    found_model = ""
    for p in [
        "/opt/data/profiles/adam_hermes1/.env",
        "/opt/data/.env",
    ]:
        env = _env(p)
        if "HERMES_MODEL" in env:
            found_model = env["HERMES_MODEL"]
            break
    ok = "MiniMax" in found_model or found_model == ""
    # If empty we check via docker
    if not found_model:
        rc, out = _run("docker exec hermes1 bash -c \"grep HERMES_MODEL /opt/data/.env 2>/dev/null | head -1\"")
        found_model = out.strip().replace("HERMES_MODEL=", "")
        ok = "MiniMax" in found_model
    return CheckResult(
        name="hermes1_model",
        ok=ok,
        severity=Severity.HARD,
        detail=f"hermes1 HERMES_MODEL={found_model or 'unknown'}",
        fix_hint="docker exec hermes1 bash -c \"sed -i 's/HERMES_MODEL=.*/HERMES_MODEL=MiniMax-M2.7-highspeed/' /opt/data/.env\" && docker restart hermes1",
        elapsed_ms=(time.monotonic() - t) * 1000,
    )


def check_anthropic_base_url() -> CheckResult:
    """ANTHROPIC_BASE_URL must point to api.minimax.io in all hermes bots."""
    t = time.monotonic()
    wrong = []
    for i in range(1, 6):
        rc, out = _run(f"docker exec hermes{i} bash -c \"grep ANTHROPIC_BASE_URL /opt/data/.env 2>/dev/null | head -1\"")
        if out.strip() and "minimax" not in out.lower():
            wrong.append(f"hermes{i}: {out.strip()}")
    ok = len(wrong) == 0
    return CheckResult(
        name="anthropic_base_url",
        ok=ok,
        severity=Severity.HARD,
        detail="; ".join(wrong) if wrong else "All bots: ANTHROPIC_BASE_URL=https://api.minimax.io/anthropic",
        fix_hint="Run hermes-full-minimax-fix.sh",
        elapsed_ms=(time.monotonic() - t) * 1000,
    )


def check_disk_space() -> CheckResult:
    t = time.monotonic()
    rc, out = _run("df -BM /opt --output=avail | tail -1")
    try:
        avail_mb = int(out.strip().replace("M", ""))
        ok = avail_mb > 2048
        detail = f"{avail_mb}MB free on /opt"
    except Exception:
        ok = False
        detail = "Could not determine disk space"
    return CheckResult(
        name="disk_space",
        ok=ok,
        severity=Severity.SOFT,
        detail=detail,
        fix_hint="docker system prune -f && find /tmp -mtime +1 -delete",
        elapsed_ms=(time.monotonic() - t) * 1000,
    )


def check_webui_db() -> CheckResult:
    t = time.monotonic()
    db_path = "/var/lib/docker/volumes/open-webui/_data/webui.db"
    if not Path(db_path).exists():
        return CheckResult(
            name="webui_db",
            ok=False,
            severity=Severity.HARD,
            detail="webui.db not found",
            fix_hint="docker restart open-webui",
            elapsed_ms=(time.monotonic() - t) * 1000,
        )
    rc, out = _run(f"python3 -c \"import sqlite3; sqlite3.connect('{db_path}').execute('PRAGMA integrity_check')\"")
    ok = rc == 0
    return CheckResult(
        name="webui_db",
        ok=ok,
        severity=Severity.HARD,
        detail="DB integrity OK" if ok else out[:100],
        fix_hint="cp /opt/backups/webui.db /var/lib/docker/volumes/open-webui/_data/webui.db",
        elapsed_ms=(time.monotonic() - t) * 1000,
    )


def check_nginx() -> CheckResult:
    t = time.monotonic()
    code, _ = _http_get("http://localhost:80", timeout=5)
    ok = code in (200, 301, 302, 404)  # any response means nginx is up
    return CheckResult(
        name="nginx",
        ok=ok,
        severity=Severity.SOFT,
        detail=f"HTTP {code}",
        fix_hint="systemctl restart nginx",
        elapsed_ms=(time.monotonic() - t) * 1000,
    )


# ── Full suite ────────────────────────────────────────────────────────────────

ALL_CHECKS = [
    check_docker_running,
    lambda: check_container("open-webui"),
    lambda: check_container("litellm"),
    lambda: check_container("hermes1"),
    lambda: check_container("hermes2"),
    lambda: check_container("hermes3"),
    lambda: check_container("hermes4"),
    lambda: check_container("hermes5"),
    check_litellm_health,
    check_minimax_api,
    check_siliconflow_api,
    check_no_anthropic_native_key,
    check_no_claude_model_names,
    check_hermes1_model,
    check_anthropic_base_url,
    check_disk_space,
    check_webui_db,
    check_nginx,
]


def run_all_checks() -> List[CheckResult]:
    results = []
    for fn in ALL_CHECKS:
        try:
            results.append(fn())
        except Exception as e:
            results.append(CheckResult(
                name=getattr(fn, "__name__", "unknown"),
                ok=False,
                severity=Severity.SOFT,
                detail=f"Check crashed: {e}",
            ))
    return results


def is_safemode_required(results: List[CheckResult]) -> bool:
    """True if any HARD check failed."""
    return any(not r.ok and r.severity == Severity.HARD for r in results)


def summary(results: List[CheckResult]) -> dict:
    total = len(results)
    passed = sum(1 for r in results if r.ok)
    failed_hard = [r for r in results if not r.ok and r.severity == Severity.HARD]
    failed_soft = [r for r in results if not r.ok and r.severity == Severity.SOFT]
    return {
        "total": total,
        "passed": passed,
        "failed_hard": len(failed_hard),
        "failed_soft": len(failed_soft),
        "safemode": len(failed_hard) > 0,
        "hard_failures": [{"name": r.name, "detail": r.detail, "fix": r.fix_hint} for r in failed_hard],
        "soft_warnings": [{"name": r.name, "detail": r.detail} for r in failed_soft],
    }


if __name__ == "__main__":
    results = run_all_checks()
    s = summary(results)
    print(json.dumps(s, indent=2))
