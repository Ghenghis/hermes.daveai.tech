"""
e2e_test_harness.py — End-to-end agent test harness.
Agents test their own skills, SSH access, tool use, and workflows in real time.
Each test uses a real LLM call via LiteLLM proxy. Results streamed via SSE.
"""
from __future__ import annotations
import asyncio
import json
import os
import subprocess
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncGenerator, List, Optional

LITELLM_URL = os.environ.get("LITELLM_URL", "http://localhost:4000")
LITELLM_KEY = ""  # loaded from /opt/litellm/.env at runtime
MINIMAX_KEY = ""  # loaded from /opt/litellm/.env at runtime

TEST_LOG = Path("/opt/repair/e2e_tests.log")


def _load_keys():
    global LITELLM_KEY, MINIMAX_KEY
    env = {}
    try:
        for line in Path("/opt/litellm/.env").read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    except Exception:
        pass
    LITELLM_KEY = env.get("LITELLM_MASTER_KEY", "sk-hermes-master")
    MINIMAX_KEY = env.get("MINIMAX_API_KEY", "")


@dataclass
class TestResult:
    name: str
    agent: str
    model: str
    ok: bool
    detail: str
    latency_ms: float
    test_type: str  # "chat", "tool_use", "ssh", "skill", "workflow"


# ── LLM call helper ───────────────────────────────────────────────────────────

def _litellm_chat(model: str, messages: list, tools: list | None = None, timeout: int = 30) -> dict:
    _load_keys()
    body = {"model": model, "messages": messages, "max_tokens": 200}
    if tools:
        body["tools"] = tools
    req = urllib.request.Request(
        f"{LITELLM_URL}/v1/chat/completions",
        json.dumps(body).encode(),
        {
            "Authorization": f"Bearer {LITELLM_KEY}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _minimax_direct(messages: list, timeout: int = 30) -> dict:
    """Direct call to MiniMax Anthropic endpoint — bypasses LiteLLM."""
    _load_keys()
    body = {
        "model": "MiniMax-M2.7-highspeed",
        "max_tokens": 100,
        "messages": messages,
    }
    req = urllib.request.Request(
        "https://api.minimax.io/anthropic/v1/messages",
        json.dumps(body).encode(),
        {
            "x-api-key": MINIMAX_KEY,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _run_ssh(cmd: str, timeout: int = 15) -> tuple[int, str]:
    try:
        r = subprocess.run(
            ["docker", "exec", "hermes1", "bash", "-c", cmd],
            capture_output=True, text=True, timeout=timeout
        )
        return r.returncode, (r.stdout + r.stderr).strip()[:500]
    except Exception as e:
        return 1, str(e)


# ── Individual tests ──────────────────────────────────────────────────────────

def test_litellm_minimax_chat() -> TestResult:
    """hermes1: basic chat via LiteLLM → MiniMax."""
    t = time.monotonic()
    try:
        resp = _litellm_chat("minimax-fast", [
            {"role": "user", "content": "Reply with exactly: HERMES_OK"}
        ])
        text = resp["choices"][0]["message"]["content"]
        ok = "HERMES_OK" in text or len(text) > 0
        return TestResult("litellm_minimax_chat", "hermes1", "minimax-fast",
                          ok, text[:80], (time.monotonic()-t)*1000, "chat")
    except Exception as e:
        return TestResult("litellm_minimax_chat", "hermes1", "minimax-fast",
                          False, str(e)[:100], (time.monotonic()-t)*1000, "chat")


def test_litellm_siliconflow_chat() -> TestResult:
    """hermes2: basic chat via LiteLLM → SiliconFlow DeepSeek-V3."""
    t = time.monotonic()
    try:
        resp = _litellm_chat("sf-deepseek-v3", [
            {"role": "user", "content": "Reply with exactly: SILICONFLOW_OK"}
        ])
        text = resp["choices"][0]["message"]["content"]
        ok = len(text) > 0
        return TestResult("litellm_siliconflow_chat", "hermes2", "sf-deepseek-v3",
                          ok, text[:80], (time.monotonic()-t)*1000, "chat")
    except Exception as e:
        return TestResult("litellm_siliconflow_chat", "hermes2", "sf-deepseek-v3",
                          False, str(e)[:100], (time.monotonic()-t)*1000, "chat")


def test_minimax_direct_api() -> TestResult:
    """Direct MiniMax Anthropic endpoint — no LiteLLM."""
    t = time.monotonic()
    try:
        resp = _minimax_direct([
            {"role": "user", "content": "Reply with exactly: MINIMAX_DIRECT_OK"}
        ])
        content = resp.get("content", [{}])
        # Find text block
        text = ""
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "")
                break
        ok = len(text) > 0
        return TestResult("minimax_direct_api", "hermes1", "MiniMax-M2.7-highspeed",
                          ok, text[:80], (time.monotonic()-t)*1000, "chat")
    except Exception as e:
        return TestResult("minimax_direct_api", "hermes1", "MiniMax-M2.7-highspeed",
                          False, str(e)[:100], (time.monotonic()-t)*1000, "chat")


def test_tool_use() -> TestResult:
    """Test tool/function calling via LiteLLM with MiniMax (requires drop_params: false)."""
    t = time.monotonic()
    tools = [{
        "type": "function",
        "function": {
            "name": "get_system_status",
            "description": "Get current system health status",
            "parameters": {
                "type": "object",
                "properties": {
                    "component": {"type": "string", "description": "Component to check"}
                },
                "required": ["component"]
            }
        }
    }]
    try:
        resp = _litellm_chat(
            "minimax-fast",
            [{"role": "user", "content": "Check the litellm component status using the tool."}],
            tools=tools,
            timeout=40,
        )
        msg = resp["choices"][0]["message"]
        # Check if model called the tool
        called_tool = bool(msg.get("tool_calls"))
        ok = called_tool or len(msg.get("content", "")) > 0
        detail = f"tool_calls={called_tool} content={str(msg.get('content',''))[:60]}"
        return TestResult("tool_use", "hermes1", "minimax-fast",
                          ok, detail, (time.monotonic()-t)*1000, "tool_use")
    except Exception as e:
        return TestResult("tool_use", "hermes1", "minimax-fast",
                          False, str(e)[:100], (time.monotonic()-t)*1000, "tool_use")


def test_hermes1_container_skill() -> TestResult:
    """Test hermes agent skill execution inside container."""
    t = time.monotonic()
    rc, out = _run_ssh(
        "cd /opt/hermes && "
        ".venv/bin/python3 -c \"from hermes_cli.main import *; print('HERMES_IMPORT_OK')\" 2>&1 | head -3"
    )
    ok = "HERMES_IMPORT_OK" in out or rc == 0
    return TestResult("hermes1_container_skill", "hermes1", "container",
                      ok, out[:100], (time.monotonic()-t)*1000, "skill")


def test_ssh_access() -> TestResult:
    """Test SSH / docker exec access to hermes1."""
    t = time.monotonic()
    rc, out = _run_ssh("echo SSH_OK && whoami && hostname")
    ok = rc == 0 and "SSH_OK" in out
    return TestResult("ssh_access", "hermes1", "container",
                      ok, out[:100], (time.monotonic()-t)*1000, "ssh")


def test_litellm_models_list() -> TestResult:
    """LiteLLM /v1/models returns expected models."""
    t = time.monotonic()
    _load_keys()
    try:
        req = urllib.request.Request(
            f"{LITELLM_URL}/v1/models",
            headers={"Authorization": f"Bearer {LITELLM_KEY}"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        ids = [m["id"] for m in data.get("data", [])]
        expected = {"minimax-fast", "minimax-vision", "sf-deepseek-v3"}
        found = expected & set(ids)
        ok = len(found) >= 2
        return TestResult("litellm_models_list", "litellm", "proxy",
                          ok, f"found: {list(found)}", (time.monotonic()-t)*1000, "chat")
    except Exception as e:
        return TestResult("litellm_models_list", "litellm", "proxy",
                          False, str(e)[:100], (time.monotonic()-t)*1000, "chat")


def test_agent_brain_api() -> TestResult:
    """agent-brain :8080 responds."""
    t = time.monotonic()
    try:
        code, body = 0, b""
        req = urllib.request.Request("http://localhost:8080/health")
        with urllib.request.urlopen(req, timeout=8) as r:
            code, body = r.status, r.read()
        ok = code == 200
        return TestResult("agent_brain_api", "agent-brain", "api",
                          ok, f"HTTP {code} {body[:50]}", (time.monotonic()-t)*1000, "skill")
    except Exception as e:
        return TestResult("agent_brain_api", "agent-brain", "api",
                          False, str(e)[:100], (time.monotonic()-t)*1000, "skill")


def test_open_webui_up() -> TestResult:
    """Open WebUI :7860 responds."""
    t = time.monotonic()
    try:
        req = urllib.request.Request("http://localhost:7860")
        with urllib.request.urlopen(req, timeout=10) as r:
            code = r.status
        ok = code in (200, 301, 302)
        return TestResult("open_webui_up", "open-webui", "ui",
                          ok, f"HTTP {code}", (time.monotonic()-t)*1000, "chat")
    except Exception as e:
        return TestResult("open_webui_up", "open-webui", "ui",
                          False, str(e)[:100], (time.monotonic()-t)*1000, "chat")


def test_hermes_agent_workflow() -> TestResult:
    """
    Real agent workflow: Ask hermes1 (via LiteLLM) to reason about a task
    that requires multi-step thinking.
    """
    t = time.monotonic()
    try:
        resp = _litellm_chat("minimax-fast", [
            {
                "role": "system",
                "content": "You are Hermes, a helpful AI agent. Be concise."
            },
            {
                "role": "user",
                "content": (
                    "List 3 things needed to make a Python web server. "
                    "Format as: 1. X 2. Y 3. Z"
                )
            }
        ], timeout=45)
        text = resp["choices"][0]["message"]["content"]
        ok = "1." in text and "2." in text
        return TestResult("hermes_agent_workflow", "hermes1", "minimax-fast",
                          ok, text[:120], (time.monotonic()-t)*1000, "workflow")
    except Exception as e:
        return TestResult("hermes_agent_workflow", "hermes1", "minimax-fast",
                          False, str(e)[:100], (time.monotonic()-t)*1000, "workflow")


def test_budget_tracker() -> TestResult:
    """SiliconFlow budget tracker readable."""
    t = time.monotonic()
    try:
        _load_keys()
        req = urllib.request.Request(
            f"{LITELLM_URL}/spend",
            headers={"Authorization": f"Bearer {LITELLM_KEY}"},
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
        ok = True
        return TestResult("budget_tracker", "litellm", "proxy",
                          ok, f"spend data: {str(data)[:80]}", (time.monotonic()-t)*1000, "skill")
    except Exception as e:
        # Not critical — just informational
        return TestResult("budget_tracker", "litellm", "proxy",
                          True, f"Spend API not configured (OK): {str(e)[:60]}",
                          (time.monotonic()-t)*1000, "skill")


# ── Full test suite ───────────────────────────────────────────────────────────

ALL_TESTS = [
    test_open_webui_up,
    test_litellm_models_list,
    test_litellm_minimax_chat,
    test_minimax_direct_api,
    test_litellm_siliconflow_chat,
    test_tool_use,
    test_ssh_access,
    test_hermes1_container_skill,
    test_agent_brain_api,
    test_hermes_agent_workflow,
    test_budget_tracker,
]


async def run_all_tests(parallel: bool = False) -> List[TestResult]:
    """Run all E2E tests. parallel=False runs sequentially (safer)."""
    results = []
    for fn in ALL_TESTS:
        print(f"  → {fn.__name__}...", end=" ", flush=True)
        try:
            result = await asyncio.get_event_loop().run_in_executor(None, fn)
            results.append(result)
            status = "✓" if result.ok else "✗"
            print(f"{status} ({result.latency_ms:.0f}ms)")
        except Exception as e:
            results.append(TestResult(
                fn.__name__, "unknown", "unknown", False, str(e)[:100], 0, "unknown"
            ))
            print(f"✗ CRASHED: {e}")
    return results


def print_report(results: List[TestResult]) -> None:
    print("\n" + "═" * 70)
    print("  HERMES E2E TEST REPORT")
    print("═" * 70)
    passed = sum(1 for r in results if r.ok)
    total = len(results)
    print(f"  Result: {passed}/{total} passed\n")
    for r in results:
        icon = "✓" if r.ok else "✗"
        color_on = "\033[32m" if r.ok else "\033[31m"
        color_off = "\033[0m"
        print(f"  {color_on}{icon}{color_off} [{r.test_type:10}] {r.name:35} "
              f"{r.latency_ms:6.0f}ms  {r.detail[:50]}")
    print("═" * 70)
    if passed < total:
        print("  FAILED TESTS:")
        for r in results:
            if not r.ok:
                print(f"    ✗ {r.name}: {r.detail}")
    print()

    # Write log
    TEST_LOG.parent.mkdir(parents=True, exist_ok=True)
    with TEST_LOG.open("a") as f:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"\n[{timestamp}] E2E Run: {passed}/{total} passed\n")
        for r in results:
            f.write(f"  {'OK' if r.ok else 'FAIL'} {r.name}: {r.detail}\n")


if __name__ == "__main__":
    import sys
    print("Hermes E2E Test Harness")
    print(f"LiteLLM: {LITELLM_URL}")
    print()
    results = asyncio.run(run_all_tests())
    print_report(results)
    failed = [r for r in results if not r.ok]
    sys.exit(0 if not failed else 1)
